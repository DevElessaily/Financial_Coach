
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.account import Account
from app.schemas.transaction import TransactionCreate


class TransactionService:

    def __init__(self, Db: Session):
        self.Db = Db

    def CreateTransaction(
        self,
        UserId: int,
        Data: TransactionCreate
    ):

        # Normalize transaction type
        TransactionType = Data.Type.lower()

        if TransactionType == "payment":
            TransactionType = "withdrawal"

        # Validate amount
        Amount = Decimal(str(Data.Amount))

        if Amount <= 0:
            raise ValueError("Invalid transaction amount")

        # Validate fees
        Fees = Decimal(str(Data.Fees or 0))

        if Fees < 0:
            raise ValueError("Invalid transaction fees")

        # Get user's account
        OwnAccount = self.Db.scalar(
            select(Account).where(
                Account.Id == Data.AccountId,
                Account.UserId == UserId
            )
        )

        if not OwnAccount:
            raise ValueError("Account not found")

        # Resolve counterparty account
        CounterpartyAccount = None

        if Data.CounterpartyAccountId:

            CounterpartyAccount = self.Db.scalar(
                select(Account).where(
                    Account.Id == Data.CounterpartyAccountId,
                    Account.UserId == UserId
                )
            )

            if not CounterpartyAccount:
                raise ValueError("Counterparty account not found")

        # Transfer validation
        if TransactionType == "transfer":

            if not CounterpartyAccount:
                raise ValueError(
                    "Transfer requires another account"
                )

            if CounterpartyAccount.Id == OwnAccount.Id:
                raise ValueError(
                    "Cannot transfer to the same account"
                )

        elif not Data.CounterpartyName and not CounterpartyAccount:
            raise ValueError("Counterparty information is required")

        # Currency validation
        AccountCurrency = OwnAccount.CurrencyCode.upper()

        TransactionCurrency = Data.CurrencyCode.upper()

        if AccountCurrency != TransactionCurrency:
            raise ValueError(
                "Transaction currency differs from account currency. "
                "Use CurrencyService for conversion."
            )

        # Calculate final amount
        TotalAmount = Amount + Fees

        # Create transaction
        NewTransaction = Transaction(

            UserId=UserId,

            AccountId=OwnAccount.Id,

            CounterpartyAccountId=(
                CounterpartyAccount.Id
                if CounterpartyAccount
                else None
            ),

            Type=TransactionType,

            Amount=TotalAmount,

            CurrencyCode=AccountCurrency,

            TransactionDate=Data.TransactionDate,

            Description=Data.Description,

            Notes=Data.Notes,

            CategoryId=Data.CategoryId,

            MerchantName=Data.CounterpartyName,

            Fees=Fees if Fees > 0 else None,

            InternalReference=Data.InternalReference,

            Source=Data.Source
        )

        self.Db.add(NewTransaction)

        self.Db.commit()

        self.Db.refresh(NewTransaction)

        return NewTransaction

    def GetUserTransactions(self, UserId: int):

        return self.Db.scalars(
            select(Transaction)
            .where(Transaction.UserId == UserId)
            .order_by(Transaction.TransactionDate.desc())
        ).all()

    def GetTransactionById(
        self,
        UserId: int,
        TransactionId: int
    ):

        return self.Db.scalar(
            select(Transaction).where(
                Transaction.Id == TransactionId,
                Transaction.UserId == UserId
            )
        )
