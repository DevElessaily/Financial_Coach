from app.ai.agents.parse_sms import ParseSMS
from app.ai.agents.resolve_currency import ResolveCurrency
from app.ai.agents.sms_category import SMSCategory


class SMSAIService:

    def __init__(self) -> None:

        self.parser = ParseSMS()
        self.currency_resolver = ResolveCurrency()

    async def process_sms(
        self,
        sms_text: str,
    ) -> dict:

        # Step 1: Extract transaction information
        parsed = await self.parser.parse(sms_text)

        if parsed.error:
            return {
                "success": False,
                "message": "SMS is not a valid transaction.",
                "transaction": None,
            }

        # Step 2: Resolve currency if missing
        if not parsed.currency:
            currency_result = await self.currency_resolver.resolve(
                sms_text
            )

            parsed.currency = currency_result.code

        # Step 3: Categorize the transaction
        category_agent = SMSCategory()

        category_result = await category_agent.categorize(
            merchant=parsed.destinationAccountName,
            description=parsed.category or sms_text,
        )

        # Step 4: Return structured transaction
        return {
            "success": True,
            "transaction": parsed.model_dump(),
            "category": parsed.category or category_result.category,
            "confidence": 0.9 if parsed.category else category_result.confidence,
        }
