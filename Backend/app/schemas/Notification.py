
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationActionSchema(BaseModel):
    label: str
    action: str


class NotificationCreate(BaseModel):
    title: str
    body: str
    type: str
    data: dict[str, Any] | None = None


class NotificationResponse(BaseModel):
    id: int
    title: str
    body: str
    type: str
    is_read: bool
    data: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceTokenCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    token: str = Field(min_length=20, max_length=512)
    platform: str = Field(min_length=1, max_length=20)


class NotificationActionCreate(BaseModel):
    title: str
    body: str
    actions: list[NotificationActionSchema] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
