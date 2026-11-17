# app/models/sms_sender.py

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class SMSSender(Base):
    __tablename__ = "smssenders"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String(255), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # One SMS sender can have multiple regular expressions.
    regular_expressions = relationship(
        "SMSRegularExp",
        back_populates="sender",
        cascade="all, delete-orphan",
    )