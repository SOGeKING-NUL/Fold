"""
Cloud Extraction Module (AWS Bedrock)
======================================
Sends images or text to a vision-language model on AWS Bedrock for
structured financial transaction extraction.

Replaces the old OCR+regex+DistilBERT pipeline with a single model call
that can reason about currency symbols, dates, UPI app layouts, etc.
"""

import base64
import json
import logging
import re

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

_log = logging.getLogger(__name__)

VALID_CATEGORIES = frozenset({
    "food", "shopping", "utilities", "travel", "entertainment",
    "healthcare", "investment", "emi", "education", "friends",
})
FALLBACK_CATEGORY = "misc"

VALID_METHODS = frozenset({"upi", "card", "cash"})

_SYSTEM_PROMPT = """\
You are a financial transaction extractor for an Indian expense tracking app.

Given an image (screenshot or receipt photo) or a text message, extract the following fields:
- amount: the primary transaction amount in INR as a float. Look for ₹, Rs, R, INR prefixes. NEVER use dates, times, transaction IDs, or phone numbers as amounts.
- cash_flow: "expense" if money was spent/paid/debited, "income" if money was received/credited.
- category: one of: food, shopping, utilities, travel, entertainment, healthcare, investment, emi, education, friends. Pick the best match.
- payment_method: "upi", "card", or "cash". Determine from context.
- payment_provider: the UPI app or payment platform if visible (gpay, phonepe, paytm, bhim, cred, slice, jupiter, fi, etc.). null if unclear.
- bank_account: the bank or financial institution name if mentioned or visible (hdfc, sbi, icici, axis, kotak, slice, jupiter, fi, niyo, etc.). null if unclear.
- description: a short 1-line summary of what this transaction is about.

CRITICAL RULES:
1. Currency amounts have ₹, Rs, R, or INR prefix. "R500.00" means ₹500, NOT 500 rupees.
2. Numbers like 25th, 08:01, dates (May 25), phone numbers, and transaction IDs are NOT amounts.
3. For UPI screenshots, the large prominent number is almost always the amount.
4. "Paid" means expense (money going out). "Received" or "Credited" means income.

Return ONLY valid JSON with these exact keys: amount, cash_flow, category, payment_method, payment_provider, bank_account, description.
No markdown, no explanation, just the JSON object."""

_IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class CloudExtractor:
    """
    Extracts structured financial data from images or text using
    a vision-language model hosted on AWS Bedrock.
    """

    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        timeout_seconds: int = 30,
        min_confidence: float = 0.0,
    ):
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.min_confidence = min_confidence
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
        )
        _log.info(
            "[Cloud] Bedrock extractor ready — model=%s region=%s",
            model_id, region,
        )

    def extract_from_image(
        self,
        image_bytes: bytes,
        image_ext: str = ".jpg",
        caption: str | None = None,
    ) -> dict:
        media_type = _IMAGE_MEDIA_TYPES.get(image_ext.lower(), "image/jpeg")
        user_content: list[dict] = [
            {
                "image": {
                    "format": media_type.split("/")[1],
                    "source": {"bytes": image_bytes},
                },
            },
        ]
        if caption:
            user_content.append({"text": f"User caption: {caption}"})
        user_content.append({"text": "Extract the financial transaction from this image."})

        return self._invoke(user_content, source="image")

    def extract_from_text(self, text: str) -> dict:
        user_content = [
            {"text": f"Extract the financial transaction from this text:\n\n{text}"},
        ]
        return self._invoke(user_content, source="text")

    def _invoke(self, user_content: list[dict], source: str) -> dict:
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": _SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": user_content}],
                inferenceConfig={
                    "maxTokens": 512,
                    "temperature": 0.0,
                },
            )
        except (ClientError, NoCredentialsError) as exc:
            _log.error("[Cloud] Bedrock invoke failed: %s", exc)
            raise RuntimeError(f"Cloud extraction failed: {exc}") from exc

        output = response.get("output", {})
        msg = output.get("message", {})
        parts = msg.get("content", [])
        raw_text = ""
        for part in parts:
            if "text" in part:
                raw_text += part["text"]

        parsed = self._parse_json(raw_text)
        parsed["debug_model_source"] = "bedrock"
        parsed["debug_model_id"] = self.model_id
        parsed["debug_raw_response"] = raw_text[:500]
        return parsed

    def _parse_json(self, raw: str) -> dict:
        cleaned = raw.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON object from surrounding text
            match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    _log.warning("[Cloud] Could not parse JSON from response: %s", cleaned[:200])
                    return self._empty_result()
            else:
                _log.warning("[Cloud] No JSON found in response: %s", cleaned[:200])
                return self._empty_result()

        return self._normalize(data)

    def _normalize(self, data: dict) -> dict:
        amount = data.get("amount")
        if amount is not None:
            try:
                amount = float(amount)
                if amount <= 0:
                    amount = None
            except (ValueError, TypeError):
                amount = None

        category = str(data.get("category") or FALLBACK_CATEGORY).lower().strip()
        if category not in VALID_CATEGORIES:
            category = FALLBACK_CATEGORY

        method = data.get("payment_method")
        if method:
            method = str(method).lower().strip()
            if method not in VALID_METHODS:
                method = None

        provider = data.get("payment_provider")
        if provider:
            provider = str(provider).lower().strip()
            if provider in ("null", "none", "unknown", "n/a", ""):
                provider = None

        bank = data.get("bank_account")
        if bank:
            bank = str(bank).lower().strip()
            if bank in ("null", "none", "unknown", "n/a", ""):
                bank = None

        cash_flow = data.get("cash_flow")
        if cash_flow:
            cash_flow = str(cash_flow).lower().strip()
            if cash_flow not in ("expense", "income"):
                cash_flow = None

        description = data.get("description") or ""
        if isinstance(description, str):
            description = description.strip()[:500]

        return {
            "amount": amount,
            "category": category,
            "payment_method": method,
            "payment_provider": provider,
            "bank_account": bank,
            "cash_flow": cash_flow,
            "description": description,
        }

    @staticmethod
    def _empty_result() -> dict:
        return {
            "amount": None,
            "category": FALLBACK_CATEGORY,
            "payment_method": None,
            "payment_provider": None,
            "bank_account": None,
            "cash_flow": None,
            "description": "",
        }
