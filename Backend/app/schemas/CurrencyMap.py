
from pydantic import BaseModel, Field, ConfigDict


class CurrencyMapCreate(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=100)
    aliases: list[str] = Field(default_factory=list)


class CurrencyMapResponse(BaseModel):
    id: int
    code: str
    name: str
    aliases: list[str]

    model_config = ConfigDict(from_attributes=True)


class CurrencyResolveRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100)


class CurrencyResolveResponse(BaseModel):
    text: str
    code: str | None
