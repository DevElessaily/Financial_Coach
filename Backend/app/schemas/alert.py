from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AlertCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    direction: str = Field(default="expense", pattern="^(income|expense|any)$")
    threshold: Decimal = Field(gt=0)
    currency_code: str = Field(default="EGP", min_length=3, max_length=3)


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    direction: str
    threshold: Decimal
    currency_code: str
    is_active: bool
