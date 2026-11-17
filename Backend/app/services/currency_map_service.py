from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.currency_map import CurrencyMap


class CurrencyMapService:
    @staticmethod
    def list_all(db: Session) -> list[CurrencyMap]:
        return list(db.scalars(select(CurrencyMap).order_by(CurrencyMap.code)).all())

    @staticmethod
    def get(db: Session, code: str) -> CurrencyMap | None:
        return db.scalar(select(CurrencyMap).where(func.upper(CurrencyMap.code) == code.strip().upper()))

    @staticmethod
    def upsert(db: Session, code: str, name: str, aliases: list[str] | None = None) -> CurrencyMap:
        normalized = code.strip().upper()
        if len(normalized) != 3:
            raise ValueError("Currency code must be three letters")
        item = CurrencyMapService.get(db, normalized)
        if item is None:
            item = CurrencyMap(code=normalized, name=name.strip(), aliases=aliases or [])
            db.add(item)
        else:
            item.name = name.strip()
            item.aliases = aliases or []
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete(db: Session, item: CurrencyMap) -> None:
        db.delete(item)
        db.commit()
