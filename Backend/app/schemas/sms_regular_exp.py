from pydantic import BaseModel, ConfigDict


class SMSRegularExpCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sender_id: int
    transaction_type: str
    regular_exp: str
    sample_message: str = ""
    ai_output: dict | None = None
    is_valid_transaction: bool = True


class SMSRegularExpUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sender_id: int | None = None
    transaction_type: str | None = None
    regular_exp: str | None = None
    is_valid_transaction: bool | None = None
    is_active: bool | None = None