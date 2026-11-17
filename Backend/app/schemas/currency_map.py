from pydantic import BaseModel, ConfigDict, Field


class CurrencyMapUpsert(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=100)
    aliases: list[str] = Field(default_factory=list)


class CurrencyMapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    aliases: list[str]
