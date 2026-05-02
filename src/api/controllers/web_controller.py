"""
Web Dashboard API Controller
==============================
Session-gated endpoints that the Next.js frontend calls.
All routes live under /api/v1/web/.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from api.services.web_auth_service import (
    create_session,
    exchange_token,
    validate_session,
    destroy_session,
)
from api.services.ledger_service import LedgerService

router = APIRouter(prefix="/api/v1/web", tags=["web-dashboard"])
ledger_service = LedgerService()

SESSION_COOKIE = "fold_session"
COOKIE_MAX_AGE = 86400 * 7


class LoginRequest(BaseModel):
    user_ref: str


def _require_session(request: Request) -> dict:
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = validate_session(sid)
    if session is None:
        raise HTTPException(status_code=401, detail="Session expired")
    return session


@router.get("/auth/exchange")
async def auth_exchange(token: str, response: Response):
    """Exchange a one-time magic-link token for a session cookie."""
    result = exchange_token(token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=result["session_id"],
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        secure=False,
    )
    return {"status": "ok", "user_ref": result["user_ref"]}


@router.get("/auth/me")
async def auth_me(request: Request):
    """Return the current session's user info."""
    session = _require_session(request)
    return {"user_ref": session["user_ref"]}


@router.post("/auth/login")
async def auth_login(payload: LoginRequest, response: Response):
    """Direct web login with a user reference."""
    try:
        result = create_session(payload.user_ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response.set_cookie(
        key=SESSION_COOKIE,
        value=result["session_id"],
        httponly=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        secure=False,
    )
    return {"status": "ok", "user_ref": result["user_ref"]}


@router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        destroy_session(sid)
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/dashboard")
async def get_dashboard(
    request: Request,
    period: str = Query(default="monthly", pattern="^(weekly|monthly)$"),
):
    """
    Single composite endpoint for the reports dashboard.
    Returns summary totals, breakdowns, balances, and recent transactions
    all using the same period window.
    """
    session = _require_session(request)
    user_ref = session["user_ref"]

    now = datetime.utcnow()
    if period == "weekly":
        days = 7
    else:
        days = max(1, now.day)

    summary = ledger_service.repository.get_report_window_summary(user_ref, days=days)
    income = int(summary["income_minor"])
    expense = int(summary["expense_minor"])
    investment = int(summary["investment_minor"])
    net = income - expense - investment

    by_category = ledger_service.repository.get_breakdown(user_ref, days=days, group_by="category")
    by_payment_method = ledger_service.repository.get_breakdown(user_ref, days=days, group_by="payment_method")
    by_account = ledger_service.repository.get_breakdown(user_ref, days=days, group_by="account")

    balances = ledger_service.get_cash_snapshot(user_ref)
    tx_result = ledger_service.get_transactions(user_ref, limit=20, offset=0)
    transactions = tx_result.get("rows", []) if isinstance(tx_result, dict) else tx_result

    daily_trend = ledger_service.repository.get_daily_trend(user_ref, days=days)

    period_label = (
        f"Last 7 days"
        if period == "weekly"
        else f"{now.strftime('%B %Y')} (month to date)"
    )

    return {
        "period": period,
        "period_label": period_label,
        "window_days": days,
        "summary": {
            "income_minor": income,
            "expense_minor": expense,
            "investment_minor": investment,
            "net_cashflow_minor": net,
        },
        "by_category": [dict(r) for r in by_category],
        "by_payment_method": [dict(r) for r in by_payment_method],
        "by_account": [dict(r) for r in by_account],
        "balances": [dict(r) for r in balances],
        "daily_trend": [_serialize_transaction(t) for t in daily_trend],
        "recent_transactions": [_serialize_transaction(t) for t in transactions],
    }


@router.get("/transactions")
async def get_transactions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    session = _require_session(request)
    user_ref = session["user_ref"]
    tx_result = ledger_service.get_transactions(user_ref, limit=limit, offset=offset)
    rows = tx_result.get("rows", []) if isinstance(tx_result, dict) else tx_result
    return {
        "transactions": [_serialize_transaction(t) for t in rows],
        "limit": limit,
        "offset": offset,
    }


def _serialize_transaction(t: dict) -> dict:
    """Ensure all values are JSON-serializable."""
    out = {}
    for k, v in t.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif hasattr(v, "items"):
            out[k] = dict(v)
        else:
            out[k] = v
    return out
