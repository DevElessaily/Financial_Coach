
import hashlib
import logging
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sms import SMS
from app.services.keyword_service import KeywordService

logger = logging.getLogger(__name__)


class SMSService:

    @staticmethod
    def is_duplicate(db: Session, sender: str, message: str) -> bool:
        message_hash = SMS.generate_hash(sender, message)

        statement = select(SMS.id).where(SMS.message_hash == message_hash)
        return db.scalar(statement) is not None

    @staticmethod
    def remove_hidden_chars(message: str) -> str:
        # Remove invisible Unicode formatting/control characters,
        # while preserving normal whitespace.
        cleaned = []

        for character in message:
            category = unicodedata.category(character)

            if category == "Cf":
                continue

            if category == "Cc" and character not in "\n\r\t":
                continue

            cleaned.append(character)

        return "".join(cleaned)

    @staticmethod
    def _replace_patterns(message: str, patterns: dict) -> str:
        for pattern, replacement in patterns.items():
            try:
                message = re.sub(
                    pattern,
                    replacement or "",
                    message,
                )
            except re.error:
                logger.warning("Invalid keyword regex: %s", pattern)

        return message

    @staticmethod
    def _remove_patterns(message: str, patterns: list) -> str:
        for pattern in patterns:
            try:
                message = re.sub(pattern, "", message)
            except re.error:
                logger.warning("Invalid keyword regex: %s", pattern)

        return message

    @staticmethod
    def pre_clean(
        db: Session,
        message: str,
        sender_id: int | None = None,
    ) -> str:
        message = SMSService.remove_hidden_chars(message)

        # Normalize Arabic-Indic digits.
        arabic_digits = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩",
            "0123456789",
        )
        message = message.translate(arabic_digits)

        # Apply keyword replacements.
        message = SMSService._replace_patterns(
            message,
            KeywordService.regex_replace_with(db, sender_id),
        )

        for old_text, replacement in (
            KeywordService.str_replace_with(db, sender_id).items()
        ):
            if old_text:
                message = message.replace(old_text, replacement or "")

        # Remove known unwanted content.
        removal_methods = [
            KeywordService.regex_phone_numbers,
            KeywordService.regex_passcodes,
            KeywordService.regex_misc,
            KeywordService.regex_date,
            KeywordService.regex_urls,
            KeywordService.regex_breaks,
        ]

        for method in removal_methods:
            patterns = method(db, sender_id)
            message = SMSService._remove_patterns(message, patterns)

        # Literal break strings.
        for value in KeywordService.non_regex_breaks(db, sender_id):
            if value:
                message = message.replace(value, "")

        message = re.sub(r"\s{2,}", " ", message)
        return message.strip()

    @staticmethod
    def is_valid_bank_transaction(
        db: Session,
        message: str,
        clean_sms: bool = True,
        sender_id: int | None = None,
        min_sms_length: int = 30,
    ) -> bool:
        if clean_sms:
            message = SMSService.pre_clean(db, message, sender_id)

        if not re.search(r"[0-9]+", message):
            logger.debug("SMS ignored because it contains no numbers.")
            return False

        if len(message) <= min_sms_length:
            logger.debug("SMS ignored because it is too short.")
            return False

        for pattern in KeywordService.regex_ignore_sms(db, sender_id):
            try:
                if re.search(pattern, message):
                    logger.debug("SMS ignored by regex rule: %s", pattern)
                    return False
            except re.error:
                logger.warning("Invalid ignore-SMS regex: %s", pattern)

        for keyword in KeywordService.str_ignore_sms(db, sender_id):
            if keyword and keyword.casefold() in message.casefold():
                logger.debug("SMS ignored by keyword: %s", keyword)
                return False

        return True

    @staticmethod
    def create_sms(
        db: Session,
        sender: str,
        message: str,
        user_id: int | None = None,
    ) -> SMS:
        message_hash = SMS.generate_hash(sender, message)

        existing = db.scalar(
            select(SMS).where(SMS.message_hash == message_hash)
        )
        if existing:
            return existing

        sms = SMS(
            sender=sender,
            message=message,
            message_hash=message_hash,
            is_valid=False,
            is_processed=False,
            user_id=user_id,
        )

        try:
            db.add(sms)
            db.commit()
            db.refresh(sms)
            return sms
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def process_invalid_sms(
        db: Session,
        sms: SMS,
        errors: dict | list | str | None = None,
        keep: bool = False,
        store_invalid: bool = False,
    ) -> SMS | None:
        if not (store_invalid or keep):
            db.delete(sms)
            db.commit()
            return None

        sms.is_valid = False
        sms.is_processed = True

        if errors:
            if isinstance(errors, str):
                sms.errors = {"reason": errors}
            elif isinstance(errors, (dict, list)):
                sms.errors = errors

        try:
            db.commit()
            db.refresh(sms)
            return sms
        except Exception:
            db.rollback()
            raise
