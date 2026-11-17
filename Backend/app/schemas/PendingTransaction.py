
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PendingTransactionCreate(BaseModel):
    sms_id: int | None = None
    reason: str = Field(min_length=1, max_length=255)
    error_message: str | None = None
    type: str | None = Field(default=None, max_length=50)
    amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    date: datetime | None = None
    description: str | None = None
    notes: str | None = None
    category_name: str | None = Field(default=None, max_length=100)
    source_account_id: int | None = None
    source_account_name: str | None = None
    destination_account_id: int | None = None
    destination_account_name: str | None = None
    tags: list[str] | None = None
    budget_id: int | None = None


class PendingTransactionUpdate(BaseModel):
    reason: str | None = Field(default=None, max_length=255)
    error_message: str | None = None
    type: str | None = Field(default=None, max_length=50)
    amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    date: datetime | None = None
    description: str | None = None
    notes: str | None = None
    category_name: str | None = Field(default=None, max_length=100)
    source_account_id: int | None = None
    source_account_name: str | None = None
    destination_account_id: int | None = None
    destination_account_name: str | None = None
    tags: list[str] | None = None
    budget_id: int | None = None


class PendingTransactionResponse(BaseModel):
    id: int
    sms_id: int | None
    reason: str | None
    error_message: str | None
    type: str | None
    amount: Decimal | None
    currency: str | None
    date: datetime | None
    description: str | None
    notes: str | None
    category_name: str | None
    source_account_id: int | None
    source_account_name: str | None
    destination_account_id: int | None
    destination_account_name: str | None
    tags: list[str] | None
    budget_id: int | None
    user_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class PendingTransactionRetryResponse(BaseModel):
    message: str
    pending_transaction_id: int
    status: str
