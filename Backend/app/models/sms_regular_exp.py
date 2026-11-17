
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SMSRegularExp(Base):
    __tablename__ = "smsregular_exps"

    __table_args__ = (
        UniqueConstraint(
            "sender_id",
            "regularExpMD5",
            name="uq_smsregular_exps_sender_regex_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("sms_senders.Id"),
        nullable=False,
        index=True,
    )

    transaction_type: Mapped[str] = mapped_column(
        "transactionType",
        String(100),
        nullable=False,
    )

    regular_exp: Mapped[str] = mapped_column(
        "regularExp",
        Text,
        nullable=False,
    )

    regular_exp_md5: Mapped[str] = mapped_column(
        "regularExpMD5",
        String(32),
        nullable=False,
    )

    created_by: Mapped[str] = mapped_column(
        "createdBy",
        String(100),
        default="system",
        nullable=False,
    )

    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    is_valid_transaction: Mapped[bool] = mapped_column(
        "is_validTransaction",
        Boolean,
        default=True,
        nullable=False,
    )

    is_valid_regular_exp: Mapped[bool] = mapped_column(
        "is_validRegularExp",
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sender = relationship(
        "SMSSender",
        back_populates="regular_expressions",
    )
