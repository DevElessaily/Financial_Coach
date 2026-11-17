
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.user import User


class AlertService:

    @staticmethod
    def CreateAlert(
        Db: Session,
        Title: str,
        Message: str,
        UserRecord: User,
        TransactionJournalId: int | None = None,
        Data: dict[str, Any] | None = None,
        Pin: bool = False,
        Topic: str | None = None
    ) -> Alert:

        NewAlert = Alert(
            UserId=UserRecord.Id,
            TransactionJournalId=TransactionJournalId,
            Title=Title,
            Message=Message,
            Data=Data,
            IsRead=False,
            IsPinned=Pin,
            Topic=Topic
        )

        Db.add(NewAlert)
        Db.commit()
        Db.refresh(NewAlert)

        # Push notification delivery is a separate operation.
        # Connect an FCM or background-queue service here later.

        return NewAlert

    @staticmethod
    def NewTransaction(
        Db: Session,
        TransactionData: Any,
        UserRecord: User
    ) -> Alert:

        Amount = Decimal(str(TransactionData.amount))
        AmountText = f"{Amount:,.2f}"

        if AmountText.endswith(".00"):
            AmountText = AmountText[:-3]

        Currency = getattr(
            TransactionData,
            "currency_symbol",
            None
        ) or ""

        TransactionType = getattr(
            TransactionData,
            "type",
            ""
        )

        # Basic English labels; localization can be added later.
        if TransactionType == "withdrawal":
            TypeText = "Spent"
        elif TransactionType == "deposit":
            TypeText = "Received"
        elif TransactionType == "transfer":
            TypeText = "Transferred"
        else:
            TypeText = "Processed"

        Title = f"{TypeText} {AmountText} {Currency}".strip()
        MessageParts = [Title]

        DestinationName = getattr(
            TransactionData,
            "destination_name",
            None
        )

        CategoryName = getattr(
            TransactionData,
            "category_name",
            None
        )

        SourceName = getattr(
            TransactionData,
            "source_name",
            None
        )

        if DestinationName:
            MessageParts.append(DestinationName)

        if CategoryName:
            MessageParts.append(CategoryName)

        if SourceName:
            MessageParts.append(SourceName)

        TransactionId = getattr(
            TransactionData,
            "transaction_journal_id",
            None
        )

        return AlertService.CreateAlert(
            Db=Db,
            Title=Title,
            Message="\n".join(MessageParts),
            UserRecord=UserRecord,
            TransactionJournalId=TransactionId,
            Data={
                "transaction_id": TransactionId
            },
            Topic="transaction"
        )

    @staticmethod
    def AbnormalTransaction(
        Db: Session,
        UserId: int,
        TransactionJournalId: int | None,
        Amount: Decimal,
        AverageAmount: Decimal,
        DifferencePercentage: Decimal
    ) -> Alert | None:

        UserRecord = Db.scalar(
            select(User).where(User.Id == UserId)
        )

        if UserRecord is None:
            return None

        Title = "Unusual transaction detected"

        Message = (
            f"Transaction amount: {Amount:,.2f}\n"
            f"Average amount: {AverageAmount:,.2f}\n"
            f"Difference: {DifferencePercentage:,.2f}%"
        )

        return AlertService.CreateAlert(
            Db=Db,
            Title=Title,
            Message=Message,
            UserRecord=UserRecord,
            TransactionJournalId=TransactionJournalId,
            Data={
                "amount": str(Amount),
                "average_amount": str(AverageAmount),
                "difference_percentage": str(
                    DifferencePercentage
                )
            },
            Pin=True,
            Topic="abnormal"
        )

    @staticmethod
    def CreateAlertWithAdminCopy(
        Db: Session,
        Title: str,
        Message: str,
        UserId: int,
        TransactionJournalId: int | None = None,
        Data: dict[str, Any] | None = None,
        Pin: bool = False,
        Topic: str | None = None
    ) -> Alert | None:

        UserRecord = Db.scalar(
            select(User).where(User.Id == UserId)
        )

        if UserRecord is None:
            return None

        # Create the user's alert first.
        UserAlert = AlertService.CreateAlert(
            Db=Db,
            Title=Title,
            Message=Message,
            UserRecord=UserRecord,
            TransactionJournalId=TransactionJournalId,
            Data=Data,
            Pin=Pin,
            Topic=Topic
        )

        # Preserve the original behavior: admin has ID 1.
        if UserId != 1:
            Admin = Db.scalar(
                select(User).where(User.Id == 1)
            )

            if Admin:
                AlertService.CreateAlert(
                    Db=Db,
                    Title=Title,
                    Message=Message,
                    UserRecord=Admin,
                    TransactionJournalId=TransactionJournalId,
                    Data=Data,
                    Pin=Pin,
                    Topic=Topic
                )

        return UserAlert
