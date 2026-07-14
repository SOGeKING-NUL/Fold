"""
build_clean_dataset.py
----------------------
Offline, deterministic generator for the CLEAN canonical NLP training dataset.

It expands the curated natural templates (natural_templates.json) by filling the
slots {merchant} {amount} {pay} {bank} with real, label-consistent values. This
guarantees the two properties that the previous synthetic data broke:

  1. The number inside `text` always equals the `amount` column.
  2. category / payment_method / payment_provider / bank_account always agree
     with the words actually present in the text.

Output: src/nlp/eda_dataset_clean.csv   (the model trains on THIS)
The messy student-facing file (eda_dataset_v3.csv) is produced separately by
inject_errors.py and is used only for the EDA teaching module.

Run:  python src/nlp/build_clean_dataset.py
"""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent
TEMPLATES_PATH = ROOT / "natural_templates.json"
OUT = ROOT / "eda_dataset_clean.csv"

CANONICAL_CATEGORIES = [
    "food", "shopping", "travel", "entertainment", "healthcare",
    "education", "emi", "utilities", "investment", "friends",
]

CATEGORY_MERCHANTS: dict[str, list[str]] = {
    "food": ["Swiggy", "Zomato", "Dominos", "McDonald's", "KFC", "Pizza Hut",
             "Burger King", "Starbucks", "Haldirams", "Subway", "Biryani Blues",
             "Behrouz", "Box8", "Zepto", "Blinkit", "BigBasket", "JioMart",
             "restaurant", "cafe", "food court", "dhaba", "mess", "canteen"],
    "shopping": ["Amazon", "Flipkart", "Myntra", "Ajio", "Meesho", "Nykaa",
                 "Croma", "Reliance Digital", "Tata CLiQ", "FirstCry",
                 "Lenskart", "Bewakoof", "H&M", "Zara", "electronics store", "mall"],
    "travel": ["Uber", "Ola", "Rapido", "IRCTC", "MakeMyTrip", "Goibibo",
               "RedBus", "Yatra", "IndiGo", "SpiceJet", "Air India", "Cleartrip",
               "petrol pump", "HP petrol", "Indian Oil", "auto", "metro"],
    "entertainment": ["Netflix", "Hotstar", "PVR", "BookMyShow", "SonyLIV",
                      "Spotify", "JioCinema", "INOX", "concert", "Steam",
                      "Apple Music", "Zomato Gold"],
    "healthcare": ["Apollo Pharmacy", "doctor", "dentist", "lab test", "Netmeds",
                   "MedPlus", "checkup", "hospital", "physio", "PharmEasy",
                   "diagnostic center", "eye clinic"],
    "education": ["upGrad", "tuition", "course", "books", "fees", "coaching",
                  "Udemy", "Coursera", "stationery", "exam fee", "school fees",
                  "Allen coaching"],
    "emi": ["car loan EMI", "bike loan EMI", "home loan EMI", "education loan EMI",
            "credit card EMI", "personal loan EMI", "EMI", "installment"],
    "utilities": ["electricity bill", "Jio recharge", "gas bill", "broadband",
                  "rent", "water bill", "Airtel recharge", "DTH recharge",
                  "mobile recharge", "wifi bill", "maintenance"],
    "investment": ["mutual fund SIP", "stocks", "PPF", "gold", "crypto",
                   "index fund", "NPS", "FD", "Groww", "Angel One",
                   "sovereign gold bond", "recurring deposit"],
    "friends": ["Rahul", "Neha", "roommate", "friend", "flatmate", "Arjun",
                "Priya", "Ananya", "brother", "sister", "Karan", "Sneha"],
}

PAYMENT_METHODS = ["cash", "upi", "card"]

UPI_PROVIDERS = ["gpay", "phonepe", "paytm", "bhim", "cred", "slice", "jupiter", "fi", "niyo"]
UPI_PROVIDER_DISPLAY = {
    "gpay": ["GPay", "Google Pay", "gpay"],
    "phonepe": ["PhonePe", "Phone Pe", "phonepe"],
    "paytm": ["Paytm", "PayTM", "paytm"],
    "bhim": ["BHIM", "bhim"],
    "cred": ["CRED", "cred"],
    "slice": ["Slice", "slice"],
    "jupiter": ["Jupiter", "jupiter"],
    "fi": ["Fi", "Fi Money"],
    "niyo": ["Niyo", "niyo"],
}

BANKS = ["hdfc", "sbi", "icici", "axis", "kotak", "pnb", "bob", "yes bank",
         "idfc", "indusind", "canara", "union bank", "federal bank", "rbl",
         "bandhan", "slice", "jupiter", "fi", "niyo"]
BANK_DISPLAY = {
    "hdfc": ["HDFC", "HDFC Bank"], "sbi": ["SBI", "State Bank"],
    "icici": ["ICICI", "ICICI Bank"], "axis": ["Axis", "Axis Bank"],
    "kotak": ["Kotak", "Kotak Mahindra"], "pnb": ["PNB", "Punjab National Bank"],
    "bob": ["BOB", "Bank of Baroda"], "yes bank": ["Yes Bank", "YES BANK"],
    "idfc": ["IDFC", "IDFC First"], "indusind": ["IndusInd", "Indusind Bank"],
    "canara": ["Canara", "Canara Bank"], "union bank": ["Union Bank"],
    "federal bank": ["Federal Bank"], "rbl": ["RBL", "RBL Bank"],
    "bandhan": ["Bandhan", "Bandhan Bank"], "slice": ["Slice"],
    "jupiter": ["Jupiter"], "fi": ["Fi", "Fi Money"], "niyo": ["Niyo"],
}

# Realistic amount ranges per category (rupees): (low, high) with optional decimal bias
CATEGORY_AMOUNTS = {
    "food": (40, 2500),
    "shopping": (150, 30000),
    "travel": (60, 15000),
    "entertainment": (99, 3000),
    "healthcare": (100, 25000),
    "education": (500, 60000),
    "emi": (1500, 40000),
    "utilities": (50, 5000),
    "investment": (500, 50000),
    "friends": (50, 10000),
}

FIELDNAMES = ["text", "amount", "category", "payment_method",
              "payment_provider", "bank_account", "text_source"]


def _amount(cat: str) -> str:
    low, high = CATEGORY_AMOUNTS[cat]
    base = random.randint(low, high)
    if random.random() < 0.30:
        return f"{base + random.randint(0, 99) / 100:.2f}"
    return str(base)


def _pick_method(cat: str) -> str:
    # category-appropriate payment mix
    if cat == "emi":
        return random.choices(PAYMENT_METHODS, weights=[5, 25, 70])[0]
    if cat == "utilities":
        return random.choices(PAYMENT_METHODS, weights=[15, 70, 15])[0]
    if cat == "investment":
        return random.choices(PAYMENT_METHODS, weights=[10, 80, 10])[0]
    if cat == "friends":
        return random.choices(PAYMENT_METHODS, weights=[20, 75, 5])[0]
    return random.choices(PAYMENT_METHODS, weights=[25, 55, 20])[0]


def _pick_provider() -> str:
    return random.choice(UPI_PROVIDERS)


def _pick_bank() -> str:
    return random.choice(BANKS)


def _disp(roster, key):
    return random.choice(roster.get(key, [key]))


def _pay_label(method: str, provider: str) -> str:
    if method == "upi":
        return _disp(UPI_PROVIDER_DISPLAY, provider)
    if method == "card":
        return random.choice(["card", "credit card", "debit card", "Visa", "Mastercard"])
    return "cash"


def _bank_label(bank: str) -> str:
    return _disp(BANK_DISPLAY, bank) if bank else ""


def fill_template(tmpl: str, merchant: str, amount: str, pay_label: str, bank_label: str) -> str:
    """Fill placeholders. Only substitute {bank} if the template references it."""
    text = tmpl.replace("{merchant}", merchant).replace("{amount}", amount)
    text = text.replace("{pay}", pay_label)
    if "{bank}" in text:
        text = text.replace("{bank}", bank_label if bank_label else "")
    text = re.sub(r"\s{2,}", " ", text).strip()
    # tidy spaces around the optional bank removal
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text



UPI_TOKENS = {
    "gpay": ["gpay", "g pay", "google pay", "googlepay"],
    "phonepe": ["phonepe", "phone pe"],
    "paytm": ["paytm"],
    "bhim": ["bhim"],
    "cred": ["cred"],
    "slice": ["slice"],
    "jupiter": ["jupiter"],
    "fi": ["fi money", "fi"],
    "niyo": ["niyo"],
}
BANK_TOKENS = {k: [v.lower() for v in vs] for k, vs in BANK_DISPLAY.items()}
CARD_TOKENS = ["card", "credit", "debit", "visa", "mastercard"]


def derive_method_provider_bank(text: str):
    """Derive payment_method / payment_provider / bank_account from the
    filled text so labels ALWAYS agree with the words actually present."""
    tl = text.lower()
    method = "unknown"
    provider = ""
    for prov, toks in UPI_TOKENS.items():
        if any(t in tl for t in toks):
            method = "upi"
            provider = prov
            break
    if method == "unknown" and any(c in tl for c in CARD_TOKENS):
        method = "card"
    if method == "unknown" and "cash" in tl:
        method = "cash"
    bank = ""
    for bk, toks in sorted(BANK_TOKENS.items(), key=lambda kv: -len(kv[0])):
        if any(t in tl for t in toks):
            bank = bk
            break
    return method, provider, bank


def row(text, amount, cat, method, provider, bank, source):
    return {"text": text, "amount": amount, "category": cat,
            "payment_method": method, "payment_provider": provider,
            "bank_account": bank, "text_source": source}


# Per-style target counts. Roughly 45k rows, balanced categories.
ROWS_PER_CATEGORY = 4500
STYLE_SHARES = {  # fractions of each category
    "english": 0.26,
    "hinglish": 0.32,
    "voice": 0.18,
    "ocr_upi": 0.14,
    "ocr_receipt": 0.10,
}


def main():
    templates = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))

    all_rows: list[dict] = []
    for cat in CANONICAL_CATEGORIES:
        n = ROWS_PER_CATEGORY
        for style, share in STYLE_SHARES.items():
            target = int(n * share)
            pool = templates.get(cat, {}).get(style, [])
            if not pool:
                continue
            for _ in range(target):
                tmpl = random.choice(pool)
                merchant = random.choice(CATEGORY_MERCHANTS[cat])
                amount = _amount(cat)
                method = _pick_method(cat)
                provider = _pick_provider() if method == "upi" else ""
                # bank only sometimes; more often when template wants it
                want_bank = "{bank}" in tmpl
                bank = ""
                if want_bank and random.random() < 0.85:
                    bank = _pick_bank()
                elif (not want_bank) and random.random() < 0.10:
                    bank = _pick_bank()
                pay_label = _pay_label(method, provider)
                bank_label = _bank_label(bank)
                text = fill_template(tmpl, merchant, amount, pay_label, bank_label)
                # Re-derive labels from the final text for perfect consistency
                method, provider, bank = derive_method_provider_bank(text)
                all_rows.append(row(text, amount, cat, method, provider, bank, style))

    random.shuffle(all_rows)

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    from collections import Counter
    print(f"Wrote {len(all_rows)} rows -> {OUT}")
    print("Category:", dict(Counter(r["category"] for r in all_rows).most_common()))
    print("Method:", dict(Counter(r["payment_method"] for r in all_rows).most_common()))
    print("Source:", dict(Counter(r["text_source"] for r in all_rows).most_common()))
    print("With provider:", sum(1 for r in all_rows if r["payment_provider"]))
    print("With bank:", sum(1 for r in all_rows if r["bank_account"]))


if __name__ == "__main__":
    main()