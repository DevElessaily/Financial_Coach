
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from Backend.database.base import Base

class Account(Base):
    __tablename__ = "accounts"

    Id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    UserId: Mapped[int | None] = mapped_column(
        ForeignKey("users.Id"),
        nullable=True,
        index=True
    )

    BudgetId: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    SenderId: Mapped[int | None] = mapped_column(
        ForeignKey("sms_senders.Id"),
        nullable=True
    )

    Shortcodes: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True
    )

    FireflyAccountName: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    IBAN: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    AccountNumber: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    FireflyAccountId: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        index=True
    )

    CurrencyCode: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True
    )

    def HasShortcode(self, Shortcode: str) -> bool:
        if not isinstance(self.Shortcodes, list):
            return False

        for Entry in self.Shortcodes:
            if isinstance(Entry, str) and Entry == Shortcode:
                return True

            if (
                isinstance(Entry, dict)
                and Entry.get("shortcode") == Shortcode
            ):
                return True

        return False

    def GetBudgetForShortcode(
        self,
        Shortcode: str
    ) -> int | None:
        if isinstance(self.Shortcodes, list):
            for Entry in self.Shortcodes:
                if (
                    isinstance(Entry, dict)
                    and Entry.get("shortcode") == Shortcode
                ):
                    BudgetId = Entry.get("budget_id")

                    if BudgetId:
                        return int(BudgetId)

                    break

        return self.BudgetId

    def GetShortcodeList(self) -> list[str]:
        if not isinstance(self.Shortcodes, list):
            return []

        Result = []

        for Entry in self.Shortcodes:
            if isinstance(Entry, str):
                Result.append(Entry)
            elif isinstance(Entry, dict):
                Result.append(Entry.get("shortcode", ""))

        return Result
