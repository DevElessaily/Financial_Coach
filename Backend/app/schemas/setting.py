from pydantic import BaseModel, ConfigDict


class SettingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str
    value: str | None = None
    description: str | None = None


class SettingUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str | None = None
    value: str | None = None
    description: str | None = None