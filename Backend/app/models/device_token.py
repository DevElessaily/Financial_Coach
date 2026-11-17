
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.Id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    device_token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False
    )

    platform: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="device_tokens"
    )
