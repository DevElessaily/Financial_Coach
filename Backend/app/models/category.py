
from typing import Any

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    Id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    Name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    Translations: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )

    CategoryPrompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    EnablePrompt: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    def TranslatedName(self, Locale: str = "en") -> str:
        if isinstance(self.Translations, dict):
            Translation = self.Translations.get(Locale)

            if Translation:
                return Translation

        return self.Name
