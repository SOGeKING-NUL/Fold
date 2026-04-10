import httpx

from api.config import get_settings
from api.repositories.ledger_repository import LedgerRepository
from api.services.ledger_service import (
    ExpenseRequest,
    IncomeRequest,
    InvestmentRequest,
    LedgerService,
    OpeningBalanceRequest,
    TransferRequest,
)


class TelegramService:
    def __init__(self, ledger_service: LedgerService | None = None) -> None:
        self.settings = get_settings()
        self.ledger_service = ledger_service or LedgerService()
        self.repository = LedgerRepository()

    async def send_message(self, chat_id: int, text: str, keyboard: list[list[dict]] | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = {"inline_keyboard": keyboard}

        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
                json=payload,
            )

    def _start_keyboard(self) -> list[list[dict]]:
        return [
            [
                {"text": "Add Expense", "callback_data": "dash:add_expense"},
                {"text": "Add Income", "callback_data": "dash:add_income"},
            ],
            [
                {"text": "Add Investment", "callback_data": "dash:add_investment"},
                {"text": "Transfer", "callback_data": "dash:transfer"},
            ],
            [
                {"text": "Weekly Report", "callback_data": "report:weekly"},
                {"text": "Monthly Report", "callback_data": "report:monthly"},
            ],
            [
                {"text": "Balance Snapshot", "callback_data": "dash:balance"},
                {"text": "Accounts", "callback_data": "acct:list"},
            ],
        ]

    def _prestart_keyboard(self) -> list[list[dict]]:
        return [[{"text": "Start Fold", "callback_data": "dash:start"}]]

    def _save_session(self, telegram_user_id: int, state: str, payload: dict) -> None:
        self.repository.upsert_session(telegram_user_id=telegram_user_id, state=state, payload=payload)

    def _get_session(self, telegram_user_id: int) -> dict:
        existing = self.repository.get_session(telegram_user_id)
        return existing or {"state": "idle", "payload_json": {}}

    async def handle_update(self, update: dict) -> dict:
        message = update.get("message", {})
        callback = update.get("callback_query", {})

        if message:
            chat_id = message["chat"]["id"]
            text = (message.get("text") or "").strip().lower()
            telegram_user_id = message["from"]["id"]
            user_ref = f"telegram:{telegram_user_id}"
            session = self._get_session(telegram_user_id)
            payload = dict(session.get("payload_json") or {})

            if text in {"/start", "/add"}:
                if not payload.get("started"):
                    await self.send_message(
                        chat_id,
                        "Welcome to Fold. Tap Start Fold to open your dashboard.",
                        keyboard=self._prestart_keyboard(),
                    )
                    self._save_session(telegram_user_id, "awaiting_start", payload)
                    return {"status": "ok", "message": "prestart_sent"}

                await self.send_message(
                    chat_id,
                    "Fold Dashboard:\nChoose an action.",
                    keyboard=self._start_keyboard(),
                )
                self._save_session(telegram_user_id, "idle", payload)
                return {"status": "ok", "message": "menu_sent"}

            if text.startswith("/expense"):
                # Format: /expense <amount> <description>
                parts = text.split(" ", 2)
                if len(parts) < 3:
                    await self.send_message(chat_id, "Use: /expense <amount> <description>")
                    return {"status": "ok", "message": "usage_sent"}
                amount = float(parts[1])
                description = parts[2]
                funding_code = payload.get("funding_account_code", "upi_wallet")
                funding_type = payload.get("funding_account_type", "asset")
                result = self.ledger_service.post_expense(
                    ExpenseRequest(
                        user_ref=user_ref,
                        source="telegram",
                        description=description,
                        expense_account_code="expense_misc",
                        funding_account_code=funding_code,
                        funding_account_type=funding_type,
                        amount=amount,
                        external_ref=str(update.get("update_id")),
                    )
                )
                await self.send_message(chat_id, f"Recorded expense. Journal ID: {result['journal_id']}")
                return {"status": "ok", "result": result}

            if text == "/balance":
                balances = self.ledger_service.get_balances(user_ref=user_ref)
                if not balances:
                    await self.send_message(chat_id, "No balances yet. Add an expense first.")
                    return {"status": "ok", "message": "no_balances"}

                lines = ["Balances:"]
                for row in balances:
                    lines.append(f"- {row['code']}: {row['balance_minor'] / 100:.2f} INR")
                await self.send_message(chat_id, "\n".join(lines))
                return {"status": "ok", "message": "balance_sent"}

            if text.startswith("/income"):
                parts = text.split(" ", 2)
                if len(parts) < 3:
                    await self.send_message(chat_id, "Use: /income <amount> <description>")
                    return {"status": "ok", "message": "usage_sent"}
                result = self.ledger_service.post_income(
                    IncomeRequest(
                        user_ref=user_ref,
                        source="telegram",
                        description=parts[2],
                        amount=float(parts[1]),
                        destination_account_code="bank_savings",
                        destination_account_type="asset",
                        external_ref=str(update.get("update_id")),
                    )
                )
                await self.send_message(chat_id, f"Recorded income. Journal ID: {result['journal_id']}")
                return {"status": "ok", "result": result}

            if text.startswith("/investment"):
                parts = text.split(" ", 2)
                if len(parts) < 3:
                    await self.send_message(chat_id, "Use: /investment <amount> <description>")
                    return {"status": "ok", "message": "usage_sent"}
                result = self.ledger_service.post_investment(
                    InvestmentRequest(
                        user_ref=user_ref,
                        source="telegram",
                        description=parts[2],
                        amount=float(parts[1]),
                        investment_account_code="investment_portfolio",
                        funding_account_code=payload.get("funding_account_code", "bank_savings"),
                        funding_account_type=payload.get("funding_account_type", "asset"),
                        external_ref=str(update.get("update_id")),
                    )
                )
                await self.send_message(chat_id, f"Recorded investment. Journal ID: {result['journal_id']}")
                return {"status": "ok", "result": result}

            if text.startswith("/transfer"):
                parts = text.split(" ")
                if len(parts) < 4:
                    await self.send_message(chat_id, "Use: /transfer <amount> <from_account_code> <to_account_code>")
                    return {"status": "ok", "message": "usage_sent"}
                amount = float(parts[1])
                from_code = parts[2]
                to_code = parts[3]
                result = self.ledger_service.post_transfer(
                    TransferRequest(
                        user_ref=user_ref,
                        source="telegram",
                        description=f"Transfer {from_code} -> {to_code}",
                        amount=amount,
                        from_account_code=from_code,
                        from_account_type="asset",
                        to_account_code=to_code,
                        to_account_type="asset",
                        external_ref=str(update.get("update_id")),
                    )
                )
                await self.send_message(chat_id, f"Recorded transfer. Journal ID: {result['journal_id']}")
                return {"status": "ok", "result": result}

            if text.startswith("/opening"):
                parts = text.split(" ")
                if len(parts) < 4:
                    await self.send_message(chat_id, "Use: /opening <account_code> <account_type> <amount>")
                    return {"status": "ok", "message": "usage_sent"}
                result = self.ledger_service.post_opening_balance(
                    OpeningBalanceRequest(
                        user_ref=user_ref,
                        source="telegram",
                        account_code=parts[1],
                        account_type=parts[2],  # type: ignore[arg-type]
                        amount=float(parts[3]),
                        external_ref=str(update.get("update_id")),
                    )
                )
                await self.send_message(chat_id, f"Recorded opening balance. Journal ID: {result['journal_id']}")
                return {"status": "ok", "result": result}

            await self.send_message(
                chat_id,
                (
                    "Commands:\n"
                    "/start\n"
                    "/expense <amount> <description>\n"
                    "/income <amount> <description>\n"
                    "/investment <amount> <description>\n"
                    "/transfer <amount> <from_account_code> <to_account_code>\n"
                    "/opening <account_code> <account_type> <amount>\n"
                    "/balance"
                ),
            )
            return {"status": "ok", "message": "help_sent"}

        if callback:
            chat_id = callback["message"]["chat"]["id"]
            telegram_user_id = callback["from"]["id"]
            user_ref = f"telegram:{telegram_user_id}"
            data = callback.get("data", "")

            if data.startswith("dash:start"):
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                session_payload["started"] = True
                self._save_session(telegram_user_id, "idle", session_payload)
                await self.send_message(
                    chat_id,
                    "Fold Dashboard:\nChoose an action.",
                    keyboard=self._start_keyboard(),
                )
            elif data.startswith("dash:add_expense"):
                await self.send_message(
                    chat_id,
                    "Quick expense accounts. Pick one for funding:",
                    keyboard=[
                        [{"text": "Cash", "callback_data": "acct:funding:cash_wallet:asset"}],
                        [{"text": "UPI", "callback_data": "acct:funding:upi_wallet:asset"}],
                        [{"text": "Card", "callback_data": "acct:funding:card_liability:liability"}],
                    ],
                )
            elif data.startswith("dash:add_income"):
                await self.send_message(chat_id, "Use /income <amount> <description> to record income.")
            elif data.startswith("dash:add_investment"):
                await self.send_message(chat_id, "Use /investment <amount> <description> to record investment.")
            elif data.startswith("dash:transfer"):
                await self.send_message(chat_id, "Use /transfer <amount> <from_account_code> <to_account_code>.")
            elif data.startswith("dash:balance"):
                balances = self.ledger_service.get_balances(user_ref=user_ref)
                if not balances:
                    await self.send_message(chat_id, "No balances yet.")
                else:
                    lines = ["Balance Snapshot:"]
                    for row in balances:
                        lines.append(f"- {row['code']}: {row['balance_minor'] / 100:.2f} INR")
                    await self.send_message(chat_id, "\n".join(lines))
            elif data.startswith("report:weekly"):
                report = self.ledger_service.get_weekly_report(user_ref)
                await self.send_message(
                    chat_id,
                    (
                        "Weekly Report:\n"
                        f"Income: {report['income_minor'] / 100:.2f}\n"
                        f"Expense: {report['expense_minor'] / 100:.2f}\n"
                        f"Investment: {report['investment_minor'] / 100:.2f}\n"
                        f"Net: {report['net_cashflow_minor'] / 100:.2f}"
                    ),
                )
            elif data.startswith("report:monthly"):
                report = self.ledger_service.get_monthly_report(user_ref)
                await self.send_message(
                    chat_id,
                    (
                        f"Monthly Report ({report['month']}):\n"
                        f"Income: {report['income_minor'] / 100:.2f}\n"
                        f"Expense: {report['expense_minor'] / 100:.2f}\n"
                        f"Investment: {report['investment_minor'] / 100:.2f}\n"
                        f"Net: {report['net_cashflow_minor'] / 100:.2f}"
                    ),
                )
            elif data.startswith("acct:list"):
                accounts = self.ledger_service.list_accounts(user_ref)
                if not accounts:
                    await self.send_message(chat_id, "No accounts found.")
                else:
                    lines = ["Accounts:"]
                    for a in accounts:
                        lines.append(f"- {a['code']} ({a['account_type']})")
                    await self.send_message(chat_id, "\n".join(lines))
            elif data.startswith("acct:funding:"):
                _, _, code, acc_type = data.split(":", 3)
                self._save_session(
                    telegram_user_id=telegram_user_id,
                    state="idle",
                    payload={"funding_account_code": code, "funding_account_type": acc_type},
                )
                await self.send_message(chat_id, f"Funding account set to {code}. Now use /expense <amount> <description>.")
            else:
                await self.send_message(chat_id, "Unknown action. Use /start.")

            return {"status": "ok", "message": "callback_handled"}

        return {"status": "ok", "message": "ignored"}
