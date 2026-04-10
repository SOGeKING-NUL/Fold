from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from api.repositories.ledger_repository import LedgerRepository


AccountType = Literal["asset", "liability", "equity", "income", "expense", "investment"]


@dataclass
class AccountUpsertRequest:
    user_ref: str
    code: str
    name: str
    account_type: AccountType
    currency: str = "INR"


@dataclass
class ExpenseRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    expense_account_code: str = "expense_misc"
    funding_account_code: str = "upi_wallet"
    funding_account_type: AccountType = "asset"
    external_ref: str | None = None
    occurred_at: str | None = None
    category: str | None = None
    payment_method: str | None = None


@dataclass
class IncomeRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    income_account_code: str = "income_misc"
    destination_account_code: str = "bank_savings"
    destination_account_type: AccountType = "asset"
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
    investment_account_code: str = "investment_portfolio"
    funding_account_code: str = "bank_savings"
    funding_account_type: AccountType = "asset"
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
        return amount_minor

    def _seed_default_accounts(self, user_ref: str) -> None:
        user = self.repository.get_or_create_user(user_ref)
        user_id = int(user["id"])
        defaults = [
            ("expense_misc", "Expense - Misc", "expense"),
            ("income_misc", "Income - Misc", "income"),
            ("investment_portfolio", "Investment Portfolio", "investment"),
            ("cash_wallet", "Cash Wallet", "asset"),
            ("upi_wallet", "UPI Wallet", "asset"),
            ("card_liability", "Card Liability", "liability"),
            ("bank_savings", "Bank Savings", "asset"),
            ("equity_opening_balance", "Equity Opening Balance", "equity"),
        ]
        for code, name, acc_type in defaults:
            self.repository.get_or_create_account(user_id, code, name, acc_type)

    def upsert_account(self, payload: AccountUpsertRequest) -> dict:
        user = self.repository.get_or_create_user(payload.user_ref)
        account = self.repository.get_or_create_account(
            user_id=int(user["id"]),
            code=payload.code,
            name=payload.name,
            account_type=payload.account_type,
        )
        return account

    def post_expense(self, payload: ExpenseRequest) -> dict:
        self._seed_default_accounts(payload.user_ref)
        amount_minor = self._to_minor(payload.amount)
        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="expense",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={
                "category": payload.category or "expense",
                "payment_method": payload.payment_method or payload.funding_account_code,
            },
            entries=[
                {
                    "account_code": payload.expense_account_code,
                    "account_type": "expense",
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": payload.funding_account_code,
                    "account_type": payload.funding_account_type,
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    def post_income(self, payload: IncomeRequest) -> dict:
        self._seed_default_accounts(payload.user_ref)
        amount_minor = self._to_minor(payload.amount)
        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="income",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={
                "category": payload.category or "income",
                "payment_method": payload.payment_method or payload.destination_account_code,
            },
            entries=[
                {
                    "account_code": payload.destination_account_code,
                    "account_type": payload.destination_account_type,
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
        self._seed_default_accounts(payload.user_ref)
        amount_minor = self._to_minor(payload.amount)
        result = self.repository.create_balanced_journal(
            user_ref=payload.user_ref,
            source=payload.source,
            external_ref=payload.external_ref,
            transaction_type="investment",
            description=payload.description,
            occurred_at=payload.occurred_at,
            metadata={
                "category": payload.category or "investment",
                "payment_method": payload.payment_method or payload.funding_account_code,
            },
            entries=[
                {
                    "account_code": payload.investment_account_code,
                    "account_type": "investment",
                    "direction": "debit",
                    "amount_minor": amount_minor,
                },
                {
                    "account_code": payload.funding_account_code,
                    "account_type": payload.funding_account_type,
                    "direction": "credit",
                    "amount_minor": amount_minor,
                },
            ],
        )
        return self._format_post_result(result)

    def post_transfer(self, payload: TransferRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
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

    def list_accounts(self, user_ref: str) -> list[dict]:
        self._seed_default_accounts(user_ref)
        return self.repository.list_accounts(user_ref)

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
