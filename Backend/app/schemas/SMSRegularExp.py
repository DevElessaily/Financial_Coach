
from pydantic import BaseModel, ConfigDict, Field


class SMSRegularExpCreate(BaseModel):
    sender_id: int = Field(gt=0)
    transaction_type: str = Field(min_length=1, max_length=100)
    regular_exp: str = Field(min_length=1)
    sample_message: str = Field(min_length=1)
    ai_output: dict | list | str | None = None
    is_valid_transaction: bool = True


class SMSRegularExpUpdate(BaseModel):
    transaction_type: str | None = Field(default=None, max_length=100)
    regular_exp: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    is_valid_transaction: bool | None = None


class SMSRegularExpResponse(BaseModel):
    id: int
    sender_id: int
    transaction_type: str
    regular_exp: str
    regular_exp_md5: str
    created_by: str
    data: dict | None
    is_active: bool
    is_valid_transaction: bool
    is_valid_regular_exp: bool

    model_config = ConfigDict(from_attributes=True)


class SMSRegularExpMatchResponse(BaseModel):
    id: int
    sender_id: int
    transaction_type: str
    matches: dict[str, str | None]


class SMSRegularExpTestRequest(BaseModel):
    sender_id: int = Field(gt=0)
    message: str = Field(min_length=1)
    is_valid_transaction: bool = True


class SMSRegularExpTestResponse(BaseModel):
    matched: bool
    result: SMSRegularExpMatchResponse | None = None
