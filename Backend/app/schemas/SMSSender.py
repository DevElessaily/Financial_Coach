# app/schemas/sms_sender.py

from pydantic import BaseModel, ConfigDict, Field


class SMSSenderCreate(BaseModel):
    sender: str = Field(min_length=1, max_length=255)
    is_active: bool = True


class SMSSenderUpdate(BaseModel):
    sender: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class SMSSenderResponse(BaseModel):
    id: int
    sender: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SMSSenderValidationResponse(BaseModel):
    sender: str
    is_valid: bool