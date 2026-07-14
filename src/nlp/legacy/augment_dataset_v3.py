"""
augment_dataset_v3.py
---------------------
Generates eda_dataset_v3.csv — a diverse, multi-column training dataset for
the Fold DistilBERT multi-head model (category + payment_method + bank_account).

Key improvements over v2:
  - Realistic OCR-style text (UPI screenshots, physical receipts) with noise.
  - Natural Hinglish with component-based generation (not rigid templates).
  - Natural English: conversational, short-form, bank-statement narrations.
  - Voice transcript patterns (Whisper STT output simulation).
  - Rupee sign variants: ₹, Rs, Rs., INR, missing, garbled (t, ?, R).
  - Digital banks: Slice, Jupiter, Fi, Niyo, CRED-as-bank.
  - New column: bank_account (training target).
  - Column: text_source (metadata for analysis, not model input).
  - Target: ~45-50k rows with balanced category/payment/bank distributions.
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
    ROOT.parent.parent / "test_transactions.csv",
]
DEFAULT_OUTPUT = ROOT / "eda_dataset_v3.csv"

# ═══════════════════════════════════════════════════════════════════════
# Constants & Rosters
# ═══════════════════════════════════════════════════════════════════════

CANONICAL_CATEGORIES = [
    "education", "emi", "entertainment", "food", "friends",
    "healthcare", "investment", "shopping", "travel", "utilities",
]

PAYMENT_METHODS = ["cash", "upi", "card"]

UPI_PROVIDERS = [
    "gpay", "phonepe", "paytm", "bhim", "cred",
    "slice", "jupiter", "fi", "niyo",
]

UPI_PROVIDER_DISPLAY: dict[str, list[str]] = {
    "gpay": ["GPay", "Google Pay", "gpay", "G Pay", "Gpay"],
    "phonepe": ["PhonePe", "Phone Pe", "phonepe", "Phonepe"],
    "paytm": ["Paytm", "paytm", "PayTM"],
    "bhim": ["BHIM", "bhim", "Bhim"],
    "cred": ["CRED", "cred", "Cred"],
    "slice": ["Slice", "slice", "SLICE"],
    "jupiter": ["Jupiter", "jupiter"],
    "fi": ["Fi", "fi", "Fi Money"],
    "niyo": ["Niyo", "niyo", "NIYO"],
}

BANKS = [
    "hdfc", "sbi", "icici", "axis", "kotak", "pnb",
    "bob", "yes bank", "idfc", "indusind", "canara",
    "union bank", "federal bank", "rbl", "bandhan",
    "slice", "jupiter", "fi", "niyo",
]

BANK_DISPLAY: dict[str, list[str]] = {
    "hdfc": ["HDFC", "HDFC Bank", "hdfc"],
    "sbi": ["SBI", "State Bank", "sbi"],
    "icici": ["ICICI", "ICICI Bank", "icici"],
    "axis": ["Axis", "Axis Bank", "axis"],
    "kotak": ["Kotak", "Kotak Mahindra", "kotak"],
    "pnb": ["PNB", "Punjab National Bank"],
    "bob": ["BOB", "Bank of Baroda"],
    "yes bank": ["Yes Bank", "YES BANK"],
    "idfc": ["IDFC", "IDFC First", "idfc"],
    "indusind": ["IndusInd", "Indusind Bank"],
    "canara": ["Canara", "Canara Bank"],
    "union bank": ["Union Bank"],
    "federal bank": ["Federal Bank"],
    "rbl": ["RBL", "RBL Bank"],
    "bandhan": ["Bandhan", "Bandhan Bank"],
    "slice": ["Slice", "slice", "SLICE"],
    "jupiter": ["Jupiter", "jupiter"],
    "fi": ["Fi", "Fi Money"],
    "niyo": ["Niyo", "NIYO"],
}

CATEGORY_MERCHANTS: dict[str, list[str]] = {
    "food": [
        "Swiggy", "Zomato", "Dominos", "McDonald's", "KFC", "Pizza Hut",
        "Burger King", "Starbucks", "CCD", "Haldirams", "Barbeque Nation",
        "Subway", "Dunkin", "Chai Point", "Biryani Blues", "Behrouz",
        "Faasos", "EatFit", "Box8", "FreshMenu", "BigBasket", "Zepto",
        "Blinkit", "JioMart", "DMart", "Reliance Fresh", "Nature's Basket",
        "food court", "restaurant", "cafe", "dhaba", "mess", "canteen",
    ],
    "shopping": [
        "Amazon", "Flipkart", "Myntra", "Ajio", "Meesho", "Nykaa",
        "Croma", "Reliance Digital", "Tata CLiQ", "Snapdeal",
        "FirstCry", "Lenskart", "Bewakoof", "H&M", "Zara",
        "electronics store", "mall", "market",
    ],
    "travel": [
        "Uber", "Ola", "Rapido", "IRCTC", "MakeMyTrip", "Goibibo",
        "RedBus", "Yatra", "IndiGo", "SpiceJet", "Air India",
        "Cleartrip", "EaseMyTrip", "petrol pump", "HP Petrol",
        "Indian Oil", "Bharat Petroleum", "metro", "auto", "rickshaw",
    ],
    "entertainment": [
        "Netflix", "Spotify", "Hotstar", "Amazon Prime", "YouTube Premium",
        "BookMyShow", "PVR", "INOX", "JioCinema", "SonyLIV",
        "Zee5", "Apple Music", "Gaana", "gaming", "concert",
    ],
    "utilities": [
        "electricity bill", "water bill", "gas bill", "broadband",
        "Jio recharge", "Airtel recharge", "Vi recharge", "BSNL",
        "ACT Fibernet", "Tata Play", "DishTV", "mobile recharge",
        "society maintenance", "rent", "insurance premium",
    ],
    "healthcare": [
        "Apollo Pharmacy", "MedPlus", "Practo", "PharmEasy", "1mg",
        "Netmeds", "hospital", "doctor", "clinic", "dentist",
        "lab test", "diagnostic", "Lenskart", "eye checkup",
    ],
    "education": [
        "school fees", "college fees", "tuition", "Udemy", "Coursera",
        "Unacademy", "BYJU'S", "upGrad", "Vedantu", "exam fee",
        "books", "stationery", "coaching", "library",
    ],
    "emi": [
        "home loan EMI", "car loan EMI", "bike loan EMI",
        "credit card EMI", "personal loan EMI", "education loan EMI",
        "Bajaj Finance EMI", "HDFC loan", "SBI loan",
    ],
    "investment": [
        "mutual fund", "SIP", "stocks", "Zerodha", "Groww",
        "Kuvera", "PPF", "FD", "NPS", "gold", "crypto",
        "Coin", "ET Money", "Paytm Money", "Angel One",
    ],
    "friends": [
        "Rahul", "Priya", "Amit", "Neha", "Vikram", "Ananya",
        "Rohan", "Shreya", "Karan", "Divya", "Arjun", "Pooja",
        "friend", "roommate", "flatmate", "colleague", "bhai",
        "dost", "bro", "yaar",
    ],
}

CATEGORY_METHOD_WEIGHTS: dict[str, list[tuple[str, int]]] = {
    "food": [("upi", 6), ("card", 2), ("cash", 3)],
    "shopping": [("upi", 4), ("card", 5), ("cash", 1)],
    "travel": [("upi", 3), ("card", 4), ("cash", 3)],
    "entertainment": [("upi", 4), ("card", 4), ("cash", 1)],
    "utilities": [("upi", 7), ("card", 2), ("cash", 1)],
    "healthcare": [("upi", 5), ("card", 3), ("cash", 2)],
    "education": [("upi", 4), ("card", 4), ("cash", 2)],
    "emi": [("upi", 3), ("card", 7), ("cash", 0)],
    "investment": [("upi", 5), ("card", 4), ("cash", 0)],
    "friends": [("upi", 8), ("card", 1), ("cash", 2)],
}

# Alias map for normalizing source CSV categories
CATEGORY_ALIASES = {
    "dining": "food", "restaurant": "food", "grocery": "shopping",
    "groceries": "shopping", "medical": "healthcare", "pharmacy": "healthcare",
    "fuel": "travel", "cab": "travel", "rent": "utilities",
    "p2p": "friends", "transfer": "friends",
}

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _pick_method(cat: str) -> str:
    weights = CATEGORY_METHOD_WEIGHTS.get(cat, [("upi", 3), ("card", 3), ("cash", 2)])
    methods, wts = zip(*weights, strict=True)
    return random.choices(list(methods), weights=list(wts), k=1)[0]


def _pick_provider() -> str:
    return random.choices(
        UPI_PROVIDERS,
        weights=[25, 20, 15, 5, 10, 8, 5, 3, 3],
        k=1,
    )[0]


def _pick_bank() -> str:
    return random.choices(
        BANKS[:15],
        weights=[25, 20, 15, 10, 8, 5, 3, 3, 3, 2, 2, 1, 1, 1, 1],
        k=1,
    )[0]


def _pick_digital_bank() -> str:
    return random.choice(["slice", "jupiter", "fi", "niyo"])


def _disp(roster: dict[str, list[str]], key: str) -> str:
    return random.choice(roster.get(key, [key]))


def _amount(low: int = 20, high: int = 50000) -> int:
    if random.random() < 0.3:
        return random.randint(low, 500)
    if random.random() < 0.6:
        return random.randint(200, 5000)
    return random.randint(2000, high)


def _amount_f() -> str:
    """Amount with optional decimals."""
    base = _amount()
    if random.random() < 0.35:
        return f"{base + random.randint(0, 99) / 100:.2f}"
    return str(base)


def _rupee_prefix() -> str:
    """Randomized rupee sign including OCR garble variants."""
    return random.choices(
        ["₹", "Rs.", "Rs ", "INR ", "Rs", "R ", "t", "?", ""],
        weights=[20, 15, 10, 10, 8, 3, 4, 3, 20],
        k=1,
    )[0]


def _last4() -> str:
    return f"{random.randint(1000, 9999)}"


def _txn_id() -> str:
    digits = random.randint(10, 15)
    return "".join(str(random.randint(0, 9)) for _ in range(digits))


def _merchant(cat: str) -> str:
    return random.choice(CATEGORY_MERCHANTS.get(cat, ["merchant"]))


def _normalize_category(raw: str) -> str:
    c = raw.strip().lower()
    if c in CANONICAL_CATEGORIES:
        return c
    return CATEGORY_ALIASES.get(c, "shopping")


def _row(text: str, amount, cat: str, method: str, provider: str,
         bank: str, source: str) -> dict:
    return {
        "text": text.strip(),
        "amount": amount,
        "category": cat,
        "payment_method": method,
        "payment_provider": provider,
        "bank_account": bank,
        "text_source": source,
    }


# ═══════════════════════════════════════════════════════════════════════
# Generator 1: OCR UPI Screenshot Text (~8-10k rows)
# ═══════════════════════════════════════════════════════════════════════

_OCR_UPI_TEMPLATES = [
    # GPay style
    lambda m, a, app, bank, l4: f"{m} {a} Completed {random.randint(1,28)}{random.choice(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])} {random.choice(['2025','2026'])},{random.randint(1,12)}:{random.randint(0,59):02d} {random.choice(['am','pm'])} {bank} {l4} UPI transaction ID {_txn_id()}",
    # GPay with TO/FROM
    lambda m, a, app, bank, l4: f"TO:{m.upper().replace(' ','')} {m.lower().replace(' ','')}.{random.randint(10000,99999)}@{bank.lower().replace(' ','')}bank From:{random.choice(['UTSAVJANA','RAHULKUMAR','PRIYASHARMA','AMITSINGH'])} ({bank} {app} : {random.choice(['user','sender'])}{random.randint(1000,9999)}@ok{bank.lower().replace(' ','')}bank",
    # PhonePe style
    lambda m, a, app, bank, l4: f"Paid {_rupee_prefix()}{a} to {m} {app} UPI {bank} {l4} {random.choice(['Completed','Successful','Done'])}",
    # Paytm style
    lambda m, a, app, bank, l4: f"Payment of {_rupee_prefix()}{a} to {m} was successful via {app} UPI Ref No {_txn_id()} {bank} Account {l4}",
    # CRED style
    lambda m, a, app, bank, l4: f"{_rupee_prefix()}{a} paid to {m} via {app} UPI from {bank} Bank ending {l4}",
    # Slice style
    lambda m, a, app, bank, l4: f"{app} payment {_rupee_prefix()}{a} {m} {bank} {l4} {random.choice(['completed','successful','done'])}",
    # Generic UPI
    lambda m, a, app, bank, l4: f"{_rupee_prefix()}{a} debited from your {bank} account for {m} ({app} UPI)",
    # Minimal GPay
    lambda m, a, app, bank, l4: f"{m} {_rupee_prefix()}{a} {app}",
    # Full dump with noise
    lambda m, a, app, bank, l4: f"D {m.upper().replace(' ','')} {a} Completed {random.randint(1,28)}{random.choice(['Jan','Feb','Mar','Apr'])} 2026,{random.randint(1,12)}:{random.randint(0,59):02d} pm {bank} Bank {l4} UPI transaction ID {_txn_id()} TO:{m.upper().replace(' ','')} {m.lower()}.{random.randint(10000,99999)}@{bank.lower()}bank {random.choice(['Soogle','Google','Goog1e'])}transaction lD {random.choice(['CICAgJjg','XYZabc'])}{_txn_id()[:6]} OPI {app}",
    # Amount without rupee sign at all
    lambda m, a, app, bank, l4: f"{m} {a} {app} {random.choice(['Completed','Successful','Payment done'])} {bank} {l4}",
]


def generate_ocr_upi_rows(count: int = 4000) -> list[dict]:
    rows = []
    for _ in range(count):
        cat = random.choice(CANONICAL_CATEGORIES)
        merchant = _merchant(cat)
        amt = _amount_f()
        provider = _pick_provider()
        app = _disp(UPI_PROVIDER_DISPLAY, provider)
        bank = _pick_bank()
        bank_disp = _disp(BANK_DISPLAY, bank)
        l4 = _last4()
        tmpl = random.choice(_OCR_UPI_TEMPLATES)
        text = tmpl(merchant, amt, app, bank_disp, l4)
        rows.append(_row(text, amt, cat, "upi", provider, bank, "ocr_upi"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 2: OCR Physical Receipt Text (~3-4k rows)
# ═══════════════════════════════════════════════════════════════════════

_OCR_RECEIPT_TEMPLATES = [
    lambda m, a, pm: f"{m.upper()}\nItem 1 {_rupee_prefix()}{random.randint(50,500)}\nItem 2 {_rupee_prefix()}{random.randint(50,500)}\nTotal {_rupee_prefix()}{a}\n{pm}",
    lambda m, a, pm: f"TAX INVOICE\n{m}\nGrand Total: {_rupee_prefix()}{a}\nPayment: {pm}",
    lambda m, a, pm: f"{m} BILL\nSt: {_rupee_prefix()}{a}\n{pm} {random.choice(['APPROVED','approved','Approved'])}",
    lambda m, a, pm: f"Receipt #{random.randint(1000,9999)}\n{m}\nAmount Paid: {_rupee_prefix()}{a}\nMode: {pm}",
    lambda m, a, pm: f"{m}\nNet Amount {a}\nPaid via {pm}",
    lambda m, a, pm: f"{m.upper()} RESTAURANT\nTotal {a}\nCash Received\nChange 0.00",
    lambda m, a, pm: f"BILL\n{m}\n{_rupee_prefix()}{a}\n{pm}\nThank You Visit Again",
]


def generate_ocr_receipt_rows(count: int = 3000) -> list[dict]:
    rows = []
    for _ in range(count):
        cat = random.choice(["food", "shopping", "healthcare", "entertainment", "utilities"])
        merchant = _merchant(cat)
        amt = _amount_f()
        method = _pick_method(cat)
        pm_label = method.upper()
        if method == "upi":
            prov = _pick_provider()
            pm_label = _disp(UPI_PROVIDER_DISPLAY, prov)
        else:
            prov = ""
        bank = _pick_bank() if random.random() < 0.3 else ""
        tmpl = random.choice(_OCR_RECEIPT_TEMPLATES)
        text = tmpl(merchant, amt, pm_label)
        rows.append(_row(text, amt, cat, method, prov, bank, "ocr_receipt"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 3: Natural Hinglish (~12-15k rows)
# ═══════════════════════════════════════════════════════════════════════

_HINGLISH_AMOUNT_WORDS = {
    "rupaye": ["rupaye", "rupay", "rupye", "rs", "rs.", "rupaiye", "rupees", "rupiya"],
    "kharcha": ["kharcha", "kharch", "khrcha", "karcha", "kharchaa", "spend"],
    "diye": ["diye", "diy", "die", "diyee", "de diya", "de diye"],
    "kiya": ["kiya", "kia", "kya", "kiyaa", "kr diya", "kar diya"],
    "liya": ["liya", "lia", "lya", "liyaa", "le liya"],
    "bhara": ["bhara", "bhra", "bharaa", "bharra", "bhar diya"],
    "khaya": ["khaya", "khya", "khayaa", "khaaya", "kha liya"],
    "laga": ["laga", "lagaa", "lgaa", "lga", "lag gaye", "lag gaya"],
    "pada": ["pada", "pda", "pad gaya", "lag gaya"],
}


def _hv(key: str) -> str:
    return random.choice(_HINGLISH_AMOUNT_WORDS.get(key, [key]))


# Component-based: assemble from parts with random ordering and dropping

_H_ACTIONS = {
    "food": ["khana order {kiya}", "khana {khaya}", "kha liya", "mangwaya", "food order {kiya}"],
    "shopping": ["shopping {kiya}", "saman {liya}", "order {kiya}", "khareed {liya}", "buy {kiya}"],
    "travel": ["ride {liya}", "cab {liya}", "ticket book {kiya}", "petrol {bhara}", "kiraya {diye}"],
    "entertainment": ["movie dekhi", "subscription renew {kiya}", "show dekha", "ticket {liya}", "game {liya}"],
    "utilities": ["bill {bhara}", "recharge {kiya}", "bill pay {kiya}", "payment {kiya}"],
    "healthcare": ["dawai {liya}", "checkup karaya", "doctor ko {diye}", "medicine {liya}", "test karaya"],
    "education": ["fees {bhara}", "course {liya}", "tuition {diye}", "admission {kiya}", "books {liya}"],
    "emi": ["EMI {bhara}", "installment {diye}", "loan payment {kiya}", "EMI kat gayi"],
    "investment": ["invest {kiya}", "SIP {bhara}", "paisa daala", "stock {liya}", "mutual fund {kiya}"],
    "friends": ["paise bheje", "transfer {kiya}", "split {kiya}", "udhar return {kiya}", "dost ko {diye}"],
}

_H_VIA = [
    "{app} se", "{app} se pay {kiya}", "{app} pe", "via {app}",
    "{method} se", "{method} se {diye}", "{method} se pay {kiya}",
]

_H_BANK_MENTION = [
    "{bank} se", "{bank} account se", "{bank} wale account se",
    "{bank} card se", "{bank} se kata",
]

_H_CASUAL_PREFIXES = [
    "bhai", "yaar", "aaj", "kal", "abhi", "subah", "raat ko",
    "dopahar ko", "office se aate hue", "ghar jaate waqt", "",
]

_H_CASUAL_SUFFIXES = [
    "bhai", "yaar", "bc", "matlab", "bohot mehenga", "sasta tha",
    "achha deal mila", "zyada ho gaya", "budget tod diya", "",
]


def _fill_verb_slots(text: str) -> str:
    for key in _HINGLISH_AMOUNT_WORDS:
        text = text.replace(f"{{{key}}}", _hv(key))
    return text


def _generate_one_hinglish(cat: str, method: str, provider: str, bank: str) -> str:
    merchant = _merchant(cat)
    amt = str(_amount())
    rp = random.choice(["rupaye", "rupay", "rs", "rs.", "₹", "rupaiye", "rupees", ""])

    action = random.choice(_H_ACTIONS.get(cat, ["kharcha {kiya}"]))
    action = _fill_verb_slots(action)

    via_label = ""
    if method == "upi" and provider:
        app = _disp(UPI_PROVIDER_DISPLAY, provider)
        via_tmpl = random.choice(_H_VIA)
        via_label = _fill_verb_slots(via_tmpl.replace("{app}", app).replace("{method}", "UPI"))
    elif method == "card":
        via_label = _fill_verb_slots(random.choice(["card se", "credit card se", "debit card se", "card se pay {kiya}"]))
    elif method == "cash":
        via_label = _fill_verb_slots(random.choice(["cash {diye}", "cash me", "naqad", "haath se {diye}"]))

    bank_mention = ""
    if bank and random.random() < 0.5:
        bank_d = _disp(BANK_DISPLAY, bank)
        bm_tmpl = random.choice(_H_BANK_MENTION)
        bank_mention = _fill_verb_slots(bm_tmpl.replace("{bank}", bank_d))

    parts = []
    if random.random() < 0.3:
        parts.append(random.choice(_H_CASUAL_PREFIXES))

    structures = [
        [merchant, "pe" if random.random() < 0.5 else "me", amt, rp, "ka", action, via_label, bank_mention],
        [amt, rp, action, merchant, "pe" if random.random() < 0.5 else "ko", via_label, bank_mention],
        [merchant, "ka", action, amt, rp, via_label, bank_mention],
        [merchant, amt, rp, via_label, bank_mention],
        [amt, rp, merchant, via_label],
        [merchant, "se", action, amt, rp, "ka", via_label, bank_mention],
    ]
    parts.extend(random.choice(structures))

    if random.random() < 0.15:
        parts.append(random.choice(_H_CASUAL_SUFFIXES))

    text = " ".join(p for p in parts if p).strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text


def generate_natural_hinglish(count: int = 12000) -> list[dict]:
    rows = []
    for _ in range(count):
        cat = random.choice(CANONICAL_CATEGORIES)
        method = _pick_method(cat)
        provider = _pick_provider() if method == "upi" else ""
        bank = ""
        if random.random() < 0.4:
            bank = _pick_bank() if random.random() < 0.7 else _pick_digital_bank()
        text = _generate_one_hinglish(cat, method, provider, bank)
        amt_match = re.search(r"\d+", text)
        amt = amt_match.group() if amt_match else str(_amount())
        rows.append(_row(text, amt, cat, method, provider, bank, "hinglish_natural"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 4: Natural English (~8-10k rows)
# ═══════════════════════════════════════════════════════════════════════

_E_CONVERSATIONAL = [
    lambda m, a, pm, bank: f"Paid {_rupee_prefix()}{a} for {m} via {pm}",
    lambda m, a, pm, bank: f"Spent {_rupee_prefix()}{a} on {m} using {pm}",
    lambda m, a, pm, bank: f"{m} {_rupee_prefix()}{a} {pm}",
    lambda m, a, pm, bank: f"Bought {m} for {_rupee_prefix()}{a} with {pm}",
    lambda m, a, pm, bank: f"{_rupee_prefix()}{a} charged for {m} on {pm}",
    lambda m, a, pm, bank: f"Just paid {_rupee_prefix()}{a} to {m} through {pm}",
    lambda m, a, pm, bank: f"{m} payment {_rupee_prefix()}{a} done via {pm}",
    lambda m, a, pm, bank: f"Paid {m} {_rupee_prefix()}{a} using {pm}" + (f" from {bank}" if bank else ""),
    lambda m, a, pm, bank: f"{_rupee_prefix()}{a} to {m} via {pm}" + (f" {bank} account" if bank else ""),
]

_E_SHORT = [
    lambda m, a, pm, bank: f"{m} {a}",
    lambda m, a, pm, bank: f"{m} {a} {pm}",
    lambda m, a, pm, bank: f"{a} {m}",
    lambda m, a, pm, bank: f"{m} {a} {bank}" if bank else f"{m} {a}",
    lambda m, a, pm, bank: f"{a} {pm} {m}",
]

_E_STATEMENT = [
    lambda m, a, pm, bank: f"UPI/{_txn_id()[:8]}/{m.upper()}/{bank.upper() if bank else 'BANK'}",
    lambda m, a, pm, bank: f"POS/{m.upper()}/{pm.upper()}/{_last4()}",
    lambda m, a, pm, bank: f"{m.upper()} INR {a}" + (f" {bank.upper()}" if bank else ""),
    lambda m, a, pm, bank: f"NEFT/TRANSFER/{m.upper()}/{bank.upper() if bank else ''}",
    lambda m, a, pm, bank: f"ATM/CASH/{bank.upper() if bank else 'BANK'}/{a}",
]

_E_WITH_BANK = [
    lambda m, a, pm, bank: f"Paid {_rupee_prefix()}{a} for {m} from my {bank} account via {pm}",
    lambda m, a, pm, bank: f"{m} {_rupee_prefix()}{a} debited from {bank}",
    lambda m, a, pm, bank: f"Used {bank} {pm} to pay {_rupee_prefix()}{a} for {m}",
    lambda m, a, pm, bank: f"{_rupee_prefix()}{a} paid to {m} via {pm} from {bank}",
]


def generate_natural_english(count: int = 8000) -> list[dict]:
    rows = []
    for _ in range(count):
        cat = random.choice(CANONICAL_CATEGORIES)
        merchant = _merchant(cat)
        amt = _amount_f()
        method = _pick_method(cat)
        provider = _pick_provider() if method == "upi" else ""
        bank = ""
        if random.random() < 0.45:
            bank = _pick_bank() if random.random() < 0.7 else _pick_digital_bank()

        pm_label = method
        if method == "upi" and provider:
            pm_label = _disp(UPI_PROVIDER_DISPLAY, provider)
        elif method == "card":
            pm_label = random.choice(["card", "credit card", "debit card", "Visa", "Mastercard"])
        elif method == "cash":
            pm_label = "cash"

        bank_label = _disp(BANK_DISPLAY, bank) if bank else ""

        r = random.random()
        if r < 0.35:
            tmpl = random.choice(_E_CONVERSATIONAL)
        elif r < 0.55:
            tmpl = random.choice(_E_SHORT)
        elif r < 0.70:
            tmpl = random.choice(_E_STATEMENT)
        elif bank:
            tmpl = random.choice(_E_WITH_BANK)
        else:
            tmpl = random.choice(_E_CONVERSATIONAL)

        text = tmpl(merchant, amt, pm_label, bank_label)
        rows.append(_row(text, amt, cat, method, provider, bank, "english_natural"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 5: Voice Transcript Patterns (~4-5k rows)
# ═══════════════════════════════════════════════════════════════════════

_VOICE_TEMPLATES = [
    lambda m, a, pm, bank: f"spent {a} rupees on {m} via {pm}",
    lambda m, a, pm, bank: f"i paid {a} rupees for {m} using {pm}",
    lambda m, a, pm, bank: f"{m} ka {a} rupees ka bill {pm} se pay kiya",
    lambda m, a, pm, bank: f"aaj {m} pe {a} rupaye kharcha hua {pm} se",
    lambda m, a, pm, bank: f"i did {a} expense on {m} using {pm}",
    lambda m, a, pm, bank: f"{a} rupees {m} {pm}" + (f" {bank} account" if bank else ""),
    lambda m, a, pm, bank: f"maine {a} rupaye {m} ko diye {pm} se",
    lambda m, a, pm, bank: f"paid {a} to {m} through {pm}" + (f" from {bank}" if bank else ""),
    lambda m, a, pm, bank: f"bhai {m} ka {a} rupaye {pm} se de diya",
    lambda m, a, pm, bank: f"{m} mein {a} lag gaye {pm} se bhara",
    lambda m, a, pm, bank: f"today i spent {a} on {m} via {pm}" + (f" from my {bank} bank" if bank else ""),
    lambda m, a, pm, bank: f"{a} ka {m} bill pay kiya {pm} se" + (f" {bank} se kata" if bank else ""),
]


def generate_voice_transcripts(count: int = 4500) -> list[dict]:
    rows = []
    for _ in range(count):
        cat = random.choice(CANONICAL_CATEGORIES)
        merchant = _merchant(cat)
        amt = str(_amount())
        method = _pick_method(cat)
        provider = _pick_provider() if method == "upi" else ""
        bank = ""
        if random.random() < 0.35:
            bank = _pick_bank() if random.random() < 0.7 else _pick_digital_bank()

        pm_label = method
        if method == "upi" and provider:
            pm_label = _disp(UPI_PROVIDER_DISPLAY, provider)
        bank_label = _disp(BANK_DISPLAY, bank) if bank else ""

        tmpl = random.choice(_VOICE_TEMPLATES)
        text = tmpl(merchant, amt, pm_label, bank_label)
        # voice transcripts often lack punctuation
        text = text.replace(",", "").replace(".", "")
        rows.append(_row(text, amt, cat, method, provider, bank, "voice_transcript"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 6: Friends / P2P dedicated rows (~2k)
# ═══════════════════════════════════════════════════════════════════════

_FRIEND_TEMPLATES = [
    lambda name, a, app: f"sent {_rupee_prefix()}{a} to {name} on {app}",
    lambda name, a, app: f"dost {name} ko {a} rupaye {app} se bheje",
    lambda name, a, app: f"split bill {a} {app} se {name} ko diya",
    lambda name, a, app: f"paid {name} {_rupee_prefix()}{a} via {app}",
    lambda name, a, app: f"{name} ko {a} transfer kiya {app} se",
    lambda name, a, app: f"bhai {name} ko udhar return kiya {a} rs {app} se",
    lambda name, a, app: f"{_rupee_prefix()}{a} to {name} {app} UPI",
    lambda name, a, app: f"dinner split {a} rupaye {name} {app}",
    lambda name, a, app: f"flatmate rent share {a} {app} {name}",
    lambda name, a, app: f"sent money to {name} {_rupee_prefix()}{a} on {app}",
]


def generate_friend_rows(count: int = 2000) -> list[dict]:
    rows = []
    for _ in range(count):
        name = random.choice(CATEGORY_MERCHANTS["friends"])
        amt = str(_amount(50, 25000))
        method = _pick_method("friends")
        provider = _pick_provider() if method == "upi" else ""
        app = _disp(UPI_PROVIDER_DISPLAY, provider) if provider else method
        bank = _pick_bank() if random.random() < 0.2 else ""

        tmpl = random.choice(_FRIEND_TEMPLATES)
        text = tmpl(name, amt, app)
        rows.append(_row(text, amt, "friends", method, provider, bank, "friends_synthetic"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 7: Source CSV expansion (keep original English rows)
# ═══════════════════════════════════════════════════════════════════════

AMOUNT_RE = re.compile(r"INR\s+(\d+)")
TXN_ID_RE = re.compile(r"\s*TXN[a-f0-9]+$", re.IGNORECASE)


def load_and_expand_source(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_text = row.get("transaction_text", row.get("text", ""))
            cat = _normalize_category(row.get("category", "shopping"))

            amount_match = AMOUNT_RE.search(raw_text)
            if not amount_match:
                continue
            amount = int(amount_match.group(1))
            merchant_part = raw_text[:amount_match.start()].strip()
            merchant_part = TXN_ID_RE.sub("", merchant_part).strip()

            method = _pick_method(cat)
            provider = _pick_provider() if method == "upi" else ""
            bank = _pick_bank() if random.random() < 0.3 else ""
            clean = TXN_ID_RE.sub("", raw_text).strip()
            rows.append(_row(clean, amount, cat, method, provider, bank, "source_english"))

            # Hinglish expansion
            h_text = _generate_one_hinglish(cat, method, provider, bank)
            rows.append(_row(h_text, amount, cat, method, provider, bank, "source_hinglish"))

    return rows


# ═══════════════════════════════════════════════════════════════════════
# Generator 8: Category cue rows (lexical anchors for DistilBERT)
# ═══════════════════════════════════════════════════════════════════════

_CATEGORY_CUE_TEMPLATES = {
    "food": [
        "lunch dinner food order swiggy zomato restaurant meal {rp}{a} {p}",
        "grocery vegetables milk bread fruits {rp}{a} paid {p}",
        "breakfast snacks chai coffee {rp}{a} {p}",
    ],
    "shopping": [
        "amazon flipkart myntra online shopping order {rp}{a} {p}",
        "electronics clothes shoes accessories purchase {rp}{a} via {p}",
    ],
    "travel": [
        "uber ola cab ride airport train ticket {rp}{a} {p}",
        "petrol diesel fuel {rp}{a} at pump {p}",
        "flight booking travel ticket {rp}{a} {p}",
    ],
    "entertainment": [
        "netflix spotify hotstar subscription movie show {rp}{a} {p}",
        "gaming concert event ticket {rp}{a} {p}",
    ],
    "utilities": [
        "electricity water broadband mobile recharge bill {rp}{a} {p}",
        "rent maintenance gas connection {rp}{a} {p}",
    ],
    "healthcare": [
        "hospital doctor pharmacy medicine diagnostic {rp}{a} {p}",
        "medical checkup lab test health insurance {rp}{a} {p}",
    ],
    "education": [
        "school college tuition course books fees {rp}{a} {p}",
        "coaching exam preparation study material {rp}{a} {p}",
    ],
    "emi": [
        "home loan car loan credit card EMI monthly {rp}{a} autopay {p}",
        "personal loan installment EMI deduction {rp}{a} {p}",
    ],
    "investment": [
        "mutual fund SIP stocks PPF FD investment {rp}{a} {p}",
        "crypto gold bonds NPS portfolio {rp}{a} {p}",
    ],
    "friends": [
        "sent {rp}{a} to friend on {p} split bill UPI",
        "paid back friend lent money {rp}{a} {p}",
    ],
}


def generate_cue_rows(count: int = 3000) -> list[dict]:
    rows = []
    for _ in range(count):
        cat = random.choice(CANONICAL_CATEGORIES)
        amt = str(_amount())
        method = _pick_method(cat)
        provider = _pick_provider() if method == "upi" else ""
        bank = _pick_bank() if random.random() < 0.2 else ""
        pm_label = method
        if method == "upi" and provider:
            pm_label = _disp(UPI_PROVIDER_DISPLAY, provider)
        rp = _rupee_prefix()
        cues = _CATEGORY_CUE_TEMPLATES.get(cat, ["{rp}{a} {p}"])
        tmpl = random.choice(cues)
        text = tmpl.format(rp=rp, a=amt, p=pm_label)
        rows.append(_row(text, amt, cat, method, provider, bank, "cue_row"))
    return rows


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

def resolve_input_path() -> Path | None:
    for p in INPUT_CANDIDATES:
        if p.is_file():
            return p
    return None


def main():
    all_rows: list[dict] = []

    # Source CSV expansion
    src = resolve_input_path()
    if src:
        source_rows = load_and_expand_source(src)
        all_rows.extend(source_rows)
        print(f"Source CSV rows: {len(source_rows)} (from {src})")
    else:
        print("No source CSV found, skipping source expansion.")

    # OCR UPI screenshots
    ocr_upi = generate_ocr_upi_rows(4500)
    all_rows.extend(ocr_upi)
    print(f"OCR UPI rows: {len(ocr_upi)}")

    # OCR physical receipts
    ocr_receipt = generate_ocr_receipt_rows(3000)
    all_rows.extend(ocr_receipt)
    print(f"OCR receipt rows: {len(ocr_receipt)}")

    # Natural Hinglish
    hinglish = generate_natural_hinglish(13000)
    all_rows.extend(hinglish)
    print(f"Natural Hinglish rows: {len(hinglish)}")

    # Natural English
    english = generate_natural_english(9000)
    all_rows.extend(english)
    print(f"Natural English rows: {len(english)}")

    # Voice transcripts
    voice = generate_voice_transcripts(5000)
    all_rows.extend(voice)
    print(f"Voice transcript rows: {len(voice)}")

    # Friends P2P
    friends = generate_friend_rows(2500)
    all_rows.extend(friends)
    print(f"Friends rows: {len(friends)}")

    # Category cue rows
    cues = generate_cue_rows(3500)
    all_rows.extend(cues)
    print(f"Cue rows: {len(cues)}")

    random.shuffle(all_rows)

    fieldnames = ["text", "amount", "category", "payment_method", "payment_provider", "bank_account", "text_source"]
    output = DEFAULT_OUTPUT
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nTotal rows: {len(all_rows)} -> {output}")

    # Distribution stats
    from collections import Counter
    cat_dist = Counter(r["category"] for r in all_rows)
    method_dist = Counter(r["payment_method"] for r in all_rows)
    source_dist = Counter(r["text_source"] for r in all_rows)
    bank_dist = Counter(r["bank_account"] for r in all_rows if r["bank_account"])
    prov_dist = Counter(r["payment_provider"] for r in all_rows if r["payment_provider"])

    print("\nCategory distribution:")
    for k, v in sorted(cat_dist.items()):
        print(f"  {k}: {v}")
    print("\nPayment method distribution:")
    for k, v in sorted(method_dist.items()):
        print(f"  {k}: {v}")
    print("\nText source distribution:")
    for k, v in sorted(source_dist.items()):
        print(f"  {k}: {v}")
    print(f"\nRows with bank_account: {sum(bank_dist.values())}")
    print(f"Rows with payment_provider: {sum(prov_dist.values())}")
    print(f"\nTop banks: {bank_dist.most_common(10)}")
    print(f"Top providers: {prov_dist.most_common(10)}")


if __name__ == "__main__":
    main()
