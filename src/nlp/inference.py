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
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModel

from ocr.amount_plausibility import (
    _is_year_in_date_context,
    is_likely_bank_last4_in_line,
    plausible_inr_amount,
)
from ocr.cash_flow import detect_cash_flow_from_text


# ─── Constants ───────────────────────────────────────────────────────────

# v1 single-head model (current deployed checkpoint)
MODEL_DIR = os.path.join(os.path.dirname(__file__), "my_finetuned_distilbert")

# v3 multi-head model (after retraining on eda_dataset_v3.csv)
MODEL_V3_DIR = os.path.join(os.path.dirname(__file__), "my_finetuned_distilbert_v3")

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
    "union bank", "federal bank", "rbl", "bandhan",
    "slice", "jupiter", "fi money", "fi bank", "niyo",
    "paytm payments bank",
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
    "slice": "slice",
    "jupiter": "jupiter",
    "fi": "fi",
    "niyo": "niyo",
}

# ─── Hindi Amount Multipliers ───────────────────────────────────────────
HINDI_MULTIPLIERS = {
    "hazaar": 1000, "hazar": 1000, "hajaar": 1000,
    "sau": 100,
    "lakh": 100000, "lac": 100000,
    "crore": 10000000,
}


class _MultiHeadDistilBERT(nn.Module):
    """DistilBERT encoder with three classification heads (category, method, bank)."""

    def __init__(self, encoder, num_cat: int, num_method: int, num_bank: int):
        super().__init__()
        self.encoder = encoder
        hidden = encoder.config.hidden_size
        self.head_cat = nn.Linear(hidden, num_cat)
        self.head_method = nn.Linear(hidden, num_method)
        self.head_bank = nn.Linear(hidden, num_bank)

    def forward(self, input_ids=None, attention_mask=None, **kwargs):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0]
        return {
            "logits_cat": self.head_cat(cls_output),
            "logits_method": self.head_method(cls_output),
            "logits_bank": self.head_bank(cls_output),
        }


class TransactionExtractor:
    """
    Loads the fine-tuned DistilBERT model once at init and provides
    a single `extract()` method for all downstream callers.

    Supports two model versions:
    - v1 (single-head): category only, regex for payment/bank
    - v3 (multi-head): category + payment_method + bank_account from model
    Falls back to v1 if v3 checkpoint is not present.
    """

    def __init__(self):
        """Load model, tokenizer, and category overrides into memory."""
        self.use_v3 = False
        self.v3_label_maps: dict = {}

        # Try v3 multi-head model first
        heads_path = os.path.join(MODEL_V3_DIR, "heads.pt")
        maps_path = os.path.join(MODEL_V3_DIR, "label_maps_v3.json")
        if os.path.isdir(MODEL_V3_DIR) and os.path.isfile(heads_path) and os.path.isfile(maps_path):
            print("[NLP] Loading multi-head v3 model from:", MODEL_V3_DIR)
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_V3_DIR)
            encoder = AutoModel.from_pretrained(MODEL_V3_DIR)
            with open(maps_path, "r", encoding="utf-8") as f:
                self.v3_label_maps = json.load(f)
            head_state = torch.load(heads_path, map_location="cpu", weights_only=True)
            self.model = _MultiHeadDistilBERT(
                encoder,
                num_cat=head_state["num_cat"],
                num_method=head_state["num_method"],
                num_bank=head_state["num_bank"],
            )
            self.model.head_cat.load_state_dict(head_state["head_cat"])
            self.model.head_method.load_state_dict(head_state["head_method"])
            self.model.head_bank.load_state_dict(head_state["head_bank"])
            self.model.eval()
            self.use_v3 = True
            print("[NLP] Multi-head v3 model loaded successfully.")
        else:
            print("[NLP] Loading single-head v1 model from:", MODEL_DIR)
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
            self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
            self.model.eval()
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

    def _predict_all_v3(self, text: str) -> dict:
        """Run v3 multi-head model and return category, payment_method, bank_account."""
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=128, padding=True
        )
        with torch.no_grad():
            out = self.model(**inputs)

        cat_map = self.v3_label_maps.get("category", {})
        method_map = self.v3_label_maps.get("payment_method", {})
        bank_map = self.v3_label_maps.get("bank_account", {})

        cat_id = out["logits_cat"].argmax(dim=1).item()
        method_id = out["logits_method"].argmax(dim=1).item()
        bank_id = out["logits_bank"].argmax(dim=1).item()

        category = cat_map.get(str(cat_id), FALLBACK_CATEGORY)
        method = method_map.get(str(method_id), "unknown")
        bank = bank_map.get(str(bank_id), "unknown")

        if category not in VALID_CATEGORIES:
            category = FALLBACK_CATEGORY
        if method == "unknown":
            method = None
        if bank == "unknown":
            bank = None

        return {"category": category, "payment_method": method, "bank_account": bank}

    def _predict_category(self, text: str) -> str:
        """
        Priority chain:
            1. Check override map for known keywords.
            2. Fall back to DistilBERT neural prediction.
            3. If model returns an outlier label, use FALLBACK_CATEGORY.
        """
        lower = text.lower()

        for keyword, category in self.overrides.items():
            if keyword in lower:
                print(f"[NLP] Override matched: '{keyword}' → '{category}'")
                return category

        if self.use_v3:
            return self._predict_all_v3(text)["category"]

        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=128, padding=True
        )
        with torch.no_grad():
            outputs = self.model(**inputs)

        predicted_id = torch.argmax(outputs.logits, dim=1).item()
        predicted_label = LABEL_MAP.get(predicted_id, FALLBACK_CATEGORY)

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

        # Layer 2: Currency-tagged numbers (includes OCR garble variants of ₹)
        currency_match = re.findall(
            r'(?:rs\.?|inr|₹|rupaye|rupay|rupees?|rupiya|rupaiye)\s*(\d[\d,]*\.?\d*)|'
            r'(\d[\d,]*\.?\d*)\s*(?:rs\.?|inr|₹|rupaye|rupay|rupees?|rupiya|rupaiye)',
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

        When the v3 multi-head model is loaded, model predictions for
        payment_method and bank_account are used as primary signal with
        regex as fallback/enrichment.
        """
        amount = self._extract_amount(text)
        regex_pm = self._extract_payment_method(text)
        regex_provider = self._extract_payment_provider(text)
        regex_bank = self._extract_bank(text)
        cash_flow = detect_cash_flow_from_text(text)

        if self.use_v3:
            v3 = self._predict_all_v3(text)
            category = v3["category"]
            # Model prediction wins; regex fills gaps the model missed
            payment_method = v3["payment_method"] or regex_pm
            bank_account = v3["bank_account"] or regex_bank
        else:
            category = self._predict_category(text)
            payment_method = regex_pm
            bank_account = regex_bank

        return {
            "amount": amount,
            "category": category,
            "payment_method": payment_method,
            "payment_provider": regex_provider,
            "bank_account": bank_account,
            "cash_flow": cash_flow,
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
