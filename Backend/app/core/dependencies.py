from typing import Any


class CurrentUser:
    def __init__(self, id: int = 1, budget_id: int | None = None):
        self.id = id
        self.budget_id = budget_id


def get_current_user() -> CurrentUser:
    return CurrentUser()