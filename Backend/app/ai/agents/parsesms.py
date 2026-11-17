from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.schemas import SMSParseOutput


class ParseSMS(BaseAgent):

    def __init__(self, timezone: str = "Africa/Cairo") -> None:
        super().__init__()
        self.timezone = timezone

    def instructions(self) -> str:

        return f"""
You are a bank SMS transaction parser.
Extract structured financial data from bank SMS notifications.

Common SMS formats:

- POS/Card purchases:
  Purchase Amount: EGP 45.00 At: STARBUCKS
  Account: ***7632 Date: 2026-01-24 12:40

- Transfers:
  Transfer of EGP 1,000.00 from account ***1234
  to account 5678901234 on 01/15

- ATM withdrawals:
  Cash withdrawal EGP 500.00 from ATM
  Account: ***3021 Date: 2026-02-10

- Deposits:
  Salary deposit EGP 10,000.00 to account ***4567

- Bill payments:
  SADAD payment EGP 350.00 for Vodafone bill

- Multi-currency:
  Purchase USD 50.00 (EGP 2,500.00) At: AMAZON

EXTRACTION RULES:

1. Account identifiers may be masked:
   ***7632, **9010, X7001, *2398*343.

2. Amounts may contain commas:
   1,000.00 must become 1000.00.

3. Do not confuse account balance with transaction amount.

4. Extract transaction fees separately.

5. Clean merchant names by removing branch codes.

6. Transaction types:
   withdrawal, deposit, payment, transfer, unknown.

7. Identify the correct source and destination accounts.

8. Use timezone {self.timezone} when interpreting local dates.

9. Return ISO 8601 datetime with timezone offset.

10. OTP, passwords, activation codes and
    non-transactional messages must return error='Cannot parse'.

11. When parsing fails, return empty strings and zero
    numeric values for the remaining fields.

12. Never invent missing transaction information.
"""

    async def parse(self, sms_text: str) -> SMSParseOutput:

        return await self.generate(
            response_model=SMSParseOutput,
            user_message=f"Parse this bank SMS:\n{sms_text}",
        )