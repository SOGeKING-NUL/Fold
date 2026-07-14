"""
Web Dashboard API Controller
==============================
Clerk-authenticated endpoints that the Next.js frontend calls.
All routes live under /api/v1/web/.

Auth flow (simple):
  1. Frontend signs in via Clerk (handled entirely by @clerk/nextjs).
  2. Frontend calls our API with: Authorization: Bearer <clerk-jwt>
  3. We verify the JWT, find-or-create the user in our DB, and proceed.

That's it — one auth system, no cookies, no magic links.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.middleware.clerk_auth import clerk_auth
from api.repositories.user_repository import get_or_create_user_from_clerk
from api.repositories.ledger_repository import get_report_window_summary, get_breakdown
from api.services import ledger_service

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/web", tags=["web-dashboard"])

# ── Shared auth dependency ─────────────────────────────────────────────
# Every endpoint below uses this. It:
#   1. Reads the Authorization header
#   2. Verifies the Clerk JWT
#   3. Creates the user in our DB if they don't exist yet
#   4. Returns a dict with user_ref and clerk_user_id

async def get_current_user(request: Request) -> dict:
    """
    Dependency: verify the Clerk JWT and return user info.

    Returns:
        {
            "user_ref": "user_2abc...",    # our DB identifier
            "clerk_user_id": "user_2abc...",
            "email": "...",
            "full_name": "...",
        }
    """
    # Step 1: Verify the Clerk JWT from the Authorization header
    user_info = await clerk_auth.get_current_user(request)
    if not user_info:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Step 2: Find or create the user in our database
    user = get_or_create_user_from_clerk(
        clerk_user_id=user_info["clerk_user_id"],
        email=user_info.get("email"),
        full_name=user_info.get("full_name"),
        avatar_url=user_info.get("avatar_url"),
    )

    return {
        "user_ref": user_info["clerk_user_id"],
        "clerk_user_id": user_info["clerk_user_id"],
        "user_id": user["id"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
    }


# ═══════════════════════════════════════════════════════════════════════
# Auth Endpoints
# ═══════════════════════════════════════════════════════════════════════

@router.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """
    Return the current user's info.

    The frontend calls this on page load to get the user_ref
    needed for other API calls (accounts, transactions, etc.).
    """
    return {
        "user_ref": user["user_ref"],
        "email": user.get("email"),
        "full_name": user.get("full_name"),
    }


# ═══════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def get_dashboard(
    user: dict = Depends(get_current_user),
    period: str = Query(default="monthly", pattern="^(weekly|monthly)$"),
):
    """
    Single composite endpoint for the reports dashboard.
    Returns summary totals, breakdowns, balances, and recent transactions.
    """
    user_ref = user["user_ref"]
    user_id = user["user_id"]

    now = datetime.utcnow()
    days = 7 if period == "weekly" else max(1, now.day)

    from api.db.connection import get_db_connection
    with get_db_connection() as conn:
        summary = get_report_window_summary(user_id, days=days, conn=conn)
        income = int(summary["income_minor"])
        expense = int(summary["expense_minor"])
        net = income - expense

        by_category = get_breakdown(user_id, days=days, group_by="category", conn=conn)
        by_payment_method = get_breakdown(user_id, days=days, group_by="payment_method", conn=conn)
        by_account = get_breakdown(user_id, days=days, group_by="account", conn=conn)

        accounts = ledger_service.list_accounts(user_ref)
        tx_result = ledger_service.get_transactions(user_ref, limit=20, offset=0)
        transactions = tx_result.get("rows", []) if isinstance(tx_result, dict) else tx_result

    period_label = (
        "Last 7 days"
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
            "investment_minor": 0,
            "net_cashflow_minor": net,
        },
        "by_category": [dict(r) for r in by_category],
        "by_payment_method": [dict(r) for r in by_payment_method],
        "by_account": [dict(r) for r in by_account],
        "accounts": [dict(r) for r in accounts],
        "daily_trend": [],
        "recent_transactions": [_serialize(t) for t in transactions],
    }


# ═══════════════════════════════════════════════════════════════════════
# Transactions
# ═══════════════════════════════════════════════════════════════════════

@router.get("/transactions")
async def get_transactions(
    user: dict = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    user_ref = user["user_ref"]
    tx_result = ledger_service.get_transactions(user_ref, limit=limit, offset=offset)
    rows = tx_result.get("rows", []) if isinstance(tx_result, dict) else tx_result
    return {
        "transactions": [_serialize(t) for t in rows],
        "limit": limit,
        "offset": offset,
    }


# ── Helper ─────────────────────────────────────────────────────────────

def _serialize(t: dict) -> dict:
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
