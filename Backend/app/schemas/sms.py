from pydantic import BaseModel, Field


class SMSParseRequest(BaseModel):
    sender: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class SMSProcessResponse(BaseModel):
    scanned: int
    transactions_created: int
    duplicates: int
    already_linked: int
    not_a_transaction: int
    failed: int
