from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SmsMessage(Base):
    """An SMS received from the phone and pushed by the Termux sync script."""

    __tablename__ = "sms_messages"

    Id: Mapped[int] = mapped_column(primary_key=True, index=True)

    Sender: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    Message: Mapped[str] = mapped_column(Text, nullable=False)

    ReceivedAt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    CreatedAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
