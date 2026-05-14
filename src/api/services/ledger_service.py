from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import logging

from api.config import get_settings
from api.repositories.ledger_repository import LedgerRepository
from api.repositories.user_repository import UserRepository

_logger = logging.getLogger(__name__)


AccountType = Literal["cash", "bank", "credit"]


@dataclass
class AccountUpsertRequest:
    user_ref: str
    name: str
    account_type: AccountType
    institution_name: str | None = None
    account_number_last4: str | None = None


@dataclass
class PaymentProfileUpsertRequest:
    user_ref: str
    provider: str
    profile_name: str
    linked_account_name: str


@dataclass
class ExpenseRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    funding_account_name: str | None = None
    external_ref: str | None = None
    occurred_at: str | None = None
    category: str | None = None
    payment_method: str | None = None
    payment_provider: str | None = None
    receipt_account_last4: str | None = None
    receipt_institution_hint: str | None = None
    bank_hint: str | None = None


@dataclass
class IncomeRequest:
    user_ref: str
    source: str
    description: str
    amount: float
    destination_account_name: str | None = None
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
    from_account_name: str
    to_account_name: str
    external_ref: str | None = None
    occurred_at: str | None = None


@dataclass
class OpeningBalanceRequest:
    user_ref: str
    source: str
    account_name: str
    amount: float
    external_ref: str | None = None
    occurred_at: str | None = None


class LedgerService:
    def __init__(self, repository: LedgerRepository | None = None, user_repo: UserRepository | None = None) -> None:
        self.repository = repository or LedgerRepository()
        self.user_repo = user_repo or UserRepository()

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

    def upsert_account(self, payload: AccountUpsertRequest) -> dict:
        user = self.user_repo.get_or_create_user_from_clerk(payload.user_ref)
        account_last4 = payload.account_number_last4
        
        # For cash wallets, institution and last4 are optional
        if payload.account_type == "cash":
            account_last4 = None
            institution = payload.institution_name or "Cash"
        else:
            institution = payload.institution_name
            if account_last4 is not None:
                account_last4 = "".join(ch for ch in account_last4 if ch.isdigit())
                if len(account_last4) != 4:
                    raise ValueError("account_number_last4 must contain exactly 4 digits")
        
        account = self.repository.get_or_create_account(
            user_id=int(user["id"]),
            name=payload.name,
            account_type=payload.account_type,
            institution_name=institution,
            account_number_last4=account_last4,
        )
        # If this is the first account, make it default
        if not user.get("default_account_id"):
            self.user_repo.set_default_account(payload.user_ref, account["id"])
            
        return account

    def ensure_cash_wallet_account(self, user_ref: str) -> dict:
        return self.upsert_account(
            AccountUpsertRequest(
                user_ref=user_ref,
                name="Physical Cash",
                account_type="cash",
                institution_name="Cash",
            )
        )

    def set_primary_funding_account(self, user_ref: str, account_name: str) -> dict:
        user = self.user_repo.get_or_create_user_from_clerk(user_ref)
        account = self.repository.get_account_by_name(user["id"], account_name)
        if not account:
            raise ValueError(f"Account {account_name} not found.")
        self.user_repo.set_default_account(user_ref, account["id"])
        return {"primary_funding_name": account_name}

    def set_default_account(self, user_ref: str, account_name: str) -> dict:
        """Set an account as the default for its type (cash/bank/credit)."""
        user = self.user_repo.get_user_by_clerk_id(user_ref)
        if not user:
            raise ValueError("User not found")
        
        account = self.repository.get_account_by_name(user["id"], account_name)
        if not account:
            raise ValueError(f"Account {account_name} not found")
        
        return self.repository.set_account_as_default(user["id"], account["id"])

    def list_accounts(self, user_ref: str) -> list[dict]:
        return self.repository.list_accounts(user_ref)

    def post_expense(self, payload: ExpenseRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        user = self.user_repo.get_user_by_clerk_id(payload.user_ref)
        if not user:
            raise ValueError("User not found")

        account_id = None
        payment_profile_id = None

        # Priority 1: Explicit funding account name
        if payload.funding_account_name:
            acc = self.repository.get_account_by_name(user["id"], payload.funding_account_name)
            if acc:
                account_id = acc["id"]
        
        # Priority 2: Payment provider (UPI app) → linked account
        # This ensures GPay detection charges the GPay-linked account, not primary
        if not account_id and payload.payment_provider:
            pp = self.repository.get_payment_profile_by_provider(payload.user_ref, payload.payment_provider)
            if pp:
                payment_profile_id = pp["id"]
                account_id = pp["linked_account_id"]
                _logger.info(f"Resolved payment provider '{payload.payment_provider}' to account ID {account_id}")
        
        # Priority 3: Bank hint (from NLP or OCR)
        if not account_id and payload.bank_hint:
            if payload.bank_hint.lower() == "cash":
                cash_acc = self.ensure_cash_wallet_account(payload.user_ref)
                account_id = cash_acc["id"]
            else:
                acc = self.repository.get_account_by_name(user["id"], payload.bank_hint)
                if acc:
                    account_id = acc["id"]
        
        # Priority 4: Default account for payment method type
        if not account_id and payload.payment_method:
            method_to_type = {"cash": "cash", "upi": "bank", "card": "credit"}
            account_type = method_to_type.get(payload.payment_method)
            if account_type:
                default_acc = self.repository.get_default_account_for_type(user["id"], account_type)
                if default_acc:
                    account_id = default_acc["id"]
                    _logger.info(f"Using default {account_type} account: {default_acc['name']}")
        
        # Priority 5: User's global default account
        if not account_id and user.get("default_account_id"):
            account_id = user["default_account_id"]
            
        if not account_id:
            raise ValueError("Could not determine funding source. Please set a default account or link a payment profile.")

        txn = self.repository.create_transaction(
            clerk_user_id=payload.user_ref,
            amount=amount_minor,
            type="expense",
            category=payload.category or "expense",
            description=payload.description,
            account_id=account_id,
            to_account_id=None,
            payment_profile_id=payment_profile_id,
            source=payload.source,
        )
        return txn

    def post_income(self, payload: IncomeRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        user = self.user_repo.get_user_by_clerk_id(payload.user_ref)
        if not user:
            raise ValueError("User not found")

        account_id = None
        if payload.destination_account_name:
            acc = self.repository.get_account_by_name(user["id"], payload.destination_account_name)
            if acc:
                account_id = acc["id"]
        
        if not account_id and user.get("default_account_id"):
            account_id = user["default_account_id"]

        if not account_id:
            raise ValueError("Could not determine destination account.")

        txn = self.repository.create_transaction(
            clerk_user_id=payload.user_ref,
            amount=amount_minor,
            type="income",
            category=payload.category or "income",
            description=payload.description,
            account_id=account_id,
            to_account_id=None,
            payment_profile_id=None,
            source=payload.source,
        )
        return txn

    def post_transfer(self, payload: TransferRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        user = self.user_repo.get_user_by_clerk_id(payload.user_ref)
        if not user:
            raise ValueError("User not found")

        from_acc = self.repository.get_account_by_name(user["id"], payload.from_account_name)
        to_acc = self.repository.get_account_by_name(user["id"], payload.to_account_name)
        
        if not from_acc or not to_acc:
            raise ValueError("Transfer accounts not found")

        txn = self.repository.create_transaction(
            clerk_user_id=payload.user_ref,
            amount=amount_minor,
            type="transfer",
            category="transfer",
            description=payload.description,
            account_id=from_acc["id"],
            to_account_id=to_acc["id"],
            payment_profile_id=None,
            source=payload.source,
        )
        return txn

    def post_opening_balance(self, payload: OpeningBalanceRequest) -> dict:
        amount_minor = self._to_minor(payload.amount)
        user = self.user_repo.get_user_by_clerk_id(payload.user_ref)
        if not user:
            raise ValueError("User not found")

        acc = self.repository.get_account_by_name(user["id"], payload.account_name)
        if not acc:
            raise ValueError("Account not found")

        txn = self.repository.create_transaction(
            clerk_user_id=payload.user_ref,
            amount=amount_minor,
            type="opening_balance",
            category="opening_balance",
            description=f"Opening balance for {payload.account_name}",
            account_id=acc["id"],
            to_account_id=None,
            payment_profile_id=None,
            source=payload.source,
        )
        return txn

    def upsert_payment_profile(self, payload: PaymentProfileUpsertRequest) -> dict:
        user = self.user_repo.get_user_by_clerk_id(payload.user_ref)
        if not user:
            raise ValueError("User not found")
            
        acc = self.repository.get_account_by_name(user["id"], payload.linked_account_name)
        if not acc:
            raise ValueError("Linked account not found")
            
        return self.repository.create_payment_profile(
            clerk_user_id=payload.user_ref,
            provider=payload.provider,
            profile_name=payload.profile_name,
            linked_account_id=acc["id"]
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
            "net_cashflow_minor": int(summary["income_minor"]) - int(summary["expense_minor"]),
        }

    def get_monthly_report(self, user_ref: str) -> dict:
        now = datetime.utcnow()
        days_in_scope = max(1, now.day)
        summary = self.repository.get_report_window_summary(user_ref, days=days_in_scope)
        return {
            "period": "monthly",
            "month": now.strftime("%Y-%m"),
            "income_minor": int(summary["income_minor"]),
            "expense_minor": int(summary["expense_minor"]),
            "net_cashflow_minor": int(summary["income_minor"]) - int(summary["expense_minor"]),
        }

    def get_enriched_period_report(self, user_ref: str, mode: Literal["weekly", "monthly"]) -> dict:
        now = datetime.utcnow()
        if mode == "weekly":
            days = 7
            title = "Weekly report"
            range_hint = f"Rolling {days}-day window ending {now.strftime('%d %b %Y, %H:%M')} UTC."
        else:
            days = max(1, now.day)
            title = f"Monthly report · {now.strftime('%B %Y')}"
            range_hint = f"Rolling {days}-day window ending {now.strftime('%d %b %Y, %H:%M')} UTC."

        summary = self.repository.get_report_window_summary(user_ref, days=days)
        income = int(summary["income_minor"])
        expense = int(summary["expense_minor"])
        net = income - expense

        by_category = self.repository.get_breakdown(user_ref, days=days, group_by="category")
        by_payment = self.repository.get_breakdown(user_ref, days=days, group_by="payment_method")

        return {
            "mode": mode,
            "title": title,
            "range_hint": range_hint,
            "window_days": days,
            "income_minor": income,
            "expense_minor": expense,
            "investment_minor": 0,
            "net_cashflow_minor": net,
            "by_category": list(by_category),
            "by_payment_method": list(by_payment),
        }

    def get_transactions(self, user_ref: str, limit: int = 50, offset: int = 0) -> dict:
        rows = self.repository.get_transactions(user_ref, limit=limit, offset=offset)
        return {"limit": limit, "offset": offset, "rows": rows}

    def reassign_expense_category(self, user_ref: str, journal_id: int, new_category: str) -> dict:
        return self.repository.reassign_expense_category(
            user_ref=user_ref, transaction_id=journal_id, new_category=new_category
        )

    def update_account(self, user_ref: str, account_name: str, new_data: dict) -> dict:
        """Update an existing account's details."""
        user = self.user_repo.get_user_by_clerk_id(user_ref)
        if not user:
            raise ValueError("User not found")
        
        account = self.repository.get_account_by_name(user["id"], account_name)
        if not account:
            raise ValueError(f"Account {account_name} not found")
        
        return self.repository.update_account(account["id"], new_data)

    def delete_account(self, user_ref: str, account_name: str) -> dict:
        """Delete an account."""
        user = self.user_repo.get_user_by_clerk_id(user_ref)
        if not user:
            raise ValueError("User not found")
        
        account = self.repository.get_account_by_name(user["id"], account_name)
        if not account:
            raise ValueError(f"Account {account_name} not found")
        
        return self.repository.delete_account(account["id"])

    def add_funds_to_account(self, user_ref: str, account_name: str, amount_cents: int) -> dict:
        """Add funds to a cash account."""
        if amount_cents <= 0:
            raise ValueError("Amount must be positive")
        
        user = self.user_repo.get_user_by_clerk_id(user_ref)
        if not user:
            raise ValueError("User not found")
        
        account = self.repository.get_account_by_name(user["id"], account_name)
        if not account:
            raise ValueError(f"Account {account_name} not found")
        
        if account["account_type"] != "cash":
            raise ValueError("Can only add funds to cash accounts")
        
        # Create an income transaction for the added funds
        txn = self.repository.create_transaction(
            clerk_user_id=user_ref,
            amount=amount_cents,
            type="income",
            category="cash_deposit",
            description=f"Added funds to {account_name}",
            account_id=account["id"],
            to_account_id=None,
            payment_profile_id=None,
            source="manual_add_funds",
        )
        return txn

