
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PendingTransaction(Base):
    __tablename__ = "pending_transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    sms_id: Mapped[int | None] = mapped_column(
        ForeignKey("sms.id"),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_account_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_account_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    destination_account_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    destination_account_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    tags: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    budget_id: Mapped[int | None] = mapped_column(
        ForeignKey("budgets.id"),
        nullable=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Relationships
    sms = relationship("SMS", back_populates="pending_transactions")
    user = relationship("User", back_populates="pending_transactions")
