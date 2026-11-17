from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pending_transaction import PendingTransaction


class PendingTransactionService:
    @staticmethod
    def list_pending(db: Session, user_id: int) -> list[PendingTransaction]:
        return list(db.scalars(select(PendingTransaction).where(
            PendingTransaction.user_id == user_id,
            PendingTransaction.status == "pending",
        ).order_by(PendingTransaction.id.desc())).all())

    @staticmethod
    def get(db: Session, user_id: int, item_id: int) -> PendingTransaction | None:
        return db.scalar(select(PendingTransaction).where(
            PendingTransaction.id == item_id,
            PendingTransaction.user_id == user_id,
        ))

    @staticmethod
    def resolve(db: Session, item: PendingTransaction, status: str) -> PendingTransaction:
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        item.status = status
        db.commit()
        db.refresh(item)
        return item
