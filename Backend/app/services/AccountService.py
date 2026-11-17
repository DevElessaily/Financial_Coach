
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.sms_sender import SMSSender


class AccountService:

    @staticmethod
    def FindBySenderAndShortcode(
        Db: Session,
        SenderName: str,
        Shortcode: str,
        GuessByIbanEnabled: bool = False,
        FallbackSenderOnlyEnabled: bool = False,
        AlwaysGuessByIban: bool = False
    ) -> dict[str, Any] | None:

        NormalizedSender = SenderName.lower().strip()

        Sender = Db.scalar(
            select(SMSSender).where(
                func.lower(SMSSender.Sender) == NormalizedSender
            )
        )

        AllAccounts = Db.scalars(
            select(Account)
        ).all()

        # Priority 1: sender + shortcode
        if Sender:
            for AccountRecord in AllAccounts:
                if (
                    AccountRecord.SenderId == Sender.Id
                    and AccountRecord.HasShortcode(Shortcode)
                ):
                    return {
                        "account": AccountRecord,
                        "match": "shortcode"
                    }

        # Priority 2: no sender assigned + shortcode
        for AccountRecord in AllAccounts:
            if (
                AccountRecord.SenderId is None
                and AccountRecord.HasShortcode(Shortcode)
            ):
                return {
                    "account": AccountRecord,
                    "match": "shortcode"
                }

        # Priority 3: match the shortcode against account suffixes
        GuessEnabled = (
            AlwaysGuessByIban or GuessByIbanEnabled
        )

        if GuessEnabled:
            CleanShortcode = re.sub(
                r"[^0-9]",
                "",
                Shortcode
            )

            if len(CleanShortcode) >= 3:
                SearchPasses = [True, False]

                for RestrictToSender in SearchPasses:
                    if RestrictToSender and not Sender:
                        continue

                    for AccountRecord in AllAccounts:
                        if (
                            RestrictToSender
                            and AccountRecord.SenderId != Sender.Id
                        ):
                            continue

                        CleanIban = re.sub(
                            r"[\s\-]",
                            "",
                            AccountRecord.IBAN or ""
                        )

                        CleanAccountNumber = re.sub(
                            r"[\s\-]",
                            "",
                            AccountRecord.AccountNumber or ""
                        )

                        if (
                            CleanIban
                            and CleanIban.endswith(CleanShortcode)
                        ):
                            return {
                                "account": AccountRecord,
                                "match": "guess"
                            }

                        if (
                            CleanAccountNumber
                            and CleanAccountNumber.endswith(
                                CleanShortcode
                            )
                        ):
                            return {
                                "account": AccountRecord,
                                "match": "guess"
                            }

        # Priority 4: sender only
        if Sender and FallbackSenderOnlyEnabled:
            for AccountRecord in AllAccounts:
                if AccountRecord.SenderId == Sender.Id:
                    return {
                        "account": AccountRecord,
                        "match": "sender_fallback"
                    }

        return None

    @staticmethod
    def GetTransactionFilter(
        Db: Session,
        UserId: int,
        BudgetId: int | None
    ) -> dict[str, Any]:

        # The original application treats user ID 1 as an admin.
        # In production, use a verified role/permission instead.
        if UserId == 1:
            return {}

        Conditions = [
            Account.UserId == UserId
        ]

        if BudgetId:
            Conditions.append(
                Account.BudgetId == BudgetId
            )

        AccountIds = Db.scalars(
            select(Account.FireflyAccountId).where(
                or_(*Conditions),
                Account.FireflyAccountId.is_not(None)
            )
        ).all()

        return (
            {"source_id": list(AccountIds)}
            if AccountIds
            else {}
        )
