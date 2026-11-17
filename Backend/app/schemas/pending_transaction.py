from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PendingTransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency_code: str = Field(default="EGP", min_length=3, max_length=3)
    transaction_type: str = Field(pattern="^(income|expense|transfer)$")
    description: str | None = None
    transaction_date: datetime | None = None
    source: str = "manual"


class PendingTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: Decimal
    currency_code: str
    transaction_type: str
    description: str | None
    transaction_date: datetime | None
    source: str
    status: str
