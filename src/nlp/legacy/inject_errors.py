"""
inject_errors.py
----------------
Reads the CLEAN canonical dataset (eda_dataset_clean.csv) and writes a MESSY,
student-facing dataset (eda_dataset_v5.csv) for the EDA teaching module.

The messy file contains the *same underlying transactions* but with realistic,
seeded data-quality defects that students must find and clean:
  - missing values (multiple sentinels: "", "NA", "null", "nan", "--")
  - whitespace + mixed-case label noise
  - label typos / synonyms (non-canonical categories)
  - exact + near-duplicate rows
  - amount anomalies (negatives, zeros, outliers, string-form amounts)
  - label noise (mislabeled rows)
  - bank canonicalization cases (display name vs canonical)

Deterministic (seed=42) so regeneration is reproducible. The clean file is kept
separately so the notebook can validate "after cleaning" against ground truth,
and the model is trained on the CLEAN file.
"""

from __future__ import annotations

import csv
import random
import re
from pathlib import Path
from collections import Counter

random.seed(42)

ROOT = Path(__file__).resolve().parent
CLEAN = ROOT / "eda_dataset_clean.csv"
OUT = ROOT / "eda_dataset_v5.csv"

FIELDNAMES = ["text", "amount", "category", "payment_method",
              "payment_provider", "bank_account", "text_source"]

CANONICAL = {"food","shopping","travel","entertainment","healthcare",
             "education","emi","utilities","investment","friends"}

# Defect targets (fraction of rows affected)
P_MISSING_AMOUNT = 0.018
P_MISSING_CATEGORY = 0.012
P_MISSING_TEXT = 0.01
P_MISSING_PROVIDER = 0.06  # provider often absent anyway, but make some NA
MISSING_SENTINELS = ["", "NA", "null", "nan", "None", "--"]

# Label typos / synonyms -> students map these back to canonical
LABEL_TYPOS = {
    "food": ["food", "foods", "Food", "dining", "meal", "restuarant", "grocery"],
    "shopping": ["shopping", "shoping", "Shopping", "purchase", "retail"],
    "travel": ["travel", "travell", "Transport", "commute", "fuel", "cab"],
    "entertainment": ["entertainment", "entrtainment", "Entertainment", "movies", "OTT", "leisure"],
    "healthcare": ["healthcare", "healthcar", "Health", "medical", "pharmacy", "hospital"],
    "education": ["education", "eduation", "Education", "tution", "school", "study"],
    "emi": ["emi", "EMI", "loan", "installment", "loans"],
    "utilities": ["utilities", "utilites", "Utilities", "bills", "recharge", "utility"],
    "investment": ["investment", "invstment", "Investment", "invest", "savings", "mutual fund"],
    "friends": ["friends", "freind", "Friends", "p2p", "transfer", "peer"],
}

# Display-name banks -> students canonicalize to the key
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


def mess_whitespace(t: str) -> str:
    s = "  " + t.strip() + "  "
    s = re.sub(r"(\s{2,})", lambda m: " " * (len(m.group(1)) + 1) if random.random() < 0.5 else m.group(1), s)
    return s.strip() if random.random() < 0.5 else s


def main():
    rows = list(csv.DictReader(open(CLEAN, encoding="utf-8")))
    n = len(rows)
    idx = list(range(n))
    random.shuffle(idx)

    # plan disjoint groups of row indices for each defect (so a row gets ~1-2 defects)
    g_missing_amount = set(idx[: int(n * P_MISSING_AMOUNT)])
    g_missing_category = set(idx[int(n * P_MISSING_AMOUNT): int(n * (P_MISSING_AMOUNT + P_MISSING_CATEGORY))])
    g_missing_text = set(idx[int(n * (P_MISSING_AMOUNT + P_MISSING_CATEGORY)): int(n * (P_MISSING_AMOUNT + P_MISSING_CATEGORY + P_MISSING_TEXT))])
    g_dup = random.sample(idx, int(n * 0.012))  # rows we duplicate
    g_outlier = set(random.sample(idx, int(n * 0.012)))
    g_mislabel = set(random.sample(idx, int(n * 0.025)))
    g_provider_na = set(random.sample([i for i in idx if rows[i]["payment_provider"]], int(n * P_MISSING_PROVIDER)))

    out_rows = []
    defect_counts = Counter()

    for i, r in enumerate(rows):
        row = dict(r)
        # default: keep canonical; but introduce a label-typo/synonym for ~40% of category values
        if random.random() < 0.40 and row["category"] in LABEL_TYPOS:
            row["category"] = random.choice(LABEL_TYPOS[row["category"]])
            defect_counts["label_typo"] += 1
        # whitespace noise on text for ~15%
        if random.random() < 0.15:
            row["text"] = mess_whitespace(row["text"])
            defect_counts["whitespace"] += 1
        # mixed-case payment method for ~10%
        if random.random() < 0.10 and row["payment_method"]:
            row["payment_method"] = random.choice([row["payment_method"].upper(), row["payment_method"].title(), row["payment_method"]])
            defect_counts["method_case"] += 1
        # bank display-name vs canonical for ~30% of banked rows
        if row["bank_account"] and random.random() < 0.30:
            row["bank_account"] = random.choice(BANK_DISPLAY.get(row["bank_account"], [row["bank_account"]]))
            defect_counts["bank_display"] += 1

        # missing values
        if i in g_missing_amount:
            row["amount"] = random.choice(MISSING_SENTINELS)
            defect_counts["missing_amount"] += 1
        if i in g_missing_category:
            row["category"] = random.choice(MISSING_SENTINELS)
            defect_counts["missing_category"] += 1
        if i in g_missing_text:
            row["text"] = random.choice(MISSING_SENTINELS)
            defect_counts["missing_text"] += 1
        if i in g_provider_na:
            row["payment_provider"] = random.choice(MISSING_SENTINELS)
            defect_counts["missing_provider"] += 1

        # amount anomalies
        if i in g_outlier:
            kind = random.random()
            if kind < 0.25:
                row["amount"] = "-" + str(row["amount"])  # negative (refund)
                defect_counts["neg_amount"] += 1
            elif kind < 0.45:
                row["amount"] = "0"
                defect_counts["zero_amount"] += 1
            elif kind < 0.70:
                row["amount"] = f"{float(row['amount']):,.2f}" if str(row["amount"]).replace("-","").replace(".","").isdigit() else row["amount"]  # string form
                defect_counts["str_amount"] += 1
            else:
                row["amount"] = str(random.choice([9999999, 999999.99, 0.01, 1234567]))
                defect_counts["outlier_amount"] += 1

        # mislabel: swap category to a wrong canonical value
        if i in g_mislabel:
            wrong = random.choice([c for c in CANONICAL if c != rows[i]["category"]])
            row["category"] = wrong
            defect_counts["mislabel"] += 1

        out_rows.append(row)

    # duplicate rows (exact + near-dup)
    dup_rows = []
    for di in g_dup:
        d = dict(out_rows[di])
        # near-duplicate: only whitespace differs
        d["text"] = "  " + d["text"].strip() + " "
        dup_rows.append(d)
        if random.random() < 0.5:
            dup_rows.append(dict(out_rows[di]))  # exact duplicate
    out_rows.extend(dup_rows)
    defect_counts["duplicates"] = len(dup_rows)

    random.shuffle(out_rows)

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Wrote {len(out_rows)} messy rows -> {OUT}  (clean had {n})")
    print("Defect counts:")
    for k, v in defect_counts.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
