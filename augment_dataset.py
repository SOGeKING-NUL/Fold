"""
augment_dataset.py
------------------
Reads test_transactions.csv and produces augmented_transactions.csv
with 6 columns: text, amount, category, payment_method, location, notes.

For every English row it also generates 1-2 synthetic Hinglish rows.
It also injects ~150 rows of dirty outliers and random column noise for EDA.
"""

import csv
import re
import random

random.seed(42)

PAYMENT_METHODS = ["cash", "upi", "card"]

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
}

DEFAULT_TEMPLATES = [
    lambda m, a, p: f"{m} pe {a} {v('rupaye')} {v('kharcha')} {v('kiya')} {p} se",
    lambda m, a, p: f"{a} {v('rupaye')} {v('diye')} {m} ko {p} se",
]

AMOUNT_RE = re.compile(r"INR\s+(\d+)")
TXN_ID_RE = re.compile(r"\s*TXN[a-f0-9]+$", re.IGNORECASE)

def parse_row(text: str):
    amount_match = AMOUNT_RE.search(text)
    if not amount_match:
        return None, None
    amount = int(amount_match.group(1))
    merchant = text[: amount_match.start()].strip()
    merchant = TXN_ID_RE.sub("", merchant).strip()
    return merchant, amount

def generate_hinglish(merchant: str, amount: int, category: str, method: str):
    templates = HINGLISH_TEMPLATES.get(category, DEFAULT_TEMPLATES)
    k = random.randint(1, min(2, len(templates)))
    chosen = random.sample(templates, k)
    return [fn(merchant.lower(), str(amount), method) for fn in chosen]

def generate_outliers(num_outliers=150):
    outliers = []
    messy_amounts = ["-100", "0", "", "NaN", "five hundred", "99999999", "-5000", "1,000", "NULL"]
    messy_methods = ["csh", "ccard", "paypal", "", "bitcoin", "123", "unknown", "UPIID123"]
    messy_categories = ["misc", "unknown", "", "1234", "blabla", "error", "shopping_err"]
    messy_locations = ["Delhi", "Mumbai", "NY", "", "NaN", "123", "NULL", "Unknown"]
    messy_texts = [
        "", "NaN", "null", "<script>alert('xss')</script>",
        "just random text 123", "!@#$%^&*()", "test transaction do not process",
        "drop table users;"
    ]

    for _ in range(num_outliers):
        outliers.append({
            "text": random.choice(messy_texts) if random.random() < 0.5 else "Messy outlier tx " + random.choice(messy_methods),
            "amount": random.choice(messy_amounts),
            "category": random.choice(messy_categories),
            "payment_method": random.choice(messy_methods),
            "location": random.choice(messy_locations) if random.random() < 0.3 else "",
            "notes": "EDA test row" if random.random() < 0.2 else ""
        })
    return outliers

def main():
    input_file = "train_transactions.csv"
    output_file = "eda_dataset_v2.csv"

    rows = []

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_text = row["transaction_text"]
            category = row["category"].strip().lower()

            merchant, amount = parse_row(raw_text)
            if merchant is None:
                continue

            method = random.choice(PAYMENT_METHODS)

            clean_text = TXN_ID_RE.sub("", raw_text).strip()
            rows.append({
                "text": clean_text,
                "amount": amount,
                "category": category,
                "payment_method": method,
                "location": "",
                "notes": ""
            })

            hinglish_texts = generate_hinglish(merchant, amount, category, method)
            for ht in hinglish_texts:
                rows.append({
                    "text": ht,
                    "amount": amount,
                    "category": category,
                    "payment_method": method,
                    "location": "",
                    "notes": ""
                })

    outliers = generate_outliers(150)
    rows.extend(outliers)

    random.shuffle(rows)

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "amount", "category", "payment_method", "location", "notes"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done! Generated {len(rows)} rows -> {output_file}")
    eng = sum(1 for r in rows if isinstance(r["text"], str) and "INR" in r["text"])
    out = 150
    hin = len(rows) - eng - out
    print(f"  English rows : {eng}")
    print(f"  Hinglish rows: {hin}")
    print(f"  Outliers     : {out}")

if __name__ == "__main__":
    main()
