"""
Detect whether UPI / payment screenshots describe money out (expense) vs money in (income),
using common app phrases like “paid to” vs “received from”.
"""

from __future__ import annotations

import re
from typing import Literal

CashFlow = Literal["expense", "income"]

# (substring after normalize, score). Longer / clearer phrases first.
_INCOME_HINTS: tuple[tuple[str, int], ...] = (
    ("received from", 10),
    ("you received", 9),
    ("payment received", 8),
    ("money received", 8),
    ("incoming", 6),
    ("credited to", 5),
)

_EXPENSE_HINTS: tuple[tuple[str, int], ...] = (
    ("paid to", 10),
    ("you paid", 9),
    ("money sent", 8),
    ("sent to", 7),
    ("you sent", 7),
    ("paid using", 6),
    ("debited from", 6),
    ("debited to", 5),
)


def detect_cash_flow_from_text(text: str) -> CashFlow | None:
    """
    Return expense vs income when the text clearly matches payment-app wording.
    If both sides score (noisy OCR), the higher score wins; a tie returns None.
    """
    if not text or not text.strip():
        return None
    lower = re.sub(r"\s+", " ", text.lower()).strip()

    inc = 0
    for phrase, w in _INCOME_HINTS:
        if phrase in lower:
            inc += w

    exp = 0
    for phrase, w in _EXPENSE_HINTS:
        if phrase in lower:
            exp += w

    if inc > exp:
        return "income"
    if exp > inc:
        return "expense"
    return None
