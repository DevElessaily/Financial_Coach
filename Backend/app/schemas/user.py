from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    budget_id: int | None = None
    account_id: int
    currency_code: str
