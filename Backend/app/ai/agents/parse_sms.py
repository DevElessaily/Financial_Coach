from dataclasses import dataclass, asdict

from app.services.sms_transaction_parser import parse_transaction_sms


@dataclass
class ParsedSMS:
    error: str | None = None
    currency: str | None = None
    destinationAccountName: str | None = None
    amount: str | None = None
    transactionType: str | None = None
    description: str | None = None
    category: str | None = None

    def model_dump(self):
        return asdict(self)


class ParseSMS:
    async def parse(self, sms_text: str) -> ParsedSMS:
        transaction = parse_transaction_sms("unknown", sms_text)
        if transaction is None:
            return ParsedSMS(error="SMS does not contain a recognized completed transaction")
        return ParsedSMS(
            currency=transaction.currency,
            destinationAccountName=transaction.merchant,
            amount=str(transaction.amount),
            transactionType=transaction.db_type,
            description=transaction.description,
            category=transaction.category,
        )
