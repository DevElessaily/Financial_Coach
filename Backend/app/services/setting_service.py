from time import monotonic

from sqlalchemy.orm import Session

from app.models.setting import Setting
from app.schemas.setting import SettingCreate, SettingUpdate


class SettingService:
    CACHE_TTL_SECONDS = 3600

    # Cache entries: key -> (value, expiration time)
    _cache: dict[str, tuple[str | None, float]] = {}

    @classmethod
    def _invalidate_cache(cls, key: str) -> None:
        cls._cache.pop(key, None)

    @classmethod
    def get(
        cls,
        db: Session,
        key: str,
        default: str | None = None,
    ) -> str | None:
        cached = cls._cache.get(key)
        now = monotonic()

        if cached is not None:
            cached_value, expires_at = cached

            if now < expires_at:
                return cached_value if cached_value is not None else default

            cls._invalidate_cache(key)

        setting = (
            db.query(Setting)
            .filter(Setting.key == key)
            .first()
        )

        value = setting.value if setting else None

        cls._cache[key] = (
            value,
            now + cls.CACHE_TTL_SECONDS,
        )

        return value if value is not None else default

    @classmethod
    def get_bool(
        cls,
        db: Session,
        key: str,
        default: bool = False,
    ) -> bool:
        value = cls.get(db, key)

        if value is None:
            return default

        normalized = value.strip().lower()

        # Matches the common true/false values accepted by PHP's
        # FILTER_VALIDATE_BOOLEAN.
        if normalized in {"1", "true", "on", "yes"}:
            return True

        return False

    @classmethod
    def get_int(
        cls,
        db: Session,
        key: str,
        default: int = 0,
    ) -> int:
        value = cls.get(db, key)

        if value is None:
            return default

        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            # PHP's (int) cast converts a non-numeric string to 0.
            return 0

    @classmethod
    def set(
        cls,
        db: Session,
        key: str,
        value: str | None,
        description: str | None = None,
    ) -> Setting:
        setting = (
            db.query(Setting)
            .filter(Setting.key == key)
            .first()
        )

        if setting is None:
            setting = Setting(
                key=key,
                value=value,
                description=description,
            )
            db.add(setting)
        else:
            setting.value = value

            # Match Laravel's array_filter behavior: don't replace
            # the description when None is passed.
            if description is not None:
                setting.description = description

        try:
            db.commit()
            db.refresh(setting)
            cls._invalidate_cache(key)
            return setting
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create(
        db: Session,
        data: SettingCreate,
    ) -> Setting:
        existing = (
            db.query(Setting)
            .filter(Setting.key == data.key)
            .first()
        )

        if existing:
            raise ValueError("This setting key already exists.")

        setting = Setting(
            key=data.key,
            value=data.value,
            description=data.description,
        )

        try:
            db.add(setting)
            db.commit()
            db.refresh(setting)
            SettingService._invalidate_cache(setting.key)
            return setting
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_key(db: Session, key: str) -> Setting | None:
        return (
            db.query(Setting)
            .filter(Setting.key == key)
            .first()
        )

    @staticmethod
    def get_all(db: Session) -> list[Setting]:
        return db.query(Setting).order_by(Setting.key.asc()).all()

    @classmethod
    def update(
        cls,
        db: Session,
        key: str,
        data: SettingUpdate,
    ) -> Setting | None:
        setting = cls.get_by_key(db, key)

        if setting is None:
            return None

        updates = data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(setting, field, value)

        try:
            db.commit()
            db.refresh(setting)
            cls._invalidate_cache(key)
            return setting
        except Exception:
            db.rollback()
            raise

    @classmethod
    def delete(cls, db: Session, key: str) -> bool:
        setting = cls.get_by_key(db, key)

        if setting is None:
            return False

        try:
            db.delete(setting)
            db.commit()
            cls._invalidate_cache(key)
            return True
        except Exception:
            db.rollback()
            raise