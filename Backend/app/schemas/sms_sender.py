from pydantic import BaseModel, ConfigDict, Field


class SMSSenderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SMSSenderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    Name: str | None
