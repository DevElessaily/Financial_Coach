from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class CategoryOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    translated_name: str
    enable_prompt: bool = False


class ApproveCategoryRequest(BaseModel):
    category_id: int


class PendingCategoryReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int | None = None
    account_name: str | None = None
    current_category_id: int | None = None
    current_category: CategoryOption | None = None
    alternative_category_ids: list[int] = []
    alternative_categories: list[CategoryOption] = []
    transaction_amount: Decimal
    currency_code: str
    transaction_date: datetime | None = None
    transaction_description: str | None = None
    status: str


class ReviewActionResponse(BaseModel):
    message: str
    review_id: int
    status: str
    selected_category_id: int | None = None