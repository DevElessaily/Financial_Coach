from pydantic import BaseModel, Field, ConfigDict


class AgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SMSParseOutput(AgentOutput):
    error: str = Field(description="Empty string for success, Cannot parse for failure.")
    transactionType: str = Field(
        description="withdrawal, deposit, payment, transfer, or unknown"
    )
    amount: float = Field(description="Transaction amount.")
    currency: str = Field(description="Three-letter ISO currency code or empty string.")
    totalAmount: float = Field(description="Explicit total transaction amount, otherwise 0.")
    totalAmountCurrency: str = Field(description="Total amount currency or empty string.")
    fees: float = Field(description="Transaction fees, otherwise 0.")
    feesCurrency: str = Field(description="Fees currency or empty string.")
    transactionDateTime: str = Field(description="ISO 8601 datetime or empty string.")
    sourceAccountNumber: str = Field(description="Source account identifier.")
    sourceAccountName: str = Field(description="Source account holder or sender.")
    destinationAccountNumber: str = Field(description="Destination account identifier.")
    destinationAccountName: str = Field(description="Merchant or beneficiary name.")


class SMSCategoryOutput(AgentOutput):
    error: str = Field(description="Empty string for success, Cannot parse for failure.")
    category: str = Field(description="Transaction category.")
    confidence: str = Field(description="high, medium, or low.")


class CurrencyOutput(AgentOutput):
    code: str = Field(description="ISO 4217 three-letter currency code or empty string.")


class RegexOutput(AgentOutput):
    regularExp: str = Field(description="PHP PCRE regex with named groups, or empty string.")


class AlternativeCategoriesOutput(AgentOutput):
    categories: str = Field(
        description="Comma-separated list of zero to four alternative categories."
    )