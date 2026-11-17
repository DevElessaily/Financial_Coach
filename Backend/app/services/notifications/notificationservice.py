from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.services.alert_service import AlertService
from app.services.account_service import ensure_user


class NotificationService:
    @staticmethod
    def notify_transaction_thresholds(
        db: Session,
        *,
        user_id: int,
        amount,
        direction: str,
        currency_code: str,
        transaction_id: int,
    ) -> int:
        matches = AlertService.check_transaction(
            db,
            user_id,
            amount=amount,
            direction=direction,
            currency_code=currency_code,
        )
        for alert in matches:
            NotificationService.create(
                db,
                user_id=user_id,
                title=alert.name,
                body=f"A {direction} transaction of {amount} {currency_code} met this alert.",
                notification_type="alert",
                data={"alert_id": alert.id, "transaction_id": transaction_id},
                commit=False,
            )
        return len(matches)

    @staticmethod
    def list_for_user(db: Session, user_id: int, limit: int = 100) -> list[Notification]:
        return list(db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(max(1, min(limit, 200)))).all())

    @staticmethod
    def create(db: Session, *, user_id: int, title: str, body: str, notification_type: str = "info", data: dict | None = None, commit: bool = True) -> Notification:
        ensure_user(db, user_id)
        item = Notification(user_id=user_id, title=title, body=body, type=notification_type, data=data)
        db.add(item)
        if commit:
            db.commit()
            db.refresh(item)
        else:
            db.flush()
        return item

    @staticmethod
    def mark_read(db: Session, item: Notification) -> Notification:
        item.is_read = True
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def register_device(db: Session, *, user_id: int, token: str, platform: str) -> DeviceToken:
        ensure_user(db, user_id)
        item = db.scalar(select(DeviceToken).where(DeviceToken.device_token == token))
        if item is None:
            item = DeviceToken(user_id=user_id, device_token=token, platform=platform)
            db.add(item)
        else:
            item.user_id = user_id
            item.platform = platform
        db.commit()
        db.refresh(item)
        return item
