from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.user import User


def ensure_user(db: Session, user_id: int = 1) -> User:
    user = db.get(User, user_id)
    if user is None:
        user = User(Id=user_id)
        db.add(user)
        db.flush()
    return user


def get_or_create_default_user_and_account(
    db: Session,
) -> tuple[User, Account]:
    """Return the single local user/account, creating them on first use.

    The app has no authentication yet, so every transaction belongs to user 1
    and account 1 (EGP).
    """

    user = ensure_user(db, 1)

    account = db.get(Account, 1)
    if account is None:
        account = Account(
            Id=1,
            UserId=user.Id,
            CurrencyCode="EGP",
        )
        db.add(account)
        db.flush()

    return user, account
