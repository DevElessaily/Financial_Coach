import json
import urllib.error
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency import Currency


class CurrencyService:
    API_URL = "https://api.frankfurter.dev/v1"

    @staticmethod
    def list_supported(db: Session) -> list[Currency]:
        return list(db.scalars(select(Currency).where(Currency.is_active.is_(True)).order_by(Currency.code)).all())

    @staticmethod
    def upsert(db: Session, code: str, name: str, symbol: str | None = None) -> Currency:
        normalized = code.strip().upper()
        if len(normalized) != 3:
            raise ValueError("Currency code must be three letters")
        item = db.get(Currency, normalized)
        if item is None:
            item = Currency(code=normalized, name=name.strip(), symbol=symbol)
            db.add(item)
        else:
            item.name = name.strip()
            item.symbol = symbol
            item.is_active = True
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete(db: Session, item: Currency) -> None:
        item.is_active = False
        db.commit()

    @staticmethod
    def exchange_rate(amount, from_currency, to_currency):
        try:
            amount = float(amount)

            if amount <= 0:
                return None

            from_currency = from_currency.strip().upper()
            to_currency = to_currency.strip().upper()

            if from_currency == to_currency:
                return amount

            url = (
                f"{CurrencyService.API_URL}/latest"
                f"?base={from_currency}&symbols={to_currency}"
            )

            with urllib.request.urlopen(url, timeout=10.0) as response:
                if response.status != 200:
                    return None

                data = json.loads(response.read().decode("utf-8"))

            rates = data.get("rates", {})
            rate = rates.get(to_currency)

            if rate is None:
                return None

            rate = float(rate)

            if rate <= 0:
                return None

            return amount * rate

        except (urllib.error.URLError, ValueError, TypeError, KeyError):
            return None
