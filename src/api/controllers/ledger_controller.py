from fastapi import APIRouter, HTTPException, Query

from api.schemas import (
    AccountListResponse,
    AccountUpsertRequest,
    LedgerBalanceResponse,
    PrimaryFundingRequest,
    LedgerIncomeRequest,
    LedgerOpeningBalanceRequest,
    LedgerPostRequest,
    LedgerPostResponse,
    PaymentProfileListResponse,
    PaymentProfileUpsertRequest,
    LedgerReportResponse,
    LedgerTransactionsResponse,
    LedgerTransferRequest,
)
from api.services import ledger_service
from api.repositories.ledger_repository import get_breakdown

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])


@router.post("/expense", response_model=LedgerPostResponse)
async def post_expense(request: LedgerPostRequest):
    try:
        result = ledger_service.post_expense(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            funding_account_name=request.funding_account_name,
            amount=request.amount,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
            category=request.category,
            payment_method=request.payment_method,
            payment_provider=request.payment_provider,
            receipt_account_last4=request.receipt_account_last4,
            receipt_institution_hint=request.receipt_institution_hint,
            bank_hint=request.bank_hint,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.post("/income", response_model=LedgerPostResponse)
async def post_income(request: LedgerIncomeRequest):
    try:
        result = ledger_service.post_income(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            amount=request.amount,
            destination_account_name=request.destination_account_name,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
            category=request.category,
            payment_method=request.payment_method,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.post("/transfer", response_model=LedgerPostResponse)
async def post_transfer(request: LedgerTransferRequest):
    try:
        result = ledger_service.post_transfer(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            amount=request.amount,
            from_account_name=request.from_account_name,
            to_account_name=request.to_account_name,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.post("/opening-balance", response_model=LedgerPostResponse)
async def post_opening_balance(request: LedgerOpeningBalanceRequest):
    try:
        result = ledger_service.post_opening_balance(
            user_ref=request.user_ref,
            source=request.source,
            account_name=request.account_name,
            amount=request.amount,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.post("/accounts", response_model=LedgerPostResponse)
async def upsert_account(request: AccountUpsertRequest):
    try:
        result = ledger_service.upsert_account(
            user_ref=request.user_ref,
            name=request.name,
            account_type=request.account_type,
            institution_name=request.institution_name,
            account_number_last4=request.account_number_last4,
        )
        # If opening balance is provided, record it as a transaction
        if request.opening_balance and request.opening_balance > 0:
            ledger_service.post_opening_balance(
                user_ref=request.user_ref,
                source="account_creation",
                account_name=request.name,
                amount=request.opening_balance,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.get("/accounts/{user_ref}", response_model=AccountListResponse)
async def list_accounts(user_ref: str):
    accounts = ledger_service.list_accounts(user_ref)
    return AccountListResponse(user_ref=user_ref, accounts=accounts)


@router.post("/primary-funding", response_model=LedgerPostResponse)
async def set_primary_funding(request: PrimaryFundingRequest):
    try:
        result = ledger_service.set_primary_funding_account(
            request.user_ref, request.account_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.post("/accounts/{user_ref}/set-default", response_model=LedgerPostResponse)
async def set_default_account_endpoint(user_ref: str, request: dict):
    """Set an account as the default for its type (cash/bank/credit)."""
    try:
        account_name = request.get("account_name")
        if not account_name:
            raise ValueError("account_name is required")
        result = ledger_service.set_default_account(user_ref, account_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.post("/payment-profiles", response_model=LedgerPostResponse)
async def upsert_payment_profile(request: PaymentProfileUpsertRequest):
    try:
        result = ledger_service.upsert_payment_profile(
            user_ref=request.user_ref,
            provider=request.provider,
            profile_name=request.profile_name,
            linked_account_name=request.linked_account_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LedgerPostResponse(result=result)


@router.get("/payment-profiles/{user_ref}", response_model=PaymentProfileListResponse)
async def list_payment_profiles(user_ref: str):
    profiles = ledger_service.list_payment_profiles(user_ref)
    return PaymentProfileListResponse(user_ref=user_ref, profiles=profiles)


@router.get("/reports/weekly/{user_ref}", response_model=LedgerReportResponse)
async def get_weekly_report(user_ref: str):
    report = ledger_service.get_weekly_report(user_ref)
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/reports/monthly/{user_ref}", response_model=LedgerReportResponse)
async def get_monthly_report(user_ref: str):
    report = ledger_service.get_monthly_report(user_ref)
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/reports/breakdown/{user_ref}", response_model=LedgerReportResponse)
async def get_breakdown_report(
    user_ref: str,
    period: str = Query(default="month", pattern="^(week|month)$"),
    group_by: str = Query(default="account", pattern="^(account|payment_method|category)$"),
):
    days = 7 if period == "week" else 30
    rows = get_breakdown(user_ref, days=days, group_by=group_by)
    report = {"period": period, "group_by": group_by, "rows": rows}
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/transactions/{user_ref}", response_model=LedgerTransactionsResponse)
async def get_transactions(user_ref: str, limit: int = 50, offset: int = 0):
    result = ledger_service.get_transactions(user_ref=user_ref, limit=limit, offset=offset)
    return LedgerTransactionsResponse(user_ref=user_ref, result=result)
