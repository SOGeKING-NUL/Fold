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
    cash_flow: Optional[Literal["expense", "income"]] = None


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


AccountType = Literal["asset", "liability", "equity", "income", "expense", "investment"]


class LedgerPostRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    expense_account_code: str = "expense_operating"
    funding_account_code: Optional[str] = None
    funding_account_type: Optional[AccountType] = None
    source: str = "manual"
    external_ref: Optional[str] = None
    payment_provider: Optional[str] = None


class LedgerPostResponse(BaseModel):
    status: Literal["success"] = "success"
    result: dict


class LedgerBalanceResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    balances: list[dict]


class PrimaryFundingRequest(BaseModel):
    user_ref: str
    account_code: str
    account_type: AccountType


class AccountUpsertRequest(BaseModel):
    user_ref: str
    code: str
    name: str
    account_type: AccountType
    currency: str = "INR"
    institution_name: Optional[str] = None
    account_number_last4: Optional[str] = None
    is_digital: bool = False


class AccountListResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    accounts: list[dict]


class LedgerIncomeRequest(BaseModel):
    user_ref: str
    amount: float
    description: str
    income_account_code: str = "income_operating"
    destination_account_code: Optional[str] = None
    destination_account_type: Optional[AccountType] = None
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
    funding_account_code: Optional[str] = None
    funding_account_type: Optional[AccountType] = None
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


class PaymentProfileUpsertRequest(BaseModel):
    user_ref: str
    profile_type: Literal["upi", "card", "wallet", "bank_app"]
    provider: str
    profile_name: str
    linked_account_code: str
    handle_ref: Optional[str] = None


class PaymentProfileListResponse(BaseModel):
    status: Literal["success"] = "success"
    user_ref: str
    profiles: list[dict]
