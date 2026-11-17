import re


class ResolveResult:
    def __init__(self, code=None):
        self.code = code


class ResolveCurrency:
    async def resolve(self, sms_text: str):
        text = sms_text.lower()
        if "$" in text or "usd" in text or "دولار" in text:
            code = "USD"
        elif "ريال" in text or re.search(r"\bsar\b", text):
            code = "SAR"
        elif "درهم" in text or re.search(r"\baed\b", text):
            code = "AED"
        elif "€" in text or re.search(r"\beur\b", text):
            code = "EUR"
        else:
            code = "EGP"
        return ResolveResult(code=code)
