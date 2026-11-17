
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pending_transaction import PendingTransaction
from app.schemas.pending_transaction import (
    PendingTransactionCreate,
    PendingTransactionUpdate,
)


def create_pending_transaction(
    db: Session,
    data: PendingTransactionCreate,
    user_id: int,
) -> PendingTransaction:
    pending = PendingTransaction(
        **data.model_dump(),
        user_id=user_id,
        status="pending",
    )

    try:
        db.add(pending)
        db.commit()
        db.refresh(pending)
        return pending
    except Exception:
        db.rollback()
        raise


def get_pending_transactions(
    db: Session,
    user_id: int,
) -> list[PendingTransaction]:
    statement = (
        select(PendingTransaction)
        .where(PendingTransaction.user_id == user_id)
        .order_by(PendingTransaction.id.desc())
    )
    return list(db.scalars(statement).all())


def get_pending_transaction(
    db: Session,
    pending_id: int,
    user_id: int,
) -> PendingTransaction | None:
    statement = select(PendingTransaction).where(
        PendingTransaction.id == pending_id,
        PendingTransaction.user_id == user_id,
    )
    return db.scalars(statement).first()


def update_pending_transaction(
    db: Session,
    pending: PendingTransaction,
    data: PendingTransactionUpdate,
) -> PendingTransaction:
    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(pending, field, value)

    try:
        db.commit()
        db.refresh(pending)
        return pending
    except Exception:
        db.rollback()
        raise


def request_pending_transaction_retry(
    db: Session,
    pending: PendingTransaction,
) -> PendingTransaction:
    pending.status = "retry_requested"

    try:
        db.commit()
        db.refresh(pending)
        return pending
    except Exception:
        db.rollback()
        raise


def delete_pending_transaction(
    db: Session,
    pending: PendingTransaction,
) -> None:
    try:
        db.delete(pending)
        db.commit()
    except Exception:
        db.rollback()
        raise
