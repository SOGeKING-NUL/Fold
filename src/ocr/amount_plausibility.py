"""Heuristics to avoid treating long numeric IDs (e.g. UPI txn refs) as INR amounts."""


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
