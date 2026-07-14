"""
generate_templates.py
---------------------
One-time helper that uses OpenRouter (DeepSeek v3.1) to create a curated pool
of natural sentence TEMPLATES per (category, style). Output is committed as
a JSON asset (src/nlp/natural_templates.json) so the dataset generator can run
fully offline and reproducibly. Students never need the API key.

A "template" is a natural sentence containing placeholders:
  {merchant} {amount} {pay} {bank}
{bank} is optional and omitted from a template when not referenced.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

MODEL = "deepseek/deepseek-chat-v3.1"
ROOT = Path(__file__).resolve().parent
ENV = ROOT.parent.parent / ".env"
OUT = ROOT / "natural_templates.json"

CATEGORIES = {
    "food": ["Swiggy", "Zomato", "Dominos", "McDonald's", "restaurant", "cafe", "Biryani Blues", "Haldirams", "groceries", "Chai Point"],
    "shopping": ["Amazon", "Flipkart", "Myntra", "Ajio", "Meesho", "Nykaa", "Croma", "H&M", "Zara", "mall"],
    "travel": ["Uber", "Ola", "Rapido", "IRCTC", "MakeMyTrip", "IndiGo", "petrol pump", "RedBus", "Cleartrip", "auto"],
    "entertainment": ["Netflix", "Hotstar", "PVR", "BookMyShow", "SonyLIV", "Spotify", "concert", "INOX", "JioCinema", "game"],
    "healthcare": ["Apollo Pharmacy", "doctor", "dentist", "lab test", "Netmeds", "MedPlus", "checkup", "hospital", "physio", "PharmEasy"],
    "education": ["upGrad", "tuition", "course", "books", "fees", "coaching", "Udemy", "Coursera", "stationery", "exam fee"],
    "emi": ["car loan EMI", "bike loan EMI", "home loan EMI", "education loan EMI", "credit card EMI", "personal loan EMI", "EMI", "installment"],
    "utilities": ["electricity bill", "Jio recharge", "gas bill", "broadband", "rent", "water bill", "Airtel recharge", "DTH recharge", "mobile recharge", "wifi bill"],
    "investment": ["mutual fund SIP", "stocks", "PPF", "gold", "crypto", "index fund", "NPS", "FD", "Groww", "Angel One"],
    "friends": ["Rahul", "Neha", "roommate", "friend", "flatmate", "Arjun", "Priya", "Ananya", "brother", "sister"],
}

STYLES = {
    "english": "Natural conversational English, as a person would type into a money app.",
    "hinglish": "Natural HINGLISH (Hindi + English mixed, roman script), casual with words like se, pe, kiya, diya, liya, yaar, bhai.",
    "voice": "A transcribed voice note style - short, run-on, no punctuation, possibly starting with 'i', 'main', 'aaj', 'bhai'.",
    "ocr_upi": "A concise UPI payment screenshot notification line (e.g. 'Paid Rs 450 to Swiggy via GPay', 'Payment of 450 to merchant successful'). Mention the app name.",
    "ocr_receipt": "A concise physical receipt summary line (e.g. 'Swiggy total 450 paid via GPay', 'Apollo Pharmacy net amount 850 GPay'). One line, no newlines.",
}


def load_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    if ENV.is_file():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY"):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("OPENROUTER_API_KEY not found in env or .env")


def make_session():
    s = requests.Session()
    s.trust_env = False  # ignore broken proxy env vars on this machine
    return s


def call(sess, key, prompt, retries=5):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 1.0, "max_tokens": 1400}
    for attempt in range(retries):
        r = sess.post("https://openrouter.ai/api/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json=body, timeout=120)
        if r.ok:
            return r.json()["choices"][0]["message"]["content"]
        if r.status_code == 429:
            wait = 12 + attempt * 4
            print(f"  429, waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    raise RuntimeError("rate-limited after retries")


PH = r"\{merchant\}|\{amount\}|\{pay\}|\{bank\}"


def clean_templates(raw):
    out = []
    seen = set()
    for line in raw.splitlines():
        l = line.strip().strip('"').strip()
        if not l or l.startswith("###") or l.startswith(("-", "*", "#")):
            continue
        l = re.sub(r"^\d+[\.\)\-]\s*", "", l)
        if not re.search(PH, l):
            continue
        if re.search(r"merchant\s*:|amount\s*:|category\s*:|pay\s*:", l, re.I):
            continue
        if l.endswith(":") or l.endswith("-"):
            continue
        if len(l) < 8 or len(l) > 140:
            continue
        l = re.sub(r"\s{2,}", " ", l)
        key = l.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(l)
    return out


def build_prompt(cat, style_key, style_desc, merchants):
    ms = ", ".join(merchants[:8])
    return (
        f"You write realistic transaction notes Indian users type into a money-tracking app.\n"
        f"Write 14 DIFFERENT natural sentence TEMPLATES for the {cat.upper()} category in this style: {style_desc}\n"
        f"Use ONLY these placeholders: {{merchant}} {{amount}} {{pay}} {{bank}}.\n"
        f"- {{merchant}} is one of: {ms}\n"
        f"- {{amount}} is a rupees number\n"
        f"- {{pay}} is a payment app/method (GPay, PhonePe, Paytm, CRED, cash, card)\n"
        f"- {{bank}} is a bank name; OPTIONAL - only include {{bank}} in a few templates, omit it from the rest.\n"
        f"Rules:\n"
        f"- Each line = one template only. No numbering, no quotes, no labels like 'merchant:', no explanations.\n"
        f"- Vary wording and structure. {{amount}} is just the number (the rupee symbol is implied, do not add it).\n"
        f"- Do not put placeholders for anything other than merchant/amount/pay/bank.\n"
        f"Examples of good templates:\n"
        f"  {{merchant}} order for {{amount}} via {{pay}}\n"
        f"  {{merchant}} pe {{amount}} ka kharcha {{pay}} se\n"
        f"  Paid {{amount}} to {{merchant}} from {{bank}} using {{pay}}\n"
    )


def main():
    key = load_key()
    sess = make_session()
    pool = {}
    total_calls = 0

    for cat, merchants in CATEGORIES.items():
        pool[cat] = {}
        for style_key, style_desc in STYLES.items():
            prompt = build_prompt(cat, style_key, style_desc, merchants)
            total_calls += 1
            print(f"[{total_calls}] {cat}/{style_key} ...", flush=True)
            raw = call(sess, key, prompt)
            tpls = clean_templates(raw)
            tries = 1
            while len(tpls) < 10 and tries < 3:
                print(f"   only {len(tpls)} valid, retrying ({tries})...", flush=True)
                raw2 = call(sess, key, prompt)
                tpls += clean_templates(raw2)
                tpls = list({t.lower(): t for t in tpls}.values())
                tries += 1
            pool[cat][style_key] = tpls
            print(f"   -> {len(tpls)} templates", flush=True)
            time.sleep(1)

    OUT.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for c in pool.values() for v in c.values())
    print(f"\nSaved {total} templates across {len(CATEGORIES)} cats x {len(STYLES)} styles -> {OUT}")
    for sk in STYLES:
        n = sum(len(c.get(sk, [])) for c in pool.values())
        print(f"  {sk}: {n}")


if __name__ == "__main__":
    main()