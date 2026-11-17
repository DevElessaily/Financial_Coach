
import hashlib
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sms_regular_exp import SMSRegularExp
from app.schemas.sms_regular_exp import SMSRegularExpCreate, SMSRegularExpUpdate

logger = logging.getLogger(__name__)

ACCOUNT_FIELDS = (
    "sourceAccountNumber",
    "sourceAccountName",
    "destinationAccountNumber",
    "destinationAccountName",
)


class SMSRegularExpService:

    @staticmethod
    def _compile_pattern(pattern: str) -> re.Pattern | None:
        try:
            return re.compile(pattern)
        except re.error as exc:
            logger.warning("Invalid SMS regex pattern: %s", exc)
            return None

    @staticmethod
    def _named_matches(match: re.Match) -> dict[str, str | None]:
        return match.groupdict()

    @staticmethod
    def find_regex(
        db: Session,
        sender_id: int,
        message: str,
        is_valid_regular_exp: bool = True,
        is_valid_transaction: bool = True,
    ) -> dict | None:
        statement = (
            select(SMSRegularExp)
            .where(
                SMSRegularExp.sender_id == sender_id,
                SMSRegularExp.is_active.is_(True),
                SMSRegularExp.is_valid_regular_exp.is_(
                    is_valid_regular_exp
                ),
                SMSRegularExp.is_valid_transaction.is_(
                    is_valid_transaction
                ),
            )
            .order_by(SMSRegularExp.id.asc())
        )

        expressions = db.scalars(statement).all()

        for expression in expressions:
            compiled = SMSRegularExpService._compile_pattern(
                expression.regular_exp
            )
            if compiled is None:
                continue

            match = compiled.search(message)
            if match:
                return {
                    "id": expression.id,
                    "sender_id": expression.sender_id,
                    "transaction_type": expression.transaction_type,
                    "matches": SMSRegularExpService._named_matches(match),
                }

        return None

    @staticmethod
    def find_valid_regex(
        db: Session,
        sender_id: int,
        message: str,
    ) -> dict | None:
        return SMSRegularExpService.find_regex(
            db=db,
            sender_id=sender_id,
            message=message,
            is_valid_regular_exp=True,
            is_valid_transaction=True,
        )

    @staticmethod
    def find_invalid_regex(
        db: Session,
        sender_id: int,
        message: str,
    ) -> dict | None:
        return SMSRegularExpService.find_regex(
            db=db,
            sender_id=sender_id,
            message=message,
            is_valid_regular_exp=True,
            is_valid_transaction=False,
        )

    @staticmethod
    def validate_regex(
        pattern: str,
        message: str,
    ) -> tuple[bool, dict]:
        compiled = SMSRegularExpService._compile_pattern(pattern)

        if compiled is None:
            return False, {}

        match = compiled.search(message)

        if match is None:
            return False, {}

        matches = match.groupdict()
        amount = matches.get("amount")

        if not amount:
            return False, matches

        normalized_amount = amount.replace(",", "").strip()

        try:
            float(normalized_amount)
        except (ValueError, TypeError):
            return False, matches

        has_account = any(
            matches.get(field) not in (None, "")
            for field in ACCOUNT_FIELDS
        )

        return has_account, matches

    @staticmethod
    def store_regex(
        db: Session,
        data: SMSRegularExpCreate,
    ) -> SMSRegularExp:
        pattern_hash = hashlib.md5(
            data.regular_exp.encode("utf-8")
        ).hexdigest()

        is_valid_regex, matches = SMSRegularExpService.validate_regex(
            data.regular_exp,
            data.sample_message,
        )

        logger.debug(
            "Storing SMS regex: sender_id=%s type=%s valid=%s",
            data.sender_id,
            data.transaction_type,
            is_valid_regex,
        )

        statement = select(SMSRegularExp).where(
            SMSRegularExp.sender_id == data.sender_id,
            SMSRegularExp.regular_exp_md5 == pattern_hash,
        )
        existing = db.scalar(statement)

        metadata = {
            "sample_smsMessage": data.sample_message,
            "ai_output": data.ai_output,
            "regular_expMatches": matches,
        }

        if existing:
            existing.transaction_type = data.transaction_type
            existing.data = metadata
            existing.is_valid_transaction = data.is_valid_transaction
            existing.is_valid_regular_exp = is_valid_regex
            existing.is_active = True
            result = existing
        else:
            result = SMSRegularExp(
                sender_id=data.sender_id,
                transaction_type=data.transaction_type,
                regular_exp=data.regular_exp,
                regular_exp_md5=pattern_hash,
                created_by="system",
                data=metadata,
                is_active=True,
                is_valid_transaction=data.is_valid_transaction,
                is_valid_regular_exp=is_valid_regex,
            )
            db.add(result)

        try:
            db.commit()
            db.refresh(result)
            return result
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_regex(
        db: Session,
        expression: SMSRegularExp,
        data: SMSRegularExpUpdate,
    ) -> SMSRegularExp:
        updates = data.model_dump(exclude_unset=True)

        new_pattern = updates.get("regular_exp", expression.regular_exp)
        new_type = updates.get(
            "transaction_type", expression.transaction_type
        )

        if not new_pattern or not new_type:
            raise ValueError("Regex and transaction type cannot be empty.")

        # Recalculate validity if the regex changes.
        if "regular_exp" in updates:
            expression.regular_exp_md5 = hashlib.md5(
                new_pattern.encode("utf-8")
            ).hexdigest()

            sample_message = (expression.data or {}).get(
                "sample_smsMessage", ""
            )
            is_valid, matches = SMSRegularExpService.validate_regex(
                new_pattern,
                sample_message,
            )
            expression.is_valid_regular_exp = is_valid

            metadata = dict(expression.data or {})
            metadata["regular_expMatches"] = matches
            expression.data = metadata

        for field, value in updates.items():
            setattr(expression, field, value)

        try:
            db.commit()
            db.refresh(expression)
            return expression
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def list_regexes(
        db: Session,
        sender_id: int | None = None,
    ) -> list[SMSRegularExp]:
        statement = select(SMSRegularExp)

        if sender_id is not None:
            statement = statement.where(
                SMSRegularExp.sender_id == sender_id
            )

        statement = statement.order_by(SMSRegularExp.id.desc())
        return list(db.scalars(statement).all())

    @staticmethod
    def get_regex(
        db: Session,
        expression_id: int,
    ) -> SMSRegularExp | None:
        return db.get(SMSRegularExp, expression_id)

    @staticmethod
    def delete_regex(
        db: Session,
        expression: SMSRegularExp,
    ) -> None:
        try:
            db.delete(expression)
            db.commit()
        except Exception:
            db.rollback()
            raise
