# app/services/sms_sender_service.py

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.sms_sender import SMSSender
from app.schemas.sms_sender import SMSSenderCreate, SMSSenderUpdate


class SMSSenderService:

    @staticmethod
    def is_valid_sender(db: Session, sender: str) -> bool:
        """
        Check whether the sender exists and is active.
        The comparison is case-insensitive, like the Laravel method.
        """
        normalized_sender = sender.strip().lower()

        if not normalized_sender:
            return False

        existing_sender = (
            db.query(SMSSender)
            .filter(
                func.lower(SMSSender.sender) == normalized_sender,
                SMSSender.is_active.is_(True),
            )
            .first()
        )

        return existing_sender is not None

    @staticmethod
    def create_sender(
        db: Session,
        data: SMSSenderCreate,
    ) -> SMSSender:
        sender_name = data.sender.strip()

        existing_sender = (
            db.query(SMSSender)
            .filter(func.lower(SMSSender.sender) == sender_name.lower())
            .first()
        )

        if existing_sender:
            raise ValueError("This SMS sender already exists.")

        new_sender = SMSSender(
            sender=sender_name,
            is_active=data.is_active,
        )

        try:
            db.add(new_sender)
            db.commit()
            db.refresh(new_sender)
            return new_sender
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_sender(db: Session, sender_id: int) -> SMSSender | None:
        return (
            db.query(SMSSender)
            .filter(SMSSender.id == sender_id)
            .first()
        )

    @staticmethod
    def get_senders(
        db: Session,
        active_only: bool = False,
    ) -> list[SMSSender]:
        query = db.query(SMSSender)

        if active_only:
            query = query.filter(SMSSender.is_active.is_(True))

        return query.order_by(SMSSender.sender.asc()).all()

    @staticmethod
    def update_sender(
        db: Session,
        sender_id: int,
        data: SMSSenderUpdate,
    ) -> SMSSender | None:
        sender = SMSSenderService.get_sender(db, sender_id)

        if sender is None:
            return None

        updates = data.model_dump(exclude_unset=True)

        if "sender" in updates and updates["sender"] is not None:
            updates["sender"] = updates["sender"].strip()

            duplicate = (
                db.query(SMSSender)
                .filter(
                    func.lower(SMSSender.sender)
                    == updates["sender"].lower(),
                    SMSSender.id != sender_id,
                )
                .first()
            )

            if duplicate:
                raise ValueError("This SMS sender already exists.")

        for field, value in updates.items():
            setattr(sender, field, value)

        try:
            db.commit()
            db.refresh(sender)
            return sender
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete_sender(db: Session, sender_id: int) -> bool:
        sender = SMSSenderService.get_sender(db, sender_id)

        if sender is None:
            return False

        try:
            db.delete(sender)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise