from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from api.config import get_settings
from api.repositories.ledger_repository import LedgerRepository


AccountType = Literal["asset", "liability", "equity", "income", "expense", "investment"]


@dataclass
class AccountUpsertRequest:
    user_ref: str
    code: str
    name: str
    account_type: AccountType
    currency: str = "INR"
    institution_name: str | None = None
    account_number_last4: str | None = None
    is_digital: bool = False


@dataclass
class PaymentProfileUpsertRequest:
    user_ref: str
    profile_type: Literal["upi", "card", "wallet", "bank_app"]
    provider: str
    profile_name: str
    linked_account_code: str
    handle_ref: str | None = None


POOLED_EXPENSE_CODE = "expense_operating"
POOLED_INCOME_CODE = "income_operating"
POOLED_INVESTMENT_CODE = "investment_portfolio"

# Physical cash pocket / wallet — use this code so balances and transfers stay consistent.
CASH_WALLET_CODE = "cash_wallet"
# Sentinel last4: real bank cards should use other digits; cash uses 0000 for onboarding/listing.
CASH_PLACEHOLDER_LAST4 = "0000"


@dataclass
class ExpenseRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    expense_account_code: str = POOLED_EXPENSE_CODE
    funding_account_code: str | None = None
    funding_account_type: AccountType | None = None
    external_ref: str | None = None
    occurred_at: str | None = None
    category: str | None = None
    payment_method: str | None = None
    payment_provider: str | None = None
    # From OCR receipt row, e.g. "HDFC Bank 1751" — overrides UPI-app link when resolved in DB
    receipt_account_last4: str | None = None
    receipt_institution_hint: str | None = None
    # From NLP bank name detection, e.g. "slice", "hdfc" — used to match user accounts by name
    bank_hint: str | None = None


@dataclass
class IncomeRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    income_account_code: str = POOLED_INCOME_CODE
    destination_account_code: str | None = None
    destination_account_type: AccountType | None = None
    external_ref: str | None = None
    occurred_at: str | None = None
    category: str | None = None
    payment_method: str | None = None


@dataclass
class InvestmentRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    investment_account_code: str = POOLED_INVESTMENT_CODE
    funding_account_code: str | None = None
    funding_account_type: AccountType | None = None
    external_ref: str | None = None
    occurred_at: str | None = None
    category: str | None = None
    payment_method: str | None = None


@dataclass
class TransferRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    from_account_code: str
    from_account_type: AccountType
    to_account_code: str
    to_account_type: AccountType
    external_ref: str | None = None
    occurred_at: str | None = None


@dataclass
class OpeningBalanceRequest:
    user_ref: str
    source: str
    account_code: str
    account_type: AccountType
    amount: float
    opening_equity_code: str = "equity_opening_balance"
    external_ref: str | None = None
    occurred_at: str | None = None


class LedgerService:
    def __init__(self, repository: LedgerRepository | None = None) -> None:
        self.repository = repository or LedgerRepository()

    @staticmethod
    def _to_minor(amount: float) -> int:
        amount_minor = int(round(amount * 100))
        if amount_minor <= 0:
            raise ValueError("Amount must be positive")
        cap = get_settings().max_transaction_inr
        if amount > cap:
            raise ValueError(
                f"Amount ₹{amount:,.2f} exceeds the single-transaction limit of ₹{cap:,.2f}. "
                "If this is real, adjust MAX_TRANSACTION_INR."
            )
        return amount_minor

    def _check_asset_sufficient(self, user_ref: str, account_code: str, account_type: str, spend_minor: int) -> None:
        if account_type != "asset":
            return
        current = self.repository.get_account_balance_minor(user_ref, account_code)
        if current - spend_minor < 0:
            raise ValueError(
                f"Insufficient balance in {account_code} (₹{current / 100:,.2f}). "
                f"Cannot spend ₹{spend_minor / 100:,.2f}."
            )

    def upsert_account(self, payload: AccountUpsertRequest) -> dict:
        user = self.repository.get_or_create_user(payload.user_ref)
        account_last4 = payload.account_number_last4
        if account_last4 is not None:
            account_last4 = "".join(ch for ch in account_last4 if ch.isdigit())
            if len(account_last4) != 4:
                raise ValueError("account_number_last4 must contain exactly 4 digits")
        account = self.repository.get_or_create_account(
            user_id=int(user["id"]),
            code=payload.code,
            name=payload.name,
            account_type=payload.account_type,
            institution_name=payload.institution_name,
            account_number_last4=account_last4,
            is_digital=payload.is_digital,
        )
        if account_last4 and len(account_last4) == 4 and payload.account_type in ("asset", "liability"):
            self._maybe_seed_primary_from_single_account(payload.user_ref)
        return account

    def ensure_cash_wallet_account(self, user_ref: str) -> dict:
        """Create or refresh the physical cash asset (listed with banks; balances enforced on spend)."""
        return self.upsert_account(
            AccountUpsertRequest(
                user_ref=user_ref,
                code=CASH_WALLET_CODE,
                name="Cash on hand",
                account_type="asset",
                institution_name="Cash",
                account_number_last4=CASH_PLACEHOLDER_LAST4,
                is_digital=False,
            )
        )

    def resolve_primary_cash_account(
        self, user_ref: str, *, spending: bool = True
    ) -> tuple[str, AccountType] | None:
        """
        Primary account for expenses/investment funding (spending=True: asset or liability with last4)
        or income destination (spending=False: asset with last4 only).
        Uses user preferences, else the only matching setup account if unambiguous.
        """
        real_all = self.repository.list_real_funding_accounts(user_ref)
        candidates = (
            real_all if spending else [a for a in real_all if a["account_type"] == "asset"]
        )
        prefs = self.repository.get_user_preferences(user_ref)
        code = prefs.get("primary_funding_code")
        typ = prefs.get("primary_funding_type")
        if code and typ and (spending or typ == "asset"):
            if any(a["code"] == code and a["account_type"] == typ for a in real_all):
                return str(code), typ  # type: ignore[return-value]
        if len(candidates) == 1:
            return candidates[0]["code"], candidates[0]["account_type"]
        return None

    def _maybe_seed_primary_from_single_account(self, user_ref: str) -> None:
        prefs = self.repository.get_user_preferences(user_ref)
        if prefs.get("primary_funding_code"):
            return
        real = self.repository.list_real_funding_accounts(user_ref)
        if len(real) == 1:
            self.repository.merge_user_preferences(
                user_ref,
                {
                    "primary_funding_code": real[0]["code"],
                    "primary_funding_type": real[0]["account_type"],
                },
            )

    def set_primary_funding_account(self, user_ref: str, account_code: str, account_type: AccountType) -> dict:
        real = self.repository.list_real_funding_accounts(user_ref)
        if not any(a["code"] == account_code and a["account_type"] == account_type for a in real):
            raise ValueError(
                "Pick one of your setup accounts (asset or liability with last 4 digits), or add one first."
            )
        self.repository.merge_user_preferences(
            user_ref,
            {"primary_funding_code": account_code, "primary_funding_type": account_type},
        )
        return {"primary_funding_code": account_code, "primary_funding_type": account_type}

    def list_setup_funding_accounts(self, user_ref: str) -> list[dict]:
        return self.repository.list_real_funding_accounts(user_ref)

    def describe_primary_funding(self, user_ref: str) -> str | None:
        prefs = self.repository.get_user_preferences(user_ref)
        code = prefs.get("primary_funding_code")
        typ = prefs.get("primary_funding_type")
        if code and typ:
            return f"{code} ({typ})"
        return None

    @staticmethod
    def _normalize_expense_payment_method(payment_method: str | None) -> str | None:
        """Canonical instrument from NLP/API; None when unspecified or unknown."""
        if payment_method is None:
            return None
        x = str(payment_method).strip().lower()
        if x in ("", "unknown", "none", "null"):
            return None
        if x in ("cash", "card", "upi"):
            return x
        return None

    def post_expense(self, payload: ExpenseRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        funding_code = payload.funding_account_code
        funding_type = payload.funding_account_type
        resolved_from_receipt = False
        if payload.receipt_account_last4:
            digits = "".join(ch for ch in str(payload.receipt_account_last4) if ch.isdigit())
            if len(digits) == 4:
                by_last4 = self.repository.resolve_funding_account_by_last4(
                    payload.user_ref,
                    digits,
                    payload.receipt_institution_hint,
                )
                if by_last4:
                    funding_code = by_last4["code"]
                    funding_type = by_last4["account_type"]
                    resolved_from_receipt = True

        pm = self._normalize_expense_payment_method(payload.payment_method)
        if not resolved_from_receipt:
            # 1) Explicit bank/institution mention in the user's text (e.g. "via slice", "hdfc")
            #    takes priority — resolve against the user's actual accounts.
            bank_hint = (payload.bank_hint or "").strip().lower() or None
            resolved_from_hint = False
            if bank_hint:
                if bank_hint == "cash":
                    self.ensure_cash_wallet_account(payload.user_ref)
                    funding_code = CASH_WALLET_CODE
                    funding_type = "asset"
                    resolved_from_hint = True
                else:
                    by_name = self.repository.resolve_funding_account_by_name(
                        payload.user_ref, bank_hint,
                    )
                    if by_name:
                        funding_code = by_name["code"]
                        funding_type = by_name["account_type"]
                        resolved_from_hint = True
                    else:
                        # User named an account we can't match — ignore the stale
                        # session funding so payment-method logic gets a fair shot.
                        funding_code = None
                        funding_type = None

            # 2) Payment-method keywords (cash / card / upi) — only when bank_hint
            #    didn't already resolve to a real account.
            if not resolved_from_hint and (funding_code is None or funding_type is None):
                if pm == "cash":
                    self.ensure_cash_wallet_account(payload.user_ref)
                    funding_code = CASH_WALLET_CODE
                    funding_type = "asset"
                elif pm == "card":
                    funding_code = "card_liability"
                    funding_type = "liability"
                elif pm == "upi" and payload.payment_provider:
                    linked = self.repository.resolve_linked_account_for_provider(
                        user_ref=payload.user_ref,
                        profile_type="upi",
                        provider=payload.payment_provider,
                    )
                    if linked:
                        funding_code = linked["code"]
                        funding_type = linked["account_type"]
                    else:
                        funding_code = "upi_wallet"
                        funding_type = "asset"
                elif payload.payment_provider:
                    linked = self.repository.resolve_linked_account_for_provider(
                        user_ref=payload.user_ref,
                        profile_type="upi",
                        provider=payload.payment_provider,
                    )
                    if linked:
                        funding_code = linked["code"]
                        funding_type = linked["account_type"]
                elif pm == "upi":
                    funding_code = "upi_wallet"
                    funding_type = "asset"

        if funding_code is None or funding_type is None:
            resolved = self.resolve_primary_cash_account(payload.user_ref, spending=True)
            if resolved is None:
                raise ValueError(
                    "No default spending account: add a bank/card with last 4 digits, set primary "
                    "(POST /api/v1/ledger/primary-funding), use Add Expense → Cash/UPI/Card in Telegram, "
                    "or pass funding_account_code."
                )
            funding_code, funding_type = resolved

        self._check_asset_sufficient(payload.user_ref, funding_code, funding_type, amount_minor)

        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="expense",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={
                "category": payload.category or "expense",
                "payment_method": payload.payment_method or funding_code,
                "payment_provider": payload.payment_provider,
            },
            entries=[
                {
                    "account_code": payload.expense_account_code,
                    "account_type": "expense",
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": funding_code,
                    "account_type": funding_type,
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    def post_income(self, payload: IncomeRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        dest_code = payload.destination_account_code
        dest_type = payload.destination_account_type
        if dest_code is None or dest_type is None:
            resolved = self.resolve_primary_cash_account(payload.user_ref, spending=False)
            if resolved:
                dest_code, dest_type = resolved
            else:
                dest_code, dest_type = "bank_savings", "asset"
        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="income",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={
                "category": payload.category or "income",
                "payment_method": payload.payment_method or dest_code,
            },
            entries=[
                {
                    "account_code": dest_code,
                    "account_type": dest_type,
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": payload.income_account_code,
                    "account_type": "income",
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    def post_investment(self, payload: InvestmentRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        funding_code = payload.funding_account_code
        funding_type = payload.funding_account_type
        if funding_code is None or funding_type is None:
            resolved = self.resolve_primary_cash_account(payload.user_ref, spending=True)
            if resolved is None:
                raise ValueError(
                    "No default funding account for investments: add a setup account, set primary, "
                    "or pass funding_account_code."
                )
            funding_code, funding_type = resolved

        self._check_asset_sufficient(payload.user_ref, funding_code, funding_type, amount_minor)

        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="investment",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={
                "category": payload.category or "investment",
                "payment_method": payload.payment_method or funding_code,
            },
            entries=[
                {
                    "account_code": payload.investment_account_code,
                    "account_type": "investment",
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": funding_code,
                    "account_type": funding_type,
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    def post_transfer(self, payload: TransferRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        self._check_asset_sufficient(
            payload.user_ref, payload.from_account_code, payload.from_account_type, amount_minor
        )
        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="transfer",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={"category": "transfer"},
            entries=[
                {
                    "account_code": payload.to_account_code,
                    "account_type": payload.to_account_type,
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": payload.from_account_code,
                    "account_type": payload.from_account_type,
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    def post_opening_balance(self, payload: OpeningBalanceRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="opening_balance",
            description=f"Opening balance for {payload.account_code}",
            occurred_at=payload.occurred_at,
            metadata={"category": "opening_balance"},
            entries=[
                {
                    "account_code": payload.account_code,
                    "account_type": payload.account_type,
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": payload.opening_equity_code,
                    "account_type": "equity",
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    @staticmethod
    def _format_post_result(result: dict) -> dict:
        journal = result["journal"]
        return {
            "journal_id": int(journal["id"]),
            "transaction_type": journal["transaction_type"],
            "occurred_at": journal["occurred_at"],
            "amount_minor": int(result["debit_total_minor"]),
            "entries": result["entries"],
        }

    def get_balances(self, user_ref: str) -> list[dict]:
        return self.repository.get_balances(user_ref)

    def get_cash_snapshot(self, user_ref: str) -> list[dict]:
        """Only asset / liability accounts — what the user actually has or owes."""
        return [
            row for row in self.repository.get_balances(user_ref)
            if row["account_type"] in ("asset", "liability")
        ]

    def list_accounts(self, user_ref: str) -> list[dict]:
        return self.repository.list_accounts(user_ref)

    def get_onboarding_status(self, user_ref: str) -> dict:
        has_account = self.repository.has_onboarding_account(user_ref)
        profiles = self.repository.list_payment_profiles(user_ref)
        return {
            "has_required_account": has_account,
            "has_upi_profile": any(p["profile_type"] == "upi" for p in profiles),
            "ready": has_account,
        }

    def upsert_payment_profile(self, payload: PaymentProfileUpsertRequest) -> dict:
        return self.repository.create_or_update_payment_profile(
            user_ref=payload.user_ref,
            profile_type=payload.profile_type,
            provider=payload.provider,
            profile_name=payload.profile_name,
            handle_ref=payload.handle_ref,
            linked_account_code=payload.linked_account_code,
        )

    def list_payment_profiles(self, user_ref: str) -> list[dict]:
        return self.repository.list_payment_profiles(user_ref)

    def get_weekly_report(self, user_ref: str) -> dict:
        summary = self.repository.get_report_window_summary(user_ref, days=7)
        return {
            "period": "weekly",
            "window_days": 7,
            "income_minor": int(summary["income_minor"]),
            "expense_minor": int(summary["expense_minor"]),
            "investment_minor": int(summary["investment_minor"]),
            "net_cashflow_minor": int(summary["income_minor"]) - int(summary["expense_minor"]) - int(summary["investment_minor"]),
        }

    def get_monthly_report(self, user_ref: str) -> dict:
        now = datetime.utcnow()
        days_in_scope = now.day
        summary = self.repository.get_report_window_summary(user_ref, days=days_in_scope)
        return {
            "period": "monthly",
            "month": now.strftime("%Y-%m"),
            "income_minor": int(summary["income_minor"]),
            "expense_minor": int(summary["expense_minor"]),
            "investment_minor": int(summary["investment_minor"]),
            "net_cashflow_minor": int(summary["income_minor"]) - int(summary["expense_minor"]) - int(summary["investment_minor"]),
        }

    def get_enriched_period_report(self, user_ref: str, mode: Literal["weekly", "monthly"]) -> dict:
        """
        Totals plus category / account / payment breakdowns for the same rolling window
        as get_weekly_report (7 days) and get_monthly_report (days = today's day-of-month).
        """
        now = datetime.utcnow()
        if mode == "weekly":
            days = 7
            title = "Weekly report"
            range_hint = (
                f"Rolling {days}-day window ending {now.strftime('%d %b %Y, %H:%M')} UTC "
                f"(same logic as weekly totals)."
            )
        else:
            days = max(1, now.day)
            title = f"Monthly report · {now.strftime('%B %Y')}"
            range_hint = (
                f"Rolling {days}-day window ending {now.strftime('%d %b %Y, %H:%M')} UTC "
                f"(same logic as monthly totals / month-to-date)."
            )

        summary = self.repository.get_report_window_summary(user_ref, days=days)
        income = int(summary["income_minor"])
        expense = int(summary["expense_minor"])
        investment = int(summary["investment_minor"])
        net = income - expense - investment

        by_category = self.repository.get_breakdown(user_ref, days=days, group_by="category")
        by_payment = self.repository.get_breakdown(user_ref, days=days, group_by="payment_method")

        return {
            "mode": mode,
            "title": title,
            "range_hint": range_hint,
            "window_days": days,
            "income_minor": income,
            "expense_minor": expense,
            "investment_minor": investment,
            "net_cashflow_minor": net,
            "by_category": list(by_category),
            "by_payment_method": list(by_payment),
        }

    def get_cashflow_report(self, user_ref: str, period: str = "month") -> dict:
        days = 30 if period == "month" else 7
        summary = self.repository.get_report_window_summary(user_ref, days=days)
        return {
            "period": period,
            "incoming_minor": int(summary["income_minor"]),
            "outgoing_minor": int(summary["expense_minor"]),
            "invested_minor": int(summary["investment_minor"]),
            "net_minor": int(summary["income_minor"]) - int(summary["expense_minor"]) - int(summary["investment_minor"]),
        }

    def get_breakdown(self, user_ref: str, period: str, group_by: str) -> dict:
        days = 7 if period == "week" else 30
        rows = self.repository.get_breakdown(user_ref, days=days, group_by=group_by)
        return {"period": period, "group_by": group_by, "rows": rows}

    def get_transactions(self, user_ref: str, limit: int = 50, offset: int = 0) -> dict:
        rows = self.repository.get_transactions(user_ref, limit=limit, offset=offset)
        return {"limit": limit, "offset": offset, "rows": rows}

    def reassign_expense_category(self, user_ref: str, journal_id: int, new_category: str) -> dict:
        return self.repository.reassign_expense_journal_category(
            user_ref=user_ref, journal_transaction_id=journal_id, new_category=new_category
        )
