
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.keyword import Keyword


class KeywordService:

    @staticmethod
    def return_active_keywords_by_type(
        db: Session,
        keyword_type: str,
        is_regular_exp: bool = True,
        sender_id: int | None = None
    ) -> list[str]:

        query = select(Keyword.keyword).where(
            Keyword.keyword_type == keyword_type,
            Keyword.is_regular_exp == is_regular_exp,
            Keyword.is_active.is_(True)
        )

        if sender_id is not None:
            query = query.where(
                (Keyword.sender_id == sender_id) |
                (Keyword.sender_id.is_(None))
            )
        else:
            query = query.where(Keyword.sender_id.is_(None))

        return list(db.scalars(query).all())

    @staticmethod
    def return_active_replace_keywords(
        db: Session,
        is_regular_exp: bool = True,
        sender_id: int | None = None
    ) -> dict[str, str | None]:

        query = select(
            Keyword.keyword,
            Keyword.replace_with
        ).where(
            Keyword.keyword_type == "replace",
            Keyword.is_regular_exp == is_regular_exp,
            Keyword.is_active.is_(True)
        )

        if sender_id is not None:
            query = query.where(
                (Keyword.sender_id == sender_id) |
                (Keyword.sender_id.is_(None))
            )
        else:
            query = query.where(Keyword.sender_id.is_(None))

        return {
            keyword: replacement
            for keyword, replacement in db.execute(query).all()
        }

    @staticmethod
    def regex_replace_with(
        db: Session,
        sender_id: int | None = None
    ) -> dict[str, str | None]:
        return KeywordService.return_active_replace_keywords(
            db, True, sender_id
        )

    @staticmethod
    def str_replace_with(
        db: Session,
        sender_id: int | None = None
    ) -> dict[str, str | None]:
        return KeywordService.return_active_replace_keywords(
            db, False, sender_id
        )

    @staticmethod
    def regex_phone_numbers(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "phone", True, sender_id
        )

    @staticmethod
    def regex_passcodes(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "passcodes", True, sender_id
        )

    @staticmethod
    def regex_misc(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "misc", True, sender_id
        )

    @staticmethod
    def regex_date(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "date", True, sender_id
        )

    @staticmethod
    def regex_breaks(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "breaks", True, sender_id
        )

    @staticmethod
    def non_regex_breaks(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "breaks", False, sender_id
        )

    @staticmethod
    def regex_urls(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "url", True, sender_id
        )

    @staticmethod
    def regex_ignore_sms(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "ignore", True, sender_id
        )

    @staticmethod
    def str_ignore_sms(
        db: Session,
        sender_id: int | None = None
    ) -> list[str]:
        return KeywordService.return_active_keywords_by_type(
            db, "ignore", False, sender_id
        )
