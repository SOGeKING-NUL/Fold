import httpx

from api.config import get_settings
from api.services.ledger_service import LedgerPostRequest, LedgerService


class TelegramService:
    def __init__(self, ledger_service: LedgerService | None = None) -> None:
        self.settings = get_settings()
        self.ledger_service = ledger_service or LedgerService()

    async def send_message(self, chat_id: int, text: str, keyboard: list[list[dict]] | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = {"inline_keyboard": keyboard}

        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
                json=payload,
            )

    async def handle_update(self, update: dict) -> dict:
        message = update.get("message", {})
        callback = update.get("callback_query", {})

        if message:
            chat_id = message["chat"]["id"]
            text = (message.get("text") or "").strip().lower()
            user_ref = f"telegram:{message['from']['id']}"

            if text in {"/start", "/add"}:
                await self.send_message(
                    chat_id,
                    "Choose payment method for quick expense entry:",
                    keyboard=[
                        [{"text": "Cash", "callback_data": "pay:cash_wallet"}],
                        [{"text": "UPI", "callback_data": "pay:upi_wallet"}],
                        [{"text": "Card", "callback_data": "pay:card_liability"}],
                    ],
                )
                return {"status": "ok", "message": "menu_sent"}

            if text.startswith("/expense"):
                # Format: /expense <amount> <description>
                parts = text.split(" ", 2)
                if len(parts) < 3:
                    await self.send_message(chat_id, "Use: /expense <amount> <description>")
                    return {"status": "ok", "message": "usage_sent"}
                amount = float(parts[1])
                description = parts[2]
                result = self.ledger_service.post_expense(
                    LedgerPostRequest(
                        user_ref=user_ref,
                        source="telegram",
                        description=description,
                        expense_account_code="expense_misc",
                        funding_account_code="upi_wallet",
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

            await self.send_message(
                chat_id,
                "Commands:\n/start\n/add\n/expense <amount> <description>\n/balance",
            )
            return {"status": "ok", "message": "help_sent"}

        if callback:
            chat_id = callback["message"]["chat"]["id"]
            data = callback.get("data", "")
            if data.startswith("pay:"):
                method = data.split(":", 1)[1]
                await self.send_message(chat_id, f"Payment method set to {method}. Use /expense <amount> <description>.")
            return {"status": "ok", "message": "callback_handled"}

        return {"status": "ok", "message": "ignored"}
