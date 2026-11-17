"""Create transactions from stored SMS.

Every SMS that arrives through ``/api/sms/filter`` or ``/api/sms/bulk`` is
parsed once. When it describes a completed money movement a ``Transaction``
row is created with ``Source="sms"`` and ``InternalReference="sms:<id>"`` so
the same message can never be imported twice.

The same message is often confirmed by several senders (Vodafone and
Vodafone Cash both report a 30 EGP airtime purchase). A second SMS is treated
as a duplicate when amount, type and category match an SMS-sourced
transaction from the last 30 minutes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.sms import SmsMessage
from app.models.transaction import Transaction
from app.services.account_service import get_or_create_default_user_and_account
from app.services.sms_transaction_parser import parse_transaction_sms
from app.services.notifications.notificationservice import NotificationService

logger = logging.getLogger(__name__)

DEDUPE_WINDOW = timedelta(minutes=30)

CREATED = "created"
DUPLICATE = "duplicate"
EXISTS = "exists"
IGNORED = "ignored"
FAILED = "failed"


def _get_or_create_category(db: Session, name: str) -> Category:
    category = db.scalar(
        select(Category).where(func.lower(Category.Name) == name.lower())
    )

    if category is None:
        category = Category(Name=name)
        db.add(category)
        db.flush()

    return category


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def import_sms_transaction(db: Session, sms: SmsMessage) -> str:
    """Create a transaction for one SMS and return the outcome.

    Outcomes: ``created``, ``duplicate``, ``exists``, ``ignored`` or
    ``failed``. Callers must not let a parsing problem block SMS storage, so
    this function never raises.
    """

    try:
        reference = f"sms:{sms.Id}"

        already_linked = db.scalar(
            select(Transaction).where(
                Transaction.InternalReference == reference
            )
        )
        if already_linked is not None:
            return EXISTS

        parsed = parse_transaction_sms(sms.Sender, sms.Message)
        if parsed is None:
            return IGNORED

        user, account = get_or_create_default_user_and_account(db)
        category = _get_or_create_category(db, parsed.category)
        occurred_at = _as_utc(sms.ReceivedAt)

        duplicate = db.scalar(
            select(Transaction).where(
                Transaction.Source == "sms",
                Transaction.Type == parsed.db_type,
                Transaction.Amount == parsed.amount,
                Transaction.CategoryId == category.Id,
                Transaction.TransactionDate >= occurred_at - DEDUPE_WINDOW,
                Transaction.TransactionDate <= occurred_at + DEDUPE_WINDOW,
            )
        )
        if duplicate is not None:
            logger.debug(
                "SMS %s looks like an existing %s %s transaction",
                sms.Id,
                parsed.db_type,
                parsed.amount,
            )
            return DUPLICATE

        # A savepoint keeps a failed import from rolling back the SMS row
        # that was just flushed by the caller.
        with db.begin_nested():
            transaction = Transaction(
                UserId=user.Id,
                AccountId=account.Id,
                Type=parsed.db_type,
                Amount=parsed.amount,
                CurrencyCode=parsed.currency or account.CurrencyCode or "EGP",
                TransactionDate=occurred_at,
                Description=parsed.description,
                CategoryId=category.Id,
                MerchantName=parsed.merchant,
                InternalReference=reference,
                Source="sms",
            )
            db.add(transaction)
            db.flush()

        NotificationService.notify_transaction_thresholds(
            db,
            user_id=user.Id,
            amount=transaction.Amount,
            direction="expense" if parsed.db_type == "withdrawal" else "income",
            currency_code=transaction.CurrencyCode,
            transaction_id=transaction.Id,
        )

        logger.info(
            "SMS %s -> transaction %s (%s %s %s)",
            sms.Id,
            transaction.Id,
            parsed.db_type,
            parsed.amount,
            parsed.currency,
        )
        return CREATED

    except Exception:  # noqa: BLE001 - SMS storage must keep working
        logger.exception("Could not turn SMS %s into a transaction", sms.Id)
        return FAILED
