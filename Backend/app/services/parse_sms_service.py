
import json
import logging
import re
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SMSParseService:
    def __init__(
        self,
        parse_agent: Any,
        regex_agent: Any,
        category_agent: Any,
        setting_get: Callable,
        setting_get_bool: Callable,
        currency_resolver: Callable,
        category_lookup: Callable,
        category_store: Callable,
    ):
        self.parse_agent = parse_agent
        self.regex_agent = regex_agent
        self.category_agent = category_agent
        self.setting_get = setting_get
        self.setting_get_bool = setting_get_bool
        self.currency_resolver = currency_resolver
        self.category_lookup = category_lookup
        self.category_store = category_store

    @staticmethod
    def _decode_json(response_text: str) -> dict | None:
        try:
            result = json.loads(response_text)
            return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

    def parse_sms_via_llm(self, sms_message: str) -> dict | bool:
        model = self.setting_get("parsesms_model")
        response = self.parse_agent.prompt(sms_message, model=model)

        output = self._decode_json(response.text)
        logger.debug("LLM parseSMS response: %s", output)

        if output is None:
            return False

        # Clear currency fields when their amounts are empty or zero.
        for amount_field, currency_field in [
            ("fees", "feesCurrency"),
            ("totalAmount", "totalAmountCurrency"),
        ]:
            amount = output.get(amount_field)

            try:
                is_zero = amount is not None and float(amount) == 0
            except (ValueError, TypeError):
                is_zero = False

            if amount is None or amount == "" or is_zero:
                if currency_field in output:
                    output[currency_field] = ""

        return output

    def generate_regex(
        self,
        sms_message: str,
        parsed_output: dict
    ) -> str | None:
        self.regex_agent.smsText = sms_message
        self.regex_agent.parsedFields = parsed_output

        model = self.setting_get("parsesms_regex_model")
        response = self.regex_agent.prompt(
            "Generate regex for this SMS",
            model=model
        )

        output = self._decode_json(response.text)
        logger.debug("LLM GenerateRegex response: %s", output)

        if output is None:
            logger.warning("GenerateRegex: invalid JSON response")
            return None

        regex = output.get("regularExp")

        if not isinstance(regex, str) or not regex:
            return None

        # Require an amount and at least one account/party field.
        has_amount = "(?P<amount>" in regex
        account_fields = [
            "(?P<sourceAccountNumber>",
            "(?P<sourceAccountName>",
            "(?P<destinationAccountNumber>",
            "(?P<destinationAccountName>",
        ]
        has_account = any(field in regex for field in account_fields)

        if not has_amount or not has_account:
            logger.warning(
                "GenerateRegex: missing required named groups"
            )
            return None

        try:
            compiled_regex = re.compile(regex)
            match = compiled_regex.search(sms_message)

            if match is None:
                logger.warning(
                    "GenerateRegex: regex does not match the SMS"
                )
                return None

            matches = match.groupdict()

            currency_fields = {
                "currency",
                "feesCurrency",
                "totalAmountCurrency",
            }
            amount_fields = {"amount", "totalAmount", "fees"}

            fields_to_compare = [
                "amount",
                "currency",
                "totalAmount",
                "totalAmountCurrency",
                "fees",
                "feesCurrency",
                "transactionDateTime",
                "sourceAccountNumber",
                "sourceAccountName",
                "destinationAccountNumber",
                "destinationAccountName",
            ]

            mismatches = {}

            for field in fields_to_compare:
                expected = str(parsed_output.get(field) or "")
                captured = str(matches.get(field) or "")

                # Empty expected values need not be captured.
                if expected in ("", "0"):
                    continue

                # Optional regex groups may be empty.
                if captured == "":
                    continue

                normalized_expected = expected.replace(",", "").strip()
                normalized_captured = captured.replace(",", "").strip()

                if field in amount_fields:
                    if normalized_expected.startswith("."):
                        normalized_expected = "0" + normalized_expected
                    if normalized_captured.startswith("."):
                        normalized_captured = "0" + normalized_captured

                    # Normalize equivalent decimal representations.
                    normalized_expected = (
                        normalized_expected.rstrip("0").rstrip(".")
                        if "." in normalized_expected
                        else normalized_expected
                    )
                    normalized_captured = (
                        normalized_captured.rstrip("0").rstrip(".")
                        if "." in normalized_captured
                        else normalized_captured
                    )

                if field in currency_fields:
                    resolved = self.currency_resolver(
                        normalized_captured
                    )
                    if resolved:
                        normalized_captured = resolved

                if field == "transactionDateTime":
                    expected_date = self._parse_datetime(
                        normalized_expected
                    )
                    captured_date = self._parse_datetime(
                        normalized_captured
                    )

                    if (
                        expected_date is not None
                        and captured_date is not None
                        and expected_date == captured_date
                    ):
                        continue

                if normalized_expected != normalized_captured:
                    mismatches[field] = {
                        "expected": expected,
                        "captured": captured,
                    }

            if mismatches:
                logger.warning(
                    "GenerateRegex: captured values mismatch: %s",
                    mismatches
                )
                return None

            logger.debug("GenerateRegex: regex validated successfully")
            return regex

        except (re.error, IndexError, ValueError, TypeError) as error:
            logger.error("GenerateRegex validation error: %s", error)
            return None

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

        for date_format in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ):
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                continue

        return None

    @staticmethod
    def _other_party_identifier(
        matches: dict,
        transaction_type: str,
        prefer_number: bool
    ) -> str | None:
        if transaction_type == "deposit":
            number = matches.get("sourceAccountNumber") or ""
            name = matches.get("sourceAccountName") or ""
        else:
            number = matches.get("destinationAccountNumber") or ""
            name = matches.get("destinationAccountName") or ""

        if prefer_number:
            return number or name or None

        return name or number or None

    def detect_category(
        self,
        message: str,
        transaction_type: str,
        matches: dict,
        categories: list | bool = False
    ) -> dict | bool:
        output = {
            "error": None,
            "category": "Unknown",
        }

        valid_types = {
            "withdrawal",
            "deposit",
            "payment",
            "transfer",
        }

        if transaction_type not in valid_types:
            return False

        if transaction_type == "withdrawal":
            output["category"] = "Cash"
            return output

        if transaction_type == "transfer":
            output["category"] = "Transfer"
            return output

        # For deposits, identify the sender.
        # For payments, identify the merchant/receiver.
        account = self._other_party_identifier(
            matches,
            transaction_type,
            prefer_number=True,
        )

        if account:
            category = self.category_lookup(account)

            if category:
                output["category"] = category
                return output

        # AI fallback is configurable.
        use_ai = self.setting_get_bool(
            "parsesms_failback_detect_category_ai",
            False,
        )

        if not use_ai:
            return output

        if categories:
            self.category_agent.default_categories = categories

        merchant = (
            self._other_party_identifier(
                matches,
                transaction_type,
                prefer_number=False,
            )
            or ""
        )

        prompt = (
            f"Merchant: {merchant}\n"
            f"Transaction type: {transaction_type}\n"
            f"SMS: {message}"
        )

        model = self.setting_get("parsesms_category_model")
        response = self.category_agent.prompt(prompt, model=model)

        ai_output = self._decode_json(response.text)

        if ai_output is None:
            return False

        output.update(ai_output)

        if (
            output.get("category")
            and output["category"] != "Unknown"
            and merchant
        ):
            self.category_store(merchant, output["category"])

        return output
