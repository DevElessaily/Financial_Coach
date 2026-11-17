
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PendingCategoryReview(Base):
    __tablename__ = "pending_category_reviews"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.Id"),
        nullable=True,
        index=True
    )

    account_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    category_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("category_mappings.Id"),
        nullable=True
    )

    current_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.Id"),
        nullable=True
    )

    alternative_category_ids: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.Id"),
        nullable=False,
        index=True
    )

    budget_id: Mapped[int | None] = mapped_column(
        ForeignKey("budgets.Id"),
        nullable=True,
        index=True
    )

    transaction_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EGP"
    )

    transaction_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    transaction_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True
    )

    category_mapping = relationship("CategoryMapping")

    current_category = relationship(
        "Category",
        foreign_keys=[current_category_id]
    )
