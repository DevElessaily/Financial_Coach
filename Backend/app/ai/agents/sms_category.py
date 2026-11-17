class CategoryResult:
    def __init__(self, category="Unknown", confidence=0.0):
        self.category = category
        self.confidence = confidence


class SMSCategory:
    async def categorize(self, merchant=None, description=None):
        text = f"{merchant or ''} {description or ''}".lower()
        keywords = (
            ("Bills", ("vodafone", "vf-cash", "recharge", "فاتورة", "كهرباء", "غاز", "باقة")),
            ("Food", ("restaurant", "cafe", "coffee", "food", "مطعم", "كافيه")),
            ("Transport", ("uber", "careem", "taxi", "fuel", "petrol", "بنزين", "مترو")),
            ("Shopping", ("amazon", "noon", "shop", "store", "مول")),
            ("Health", ("pharmacy", "hospital", "clinic", "صيدلية", "مستشفى")),
            ("Entertainment", ("netflix", "cinema", "spotify", "ترفيه")),
            ("Salary", ("salary", "payroll", "راتب", "مرتب")),
        )
        for category, terms in keywords:
            if any(term in text for term in terms):
                return CategoryResult(category, 0.8)
        return CategoryResult("Other", 0.4)
