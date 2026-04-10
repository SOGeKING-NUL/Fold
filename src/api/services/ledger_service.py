from dataclasses import dataclass

from api.repositories.ledger_repository import LedgerRepository


@dataclass
class LedgerPostRequest:
    user_ref: str
    source: str
    description: str
    expense_account_code: str
    funding_account_code: str
    amount: float
    external_ref: str | None = None


class LedgerService:
    def __init__(self, repository: LedgerRepository | None = None) -> None:
        self.repository = repository or LedgerRepository()

    def _seed_default_accounts(self, user_id: int) -> None:
        defaults = [
            ("expense_misc", "Expense - Misc", "expense"),
            ("income_misc", "Income - Misc", "income"),
            ("cash_wallet", "Cash Wallet", "asset"),
            ("upi_wallet", "UPI Wallet", "asset"),
            ("card_liability", "Card Liability", "liability"),
            ("bank_savings", "Bank Savings", "asset"),
        ]
        for code, name, acc_type in defaults:
            self.repository.get_or_create_account(user_id, code, name, acc_type)

    def post_expense(self, payload: LedgerPostRequest) -> dict:
        amount_minor = int(round(payload.amount * 100))
        if amount_minor <= 0:
            raise ValueError("Amount must be positive")

        user = self.repository.get_or_create_user(payload.user_ref)
        user_id = int(user["id"])
        self._seed_default_accounts(user_id)

        expense_account = self.repository.get_or_create_account(
            user_id=user_id,
            code=payload.expense_account_code,
            name=payload.expense_account_code.replace("_", " ").title(),
            account_type="expense",
        )
        funding_account = self.repository.get_or_create_account(
            user_id=user_id,
            code=payload.funding_account_code,
            name=payload.funding_account_code.replace("_", " ").title(),
            account_type="asset",
        )

        journal = self.repository.create_journal_transaction(
            user_id=user_id,
            source=payload.source,
            external_ref=payload.external_ref,
            description=payload.description,
        )
        journal_id = int(journal["id"])

        self.repository.insert_ledger_entry(
            journal_transaction_id=journal_id,
            account_id=int(expense_account["id"]),
            direction="debit",
            amount_minor=amount_minor,
        )
        self.repository.insert_ledger_entry(
            journal_transaction_id=journal_id,
            account_id=int(funding_account["id"]),
            direction="credit",
            amount_minor=amount_minor,
        )

        return {
            "journal_id": journal_id,
            "amount_minor": amount_minor,
            "debit_account": expense_account["code"],
            "credit_account": funding_account["code"],
        }

    def get_balances(self, user_ref: str) -> list[dict]:
        return self.repository.get_balances(user_ref)
