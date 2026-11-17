import json

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.schemas import RegexOutput


class GenerateRegex(BaseAgent):

    def __init__(
        self,
        sms_text: str = "",
        parsed_fields: dict | None = None,
    ) -> None:

        super().__init__()

        self.sms_text = sms_text
        self.parsed_fields = parsed_fields or {}

    def instructions(self) -> str:

        fields_json = json.dumps(
            self.parsed_fields,
            ensure_ascii=False,
            indent=4,
        )

        return f"""
You are a PHP regular expression generator
for bank SMS messages.

Original SMS:

{self.sms_text}

Extracted fields:

{fields_json}

REQUIREMENTS:

1. Use PHP PCRE regex syntax.

2. Use named groups:

   (?P<amount>...)
   (?P<currency>...)
   (?P<sourceAccountNumber>...)
   (?P<sourceAccountName>...)
   (?P<destinationAccountNumber>...)
   (?P<destinationAccountName>...)
   (?P<fees>...)
   (?P<feesCurrency>...)
   (?P<transactionDateTime>...)

3. Only include groups for fields with non-empty values.

4. Must include amount and at least one account
   or merchant identifier.

5. Match the exact SMS provided.

6. Make the regex reusable for similar SMS formats.

7. Support masked account identifiers and
   thousand-separated amounts.

8. Use /pattern/s delimiters.

9. Return an empty string if a valid regex cannot
   be generated.

Return the pattern in the regularExp field.
"""

    async def generate_regex(self) -> RegexOutput:

        return await self.generate(
            response_model=RegexOutput,
            user_message="Generate a reusable PHP regex for this SMS.",
        )