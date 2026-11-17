
from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CategoryMapping(Base):
    __tablename__ = "category_mappings"

    Id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    AccountName: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    CategoryId: Mapped[int] = mapped_column(
        ForeignKey("categories.Id"),
        nullable=False
    )

    AlternativeCategoryIds: Mapped[list[int] | None] = mapped_column(
        JSON,
        nullable=True
    )

    Category = relationship(
        "Category",
        lazy="joined"
    )

    def HasAlternatives(self) -> bool:
        return bool(self.AlternativeCategoryIds)

    def GetAlternativeCategories(self, Db) -> list:
        if not self.AlternativeCategoryIds:
            return []

        from sqlalchemy import select
        from app.models.category import Category

        Categories = Db.scalars(
            select(Category).where(
                Category.Id.in_(self.AlternativeCategoryIds)
            )
        ).all()

        return list(Categories)
