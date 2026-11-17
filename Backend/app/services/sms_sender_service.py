from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sms_sender import SMSSender


class SMSSenderService:
    @staticmethod
    def list(db: Session) -> list[SMSSender]:
        return list(db.scalars(select(SMSSender).order_by(SMSSender.Name)).all())

    @staticmethod
    def create(db: Session, name: str) -> SMSSender:
        clean = name.strip()
        if not clean:
            raise ValueError("Sender name cannot be empty")
        item = db.scalar(select(SMSSender).where(func.lower(SMSSender.Name) == clean.lower()))
        if item:
            return item
        item = SMSSender(Name=clean)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def get(db: Session, sender_id: int) -> SMSSender | None:
        return db.get(SMSSender, sender_id)

    @staticmethod
    def delete(db: Session, sender: SMSSender) -> None:
        db.delete(sender)
        db.commit()
