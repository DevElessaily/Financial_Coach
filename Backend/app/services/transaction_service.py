from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class TransactionService:
    @staticmethod
    def get(db: Session, transaction_id: int) -> Transaction | None:
        return db.get(Transaction, transaction_id)

    @staticmethod
    def list(db: Session, limit: int = 50) -> list[Transaction]:
        limit = max(1, min(limit, 200))
        return list(db.scalars(select(Transaction).order_by(Transaction.TransactionDate.desc(), Transaction.Id.desc()).limit(limit)).all())

    @staticmethod
    def delete(db: Session, transaction: Transaction) -> None:
        db.delete(transaction)
        db.commit()
