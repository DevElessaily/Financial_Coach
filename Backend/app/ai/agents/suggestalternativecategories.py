"""Small offline category suggestions used when an SMS is ambiguous."""

from app.ai.agents.sms_category import SMSCategory


class SuggestAlternativeCategories:
    async def suggest(self, merchant: str | None, description: str | None) -> list[str]:
        result = await SMSCategory().categorize(merchant, description)
        if result.category == "Other":
            return ["Bills", "Food", "Transport", "Shopping"]
        return [result.category, "Other"]
