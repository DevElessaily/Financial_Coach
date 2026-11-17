from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.account_service import get_or_create_default_user_and_account
from app.services.notifications.notificationservice import NotificationService

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

# The UI speaks "income / expense / transfer"; the database stores
# Firefly-style transaction types.
_TYPE_TO_DB = {
    "income": "deposit",
    "expense": "withdrawal",
    "transfer": "transfer",
}

_DB_TO_TYPE = {
    "deposit": "income",
    "withdrawal": "expense",
    "transfer": "transfer",
}


class TransactionCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    type: Literal["income", "expense", "transfer"]
    description: str | None = Field(default=None, max_length=255)
    date: datetime | None = None


def _iso_utc(value: datetime | None) -> str | None:
    """Serialise a (possibly naive) UTC datetime so clients can localise it."""

    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_user_and_account(db: Session):
    """Make sure the single local user/account exist (no auth yet)."""

    return get_or_create_default_user_and_account(db)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreateRequest,
    db: Session = Depends(get_db),
):
    user, account = _default_user_and_account(db)

    category_name = payload.category.strip() or "Other"
    category = db.scalar(
        select(Category).where(
            func.lower(Category.Name) == category_name.lower()
        )
    )

    if category is None:
        category = Category(Name=category_name)
        db.add(category)
        db.flush()

    transaction = Transaction(
        UserId=user.Id,
        AccountId=account.Id,
        Type=_TYPE_TO_DB[payload.type],
        Amount=payload.amount,
        CurrencyCode=account.CurrencyCode or "EGP",
        TransactionDate=payload.date or datetime.now(timezone.utc),
        Description=payload.description or category_name,
        CategoryId=category.Id,
        Source="manual",
    )

    db.add(transaction)
    db.flush()
    NotificationService.notify_transaction_thresholds(
        db,
        user_id=user.Id,
        amount=transaction.Amount,
        direction=payload.type,
        currency_code=transaction.CurrencyCode,
        transaction_id=transaction.Id,
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(transaction)

    return {
        "status": "created",
        "id": transaction.Id,
        "amount": str(transaction.Amount),
        "category": category.Name,
        "type": payload.type,
        "description": transaction.Description,
        "date": _iso_utc(transaction.TransactionDate),
        "currency": transaction.CurrencyCode,
    }


@router.get("")
def list_transactions(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))

    rows = db.execute(
        select(Transaction, Category)
        .outerjoin(Category, Category.Id == Transaction.CategoryId)
        .order_by(
            Transaction.TransactionDate.desc(),
            Transaction.Id.desc(),
        )
        .limit(limit)
    ).all()

    return [
        {
            "id": transaction.Id,
            "amount": str(transaction.Amount),
            "type": _DB_TO_TYPE.get(transaction.Type, transaction.Type),
            "category": category.Name if category else "Other",
            "description": transaction.Description,
            "date": _iso_utc(transaction.TransactionDate),
            "currency": transaction.CurrencyCode,
            "source": transaction.Source,
        }
        for transaction, category in rows
    ]


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    db.delete(transaction)
    db.commit()

    return {"status": "deleted", "id": transaction_id}
