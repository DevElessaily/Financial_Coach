
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Numeric,
    ForeignKey,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    Id: Mapped[int] = mapped_column(primary_key=True, index=True)

    UserId: Mapped[int] = mapped_column(
        ForeignKey("users.Id"),
        nullable=False,
        index=True
    )

    AccountId: Mapped[int] = mapped_column(
        ForeignKey("accounts.Id"),
        nullable=False
    )

    CounterpartyAccountId: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.Id"),
        nullable=True
    )

    Type: Mapped[str] = mapped_column(String(20), nullable=False)

    Amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    CurrencyCode: Mapped[str] = mapped_column(
        String(3),
        nullable=False
    )

    ForeignAmount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True
    )

    ForeignCurrencyCode: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True
    )

    TransactionDate: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    Description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    Notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    CategoryId: Mapped[int | None] = mapped_column(
        ForeignKey("categories.Id"),
        nullable=True
    )

    MerchantName: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    Fees: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True
    )

    InternalReference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    Source: Mapped[str] = mapped_column(
        String(30),
        default="manual",
        nullable=False
    )

    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    Account = relationship(
        "Account",
        foreign_keys=[AccountId]
    )

    CounterpartyAccount = relationship(
        "Account",
        foreign_keys=[CounterpartyAccountId]
    )
