"""
augment_dataset.py
------------------
Reads train_transactions.csv and produces eda_dataset_v2.csv
with columns: text, amount, category, payment_method, payment_provider, location, notes.

Improvements for categorization:
- Resolves input path (project root or src/nlp/train_transactions.csv).
- Normalizes categories to the canonical training label set.
- Picks payment_method with category-aware weights (UPI-heavy for daily spend, etc.).
- Adds explicit English cue lines per category to strengthen DistilBERT features.
- friends: Hinglish + English P2P / split-bill templates (retrain model to predict this label).
- UPI English templates include occasional "bank + last4" noise with correct ₹ amount in text.
- Outliers: not injected; output is clean for production retraining.
"""

from __future__ import annotations

import csv
import random
import re
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent
INPUT_CANDIDATES = [
    ROOT / "train_transactions.csv",
    ROOT / "src" / "nlp" / "train_transactions.csv",
]
DEFAULT_OUTPUT = ROOT / "eda_dataset_v2.csv"

PAYMENT_METHODS = ("cash", "upi", "card")

# UPI providers we want the NLP layer to recognise
UPI_PROVIDERS = ["gpay", "phonepe", "paytm", "bhim", "cred"]

# Human-readable names used inside generated text
UPI_PROVIDER_DISPLAY: dict[str, list[str]] = {
    "gpay": ["GPay", "Google Pay", "gpay"],
    "phonepe": ["PhonePe", "Phone Pe", "phonepe"],
    "paytm": ["Paytm", "paytm"],
    "bhim": ["BHIM", "bhim"],
    "cred": ["CRED", "cred"],
}

# Canonical labels (must match inference VALID_CATEGORIES for a clean retrain)
CANONICAL_CATEGORIES = frozenset(
    {
        "education",
        "emi",
        "entertainment",
        "food",
        "friends",
        "healthcare",
        "investment",
        "shopping",
        "travel",
        "utilities",
    }
)

# Rough (method, weight) — higher weight = more likely for that category
_CATEGORY_METHOD_WEIGHTS: dict[str, tuple[tuple[str, int], ...]] = {
    "food": (("upi", 5), ("card", 2), ("cash", 3)),
    "shopping": (("upi", 4), ("card", 4), ("cash", 1)),
    "travel": (("upi", 3), ("card", 5), ("cash", 1)),
    "entertainment": (("upi", 4), ("card", 3), ("cash", 2)),
    "utilities": (("upi", 6), ("card", 3), ("cash", 1)),
    "healthcare": (("upi", 5), ("card", 4), ("cash", 1)),
    "education": (("upi", 5), ("card", 4), ("cash", 1)),
    "emi": (("upi", 4), ("card", 6), ("cash", 0)),
    "investment": (("upi", 5), ("card", 4), ("cash", 0)),
    "friends": (("upi", 8), ("card", 1), ("cash", 2)),
    "misc": (("upi", 3), ("card", 3), ("cash", 2)),
}

_DEFAULT_METHOD_WEIGHTS = (("upi", 3), ("card", 2), ("cash", 2))


def _pick_payment_method(category: str) -> str:
    weights = _CATEGORY_METHOD_WEIGHTS.get(category, _DEFAULT_METHOD_WEIGHTS)
    methods, wts = zip(*weights, strict=True)
    return random.choices(list(methods), weights=list(wts), k=1)[0]


def _normalize_category(raw: str) -> str:
    c = raw.strip().lower()
    if c in CANONICAL_CATEGORIES:
        return c
    # Light aliases from dirty source data
    aliases = {
        "dining": "food",
        "restaurant": "food",
        "grocery": "shopping",
        "groceries": "shopping",
        "medical": "healthcare",
        "pharmacy": "healthcare",
        "fuel": "travel",
        "cab": "travel",
        "rent": "utilities",
        "p2p": "friends",
        "transfer": "friends",
    }
    return aliases.get(c, "misc" if c not in CANONICAL_CATEGORIES else c)


# Extra English lines with strong lexical cues (helps DistilBERT)
_CATEGORY_CUE_TEMPLATES: dict[str, list[str]] = {
    "food": [
        "lunch dinner food order swiggy zomato restaurant meal ₹{a} {p}",
        "grocery vegetables milk bread ₹{a} paid {p}",
    ],
    "shopping": [
        "amazon flipkart myntra online shopping order ₹{a} {p}",
        "electronics clothes purchase ₹{a} via {p}",
    ],
    "travel": [
        "uber ola cab ride airport train ticket ₹{a} {p}",
        "petrol diesel fuel ₹{a} at pump {p}",
    ],
    "entertainment": [
        "netflix spotify hotstar subscription movie show ₹{a} {p}",
    ],
    "utilities": [
        "electricity water broadband mobile recharge bill ₹{a} {p}",
    ],
    "healthcare": [
        "hospital doctor pharmacy medicine diagnostic ₹{a} {p}",
    ],
    "education": [
        "school college tuition course books fees ₹{a} {p}",
    ],
    "emi": [
        "home loan car loan credit card EMI monthly ₹{a} autopay {p}",
    ],
    "investment": [
        "mutual fund SIP stocks PPF FD investment ₹{a} {p}",
    ],
    "friends": [
        "sent ₹{a} to friend on {p} split bill UPI",
        "paid back friend lent money ₹{a} {p}",
        "birthday gift money transfer friend ₹{a} via {p}",
    ],
}

# English UPI screenshot-style sentences (injected when method == upi)
UPI_ENGLISH_TEMPLATES = [
    lambda m, a, app: f"Rs. {a} sent to {m} via {app} UPI",
    lambda m, a, app: f"{app}: Payment of ₹{a} to {m} successful",
    lambda m, a, app: f"Paid ₹{a} to {m} using {app}",
    lambda m, a, app: f"₹{a} debited from your account for {m} ({app} UPI)",
    lambda m, a, app: f"{m} INR {a} paid through {app}",
    lambda m, a, app: f"Transaction successful — ₹{a} to {m} via {app} UPI",
    lambda m, a, app: f"{app} payment ₹{a} {m}",
]

# Occasional realistic receipt clutter: amount is still ₹{a} in the same line
_UPI_BANK_NOISE_SUFFIXES = [
    " HDFC Bank {last4}",
    " paid from account …{last4}",
    " SBI {last4}",
]

AMOUNT_WORDS = {
    "rupaye": ["rupaye", "rupay", "rupye", "rs", "rs.", "rupaiye"],
    "kharcha": ["kharcha", "kharch", "khrcha", "karcha", "kharchaa"],
    "diye": ["diye", "diy", "die", "diyee"],
    "kiya": ["kiya", "kia", "kya", "kiyaa"],
    "liya": ["liya", "lia", "lya", "liyaa"],
    "bhara": ["bhara", "bhra", "bharaa", "bharra"],
    "khaya": ["khaya", "khya", "khayaa", "khaaya"],
    "laga": ["laga", "lagaa", "lgaa", "lga"],
}


def v(key: str) -> str:
    return random.choice(AMOUNT_WORDS.get(key, [key]))


HINGLISH_TEMPLATES = {
    "food": [
        lambda m, a, p: f"{m} me {a} {v('rupaye')} ka khana {v('khaya')} {p} se",
        lambda m, a, p: f"{a} {v('rupaye')} {v('kharcha')} {v('kiya')} {m} pe {p} se",
        lambda m, a, p: f"{m} pe {a} ka bill tha, {p} se pay {v('kiya')}",
        lambda m, a, p: f"aaj {m} se khana order {v('kiya')} {a} {v('rupaye')} {p} se {v('diye')}",
        lambda m, a, p: f"{m} ka khana {a} {v('rupaye')} me aaya {p} se {v('diye')}",
    ],
    "shopping": [
        lambda m, a, p: f"{m} se {a} {v('rupaye')} ka shopping {v('kiya')} {p} se",
        lambda m, a, p: f"{a} {v('rupaye')} ka order {v('diye')} {m} pe {p} se",
        lambda m, a, p: f"{m} pe shopping {v('kiya')} {a} {v('rupaye')} {v('kharcha')} {p} se",
        lambda m, a, p: f"online {m} se {a} ka saman {v('liya')} {p} se pay {v('kiya')}",
    ],
    "travel": [
        lambda m, a, p: f"{m} ka kiraya {a} {v('rupaye')} {v('diye')} {p} se",
        lambda m, a, p: f"{a} {v('rupaye')} {v('laga')} {m} me {p} se {v('diye')}",
        lambda m, a, p: f"{m} ki ticket {a} {v('rupaye')} me book {v('kiya')} {p} se",
        lambda m, a, p: f"aaj {m} {v('liya')} {a} {v('rupaye')} {p} se pay {v('kiya')}",
    ],
    "entertainment": [
        lambda m, a, p: f"{m} ka ticket {a} {v('rupaye')} me {v('liya')} {p} se",
        lambda m, a, p: f"{a} {v('rupaye')} {v('kharcha')} {v('kiya')} {m} pe {p} se",
        lambda m, a, p: f"{m} ka subscription {a} {v('rupaye')} {p} se renew {v('kiya')}",
        lambda m, a, p: f"{m} dekha {a} {v('rupaye')} {v('laga')} {p} se {v('diye')}",
    ],
    "utilities": [
        lambda m, a, p: f"{m} ka bill {a} {v('rupaye')} {p} se {v('bhara')}",
        lambda m, a, p: f"{a} {v('rupaye')} ka {m} bill pay {v('kiya')} {p} se",
        lambda m, a, p: f"{m} recharge {v('kiya')} {a} {v('rupaye')} {p} se",
        lambda m, a, p: f"aaj {m} ka {a} {v('rupaye')} ka bill {p} se {v('bhara')}",
    ],
    "healthcare": [
        lambda m, a, p: f"{m} me {a} {v('rupaye')} {v('kharcha')} hua {p} se {v('diye')}",
        lambda m, a, p: f"doctor ke yahan {a} {v('rupaye')} {v('laga')} {p} se {v('diye')}",
        lambda m, a, p: f"{a} {v('rupaye')} ka {m} bill aaya {p} se pay {v('kiya')}",
        lambda m, a, p: f"{m} pe {a} {v('rupaye')} {v('kharcha')} hui davai pe {p} se",
    ],
    "education": [
        lambda m, a, p: f"{m} ki fees {a} {v('rupaye')} {p} se {v('bhara')}",
        lambda m, a, p: f"{a} {v('rupaye')} {v('diye')} {m} ke liye {p} se",
        lambda m, a, p: f"{m} ka course {a} {v('rupaye')} me {v('liya')} {p} se pay {v('kiya')}",
        lambda m, a, p: f"padhai ke liye {m} pe {a} {v('rupaye')} {v('kharcha')} {v('kiya')} {p} se",
    ],
    "emi": [
        lambda m, a, p: f"{m} ki EMI {a} {v('rupaye')} {p} se {v('bhara')}",
        lambda m, a, p: f"{a} {v('rupaye')} ka {m} installment {p} se {v('diye')}",
        lambda m, a, p: f"loan ka {m} {a} {v('rupaye')} {p} se pay {v('kiya')}",
        lambda m, a, p: f"{m} EMI {a} {v('rupaye')} kat gaye {p} se",
    ],
    "investment": [
        lambda m, a, p: f"{m} me {a} {v('rupaye')} invest {v('kiya')} {p} se",
        lambda m, a, p: f"{a} {v('rupaye')} {m} me daale {p} se",
        lambda m, a, p: f"{m} ka SIP {a} {v('rupaye')} {p} se {v('bhara')}",
        lambda m, a, p: f"aaj {m} me {a} {v('rupaye')} lagaye {p} se",
    ],
    "friends": [
        lambda m, a, p: f"dost ko {a} {v('rupaye')} {p} se bheje",
        lambda m, a, p: f"{a} {v('rupaye')} friend ko UPI {p} se transfer",
        lambda m, a, p: f"split bill {a} {v('rupaye')} {p} se {v('diye')}",
        lambda m, a, p: f"kal raat dinner split {a} {v('rupaye')} {p}",
        lambda m, a, p: f"bhai ko udhaar return {a} {v('rupaye')} {p} se",
    ],
}

DEFAULT_TEMPLATES = [
    lambda m, a, p: f"{m} pe {a} {v('rupaye')} {v('kharcha')} {v('kiya')} {p} se",
    lambda m, a, p: f"{a} {v('rupaye')} {v('diye')} {m} ko {p} se",
]

AMOUNT_RE = re.compile(r"INR\s+(\d+)")
TXN_ID_RE = re.compile(r"\s*TXN[a-f0-9]+$", re.IGNORECASE)

# Synthetic friend / P2P merchants (no row in train_transactions.csv)
_FRIEND_MERCHANTS = [
    "Rahul",
    "Priya",
    "Amit",
    "Neha",
    "Vikram",
    "Ananya",
    "split dinner group",
    "flatmate rent share",
]


def parse_row(text: str):
    amount_match = AMOUNT_RE.search(text)
    if not amount_match:
        return None, None
    amount = int(amount_match.group(1))
    merchant = text[: amount_match.start()].strip()
    merchant = TXN_ID_RE.sub("", merchant).strip()
    return merchant, amount


def generate_hinglish(merchant: str, amount: int, category: str, method: str, provider: str | None = None):
    templates = HINGLISH_TEMPLATES.get(category, DEFAULT_TEMPLATES)
    k = random.randint(1, min(2, len(templates)))
    chosen = random.sample(templates, k)
    payment_label = method
    if provider and method == "upi":
        payment_label = random.choice(UPI_PROVIDER_DISPLAY.get(provider, [provider]))
    return [fn(merchant.lower(), str(amount), payment_label) for fn in chosen]


def _payment_label(method: str, provider: str | None) -> str:
    if provider and method == "upi":
        return random.choice(UPI_PROVIDER_DISPLAY.get(provider, [provider]))
    return method


def _add_category_cue_row(
    rows: list[dict], category: str, amount: int, method: str, provider: str
) -> None:
    cues = _CATEGORY_CUE_TEMPLATES.get(category)
    if not cues:
        return
    tmpl = random.choice(cues)
    pl = _payment_label(method, provider or None)
    text = tmpl.format(a=amount, p=pl)
    rows.append(
        {
            "text": text,
            "amount": amount,
            "category": category,
            "payment_method": method,
            "payment_provider": provider if method == "upi" else "",
            "location": "",
            "notes": "",
        }
    )


def generate_friend_only_rows(target_count: int = 400) -> list[dict]:
    """Pure synthetic P2P — category always friends."""
    out: list[dict] = []
    for _ in range(target_count):
        amount = random.randint(50, 25000)
        merchant = random.choice(_FRIEND_MERCHANTS)
        method = _pick_payment_method("friends")
        provider = random.choice(UPI_PROVIDERS) if method == "upi" else ""
        for ht in generate_hinglish(merchant, amount, "friends", method, provider or None):
            out.append(
                {
                    "text": ht,
                    "amount": amount,
                    "category": "friends",
                    "payment_method": method,
                    "payment_provider": provider,
                    "location": "",
                    "notes": "",
                }
            )
        if method == "upi" and provider:
            app_display = random.choice(UPI_PROVIDER_DISPLAY.get(provider, [provider]))
            tmpl = random.choice(UPI_ENGLISH_TEMPLATES)
            out.append(
                {
                    "text": tmpl(merchant, str(amount), app_display),
                    "amount": amount,
                    "category": "friends",
                    "payment_method": "upi",
                    "payment_provider": provider,
                    "location": "",
                    "notes": "",
                }
            )
        _add_category_cue_row(out, "friends", amount, method, provider)
    return out


def generate_outliers(num_outliers: int = 120) -> list[dict]:
    outliers = []
    messy_amounts = ["-100", "0", "", "NaN", "five hundred", "99999999", "-5000", "1,000", "NULL"]
    messy_methods = ["csh", "ccard", "paypal", "", "bitcoin", "123", "unknown", "UPIID123"]
    # Avoid labels that are valid categories — reduces accidental mis-training
    messy_categories = ["1234", "blabla", "error", "shopping_err", "unknown", "junk_tag"]
    messy_locations = ["Delhi", "Mumbai", "NY", "", "NaN", "123", "NULL", "Unknown"]
    messy_texts = [
        "",
        "NaN",
        "null",
        "just random text 123",
        "!@#$%^&*()",
        "test transaction do not process",
    ]

    for _ in range(num_outliers):
        outliers.append(
            {
                "text": random.choice(messy_texts)
                if random.random() < 0.5
                else "Messy outlier tx " + random.choice(messy_methods),
                "amount": random.choice(messy_amounts),
                "category": random.choice(messy_categories),
                "payment_method": random.choice(messy_methods),
                "payment_provider": "",
                "location": random.choice(messy_locations) if random.random() < 0.3 else "",
                "notes": "EDA test row" if random.random() < 0.2 else "",
            }
        )
    return outliers


def resolve_input_path() -> Path:
    for p in INPUT_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "train_transactions.csv not found. Tried:\n  " + "\n  ".join(str(p) for p in INPUT_CANDIDATES)
    )


def main():
    input_file = resolve_input_path()
    output_file = DEFAULT_OUTPUT

    rows: list[dict] = []

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_text = row["transaction_text"]
            category = _normalize_category(row.get("category", "misc"))

            merchant, amount = parse_row(raw_text)
            if merchant is None:
                continue

            method = _pick_payment_method(category)

            provider = ""
            if method == "upi":
                provider = random.choice(UPI_PROVIDERS)

            clean_text = TXN_ID_RE.sub("", raw_text).strip()
            rows.append(
                {
                    "text": clean_text,
                    "amount": amount,
                    "category": category,
                    "payment_method": method,
                    "payment_provider": provider,
                    "location": "",
                    "notes": "",
                }
            )

            hinglish_texts = generate_hinglish(merchant, amount, category, method, provider or None)
            for ht in hinglish_texts:
                rows.append(
                    {
                        "text": ht,
                        "amount": amount,
                        "category": category,
                        "payment_method": method,
                        "payment_provider": provider,
                        "location": "",
                        "notes": "",
                    }
                )

            _add_category_cue_row(rows, category, amount, method, provider)

            if method == "upi" and provider:
                app_display = random.choice(UPI_PROVIDER_DISPLAY.get(provider, [provider]))
                tmpl = random.choice(UPI_ENGLISH_TEMPLATES)
                line = tmpl(merchant, str(amount), app_display)
                if random.random() < 0.25:
                    last4 = f"{random.randint(0, 9999):04d}"
                    line = line + random.choice(_UPI_BANK_NOISE_SUFFIXES).format(last4=last4)
                rows.append(
                    {
                        "text": line,
                        "amount": amount,
                        "category": category,
                        "payment_method": "upi",
                        "payment_provider": provider,
                        "location": "",
                        "notes": "",
                    }
                )

    rows.extend(generate_friend_only_rows(350))

    random.shuffle(rows)

    fieldnames = ["text", "amount", "category", "payment_method", "payment_provider", "location", "notes"]
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done! Read {input_file}")
    print(f"Generated {len(rows)} rows -> {output_file}")
    eng = sum(1 for r in rows if isinstance(r["text"], str) and "INR" in r["text"])
    out = 0
    upi_rows = sum(1 for r in rows if r.get("payment_provider"))
    hin = len(rows) - eng
    print(f"  English rows   : {eng}")
    print(f"  Hinglish rows  : {hin}")
    print(f"  Outliers       : {out}")
    print(f"  UPI w/ provider: {upi_rows}")


if __name__ == "__main__":
    main()
