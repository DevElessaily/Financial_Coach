
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):

    Type: Literal["withdrawal", "deposit", "payment", "transfer"]

    Amount: Decimal = Field(gt=0)

    CurrencyCode: str = Field(
        min_length=3,
        max_length=3
    )

    TransactionDate: datetime

    AccountId: int

    CounterpartyAccountId: int | None = None

    CounterpartyName: str | None = None

    Description: str | None = None

    Notes: str | None = None

    CategoryId: int | None = None

    Fees: Decimal | None = Field(default=None, ge=0)

    InternalReference: str | None = None

    Source: str = "manual"

    @field_validator("CurrencyCode")
    @classmethod
    def ValidateCurrency(cls, value):
        return value.strip().upper()


class TransactionUpdate(BaseModel):

    Type: Literal["withdrawal", "deposit", "payment", "transfer"] | None = None

    Amount: Decimal | None = Field(default=None, gt=0)

    CurrencyCode: str | None = None

    TransactionDate: datetime | None = None

    Description: str | None = None

    Notes: str | None = None

    CategoryId: int | None = None


class TransactionResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    Id: int
    UserId: int
    AccountId: int
    CounterpartyAccountId: int | None

    Type: str
    Amount: Decimal
    CurrencyCode: str

    TransactionDate: datetime

    Description: str | None
    Notes: str | None

    CategoryId: int | None
    MerchantName: str | None

    Fees: Decimal | None
    Source: str
