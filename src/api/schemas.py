"""
Pydantic Schemas
================
Defines the request/response validation models for the FastAPI endpoints.
All three pipelines (audio, text, image) converge on the same
TransactionResponse output schema.
"""

from pydantic import BaseModel
from typing import Optional, Literal


# ─── Response Models ─────────────────────────────────────────────────────

class TransactionData(BaseModel):
    """The structured financial data extracted from any input modality."""
    text_transcript: str
    amount: Optional[float] = None
    category: str
    payment_method: Optional[str] = None
    bank_account: Optional[str] = None


class TransactionResponse(BaseModel):
    """
    Uniform API response wrapper.
    Every endpoint returns this exact shape regardless of input source.
    """
    status: Literal["success", "error"] = "success"
    source: Literal["audio", "text", "image"]
    data: TransactionData


class ErrorResponse(BaseModel):
    """Returned when processing fails."""
    status: Literal["error"] = "error"
    detail: str


# ─── Request Models ──────────────────────────────────────────────────────

class TextRequest(BaseModel):
    """Request body for the /extract/text endpoint."""
    text: str


class CorrectionRequest(BaseModel):
    """Request body for the /correct endpoint (category override)."""
    keyword: str
    correct_category: str
