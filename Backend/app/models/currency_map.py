
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CurrencyMap(Base):
    __tablename__ = "currency_maps"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    code: Mapped[str] = mapped_column(
        String(3),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    aliases: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False
    )
