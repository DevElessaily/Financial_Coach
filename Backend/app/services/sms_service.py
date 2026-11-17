from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sms import SmsMessage
from app.services.sms_transaction_service import import_sms_transaction


class SMSService:
    @staticmethod
    def history(db: Session, limit: int = 100) -> list[SmsMessage]:
        limit = max(1, min(limit, 500))
        return list(db.scalars(select(SmsMessage).order_by(SmsMessage.ReceivedAt.desc(), SmsMessage.Id.desc()).limit(limit)).all())

    @staticmethod
    def process_unlinked(db: Session, limit: int = 5000) -> dict[str, int]:
        limit = max(1, min(limit, 5000))
        messages = db.scalars(select(SmsMessage).order_by(SmsMessage.Id).limit(limit)).all()
        counts = {"created": 0, "duplicate": 0, "exists": 0, "ignored": 0, "failed": 0}
        for sms in messages:
            outcome = import_sms_transaction(db, sms)
            counts[outcome] = counts.get(outcome, 0) + 1
        db.commit()
        return counts
