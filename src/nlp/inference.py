"""
NLP Inference Module
====================
Unified extraction engine that takes any raw text (from STT transcription,
OCR text wall, or direct WhatsApp message) and returns structured financial
data: amount, category, payment_method, bank_account.

Architecture:
    1. Run DistilBERT sequence classification for category, payment method,
       and bank account.
    2. Extract amount using a custom-trained spaCy NER model (no regex!).

Models Used:
    - DistilBERT (Sequence Classification): Predicts category, payment
      method, and bank account from the full sentence.
    - spaCy NER (Token Classification): Identifies the AMOUNT entity
      in the text by tagging individual words.

Dependencies:
    - transformers  (HuggingFace)
    - torch
    - spacy
"""

import json
import os
import torch
import torch.nn as nn
import spacy
from transformers import AutoTokenizer, AutoModel



# ─── Constants ───────────────────────────────────────────────────────────

# Path to the multi-head DistilBERT model (trained in model_v3.ipynb)
MODEL_V3_DIR = os.path.join(os.path.dirname(__file__), "my_finetuned_distilbert_v3")

# Path to the spaCy NER model (trained in train_ner.ipynb)
NER_MODEL_DIR = os.path.join(os.path.dirname(__file__), "amount_ner_model")


# Valid production categories
VALID_CATEGORIES = {
    "education", "emi", "entertainment", "food", "friends",
    "healthcare", "investment", "shopping", "travel", "utilities",
}

# Default category if the model predicts something unexpected
FALLBACK_CATEGORY = "shopping"

# ─── Indian Banks (must match bank classes from model_v3.ipynb) ──────────
INDIAN_BANKS = [
    "hdfc", "sbi", "icici", "axis", "kotak", "pnb",
    "bob", "yes bank", "idfc", "indusind", "canara",
    "union bank", "federal bank", "rbl", "bandhan",
    "slice", "jupiter", "fi", "niyo",
]

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


# ═══════════════════════════════════════════════════════════════════════
# Multi-Head DistilBERT Model (Sequence Classification)
# ═══════════════════════════════════════════════════════════════════════

class _MultiHeadDistilBERT(nn.Module):
    """
    DistilBERT encoder with three classification heads.

    The shared encoder processes the sentence once, then three separate
    linear layers predict category, payment method, and bank account.
    This is efficient because one forward pass gives us three answers.
    """

    def __init__(self, encoder, num_cat: int, num_method: int, num_bank: int):
        super().__init__()
        self.encoder = encoder
        hidden = encoder.config.hidden_size
        self.head_cat = nn.Linear(hidden, num_cat)
        self.head_method = nn.Linear(hidden, num_method)
        self.head_bank = nn.Linear(hidden, num_bank)

    def forward(self, input_ids=None, attention_mask=None, **kwargs):
        # Get the encoder's output for all tokens
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)

        # Use the [CLS] token's representation (first token) as the sentence embedding
        cls_output = outputs.last_hidden_state[:, 0]

        # Each head produces logits (raw scores) for its classification task
        return {
            "logits_cat": self.head_cat(cls_output),
            "logits_method": self.head_method(cls_output),
            "logits_bank": self.head_bank(cls_output),
        }


# ═══════════════════════════════════════════════════════════════════════
# Transaction Extractor — The Main Class
# ═══════════════════════════════════════════════════════════════════════

class TransactionExtractor:
    """
    Loads two models at startup and provides a single `extract()` method:

    1. DistilBERT (Sequence Classification) → category, payment_method, bank
    2. spaCy NER (Token Classification) → amount

    This replaces the old regex-based extraction with ML models.
    """

    def __init__(self):
        """Load all models and data into memory."""

        # ── Load DistilBERT multi-head model ──
        self.v3_label_maps: dict = {}
        heads_path = os.path.join(MODEL_V3_DIR, "heads.pt")
        maps_path = os.path.join(MODEL_V3_DIR, "label_maps_v3.json")

        if os.path.isdir(MODEL_V3_DIR) and os.path.isfile(heads_path) and os.path.isfile(maps_path):
            print("[NLP] Loading multi-head DistilBERT model...")
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
            print("[NLP] DistilBERT model loaded successfully.")
        else:
            raise FileNotFoundError(
                f"DistilBERT model not found at {MODEL_V3_DIR}. "
                "Please train it first using model_v3.ipynb."
            )

        # ── Load spaCy NER model for amount extraction ──
        if os.path.isdir(NER_MODEL_DIR):
            print("[NLP] Loading spaCy NER model for amount extraction...")
            self.ner_model = spacy.load(NER_MODEL_DIR)
            print("[NLP] NER model loaded successfully.")
        else:
            print(f"[NLP] WARNING: NER model not found at {NER_MODEL_DIR}.")
            print("[NLP] Amount extraction will be unavailable. Train it with: python -m src.nlp.train_ner")
            self.ner_model = None



    # ─── DistilBERT Prediction (Category + Payment + Bank) ───────────

    def _predict_all(self, text: str) -> dict:
        """
        Run the multi-head DistilBERT model to get:
        - category (e.g., "food", "travel")
        - payment_method (e.g., "upi", "card", "cash")
        - bank_account (e.g., "hdfc", "sbi")
        """
        # Tokenize the input text
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=128, padding=True
        )

        # Run the model (no gradient computation needed for inference)
        with torch.no_grad():
            out = self.model(**inputs)

        # Get the label maps for each head
        cat_map = self.v3_label_maps.get("category", {})
        method_map = self.v3_label_maps.get("payment_method", {})
        bank_map = self.v3_label_maps.get("bank_account", {})

        # Pick the class with the highest score (argmax)
        cat_id = out["logits_cat"].argmax(dim=1).item()
        method_id = out["logits_method"].argmax(dim=1).item()
        bank_id = out["logits_bank"].argmax(dim=1).item()

        # Convert numeric IDs back to human-readable labels
        category = cat_map.get(str(cat_id), FALLBACK_CATEGORY)
        method = method_map.get(str(method_id), "unknown")
        bank = bank_map.get(str(bank_id), "unknown")

        # Validate the category
        if category not in VALID_CATEGORIES:
            category = FALLBACK_CATEGORY

        # Treat "unknown" as None (meaning the model couldn't determine it)
        if method == "unknown":
            method = None
        if bank == "unknown":
            bank = None

        return {"category": category, "payment_method": method, "bank_account": bank}

    # ─── NER-based Amount Extraction ─────────────────────────────────

    def _extract_amount(self, text: str) -> float | None:
        """
        Extract the monetary amount from text using our trained NER model.

        The NER model scans each word in the text and tags words that
        represent monetary amounts with the "AMOUNT" label.

        Returns the first valid amount found, or None if no amount detected.
        """
        # If NER model isn't available, we can't extract amounts
        if self.ner_model is None:
            return None

        # Run the NER model on the text
        doc = self.ner_model(text)

        # Look for entities tagged as "AMOUNT"
        for ent in doc.ents:
            if ent.label_ == "AMOUNT":
                try:
                    # Clean the extracted text and convert to a number
                    amount_text = ent.text.replace(",", "").strip()
                    amount = float(amount_text)

                    # Only return positive, reasonable amounts
                    if amount > 0:
                        return amount
                except (ValueError, TypeError):
                    # If conversion fails, try next entity
                    continue

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

    # ─── Unified Extraction Pipeline ────────────────────────────────

    def extract(self, text: str) -> dict:
        """
        Master extraction method. Takes any raw text and returns
        a fully structured transaction dict.

        Pipeline:
            1. DistilBERT → category, payment_method, bank_account
            2. spaCy NER → amount
            3. Keyword scan → payment_provider
        """
        # Step 1: Run DistilBERT for classification
        predictions = self._predict_all(text)

        # Step 2: Run NER for amount extraction
        amount = self._extract_amount(text)

        # Step 3: Extract UPI provider name
        payment_provider = self._extract_payment_provider(text)

        # Step 4: Fallback — scan text for bank names the model might have missed
        lower = text.lower()
        bank_account = predictions["bank_account"]
        if not bank_account:
            for bank in INDIAN_BANKS:
                if bank in lower:
                    bank_account = bank
                    break

        # If payment method is cash but no bank detected, set bank to "cash"
        # so the backend can match it to the Cash Wallet account
        payment_method = predictions["payment_method"]
        if payment_method == "cash" and not bank_account:
            bank_account = "cash"

        return {
            "amount": amount,
            "category": predictions["category"],
            "payment_method": payment_method,
            "payment_provider": payment_provider,
            "bank_account": bank_account,
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
