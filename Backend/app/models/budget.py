from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Budget(Base):
    __tablename__ = "budgets"

    Id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    Name: Mapped[str | None] = mapped_column(String(255), nullable=True)