
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryOption(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class PendingCategoryReviewResponse(BaseModel):
    id: int
    transaction_id: int | None
    account_name: str | None
    current_category_id: int | None
    current_category: CategoryOption | None = None
    alternative_category_ids: list[int] = Field(default_factory=list)
    alternative_categories: list[CategoryOption] = Field(
        default_factory=list
    )
    transaction_amount: Decimal
    currency_code: str
    transaction_date: datetime | None
    transaction_description: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class ApproveCategoryRequest(BaseModel):
    category_id: int = Field(gt=0)


class ReviewActionResponse(BaseModel):
    message: str
    review_id: int
    status: str
    selected_category_id: int | None = None
