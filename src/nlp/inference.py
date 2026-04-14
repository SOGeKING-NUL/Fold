"""
NLP Inference Module
====================
Unified extraction engine that takes any raw text (from STT transcription,
OCR text wall, or direct WhatsApp message) and returns structured financial
data: amount, category, payment_method, bank_account.

Architecture:
    1. Check category_overrides.json for known merchant → category mappings.
    2. If no override, run DistilBERT sequence classification for category.
    3. Extract amount via regex (Hindi multiplier words + currency patterns).
    4. Extract payment method via keyword dictionary.
    5. Extract bank account via Indian bank name dictionary.

Dependencies:
    - transformers  (HuggingFace)
    - torch
"""

import re
import json
import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from ocr.amount_plausibility import (
    _is_year_in_date_context,
    is_likely_bank_last4_in_line,
    plausible_inr_amount,
)
from ocr.cash_flow import detect_cash_flow_from_text


# ─── Constants ───────────────────────────────────────────────────────────

# Path to the fine-tuned DistilBERT model directory
MODEL_DIR = os.path.join(os.path.dirname(__file__), "my_finetuned_distilbert")

# Path to the user-correctable category override file
OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "category_overrides.json")

# Label mapping — must match LabelEncoder.classes_ from training.
# We only keep real production categories (no synthetic outlier labels).
LABEL_MAP = {
    0: "education",
    1: "emi",
    2: "entertainment",
    3: "food",
    4: "friends",
    5: "healthcare",
    6: "investment",
    7: "shopping",
    8: "travel",
    9: "utilities",
}

# Valid production categories.
VALID_CATEGORIES = {
    "education", "emi", "entertainment", "food", "friends",
    "healthcare", "investment", "shopping", "travel", "utilities",
}

FALLBACK_CATEGORY = "shopping"  # Default if model predicts an outlier label

# ─── Indian Banks ────────────────────────────────────────────────────────
INDIAN_BANKS = [
    "hdfc", "sbi", "icici", "axis", "kotak", "pnb",
    "bob", "yes bank", "idfc", "indusind", "canara",
    "union bank", "federal bank", "rbl", "bandhan"
]

# ─── Payment Method Keywords ────────────────────────────────────────────
UPI_KEYWORDS = ["upi", "gpay", "google pay", "paytm", "phonepe", "phone pe", "bhim", "cred", "bharatpe"]
CARD_KEYWORDS = ["card", "visa", "mastercard", "amex", "debit", "credit"]
CASH_KEYWORDS = ["cash", "naqad", "nakd", "naqdi"]

# ─── UPI Provider Mapping (keyword → canonical provider name) ───────────
UPI_PROVIDER_MAP: dict[str, str] = {
    "gpay": "gpay",
    "google pay": "gpay",
    "g pay": "gpay",
    "phonepe": "phonepe",
    "phone pe": "phonepe",
    "paytm": "paytm",
    "bhim": "bhim",
    "cred": "cred",
    "bharatpe": "bharatpe",
    "amazon pay": "amazonpay",
    "amazonpay": "amazonpay",
    "freecharge": "freecharge",
    "mobikwik": "mobikwik",
}

# ─── Hindi Amount Multipliers ───────────────────────────────────────────
HINDI_MULTIPLIERS = {
    "hazaar": 1000, "hazar": 1000, "hajaar": 1000,
    "sau": 100,
    "lakh": 100000, "lac": 100000,
    "crore": 10000000,
}


class TransactionExtractor:
    """
    Loads the fine-tuned DistilBERT model once at init and provides
    a single `extract()` method for all downstream callers.
    """

    def __init__(self):
        """Load model, tokenizer, and category overrides into memory."""
        print("[NLP] Loading DistilBERT model from:", MODEL_DIR)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
        self.model.eval()  # Freeze dropout and batch-norm layers
        print("[NLP] Model loaded successfully.")

        self.overrides = self._load_overrides()

    # ─── Category Overrides ──────────────────────────────────────────

    def _load_overrides(self) -> dict:
        """Load user-corrected category mappings from disk."""
        if os.path.exists(OVERRIDES_PATH):
            with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_correction(self, keyword: str, correct_category: str):
        """
        Persist a user's category correction so future transactions
        containing this keyword bypass the model entirely.

        Args:
            keyword:          The merchant/phrase to remember (e.g., "xyz society").
            correct_category: The correct category (e.g., "rent").
        """
        self.overrides[keyword.lower().strip()] = correct_category.lower().strip()
        with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.overrides, f, indent=2)
        print(f"[NLP] Override saved: '{keyword}' → '{correct_category}'")

    # ─── Category Prediction ────────────────────────────────────────

    def _predict_category(self, text: str) -> str:
        """
        Priority chain:
            1. Check override map for known keywords.
            2. Fall back to DistilBERT neural prediction.
            3. If model returns an outlier label, use FALLBACK_CATEGORY.
        """
        lower = text.lower()

        # Step 1: Override check (exact substring match)
        for keyword, category in self.overrides.items():
            if keyword in lower:
                print(f"[NLP] Override matched: '{keyword}' → '{category}'")
                return category

        # Step 2: DistilBERT inference
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        predicted_id = torch.argmax(outputs.logits, dim=1).item()
        predicted_label = LABEL_MAP.get(predicted_id, FALLBACK_CATEGORY)

        # Step 3: Validate — if model returned an outlier label, use fallback
        if predicted_label not in VALID_CATEGORIES:
            print(f"[NLP] Model predicted outlier '{predicted_label}', using fallback.")
            return FALLBACK_CATEGORY

        return predicted_label

    # ─── Amount Extraction ──────────────────────────────────────────

    @staticmethod
    def _extract_amount(text: str) -> float | None:
        """
        Extract the monetary amount from text using a layered regex strategy:
            1. Hindi multiplier words (e.g., "do hazaar" → 2000).
            2. Currency-tagged numbers (e.g., "rs 500", "₹1200").
            3. Bare number fallback — largest number ≥ 10.
        """
        lower = text.lower()

        # Layer 1: Hindi multiplier words
        for word, factor in HINDI_MULTIPLIERS.items():
            match = re.search(rf'(\d+\.?\d*)\s*{word}', lower)
            if match:
                amt = float(match.group(1)) * factor
                if plausible_inr_amount(amt):
                    return amt

        # Layer 2: Currency-tagged numbers
        currency_match = re.findall(
            r'(?:rs\.?|inr|₹|rupaye|rupay|rupees?)\s*(\d[\d,]*\.?\d*)|'
            r'(\d[\d,]*\.?\d*)\s*(?:rs\.?|inr|₹|rupaye|rupay|rupees?)',
            lower
        )
        if currency_match:
            # Flatten tuples and pick the first non-empty match
            for group in currency_match:
                for val in group:
                    if val:
                        amt = float(val.replace(',', ''))
                        if plausible_inr_amount(amt):
                            return amt

        # Layer 3: Bare number fallback (largest number ≥ 10), excluding ref-id-sized integers
        # and 4-digit bank/card last-4 (same heuristic as OCR — e.g. "HDFC Bank 1751").
        numbers = re.findall(r'\b(\d[\d,]*\.?\d*)\b', lower)
        if numbers:
            parsed = [float(n.replace(',', '')) for n in numbers]
            large = [n for n in parsed if n >= 10 and plausible_inr_amount(n)]
            large = [n for n in large if not is_likely_bank_last4_in_line(lower, n)]
            large = [n for n in large if not _is_year_in_date_context(lower, n)]
            if large:
                return max(large)

        return None

    # ─── Payment Method Extraction ──────────────────────────────────

    @staticmethod
    def _extract_payment_method(text: str) -> str | None:
        """
        Scan for UPI / Card / Cash keywords.
        Returns None if no payment method is mentioned (triggers UX fallback).
        """
        lower = text.lower()

        if any(kw in lower for kw in UPI_KEYWORDS):
            return "upi"
        if any(kw in lower for kw in CARD_KEYWORDS):
            return "card"
        if any(kw in lower for kw in CASH_KEYWORDS):
            return "cash"

        return None

    # ─── UPI Provider Extraction ────────────────────────────────────

    @staticmethod
    def _extract_payment_provider(text: str) -> str | None:
        """
        If a UPI app name is found in text, return the canonical provider
        slug (gpay, phonepe, paytm, …). Returns None when no app is mentioned.
        """
        lower = text.lower()
        for keyword, provider in UPI_PROVIDER_MAP.items():
            if keyword in lower:
                return provider
        return None

    # ─── Bank Account Extraction ────────────────────────────────────

    @staticmethod
    def _extract_bank(text: str) -> str | None:
        """Detect which Indian bank account the transaction belongs to."""
        lower = text.lower()

        for bank in INDIAN_BANKS:
            if bank in lower:
                return bank

        return None

    # ─── Unified Extraction Pipeline ────────────────────────────────

    def extract(self, text: str) -> dict:
        """
        Master extraction method. Takes any raw text and returns
        a fully structured transaction dict.

        Args:
            text: Raw input (Whisper transcript, OCR text, or WhatsApp message).

        Returns:
            {
                "amount": float | None,
                "category": str,
                "payment_method": str | None,
                "payment_provider": str | None,
                "bank_account": str | None,
                "cash_flow": expense, income, or None (from phrases like paid to / received from),
            }
        """
        return {
            "amount": self._extract_amount(text),
            "category": self._predict_category(text),
            "payment_method": self._extract_payment_method(text),
            "payment_provider": self._extract_payment_provider(text),
            "bank_account": self._extract_bank(text),
            "cash_flow": detect_cash_flow_from_text(text),
        }


# ═══════════════════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    extractor = TransactionExtractor()

    test_sentences = [
        "Bhai Swiggy se pizza mangwaya 450 rupaye ka, UPI se pay kiya",
        "Amazon pe 2000 ka shopping kiya hdfc card se",
        "Ola cab liya 350 rupaye cash diye",
        "Netflix subscription 199 rupaye renew kiya",
        "Electricity bill 1200 rupaye card se pay kiya",
    ]

    # Allow custom input from CLI
    if len(sys.argv) > 1:
        test_sentences = [" ".join(sys.argv[1:])]

    for sentence in test_sentences:
        print(f"\n{'='*60}")
        print(f"INPUT: {sentence}")
        result = extractor.extract(sentence)
        print(f"OUTPUT: {json.dumps(result, indent=2)}")
