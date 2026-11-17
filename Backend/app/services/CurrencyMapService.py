
from functools import lru_cache
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency_map import CurrencyMap


class CurrencyMapService:
    @staticmethod
    def lookup(text: str, db: Session) -> str | None:
        text = text.strip()

        if not text:
            return None

        upper_text = text.upper()

        # Find an exact ISO code
        if len(upper_text) == 3 and upper_text.isalpha():
            currency = db.scalar(
                select(CurrencyMap).where(
                    CurrencyMap.code == upper_text
                )
            )

            if currency:
                return currency.code

        # Search currency names and aliases
        currencies = db.scalars(
            select(CurrencyMap)
        ).all()

        for currency in currencies:
            if currency.code.upper() == upper_text:
                return currency.code

            if currency.name.casefold() == text.casefold():
                return currency.code

            for alias in currency.aliases or []:
                if alias.casefold() == text.casefold():
                    return currency.code

        return None

    @staticmethod
    def add_alias(
        code: str,
        alias: str,
        db: Session
    ) -> bool:
        code = code.strip().upper()
        alias = alias.strip()

        if not alias:
            return False

        currency = db.scalar(
            select(CurrencyMap).where(
                CurrencyMap.code == code
            )
        )

        if not currency:
            return False

        aliases = list(currency.aliases or [])

        if any(
            existing.casefold() == alias.casefold()
            for existing in aliases
        ):
            return True

        aliases.append(alias)
        currency.aliases = aliases

        db.commit()
        db.refresh(currency)

        return True

    @staticmethod
    def clear_cache() -> None:
        # Database queries are used directly in this version,
        # so there is no application-level lookup cache to clear.
        return None

    @staticmethod
    def resolve(
        text: str,
        db: Session,
        ai_resolver=None
    ) -> str | None:
        text = text.strip()

        if not text:
            return None

        # Try the database first
        code = CurrencyMapService.lookup(text, db)

        if code:
            return code

        # Optional AI fallback
        if ai_resolver is None:
            return None

        try:
            result = ai_resolver(text)

            if not isinstance(result, str):
                return None

            code = result.strip().upper()

            if (
                len(code) != 3
                or not code.isalpha()
            ):
                return None

            # Only accept codes that exist in our currency table
            currency = db.scalar(
                select(CurrencyMap).where(
                    CurrencyMap.code == code
                )
            )

            if not currency:
                return None

            CurrencyMapService.add_alias(code, text, db)

            return code

        except Exception:
            # A failed AI lookup should not crash the application
            return None
