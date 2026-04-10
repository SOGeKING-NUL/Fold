from fastapi import APIRouter

from api.schemas import LedgerBalanceResponse, LedgerPostRequest, LedgerPostResponse
from api.services.ledger_service import LedgerPostRequest as LedgerServicePostRequest
from api.services.ledger_service import LedgerService

router = APIRouter(prefix="/api/v1/ledger", tags=["ledger"])
ledger_service = LedgerService()


@router.post("/expense", response_model=LedgerPostResponse)
async def post_expense(request: LedgerPostRequest):
    result = ledger_service.post_expense(
        LedgerServicePostRequest(
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


@router.get("/balances/{user_ref}", response_model=LedgerBalanceResponse)
async def get_balances(user_ref: str):
    balances = ledger_service.get_balances(user_ref)
    return LedgerBalanceResponse(user_ref=user_ref, balances=balances)
