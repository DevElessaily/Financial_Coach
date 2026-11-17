from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SMSSender(Base):
    __tablename__ = "sms_senders"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    Name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    regular_expressions = relationship(
        "SMSRegularExp",
        back_populates="sender",
    )