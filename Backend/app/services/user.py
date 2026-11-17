from sqlalchemy.orm import Session

from app.models.user import User
from app.services.account_service import ensure_user, get_or_create_default_user_and_account


class UserService:
    @staticmethod
    def get_current(db: Session, user_id: int = 1) -> tuple[User, int, str]:
        if user_id == 1:
            user, account = get_or_create_default_user_and_account(db)
        else:
            user = ensure_user(db, user_id)
            account_id = 1
            currency = "EGP"
            db.commit()
            return user, account_id, currency
        db.commit()
        return user, account.Id, account.CurrencyCode or "EGP"
