from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.schemas import SMSCategoryOutput


class SMSCategory(BaseAgent):

    def __init__(
        self,
        default_categories: list[str] | None = None,
        category_prompt: str | None = None,
        category_prompts: dict[str, str] | None = None,
    ) -> None:

        super().__init__()

        self.default_categories = default_categories or []
        self.category_prompt = category_prompt
        self.category_prompts = category_prompts or {}

    def instructions(self) -> str:

        default_prompt = """
You are a financial transaction categorizer.

Identify the spending category based on the merchant name,
transaction description, or payment type.

Focus on the merchant/store name first.

Category mapping hints:

- Cafe: Starbucks, Dunkin, Costa, Caribou.
- Groceries: Carrefour, Panda, Lulu, supermarkets.
- Shopping: General retail and department stores.
- Dining: McDonald's, KFC, Burger King, restaurants.
- Transportation: Uber, Careem, fuel stations, parking.
- Utilities: Electricity, water, telecom bills.
- Healthcare: Pharmacies, hospitals, clinics.
- Entertainment: Netflix, Spotify, cinemas, gaming.
- Online Shopping: Amazon, Noon, Shein, AliExpress.
- Education: Schools, universities, courses.
- Travel: Airlines, hotels, car rentals.
- Personal Care: Salons, barbers, spas.
- Clothing: Zara, H&M, Nike, Adidas.
- Home & Furniture: IKEA, furniture and maintenance.
- Government: Government fees and traffic fines.
- Insurance: Car, medical and travel insurance.
- Charity: Donations and Zakah.
- Cash: ATM withdrawals.
- Transfer: Bank transfers between accounts.
"""

        prompt = self.category_prompt or default_prompt

        if "%categories_prompts%" in prompt:

            lines = [
                f"- {name}: {description}"
                for name, description in self.category_prompts.items()
            ]

            prompt = prompt.replace(
                "%categories_prompts%",
                "\n".join(lines),
            )

        preferred = ""

        if self.default_categories:
            preferred = (
                "\nPrefer these categories: "
                + ", ".join(self.default_categories)
                + ". You may suggest another category if necessary."
            )

        return prompt + preferred + """

Return:
- error: empty string if successful.
- category: best matching category.
- confidence: high, medium, or low.

Use low confidence when the merchant is unknown
or the transaction description is ambiguous.

Never invent merchant information.
"""

    async def categorize(
        self,
        merchant: str,
        description: str = "",
    ) -> SMSCategoryOutput:

        message = f"""
Merchant: {merchant}
Transaction description: {description}

Identify the most appropriate spending category.
"""

        return await self.generate(
            response_model=SMSCategoryOutput,
            user_message=message,
        )