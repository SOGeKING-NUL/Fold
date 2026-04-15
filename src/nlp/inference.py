"""
NLP Inference Module (Local Fallback)
======================================
Lightweight regex-based extraction for when the cloud VLM is unavailable.
Extracts amount, payment method, UPI provider, bank name, and cash flow
from plain text using keyword dictionaries and pattern matching.

Also manages the category_overrides.json correction memory.
"""

import re
import json
import os

from ocr.amount_plausibility import (
    _is_year_in_date_context,
    is_likely_bank_last4_in_line,
    plausible_inr_amount,
)
from ocr.cash_flow import detect_cash_flow_from_text


OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "category_overrides.json")

VALID_CATEGORIES = {
    "education", "emi", "entertainment", "food", "friends",
    "healthcare", "investment", "shopping", "travel", "utilities",
}
FALLBACK_CATEGORY = "shopping"

INDIAN_BANKS = [
    "hdfc", "sbi", "icici", "axis", "kotak", "pnb",
    "bob", "yes bank", "idfc", "indusind", "canara",
    "union bank", "federal bank", "rbl", "bandhan",
    "slice", "jupiter", "fi money", "fi bank", "niyo",
    "paytm payments bank",
]

UPI_KEYWORDS = ["upi", "gpay", "google pay", "paytm", "phonepe", "phone pe", "bhim", "cred", "bharatpe"]
CARD_KEYWORDS = ["card", "visa", "mastercard", "amex", "debit", "credit"]
CASH_KEYWORDS = ["cash", "naqad", "nakd", "naqdi"]

UPI_PROVIDER_MAP: dict[str, str] = {
    "gpay": "gpay", "google pay": "gpay", "g pay": "gpay",
    "phonepe": "phonepe", "phone pe": "phonepe",
    "paytm": "paytm", "bhim": "bhim", "cred": "cred",
    "bharatpe": "bharatpe", "amazon pay": "amazonpay", "amazonpay": "amazonpay",
    "freecharge": "freecharge", "mobikwik": "mobikwik",
    "slice": "slice", "jupiter": "jupiter", "fi": "fi", "niyo": "niyo",
}

HINDI_MULTIPLIERS = {
    "hazaar": 1000, "hazar": 1000, "hajaar": 1000,
    "sau": 100, "lakh": 100000, "lac": 100000, "crore": 10000000,
}


class TransactionExtractor:
    """
    Regex-based local extraction fallback.
    Used only when the cloud VLM (Bedrock) is disabled or unreachable.
    """

    def __init__(self):
        self.overrides = self._load_overrides()

    def _load_overrides(self) -> dict:
        if os.path.exists(OVERRIDES_PATH):
            with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_correction(self, keyword: str, correct_category: str):
        self.overrides[keyword.lower().strip()] = correct_category.lower().strip()
        with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.overrides, f, indent=2)

    def _predict_category(self, text: str) -> str:
        lower = text.lower()
        for keyword, category in self.overrides.items():
            if keyword in lower:
                return category
        return FALLBACK_CATEGORY

    @staticmethod
    def _extract_amount(text: str) -> float | None:
        lower = text.lower()

        for word, factor in HINDI_MULTIPLIERS.items():
            match = re.search(rf'(\d+\.?\d*)\s*{word}', lower)
            if match:
                amt = float(match.group(1)) * factor
                if plausible_inr_amount(amt):
                    return amt

        currency_match = re.findall(
            r'(?:rs\.?|inr|₹|rupaye|rupay|rupees?|rupiya|rupaiye)\s*(\d[\d,]*\.?\d*)|'
            r'(\d[\d,]*\.?\d*)\s*(?:rs\.?|inr|₹|rupaye|rupay|rupees?|rupiya|rupaiye)',
            lower
        )
        if currency_match:
            for group in currency_match:
                for val in group:
                    if val:
                        amt = float(val.replace(',', ''))
                        if plausible_inr_amount(amt):
                            return amt

        numbers = re.findall(r'\b(\d[\d,]*\.?\d*)\b', lower)
        if numbers:
            parsed = [float(n.replace(',', '')) for n in numbers]
            large = [n for n in parsed if n >= 10 and plausible_inr_amount(n)]
            large = [n for n in large if not is_likely_bank_last4_in_line(lower, n)]
            large = [n for n in large if not _is_year_in_date_context(lower, n)]
            if large:
                return max(large)

        return None

    @staticmethod
    def _extract_payment_method(text: str) -> str | None:
        lower = text.lower()
        if any(kw in lower for kw in UPI_KEYWORDS):
            return "upi"
        if any(kw in lower for kw in CARD_KEYWORDS):
            return "card"
        if any(kw in lower for kw in CASH_KEYWORDS):
            return "cash"
        return None

    @staticmethod
    def _extract_payment_provider(text: str) -> str | None:
        lower = text.lower()
        for keyword, provider in UPI_PROVIDER_MAP.items():
            if keyword in lower:
                return provider
        return None

    @staticmethod
    def _extract_bank(text: str) -> str | None:
        lower = text.lower()
        for bank in INDIAN_BANKS:
            if bank in lower:
                return bank
        return None

    def extract(self, text: str) -> dict:
        return {
            "amount": self._extract_amount(text),
            "category": self._predict_category(text),
            "payment_method": self._extract_payment_method(text),
            "payment_provider": self._extract_payment_provider(text),
            "bank_account": self._extract_bank(text),
            "cash_flow": detect_cash_flow_from_text(text),
        }
