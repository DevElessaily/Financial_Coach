
from pydantic import BaseModel, Field, ConfigDict


class CurrencyConversionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: float = Field(gt=0)
    from_currency: str = Field(min_length=3, max_length=3)
    to_currency: str = Field(min_length=3, max_length=3)


class CurrencyConversionResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    exchange_rate: float
    converted_amount: float


class CurrencyUpsert(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=100)
    symbol: str | None = Field(default=None, max_length=10)


class CurrencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    symbol: str | None
    is_active: bool
