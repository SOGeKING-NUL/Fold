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
    payment_provider: Optional[str] = None
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



# Flat schema account types: cash (physical), bank (savings/current), credit (credit card)
AccountType = Literal["cash", "bank", "credit"]


class LedgerPostRequest(BaseModel):
    """Post an expense transaction."""
    user_ref: str
    amount: float
    description: str
    funding_account_name: Optional[str] = None
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    payment_provider: Optional[str] = None
    receipt_account_last4: Optional[str] = None
    receipt_institution_hint: Optional[str] = None
    bank_hint: Optional[str] = None


class LedgerPostResponse(BaseModel):
    status: Literal["success"] = "success"
    result: dict


class LedgerBalanceResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    balances: list[dict]


class PrimaryFundingRequest(BaseModel):
    user_ref: str
    account_name: str


class AccountUpsertRequest(BaseModel):
    user_ref: str
    name: str
    account_type: AccountType
    institution_name: Optional[str] = None
    account_number_last4: Optional[str] = None
    opening_balance: Optional[float] = None


class AccountListResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    accounts: list[dict]


class LedgerIncomeRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    destination_account_name: Optional[str] = None
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None


class LedgerTransferRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    from_account_name: str
    to_account_name: str
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None


class LedgerOpeningBalanceRequest(BaseModel):
    user_ref: str
    account_name: str
    amount: float
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None


class LedgerReportResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    report: dict


class LedgerTransactionsResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    result: dict


class PaymentProfileUpsertRequest(BaseModel):
    user_ref: str
    provider: str
    profile_name: str
    linked_account_name: str


class PaymentProfileListResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    profiles: list[dict]
