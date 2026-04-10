from fastapi import APIRouter, Query

from api.schemas import (
    AccountListResponse,
    AccountUpsertRequest,
    LedgerBalanceResponse,
    LedgerIncomeRequest,
    LedgerInvestmentRequest,
    LedgerOpeningBalanceRequest,
    LedgerPostRequest,
    LedgerPostResponse,
    LedgerReportResponse,
    LedgerTransactionsResponse,
    LedgerTransferRequest,
)
from api.services.ledger_service import LedgerService
from api.services.ledger_service import (
    AccountUpsertRequest as ServiceAccountUpsertRequest,
    ExpenseRequest,
    IncomeRequest,
    InvestmentRequest,
    OpeningBalanceRequest,
    TransferRequest,
)

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])
ledger_service = LedgerService()


@router.post("/expense", response_model=LedgerPostResponse)
async def post_expense(request: LedgerPostRequest):
    result = ledger_service.post_expense(
        ExpenseRequest(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            expense_account_code=request.expense_account_code,
            funding_account_code=request.funding_account_code,
            amount=request.amount,
            external_ref=request.external_ref,
        )
    )
    return LedgerPostResponse(result=result)


@router.post("/income", response_model=LedgerPostResponse)
async def post_income(request: LedgerIncomeRequest):
    result = ledger_service.post_income(
        IncomeRequest(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            amount=request.amount,
            income_account_code=request.income_account_code,
            destination_account_code=request.destination_account_code,
            destination_account_type=request.destination_account_type,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
            category=request.category,
            payment_method=request.payment_method,
        )
    )
    return LedgerPostResponse(result=result)


@router.post("/investment", response_model=LedgerPostResponse)
async def post_investment(request: LedgerInvestmentRequest):
    result = ledger_service.post_investment(
        InvestmentRequest(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            amount=request.amount,
            investment_account_code=request.investment_account_code,
            funding_account_code=request.funding_account_code,
            funding_account_type=request.funding_account_type,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
            category=request.category,
            payment_method=request.payment_method,
        )
    )
    return LedgerPostResponse(result=result)


@router.post("/transfer", response_model=LedgerPostResponse)
async def post_transfer(request: LedgerTransferRequest):
    result = ledger_service.post_transfer(
        TransferRequest(
            user_ref=request.user_ref,
            source=request.source,
            description=request.description,
            amount=request.amount,
            from_account_code=request.from_account_code,
            from_account_type=request.from_account_type,
            to_account_code=request.to_account_code,
            to_account_type=request.to_account_type,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
        )
    )
    return LedgerPostResponse(result=result)


@router.post("/opening-balance", response_model=LedgerPostResponse)
async def post_opening_balance(request: LedgerOpeningBalanceRequest):
    result = ledger_service.post_opening_balance(
        OpeningBalanceRequest(
            user_ref=request.user_ref,
            source=request.source,
            account_code=request.account_code,
            account_type=request.account_type,
            amount=request.amount,
            opening_equity_code=request.opening_equity_code,
            external_ref=request.external_ref,
            occurred_at=request.occurred_at,
        )
    )
    return LedgerPostResponse(result=result)


@router.post("/accounts", response_model=LedgerPostResponse)
async def upsert_account(request: AccountUpsertRequest):
    result = ledger_service.upsert_account(
        ServiceAccountUpsertRequest(
            user_ref=request.user_ref,
            code=request.code,
            name=request.name,
            account_type=request.account_type,
            currency=request.currency,
        )
    )
    return LedgerPostResponse(result=result)


@router.get("/accounts/{user_ref}", response_model=AccountListResponse)
async def list_accounts(user_ref: str):
    accounts = ledger_service.list_accounts(user_ref)
    return AccountListResponse(user_ref=user_ref, accounts=accounts)


@router.get("/balances/{user_ref}", response_model=LedgerBalanceResponse)
async def get_balances(user_ref: str):
    balances = ledger_service.get_balances(user_ref)
    return LedgerBalanceResponse(user_ref=user_ref, balances=balances)


@router.get("/reports/weekly/{user_ref}", response_model=LedgerReportResponse)
async def get_weekly_report(user_ref: str):
    report = ledger_service.get_weekly_report(user_ref)
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/reports/monthly/{user_ref}", response_model=LedgerReportResponse)
async def get_monthly_report(user_ref: str):
    report = ledger_service.get_monthly_report(user_ref)
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/reports/cashflow/{user_ref}", response_model=LedgerReportResponse)
async def get_cashflow_report(user_ref: str, period: str = Query(default="month", pattern="^(week|month)$")):
    report = ledger_service.get_cashflow_report(user_ref, period=period)
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/reports/breakdown/{user_ref}", response_model=LedgerReportResponse)
async def get_breakdown_report(
    user_ref: str,
    period: str = Query(default="month", pattern="^(week|month)$"),
    group_by: str = Query(default="account", pattern="^(account|payment_method|category)$"),
):
    report = ledger_service.get_breakdown(user_ref=user_ref, period=period, group_by=group_by)
    return LedgerReportResponse(user_ref=user_ref, report=report)


@router.get("/transactions/{user_ref}", response_model=LedgerTransactionsResponse)
async def get_transactions(user_ref: str, limit: int = 50, offset: int = 0):
    result = ledger_service.get_transactions(user_ref=user_ref, limit=limit, offset=offset)
    return LedgerTransactionsResponse(user_ref=user_ref, result=result)
