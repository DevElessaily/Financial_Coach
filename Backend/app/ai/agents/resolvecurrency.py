from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.schemas import CurrencyOutput


class ResolveCurrency(BaseAgent):

    def instructions(self) -> str:

        return """
You are a currency code resolver.

Given text representing a currency,
return its ISO 4217 three-letter currency code.

Examples:

Egyptian Pound -> EGP
جنيه -> EGP
جنيه مصري -> EGP
دولار -> USD
$ -> USD
Euro -> EUR
€ -> EUR
Pound Sterling -> GBP
£ -> GBP
ريال سعودي -> SAR
ر.س. -> SAR
درهم إماراتي -> AED
¥ -> JPY

For ambiguous currencies, use surrounding context.

If the currency cannot be determined,
return an empty string.

Never invent a currency code.
"""

    async def resolve(
        self,
        currency_text: str,
    ) -> CurrencyOutput:

        return await self.generate(
            response_model=CurrencyOutput,
            user_message=f"Resolve this currency: {currency_text}",
        )