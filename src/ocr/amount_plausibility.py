"""Heuristics to avoid treating long numeric IDs (e.g. UPI txn refs) as INR amounts."""

from __future__ import annotations

import re

# Years that commonly appear on receipt / UPI screenshots — never a rupee amount
_YEAR_RANGE = set(range(2020, 2035))

# Date-like prefixes that glue a year to text, e.g. "1Jan2026" "Mar2025" "01-01-2026"
_RE_DATE_YEAR = re.compile(
    r"(?:\d{1,2}\s*[-/.]?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    r"\s*[-/.,]?\s*(\d{4}))"
    r"|(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*[-/.,]?\s*\d{0,2}\s*[-/.,]?\s*(\d{4}))"
    r"|(?:\d{1,2}[-/.]\d{1,2}[-/.](\d{4}))"
    r"|(?:(\d{4})[-/.]\d{1,2}[-/.]\d{1,2})",
    re.I,
)


def _is_year_in_date_context(line: str, val: float) -> bool:
    """True if val is a calendar year that appears embedded in a date on this line."""
    iv = int(val)
    if iv not in _YEAR_RANGE:
        return False
    if val != iv:
        return False
    for m in _RE_DATE_YEAR.finditer(line):
        for g in m.groups():
            if g and int(g) == iv:
                return True
    s = str(iv)
    # Bare "2026" without any currency prefix → likely a year on receipts dated 2020-2034
    if re.search(r"(?:^|[^\d₹$])" + re.escape(s) + r"(?:\b|[,;.\s]|$)", line):
        if not re.search(r"[₹]\s*" + re.escape(s), line) and not re.search(
            r"(?:rs\.?|inr)\s*" + re.escape(s), line, re.I
        ):
            return True
    return False


def plausible_inr_amount(val: float) -> bool:
    """
    Drop OCR noise where a long reference (e.g. 12-digit UPI txn id) is parsed as rupees.
    Allows typical totals; rejects integer parts with 10+ digits (and absurd magnitudes).
    """
    if val is None or val <= 0:
        return False
    intpart = f"{abs(val):.2f}".split(".")[0]
    if len(intpart) >= 10:
        return False
    if val >= 1e11:
        return False
    return True


def is_likely_bank_last4_in_line(line: str, val: float) -> bool:
    """
    True when val looks like a card/account last-4 printed after a bank name (e.g. "HDFC Bank 1751"),
    not a rupee amount. OCR often merges these on UPI screenshots; callers must not treat them as ₹.

    If the same number is clearly currency-prefixed (₹ / Rs / INR) on this line, returns False.
    """
    if val is None or val <= 0:
        return False
    if val != int(val):
        return False
    iv = int(val)
    if iv < 1000 or iv > 9999:
        return False
    s = str(iv)
    if len(s) != 4:
        return False
    # Explicit currency before this exact figure → treat as payment amount
    if re.search(r"[₹]\s*" + re.escape(s) + r"(?:\b|[,.])", line) or re.search(
        r"(?:^|\s)(?:rs\.?|inr)\s*" + re.escape(s) + r"(?:\b|[,.])", line, re.I
    ):
        return False
    lower = line.lower()
    # "… Bank 1751" (Google Pay, PhonePe, etc.)
    if re.search(r"\bbank\s+" + re.escape(s) + r"\b", lower):
        return True
    # "HDFC 1751" / "Axis Bank 1751"
    if re.search(
        r"\b(?:hdfc|icici|axis|sbi|kotak|yes|idfc|union|indus|bob|rbl|pnb|canara|federal)\s+(?:bank\s+)?"
        + re.escape(s)
        + r"\b",
        lower,
    ):
        return True
    return False


# Lines like "HDFC Bank 1751" on GPay / PhonePe — last4 is the *instrument*, not the rupee amount.
_RE_INSTRUMENT_NAMED = re.compile(
    r"(?i)\b(?P<bank>hdfc|icici|axis|sbi|kotak|idfc|indusind|canara|federal|rbl|bob|pnb|bandhan)"
    r"\s+(?:bank\s+)?(?P<last4>\d{4})\b"
)
_RE_INSTRUMENT_YES = re.compile(r"(?i)\byes\s+bank\s+(?P<last4>\d{4})\b")
_RE_INSTRUMENT_UNION = re.compile(r"(?i)\bunion\s+bank\s+(?P<last4>\d{4})\b")
_RE_INSTRUMENT_BANK_ONLY = re.compile(r"(?i)\bbank\s+(?P<last4>\d{4})\b")


def extract_payment_instrument_from_lines(lines: list[str]) -> tuple[str | None, str | None]:
    """
    Find card/bank row on UPI screenshots, e.g. "HDFC Bank 1751", so the ledger can
    match the user's setup account by account_number_last4 (and optional institution hint).

    Returns (last4, institution_hint) — institution_hint is a lowercase slug for DB disambiguation.
    """
    for line in lines:
        if not line or not line.strip():
            continue
        m = _RE_INSTRUMENT_NAMED.search(line)
        if m:
            return m.group("last4"), m.group("bank").lower()
        m = _RE_INSTRUMENT_YES.search(line)
        if m:
            return m.group("last4"), "yes bank"
        m = _RE_INSTRUMENT_UNION.search(line)
        if m:
            return m.group("last4"), "union bank"
        m = _RE_INSTRUMENT_BANK_ONLY.search(line)
        if m:
            return m.group("last4"), None
    return None, None
