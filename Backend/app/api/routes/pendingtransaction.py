from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.pending_transaction import PendingTransaction
from app.schemas.pending_transaction import PendingTransactionCreate, PendingTransactionResponse
from app.services.pending_transaction_service import PendingTransactionService
from app.services.account_service import ensure_user

router = APIRouter(prefix="/api/pending-transactions", tags=["Pending Transactions"])


@router.get("", response_model=list[PendingTransactionResponse])
def list_pending(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return PendingTransactionService.list_pending(db, user.id)


@router.post("", response_model=PendingTransactionResponse, status_code=201)
def create_pending(payload: PendingTransactionCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    ensure_user(db, user.id)
    item = PendingTransaction(
        user_id=user.id,
        amount=payload.amount,
        currency_code=payload.currency_code.upper(),
        transaction_type=payload.transaction_type,
        description=payload.description,
        transaction_date=payload.transaction_date,
        source=payload.source,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/{decision}", response_model=PendingTransactionResponse)
def resolve_pending(item_id: int, decision: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=404, detail="Decision must be approve or reject")
    item = PendingTransactionService.get(db, user.id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pending transaction not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Transaction already resolved")
    try:
        if decision == "approve":
            from app.models.category import Category
            from app.models.transaction import Transaction
            from app.services.account_service import get_or_create_default_user_and_account
            from sqlalchemy import func

            account_user, account = get_or_create_default_user_and_account(db)
            category_name = "Other"
            category = db.scalar(select(Category).where(func.lower(Category.Name) == category_name.lower()))
            if category is None:
                category = Category(Name=category_name[:100])
                db.add(category)
                db.flush()
            direction = {"income": "deposit", "expense": "withdrawal", "transfer": "transfer"}[item.transaction_type]
            db.add(Transaction(
                UserId=account_user.Id, AccountId=account.Id, Type=direction,
                Amount=item.amount, CurrencyCode=item.currency_code,
                TransactionDate=item.transaction_date or datetime.now(timezone.utc), Description=item.description,
                CategoryId=category.Id, Source=item.source,
            ))
        return PendingTransactionService.resolve(db, item, "approved" if decision == "approve" else "rejected")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
