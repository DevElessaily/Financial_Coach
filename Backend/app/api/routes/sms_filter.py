from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.models.sms import SmsMessage
from app.models.transaction import Transaction
from app.services.sms_transaction_service import import_sms_transaction


class SmsFilterRequest(BaseModel):
    sender: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    # Epoch seconds (Termux script and the Flutter app both send this).
    date: int | None = None


class SmsBulkRequest(BaseModel):
    items: list[SmsFilterRequest] = Field(default_factory=list, max_length=5000)


router = APIRouter(prefix="/api/sms", tags=["SMS"])


def _iso_utc(value: datetime | None) -> str | None:
    """Serialise a (possibly naive) UTC datetime so clients can localise it."""

    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _received_at(epoch_seconds: int | None) -> datetime:
    if epoch_seconds is None:
        return datetime.now(timezone.utc)

    # Some clients send milliseconds by mistake; normalise to seconds.
    if epoch_seconds > 10_000_000_000:
        epoch_seconds = epoch_seconds // 1000

    try:
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return datetime.now(timezone.utc)


def _store_sms(
    db: Session,
    payload: SmsFilterRequest,
) -> tuple[SmsMessage, bool, str]:
    """Insert an SMS unless the exact same message is already stored.

    Also tries to turn it into a transaction. The third return value is the
    import outcome (``created``, ``duplicate``, ``exists``, ``ignored``...).
    """

    received_at = _received_at(payload.date)

    existing = db.scalar(
        select(SmsMessage).where(
            SmsMessage.Sender == payload.sender,
            SmsMessage.Message == payload.message,
            SmsMessage.ReceivedAt == received_at,
        )
    )

    if existing is not None:
        # Re-syncing old messages also backfills transactions that were
        # missed before SMS processing existed.
        return existing, False, import_sms_transaction(db, existing)

    sms = SmsMessage(
        Sender=payload.sender,
        Message=payload.message,
        ReceivedAt=received_at,
    )
    db.add(sms)
    db.flush()

    return sms, True, import_sms_transaction(db, sms)


def _transaction_for(db: Session, sms: SmsMessage) -> Transaction | None:
    return db.scalar(
        select(Transaction).where(
            Transaction.InternalReference == f"sms:{sms.Id}"
        )
    )


def _transaction_summary(
    db: Session,
    transaction: Transaction | None,
) -> dict | None:
    if transaction is None:
        return None

    category = (
        db.get(Category, transaction.CategoryId)
        if transaction.CategoryId
        else None
    )

    return {
        "id": transaction.Id,
        "amount": str(transaction.Amount),
        "currency": transaction.CurrencyCode,
        "category": category.Name if category else "Other",
        "type": transaction.Type,
    }


@router.post("/filter")
def filter_sms(
    payload: SmsFilterRequest,
    db: Session = Depends(get_db),
):
    sms, created, outcome = _store_sms(db, payload)
    db.commit()
    db.refresh(sms)

    transaction = _transaction_for(db, sms) if outcome == "created" else None

    return {
        "status": "received" if created else "duplicate",
        "id": sms.Id,
        "sender": sms.Sender,
        "length": len(sms.Message),
        "received_at": _iso_utc(sms.ReceivedAt),
        "transaction_created": outcome == "created",
        "transaction": _transaction_summary(db, transaction),
    }


@router.post("/bulk")
def bulk_sms(
    payload: SmsBulkRequest,
    db: Session = Depends(get_db),
):
    stored = 0
    skipped = 0
    created = 0

    for item in payload.items:
        _, is_new, outcome = _store_sms(db, item)
        if is_new:
            stored += 1
        else:
            skipped += 1
        if outcome == "created":
            created += 1

    db.commit()

    return {
        "status": "received",
        "total": len(payload.items),
        "stored": stored,
        "skipped": skipped,
        "transactions_created": created,
    }


@router.post("/process")
def process_stored_sms(
    limit: int = 5000,
    db: Session = Depends(get_db),
):
    """Parse SMS that were stored before automatic processing existed."""

    limit = max(1, min(limit, 5000))

    messages = db.scalars(
        select(SmsMessage).order_by(SmsMessage.Id).limit(limit)
    ).all()

    counts = {"created": 0, "duplicate": 0, "exists": 0, "ignored": 0, "failed": 0}

    for sms in messages:
        outcome = import_sms_transaction(db, sms)
        counts[outcome] = counts.get(outcome, 0) + 1

    db.commit()

    return {
        "scanned": len(messages),
        "transactions_created": counts["created"],
        "duplicates": counts["duplicate"],
        "already_linked": counts["exists"],
        "not_a_transaction": counts["ignored"],
        "failed": counts["failed"],
    }


@router.get("/history")
def sms_history(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))

    messages = db.scalars(
        select(SmsMessage)
        .order_by(SmsMessage.ReceivedAt.desc(), SmsMessage.Id.desc())
        .limit(limit)
    ).all()

    references = [f"sms:{sms.Id}" for sms in messages]

    transactions: dict[str, tuple[Transaction, str]] = {}
    if references:
        rows = db.execute(
            select(Transaction, Category)
            .outerjoin(Category, Category.Id == Transaction.CategoryId)
            .where(Transaction.InternalReference.in_(references))
        ).all()

        for transaction, category in rows:
            transactions[transaction.InternalReference] = (
                transaction,
                category.Name if category else "Other",
            )

    result = []
    for sms in messages:
        linked = transactions.get(f"sms:{sms.Id}")

        result.append(
            {
                "id": sms.Id,
                "sender": sms.Sender,
                "message": sms.Message,
                "received_at": _iso_utc(sms.ReceivedAt),
                "transaction_id": linked[0].Id if linked else None,
                "transaction_amount": (
                    str(linked[0].Amount) if linked else None
                ),
                "transaction_currency": (
                    linked[0].CurrencyCode if linked else None
                ),
                "transaction_category": linked[1] if linked else None,
            }
        )

    return result
