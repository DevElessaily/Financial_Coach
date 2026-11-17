from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.services.account_service import ensure_user


class AlertService:
    @staticmethod
    def list_for_user(db: Session, user_id: int) -> list[Alert]:
        return list(db.scalars(select(Alert).where(Alert.user_id == user_id).order_by(Alert.id.desc())).all())

    @staticmethod
    def create(db: Session, *, user_id: int, name: str, direction: str, threshold: Decimal, currency_code: str = "EGP") -> Alert:
        if direction not in {"income", "expense", "any"}:
            raise ValueError("direction must be income, expense, or any")
        ensure_user(db, user_id)
        alert = Alert(user_id=user_id, name=name.strip(), direction=direction, threshold=threshold, currency_code=currency_code.upper())
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def delete(db: Session, alert: Alert) -> None:
        db.delete(alert)
        db.commit()

    @staticmethod
    def check_transaction(db: Session, user_id: int, *, amount: Decimal, direction: str, currency_code: str) -> list[Alert]:
        return list(db.scalars(select(Alert).where(
            Alert.user_id == user_id,
            Alert.is_active.is_(True),
            Alert.threshold <= amount,
            Alert.currency_code == currency_code.upper(),
            Alert.direction.in_(["any", direction]),
        )).all())
