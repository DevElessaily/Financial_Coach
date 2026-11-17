
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    Id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    UserId: Mapped[int] = mapped_column(
        ForeignKey("users.Id"),
        nullable=False,
        index=True
    )

    TransactionJournalId: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    Title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    Message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    Data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )

    IsRead: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    IsPinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    NotifiedAt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    Topic: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )

    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    User = relationship("User", lazy="joined")
