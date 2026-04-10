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


class LedgerPostRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    expense_account_code: str = "expense_misc"
    funding_account_code: str = "upi_wallet"
    source: str = "manual"
    external_ref: Optional[str] = None


class LedgerPostResponse(BaseModel):
    status: Literal["success"] = "success"
    result: dict


class LedgerBalanceResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    balances: list[dict]


AccountType = Literal["asset", "liability", "equity", "income", "expense", "investment"]


class AccountUpsertRequest(BaseModel):
    user_ref: str
    code: str
    name: str
    account_type: AccountType
    currency: str = "INR"


class AccountListResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    accounts: list[dict]


class LedgerIncomeRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    income_account_code: str = "income_misc"
    destination_account_code: str = "bank_savings"
    destination_account_type: AccountType = "asset"
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None


class LedgerInvestmentRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    investment_account_code: str = "investment_portfolio"
    funding_account_code: str = "bank_savings"
    funding_account_type: AccountType = "asset"
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None


class LedgerTransferRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    from_account_code: str
    from_account_type: AccountType
    to_account_code: str
    to_account_type: AccountType
    source: str = "manual"
    external_ref: Optional[str] = None
    occurred_at: Optional[str] = None


class LedgerOpeningBalanceRequest(BaseModel):
    user_ref: str
    account_code: str
    account_type: AccountType
    amount: float
    opening_equity_code: str = "equity_opening_balance"
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
