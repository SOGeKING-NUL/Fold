import asyncio
import logging
import os
import re
import tempfile

import httpx

from api.config import get_settings
from api.repositories.ledger_repository import LedgerRepository
from api.services.ledger_service import (
    AccountUpsertRequest,
    ExpenseRequest,
    IncomeRequest,
    InvestmentRequest,
    LedgerService,
    OpeningBalanceRequest,
    PaymentProfileUpsertRequest,
    TransferRequest,
    POOLED_EXPENSE_CODE,
    POOLED_INCOME_CODE,
    POOLED_INVESTMENT_CODE,
)

# Must match `reassign_expense_journal_category` allowed set and NLP VALID_CATEGORIES (+ misc).
EXPENSE_CATEGORY_FIX = (
    "food",
    "shopping",
    "utilities",
    "travel",
    "entertainment",
    "healthcare",
    "investment",
    "emi",
    "education",
    "friends",
    "misc",
)


def register_telegram_bot_commands(bot_token: str) -> None:
    """
    Registers commands in the Telegram client menu (typing / shows the list).
    See: https://core.telegram.org/bots/api#setmycommands
    """
    commands = [
        {"command": "start", "description": "Open Fold dashboard"},
        {"command": "expense", "description": "Optional: /expense amount note"},
        {"command": "income", "description": "Log income: amount then note"},
        {"command": "investment", "description": "Log investment: amount then note"},
        {"command": "balance", "description": "Show account balances"},
        {"command": "opening", "description": "Set opening balance (/opening code asset amt)"},
        {"command": "transfer", "description": "Move money between accounts"},
        {"command": "cancel", "description": "Cancel current setup step"},
        {"command": "link_upi", "description": "Legacy: link UPI in one line"},
    ]
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"https://api.telegram.org/bot{bot_token}/setMyCommands",
                json={"commands": commands},
            )
            r.raise_for_status()
    except Exception:
        # Do not fail app startup if Telegram is unreachable
        pass


class TelegramService:
    """Account / UPI setup: slash commands other than /cancel (and /start /add to restart) must not clear wizard."""

    _ONBOARDING_FLOW_STATES = frozenset(
        {
            "awaiting_account_last4",
            "awaiting_account_nickname",
            "awaiting_account_opening_balance",
            "awaiting_upi_provider",
            "awaiting_upi_account_pick",
            "awaiting_upi_profile_name",
            "awaiting_upi_handle",
        }
    )
    _EXPENSE_FLOW_STATES = frozenset({"awaiting_expense_entry", "awaiting_expense_amount"})

    def __init__(self, ledger_service: LedgerService | None = None) -> None:
        self.settings = get_settings()
        self.ledger_service = ledger_service or LedgerService()
        self.repository = LedgerRepository()

    @staticmethod
    def _slugify_account_code(name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s[:48] if s else "account"

    def _unique_account_code(self, user_ref: str, base: str) -> str:
        accounts = self.ledger_service.list_accounts(user_ref)
        codes = {a["code"] for a in accounts}
        candidate = base[:48]
        if candidate not in codes:
            return candidate
        i = 2
        while f"{candidate}_{i}" in codes:
            i += 1
        return f"{candidate}_{i}"

    def _upi_account_pick_keyboard(self, user_ref: str) -> list[list[dict]] | None:
        """Inline buttons for accounts that can fund UPI (asset / liability)."""
        accounts = self.ledger_service.list_accounts(user_ref)
        eligible = [a for a in accounts if a.get("account_type") in ("asset", "liability")]
        if not eligible:
            return None
        rows: list[list[dict]] = []
        for i in range(0, len(eligible), 2):
            row = []
            for j in range(i, min(i + 2, len(eligible))):
                a = eligible[j]
                code = str(a["code"])
                last4 = a.get("account_number_last4")
                label = f"{code}" if not last4 else f"{code} ·{last4}"
                if len(label) > 40:
                    label = label[:37] + "..."
                cb = f"upilink:acct:{code}"
                if len(cb.encode("utf-8")) > 64:
                    cb = f"upilink:acct:{code[:40]}"
                row.append({"text": label, "callback_data": cb})
            rows.append(row)
        return rows

    @staticmethod
    def _clear_upi_wizard_payload(payload: dict) -> None:
        payload.pop("pending_upi_provider", None)
        payload.pop("pending_upi_account_code", None)
        payload.pop("pending_upi_profile_name", None)

    @staticmethod
    def _clear_expense_wizard_payload(payload: dict) -> None:
        payload.pop("funding_account_code", None)
        payload.pop("funding_account_type", None)
        payload.pop("pending_expense_partial", None)

    @staticmethod
    def _clear_opening_balance_pick_payload(payload: dict) -> None:
        payload.pop("pending_opening_account_code", None)
        payload.pop("pending_opening_account_label", None)
        payload.pop("pending_opening_from_wizard", None)
        payload.pop("pending_opening_last4", None)

    def _opening_balance_asset_keyboard(self, user_ref: str) -> list[list[dict]] | None:
        accounts = self.ledger_service.list_accounts(user_ref)
        assets = [a for a in accounts if a.get("account_type") == "asset"]
        if not assets:
            return None
        prefix = "openbal:"
        rows: list[list[dict]] = []
        for a in assets:
            code = str(a["code"])
            cb = f"{prefix}{code}"
            if len(cb.encode("utf-8")) > 64:
                continue
            last4 = a.get("account_number_last4")
            label = f"{code} ·{last4}" if last4 else code
            if len(label) > 42:
                label = label[:39] + "..."
            rows.append([{"text": label, "callback_data": cb}])
        return rows or None

    def _clear_expense_wizard(self, telegram_user_id: int, payload: dict) -> None:
        self._clear_expense_wizard_payload(payload)
        self.repository.delete_pending_expense_media(telegram_user_id)

    @staticmethod
    def _mime_for_image_ext(ext: str) -> str:
        e = (ext or "").lower()
        return {
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".heic": "image/heic",
            ".bmp": "image/bmp",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
        }.get(e, "image/jpeg")

    @staticmethod
    def _mime_for_audio_ext(ext: str) -> str | None:
        e = (ext or "").lower()
        return {
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".opus": "audio/opus",
            ".flac": "audio/flac",
        }.get(e)

    @staticmethod
    def _expense_message_kind(message: dict) -> str:
        if message.get("photo"):
            return "photo"
        if message.get("voice"):
            return "voice"
        if message.get("audio"):
            return "audio"
        doc = message.get("document")
        if isinstance(doc, dict):
            mime = (doc.get("mime_type") or "").lower()
            if mime.startswith("image/"):
                return "image_doc"
            if mime.startswith("audio/") or mime in ("application/ogg",):
                return "audio_doc"
        if message.get("text"):
            return "text"
        return "unknown"

    @staticmethod
    def _extract_from_text(text: str) -> dict:
        from api.routes import get_nlp

        nlp = get_nlp()
        r = nlp.extract(text)
        return {**r, "transcript": text}

    @staticmethod
    def _extract_from_audio_file(path: str) -> dict:
        from api.routes import get_nlp, get_stt

        stt = get_stt()
        transcript = stt.process_audio(path)["transcript"]
        nlp = get_nlp()
        r = nlp.extract(transcript)
        return {**r, "transcript": transcript}

    @staticmethod
    def _extract_from_image_file(path: str, caption: str = "") -> dict:
        from api.routes import get_nlp, get_ocr, get_upi_detector

        ocr = get_ocr()
        ocr_result = ocr.process_receipt(path, use_preprocessing=False)
        lines = ocr_result.get("all_lines", [])
        combined = " ".join(lines)
        cap = (caption or "").strip()
        blob = f"{cap}\n{combined}".strip() if cap else combined.strip()
        if not blob:
            blob = cap or "receipt"
        ocr_parsed = ocr_result.get("parsed", {})
        nlp = get_nlp()
        nlp_result = nlp.extract(blob)
        final_amount = ocr_parsed.get("amount") or nlp_result.get("amount")
        final_payment = ocr_parsed.get("payment_method")
        if final_payment == "unknown":
            final_payment = nlp_result.get("payment_method")

        visual_provider: str | None = None
        detector = get_upi_detector()
        if detector is not None:
            visual_provider = detector.detect(path)

        final_provider = (
            visual_provider
            or ocr_parsed.get("payment_provider")
            or nlp_result.get("payment_provider")
        )
        if final_provider and (final_payment is None or final_payment == "unknown"):
            final_payment = "upi"

        final_cash_flow = ocr_parsed.get("cash_flow") or nlp_result.get("cash_flow")

        return {
            "amount": final_amount,
            "category": nlp_result.get("category", "misc"),
            "payment_method": final_payment,
            "payment_provider": final_provider,
            "bank_account": nlp_result.get("bank_account"),
            "cash_flow": final_cash_flow,
            "transcript": blob[:2000],
        }

    async def _download_telegram_file(self, file_id: str) -> tuple[bytes, str]:
        token = self.settings.telegram_bot_token
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": file_id},
            )
            r.raise_for_status()
            body = r.json()
            if not body.get("ok"):
                raise RuntimeError(body.get("description", "getFile failed"))
            fj = body["result"]
            path = str(fj["file_path"])
            ext = ""
            if "." in path:
                ext = "." + path.rsplit(".", 1)[-1].lower()
            fr = await client.get(f"https://api.telegram.org/file/bot{token}/{path}")
            fr.raise_for_status()
            return fr.content, ext

    @staticmethod
    def _expense_account_code() -> str:
        return POOLED_EXPENSE_CODE

    @staticmethod
    def _income_account_code() -> str:
        return POOLED_INCOME_CODE

    async def _post_ledger_from_extract(
        self,
        *,
        chat_id: int,
        user_ref: str,
        telegram_user_id: int,
        payload: dict,
        extracted: dict,
        update_id: int,
        message_id: int | None,
        media_blob: bytes | None = None,
        media_kind: str | None = None,
        media_mime: str | None = None,
    ) -> None:
        if extracted.get("cash_flow") == "income":
            await self._post_income_from_extract(
                chat_id=chat_id,
                user_ref=user_ref,
                telegram_user_id=telegram_user_id,
                payload=payload,
                extracted=extracted,
                update_id=update_id,
                message_id=message_id,
                media_blob=media_blob,
                media_kind=media_kind,
                media_mime=media_mime,
            )
        else:
            await self._post_expense_from_extract(
                chat_id=chat_id,
                user_ref=user_ref,
                telegram_user_id=telegram_user_id,
                payload=payload,
                extracted=extracted,
                update_id=update_id,
                message_id=message_id,
                media_blob=media_blob,
                media_kind=media_kind,
                media_mime=media_mime,
            )

    async def _post_income_from_extract(
        self,
        *,
        chat_id: int,
        user_ref: str,
        telegram_user_id: int,
        payload: dict,
        extracted: dict,
        update_id: int,
        message_id: int | None,
        media_blob: bytes | None = None,
        media_kind: str | None = None,
        media_mime: str | None = None,
    ) -> None:
        amount = extracted.get("amount")
        if amount is None:
            raise ValueError("amount required")
        amount_f = float(amount)
        transcript = (extracted.get("transcript") or "Income").strip() or "Income"
        category = extracted.get("category") or "misc"
        dest_code = payload.get("funding_account_code")
        dest_type = payload.get("funding_account_type")
        pm = extracted.get("payment_method")
        ref = f"tg:{update_id}:{message_id}" if message_id is not None else f"tg:{update_id}"
        onboarding = self.ledger_service.get_onboarding_status(user_ref)
        if not onboarding["ready"]:
            await self.send_message(
                chat_id,
                "Finish account setup first — tap /start and add at least one account with last 4 digits.",
            )
            return
        result = self.ledger_service.post_income(
            IncomeRequest(
                user_ref=user_ref,
                source="telegram_ai",
                description=transcript[:500],
                income_account_code=self._income_account_code(),
                destination_account_code=dest_code,
                destination_account_type=dest_type,
                amount=amount_f,
                external_ref=ref,
                category=str(category),
                payment_method=str(pm) if pm is not None else None,
            )
        )
        if media_blob and media_kind in ("image", "audio"):
            try:
                self.repository.insert_journal_media(
                    int(result["journal_id"]),
                    media_kind,
                    media_mime,
                    media_blob,
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "journal_media insert failed for journal_id=%s",
                    result.get("journal_id"),
                )
        self.repository.delete_pending_expense_media(telegram_user_id)
        payload.pop("pending_expense_partial", None)
        auto_fb = payload.pop("_funding_auto_default", False)
        self._save_session(telegram_user_id, "awaiting_expense_entry", payload)
        short = transcript[:120] + ("…" if len(transcript) > 120 else "")
        dest_line = next((e for e in result["entries"] if e.get("direction") == "debit"), None)
        credited_to = str(dest_line["account_code"]) if dest_line else "?"
        lines = [
            f"Recorded income ₹{amount_f:.2f} — {short}",
            f"Category: {category}. Journal #{result['journal_id']}.",
            "Send another receipt or use the menu.",
        ]
        if auto_fb:
            lines.insert(
                2,
                f"Credited to {credited_to} (your default).",
            )
        await self.send_message(
            chat_id,
            "\n".join(lines),
            keyboard=self._start_keyboard(),
        )

    async def _post_expense_from_extract(
        self,
        *,
        chat_id: int,
        user_ref: str,
        telegram_user_id: int,
        payload: dict,
        extracted: dict,
        update_id: int,
        message_id: int | None,
        media_blob: bytes | None = None,
        media_kind: str | None = None,
        media_mime: str | None = None,
    ) -> None:
        amount = extracted.get("amount")
        if amount is None:
            raise ValueError("amount required")
        amount_f = float(amount)
        transcript = (extracted.get("transcript") or "Expense").strip() or "Expense"
        category = extracted.get("category") or "misc"
        funding_code = payload.get("funding_account_code")
        funding_type = payload.get("funding_account_type")
        payment_provider = payload.get("payment_provider") or extracted.get("payment_provider")
        pm = extracted.get("payment_method")
        ref = f"tg:{update_id}:{message_id}" if message_id is not None else f"tg:{update_id}"
        onboarding = self.ledger_service.get_onboarding_status(user_ref)
        if not onboarding["ready"]:
            await self.send_message(
                chat_id,
                "Finish account setup first — tap /start and add at least one account with last 4 digits.",
            )
            return
        result = self.ledger_service.post_expense(
            ExpenseRequest(
                user_ref=user_ref,
                source="telegram_ai",
                description=transcript[:500],
                expense_account_code=self._expense_account_code(),
                funding_account_code=funding_code,
                funding_account_type=funding_type,
                amount=amount_f,
                external_ref=ref,
                category=str(category),
                payment_method=str(pm) if pm is not None else None,
                payment_provider=payment_provider,
            )
        )
        if media_blob and media_kind in ("image", "audio"):
            try:
                self.repository.insert_journal_media(
                    int(result["journal_id"]),
                    media_kind,
                    media_mime,
                    media_blob,
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "journal_media insert failed for journal_id=%s",
                    result.get("journal_id"),
                )
        self.repository.delete_pending_expense_media(telegram_user_id)
        payload.pop("pending_expense_partial", None)
        auto_fb = payload.pop("_funding_auto_default", False)
        self._save_session(telegram_user_id, "awaiting_expense_entry", payload)
        short = transcript[:120] + ("…" if len(transcript) > 120 else "")
        fund_line = next((e for e in result["entries"] if e.get("direction") == "credit"), None)
        paid_from = str(fund_line["account_code"]) if fund_line else "?"
        lines = [
            f"Recorded ₹{amount_f:.2f} — {short}",
            f"Category: {category}. Journal #{result['journal_id']}.",
            "Wrong category? Tap Change category, pick the right label, or use Back.",
            "Send another purchase (text, voice, or receipt photo) or use the menu.",
        ]
        if auto_fb:
            lines.insert(
                2,
                f"Paid from {paid_from} (your default). Add Expense → Cash/UPI/Card for generic buckets, or pick another account.",
            )
        await self.send_message(
            chat_id,
            "\n".join(lines),
            keyboard=self._keyboard_expense_recorded(int(result["journal_id"])),
        )

    async def _handle_awaiting_expense_entry(
        self,
        *,
        chat_id: int,
        telegram_user_id: int,
        user_ref: str,
        message: dict,
        payload: dict,
        update: dict,
    ) -> dict:
        kind = self._expense_message_kind(message)
        uid = int(update.get("update_id", 0))
        mid = message.get("message_id")

        tmp_path: str | None = None
        extracted: dict | None = None
        media_blob: bytes | None = None
        media_store_kind: str | None = None
        media_mime: str | None = None
        try:
            if kind == "text":
                raw = (message.get("text") or "").strip()
                if not raw:
                    await self.send_message(
                        chat_id,
                        "Send what you bought (and amount if you can), a voice note, or a receipt photo.",
                    )
                    return {"status": "ok", "message": "expense_need_input"}
                extracted = await asyncio.to_thread(self._extract_from_text, raw)
            elif kind in ("voice", "audio", "audio_doc"):
                if kind == "audio_doc":
                    doc = message.get("document") or {}
                    file_obj = doc
                else:
                    file_obj = message.get("voice") or message.get("audio")
                if not file_obj or not file_obj.get("file_id"):
                    await self.send_message(chat_id, "Could not read that audio. Try again or send text.")
                    return {"status": "ok", "message": "expense_bad_audio"}
                content, ext = await self._download_telegram_file(file_obj["file_id"])
                if kind == "audio_doc" and not ext:
                    fname = (file_obj.get("file_name") or "").lower()
                    for cand in (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac"):
                        if fname.endswith(cand):
                            ext = cand
                            break
                media_blob = content
                media_store_kind = "audio"
                if kind == "voice":
                    media_mime = "audio/ogg"
                elif kind == "audio":
                    aud = message.get("audio") or {}
                    media_mime = aud.get("mime_type") or self._mime_for_audio_ext(ext) or "audio/mpeg"
                else:
                    media_mime = file_obj.get("mime_type") or self._mime_for_audio_ext(ext) or "application/octet-stream"
                suffix = ext if ext else ".ogg"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                with open(tmp_path, "wb") as f:
                    f.write(content)
                extracted = await asyncio.to_thread(self._extract_from_audio_file, tmp_path)
            elif kind in ("photo", "image_doc"):
                if kind == "photo":
                    photos = message["photo"]
                    file_id = max(photos, key=lambda p: p.get("file_size", 0))["file_id"]
                else:
                    doc = message.get("document") or {}
                    file_id = doc.get("file_id")
                if not file_id:
                    await self.send_message(chat_id, "Could not read that image. Try again.")
                    return {"status": "ok", "message": "expense_bad_image"}
                caption = (message.get("caption") or "").strip()
                content, ext = await self._download_telegram_file(file_id)
                media_blob = content
                media_store_kind = "image"
                if kind == "photo":
                    media_mime = self._mime_for_image_ext(ext)
                else:
                    doc = message.get("document") or {}
                    media_mime = doc.get("mime_type") or self._mime_for_image_ext(ext)
                suffix = ext if ext else ".jpg"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                with open(tmp_path, "wb") as f:
                    f.write(content)
                extracted = await asyncio.to_thread(self._extract_from_image_file, tmp_path, caption)
            else:
                await self.send_message(
                    chat_id,
                    "Send plain text, a voice note, an audio file, or a receipt image.",
                )
                return {"status": "ok", "message": "expense_bad_type"}
        except Exception:
            await self.send_message(
                chat_id,
                "Could not process that. Try clearer text with an amount, another voice note or photo, or /cancel.",
            )
            return {"status": "ok", "message": "expense_ai_error"}
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        if not extracted:
            return {"status": "ok", "message": "expense_no_extract"}

        amount = extracted.get("amount")
        if amount is None:
            if media_blob and media_store_kind in ("image", "audio"):
                self.repository.upsert_pending_expense_media(
                    telegram_user_id,
                    media_store_kind,
                    media_mime,
                    media_blob,
                )
            else:
                self.repository.delete_pending_expense_media(telegram_user_id)
            payload["pending_expense_partial"] = extracted
            self._save_session(telegram_user_id, "awaiting_expense_amount", payload)
            await self.send_message(
                chat_id,
                "I couldn't detect an amount. Reply with just the number (e.g. 250 or 99.50). Or /cancel.",
            )
            return {"status": "ok", "message": "need_amount"}

        try:
            await self._post_ledger_from_extract(
                chat_id=chat_id,
                user_ref=user_ref,
                telegram_user_id=telegram_user_id,
                payload=payload,
                extracted=extracted,
                update_id=uid,
                message_id=mid,
                media_blob=media_blob,
                media_kind=media_store_kind,
                media_mime=media_mime,
            )
        except ValueError as exc:
            await self.send_message(
                chat_id,
                f"{exc}\nTap Add Expense to choose funding, or Accounts → set a default account.",
            )
            return {"status": "ok", "message": "expense_funding_unresolved"}
        except Exception:
            await self.send_message(
                chat_id,
                "Could not save that expense to the ledger. Try again or /cancel.",
            )
            return {"status": "ok", "message": "expense_post_failed"}
        return {"status": "ok", "message": "expense_posted"}

    async def send_message(self, chat_id: int, text: str, keyboard: list[list[dict]] | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = {"inline_keyboard": keyboard}

        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
                json=payload,
            )

    async def answer_callback_query(
        self, callback_query_id: str | None, text: str | None = None, *, show_alert: bool = False
    ) -> None:
        if not callback_query_id:
            return
        body: dict = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            body["text"] = text[:200]
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/answerCallbackQuery",
                json=body,
            )

    async def clear_inline_keyboard(self, chat_id: int, message_id: int) -> None:
        await self.set_message_inline_keyboard(chat_id, message_id, [])

    async def set_message_inline_keyboard(
        self, chat_id: int, message_id: int, keyboard: list[list[dict]]
    ) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": keyboard},
                },
            )

    def _keyboard_expense_recorded(self, journal_id: int) -> list[list[dict]]:
        """Change category + main menu (categories shown only after catch:)."""
        cb = f"catch:{journal_id}"
        if len(cb.encode("utf-8")) > 64:
            return self._start_keyboard()
        return [[{"text": "Change category", "callback_data": cb}]] + self._start_keyboard()

    @staticmethod
    def _format_inr_minor(minor: int) -> str:
        return f"₹{minor / 100:,.2f}"

    @staticmethod
    def _append_report_breakdown(lines: list[str], heading: str, rows: list[dict], limit: int) -> None:
        lines.append("")
        lines.append(heading)
        n = 0
        for r in rows:
            if n >= limit:
                break
            m = int(r.get("amount_minor", 0))
            if m <= 0:
                continue
            k = str(r.get("key", "?"))
            lines.append(f"  • {k}: ₹{m / 100:,.2f}")
            n += 1
        if n == 0:
            lines.append("  (no activity in this window)")

    def _message_text_enriched_report(self, bundle: dict) -> str:
        lines = [
            bundle["title"],
            bundle["range_hint"],
            "",
            "Totals",
            f"  Income:      {self._format_inr_minor(bundle['income_minor'])}",
            f"  Expense:     {self._format_inr_minor(bundle['expense_minor'])}",
            f"  Investment:  {self._format_inr_minor(bundle['investment_minor'])}",
            f"  Net:         {self._format_inr_minor(bundle['net_cashflow_minor'])}",
        ]
        self._append_report_breakdown(lines, "Top categories", bundle.get("by_category") or [], 8)
        self._append_report_breakdown(lines, "By payment method", bundle.get("by_payment_method") or [], 6)
        text = "\n".join(lines)
        if len(text) > 4000:
            return text[:3990] + "\n… (truncated)"
        return text

    def _keyboard_category_picker(self, journal_id: int) -> list[list[dict]]:
        rows: list[list[dict]] = []
        row: list[dict] = []
        for cat in EXPENSE_CATEGORY_FIX:
            cb = f"c:{journal_id}:{cat}"
            if len(cb.encode("utf-8")) > 64:
                continue
            row.append({"text": cat.replace("_", " ").title(), "callback_data": cb})
            if len(row) == 3:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        back_cb = f"catback:{journal_id}"
        if len(back_cb.encode("utf-8")) <= 64:
            rows.append([{"text": "« Back", "callback_data": back_cb}])
        return rows

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
            [
                {"text": "Add bank / Link UPI", "callback_data": "dash:setup_menu"},
            ],
            [{"text": "Opening balance", "callback_data": "dash:opening_balance"}],
        ]

    def _prestart_keyboard(self) -> list[list[dict]]:
        return [[{"text": "Start Fold", "callback_data": "dash:start"}]]

    @staticmethod
    def _onboarding_prompt_text() -> str:
        return (
            "Set up Fold:\n"
            "1) Add one or more bank / card accounts (last 4 digits each). You can add 2–3 banks over time.\n"
            "2) Link each UPI app (GPay, PhonePe, …) to the bank account it spends from — "
            "so receipt imports pick the right funding account.\n"
            "Digital banks (Slice, Jupiter, Fi) use “Add Digital Bank”.\n"
            "When at least one account is saved, tap Done."
        )

    def _onboarding_keyboard(self) -> list[list[dict]]:
        return [
            [
                {"text": "Add Bank Account", "callback_data": "setup:add_bank"},
                {"text": "Add Digital Bank", "callback_data": "setup:add_digital"},
            ],
            [{"text": "Link UPI App", "callback_data": "setup:link_upi"}],
            [{"text": "Done", "callback_data": "setup:done"}],
        ]

    def _setup_menu_keyboard(self) -> list[list[dict]]:
        """After onboarding: add more banks or UPI without losing dashboard access."""
        return [
            [
                {"text": "Add Bank Account", "callback_data": "setup:add_bank"},
                {"text": "Add Digital Bank", "callback_data": "setup:add_digital"},
            ],
            [{"text": "Link UPI App", "callback_data": "setup:link_upi"}],
            [{"text": "Back to menu", "callback_data": "dash:start"}],
        ]

    def _save_session(self, telegram_user_id: int, state: str, payload: dict) -> None:
        self.repository.upsert_session(telegram_user_id=telegram_user_id, state=state, payload=payload)

    def _get_session(self, telegram_user_id: int) -> dict:
        existing = self.repository.get_session(telegram_user_id)
        return existing or {"state": "idle", "payload_json": {}}

    async def handle_update(self, update: dict) -> dict:
        uid = int(update.get("update_id") or 0)
        if uid and not self.repository.try_claim_telegram_update(uid):
            return {"status": "ok", "message": "duplicate_update_ignored"}

        message = update.get("message", {})
        callback = update.get("callback_query", {})

        if message:
            chat_id = message["chat"]["id"]
            raw_text = (message.get("text") or "").strip()
            text = raw_text.lower()
            telegram_user_id = message["from"]["id"]
            user_ref = f"telegram:{telegram_user_id}"
            self.repository.get_or_create_user(user_ref)
            session = self._get_session(telegram_user_id)
            payload = dict(session.get("payload_json") or {})
            flow_state = session.get("state") or "idle"

            # ─── /start clears any in-progress wizard ───
            if text in {"/start", "/add"}:
                if flow_state in (
                    "awaiting_account_last4",
                    "awaiting_account_nickname",
                    "awaiting_account_opening_balance",
                    "awaiting_upi_provider",
                    "awaiting_upi_account_pick",
                    "awaiting_upi_profile_name",
                    "awaiting_upi_handle",
                    "awaiting_expense_entry",
                    "awaiting_expense_amount",
                ):
                    payload.pop("pending_last4", None)
                    payload.pop("setup_kind", None)
                    self._clear_upi_wizard_payload(payload)
                    self._clear_opening_balance_pick_payload(payload)
                    self._clear_expense_wizard(telegram_user_id, payload)
                    self._save_session(telegram_user_id, "idle", payload)
                    flow_state = "idle"

            # ─── Guided setup: one message at a time (no long /add_account strings) ───
            if text == "/cancel":
                payload.pop("pending_last4", None)
                payload.pop("setup_kind", None)
                self._clear_upi_wizard_payload(payload)
                self._clear_opening_balance_pick_payload(payload)
                self._clear_expense_wizard(telegram_user_id, payload)
                self._save_session(telegram_user_id, "idle", payload)
                onboarding = self.ledger_service.get_onboarding_status(user_ref)
                kb = self._start_keyboard() if onboarding["ready"] else self._onboarding_keyboard()
                await self.send_message(chat_id, "Cancelled.", keyboard=kb)
                return {"status": "ok", "message": "wizard_cancelled"}

            flow_in_onboarding = flow_state in self._ONBOARDING_FLOW_STATES
            flow_in_expense = flow_state in self._EXPENSE_FLOW_STATES
            if (flow_in_onboarding or flow_in_expense) and text.startswith("/") and text not in (
                "/cancel",
                "/start",
                "/add",
            ):
                if flow_in_onboarding:
                    await self.send_message(
                        chat_id,
                        "You're in account setup — finish the step above, or send /cancel to stop.\n"
                        "Other commands work after setup is done.",
                    )
                    return {"status": "ok", "message": "setup_blocks_slash_commands"}
                payload.pop("pending_last4", None)
                payload.pop("setup_kind", None)
                self._clear_upi_wizard_payload(payload)
                self._clear_opening_balance_pick_payload(payload)
                self._clear_expense_wizard(telegram_user_id, payload)
                self._save_session(telegram_user_id, "idle", payload)
                flow_state = "idle"

            if flow_state == "awaiting_expense_amount":
                if message.get("photo") or message.get("voice") or message.get("audio") or message.get("document"):
                    await self.send_message(
                        chat_id,
                        "Reply with the amount as a number only (e.g. 250). Or /cancel.",
                    )
                    return {"status": "ok", "message": "amount_need_text"}
                if not raw_text or raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        "Reply with the amount as a number only (e.g. 250 or 99.50). Or /cancel.",
                    )
                    return {"status": "ok", "message": "amount_need_number"}
                cleaned = raw_text.strip().lower().replace("₹", "").replace("rs.", "").replace("rs", "").replace(",", "")
                m = re.search(r"\d+(?:\.\d+)?", cleaned)
                if not m:
                    await self.send_message(
                        chat_id,
                        "Couldn't parse that. Send a number like 250 or 99.5. Or /cancel.",
                    )
                    return {"status": "ok", "message": "amount_bad"}
                amount_f = float(m.group())
                partial = payload.pop("pending_expense_partial", None) or {}
                partial["amount"] = amount_f
                pending_media = self.repository.fetch_pending_expense_media(telegram_user_id)
                media_kw: dict = {}
                if pending_media and pending_media.get("file_bytes") is not None:
                    raw_b = pending_media["file_bytes"]
                    media_kw["media_blob"] = raw_b if isinstance(raw_b, (bytes, bytearray)) else bytes(raw_b)
                    media_kw["media_kind"] = pending_media["media_kind"]
                    media_kw["media_mime"] = pending_media.get("mime_type")
                try:
                    await self._post_ledger_from_extract(
                        chat_id=chat_id,
                        user_ref=user_ref,
                        telegram_user_id=telegram_user_id,
                        payload=payload,
                        extracted=partial,
                        update_id=int(update.get("update_id", 0)),
                        message_id=message.get("message_id"),
                        **media_kw,
                    )
                except ValueError as exc:
                    await self.send_message(
                        chat_id,
                        f"{exc}\nTap Add Expense to choose funding, or Accounts → set a default account.",
                    )
                    return {"status": "ok", "message": "expense_funding_unresolved"}
                except Exception:
                    await self.send_message(
                        chat_id,
                        "Could not save that expense. Try again or /cancel.",
                    )
                    return {"status": "ok", "message": "expense_post_failed"}
                return {"status": "ok", "message": "expense_posted"}

            if flow_state == "awaiting_expense_entry":
                return await self._handle_awaiting_expense_entry(
                    chat_id=chat_id,
                    telegram_user_id=telegram_user_id,
                    user_ref=user_ref,
                    message=message,
                    payload=payload,
                    update=update,
                )

            if flow_state == "idle":
                kind = self._expense_message_kind(message)
                if kind in ("voice", "audio", "photo", "image_doc", "audio_doc"):
                    onboarding = self.ledger_service.get_onboarding_status(user_ref)
                    if not onboarding["ready"]:
                        await self.send_message(
                            chat_id,
                            "Finish setup first — tap /start and add at least one account (last 4 digits). "
                            "Then you can send receipts or audio without picking funding first.",
                            keyboard=self._onboarding_keyboard(),
                        )
                        return {"status": "ok", "message": "onboarding_required_media"}
                    media_payload = dict(payload)
                    if not media_payload.get("funding_account_code"):
                        r = self.ledger_service.resolve_primary_cash_account(user_ref, spending=True)
                        if r is None:
                            await self.send_message(
                                chat_id,
                                "Tap Add Expense first to choose where money comes from, or open Accounts and set "
                                "★ Default on one of your bank/card accounts.\n"
                                "(Voice/receipt shortcuts need one clear default when you have several accounts.)",
                                keyboard=self._start_keyboard(),
                            )
                            return {"status": "ok", "message": "need_funding_or_primary"}
                        media_payload["funding_account_code"] = r[0]
                        media_payload["funding_account_type"] = r[1]
                        media_payload["_funding_auto_default"] = True
                    return await self._handle_awaiting_expense_entry(
                        chat_id=chat_id,
                        telegram_user_id=telegram_user_id,
                        user_ref=user_ref,
                        message=message,
                        payload=media_payload,
                        update=update,
                    )

            if flow_state == "awaiting_account_last4":
                if not raw_text or raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        "Send exactly 4 digits (last 4 of your account or card). Or /cancel.",
                    )
                    return {"status": "ok", "message": "wizard_need_digits"}
                digits = "".join(ch for ch in raw_text if ch.isdigit())
                if len(digits) != 4:
                    await self.send_message(
                        chat_id,
                        "Please send exactly 4 digits only (e.g. 1234). Or /cancel.",
                    )
                    return {"status": "ok", "message": "wizard_bad_digits"}
                payload["pending_last4"] = digits
                self._save_session(telegram_user_id, "awaiting_account_nickname", payload)
                await self.send_message(
                    chat_id,
                    "Step 2/3: What should we call this account?\n"
                    "Example: HDFC Primary or Slice card\n"
                    "(Reply with a short name — not a command.)",
                )
                return {"status": "ok", "message": "wizard_need_nickname"}

            if flow_state == "awaiting_account_opening_balance":
                code = payload.get("pending_opening_account_code")
                if not code:
                    self._clear_opening_balance_pick_payload(payload)
                    self._save_session(telegram_user_id, "idle", payload)
                    await self.send_message(chat_id, "Nothing to set. Tap Opening balance or /start.")
                    return {"status": "ok", "message": "opening_expired"}
                if not raw_text or raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        f"Opening balance for {code} — reply with the amount in INR (numbers only), e.g. 50000.\n"
                        "Send 0 or skip if the account starts at zero. Or /cancel.",
                    )
                    return {"status": "ok", "message": "opening_need_amount"}
                tlow = raw_text.strip().lower()
                if tlow in ("skip", "no", "none", "-", "n/a"):
                    amount_f = 0.0
                else:
                    cleaned = raw_text.strip().lower().replace("₹", "").replace("rs.", "").replace("rs", "").replace(",", "")
                    m = re.search(r"\d+(?:\.\d+)?", cleaned)
                    if not m:
                        await self.send_message(
                            chat_id,
                            "Send a number like 50000, or skip / 0. Or /cancel.",
                        )
                        return {"status": "ok", "message": "opening_bad_amount"}
                    amount_f = float(m.group())
                from_wizard = bool(payload.get("pending_opening_from_wizard", False))
                label = payload.get("pending_opening_account_label")
                last4_disp = payload.get("pending_opening_last4")
                self._clear_opening_balance_pick_payload(payload)
                self._save_session(telegram_user_id, "idle", payload)
                opener_msg = ""
                if amount_f > 0:
                    try:
                        result = self.ledger_service.post_opening_balance(
                            OpeningBalanceRequest(
                                user_ref=user_ref,
                                source="telegram",
                                account_code=code,
                                account_type="asset",
                                amount=amount_f,
                                external_ref=str(update.get("update_id")),
                            )
                        )
                        opener_msg = f"Opening balance recorded: ₹{amount_f:,.2f} on {code} (journal #{result['journal_id']})."
                    except Exception as exc:
                        await self.send_message(
                            chat_id,
                            f"Could not save opening balance: {exc}\nTry /opening {code} asset <amount> or tap Opening balance again.",
                        )
                        return {"status": "ok", "message": "opening_post_failed"}
                else:
                    opener_msg = f"No opening balance set for {code} (add one anytime: Opening balance button or /opening)."
                onboarding = self.ledger_service.get_onboarding_status(user_ref)
                kb = self._start_keyboard() if onboarding["ready"] else self._onboarding_keyboard()
                if from_wizard and label:
                    await self.send_message(
                        chat_id,
                        f"{opener_msg}\n\n"
                        f"Saved: {label} (code {code}) ending {last4_disp or '****'}.\n\n"
                        "Optional: open the main menu → “Add bank / Link UPI” to connect GPay/PhonePe to this account, "
                        "or add another bank.\n"
                        "Use the buttons below.",
                        keyboard=kb,
                    )
                else:
                    await self.send_message(chat_id, f"{opener_msg}", keyboard=kb)
                return {"status": "ok", "message": "opening_saved"}

            if flow_state == "awaiting_account_nickname":
                if not raw_text or raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        "Please send a short name for this account (plain text). Or /cancel.",
                    )
                    return {"status": "ok", "message": "wizard_need_name"}
                nickname = raw_text.strip()
                base_code = self._slugify_account_code(nickname)
                code = self._unique_account_code(user_ref, base_code)
                setup_kind = payload.get("setup_kind", "bank")
                is_digital = setup_kind == "digital"
                institution = nickname.split()[0] if nickname else None
                last4_saved = payload.get("pending_last4")
                self.ledger_service.upsert_account(
                    AccountUpsertRequest(
                        user_ref=user_ref,
                        code=code,
                        name=nickname,
                        account_type="asset",
                        institution_name=institution,
                        account_number_last4=last4_saved,
                        is_digital=is_digital,
                    )
                )
                payload["pending_opening_account_code"] = code
                payload["pending_opening_account_label"] = nickname
                payload["pending_opening_from_wizard"] = True
                payload["pending_opening_last4"] = last4_saved
                payload.pop("pending_last4", None)
                payload.pop("setup_kind", None)
                self._save_session(telegram_user_id, "awaiting_account_opening_balance", payload)
                await self.send_message(
                    chat_id,
                    "Step 3/3: What should the opening balance be for this account (in INR)?\n"
                    f"Account: {nickname} (code {code}).\n"
                    "Reply with a number only (e.g. 50000), or 0 / skip if it starts at zero.\n"
                    "Or /cancel.",
                )
                return {"status": "ok", "message": "wizard_need_opening"}

            # ─── UPI link wizard (provider → pick account → label → optional VPA) ───
            if flow_state == "awaiting_upi_account_pick":
                if raw_text and not raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        "Please tap one of the account buttons above to choose where this UPI app spends from.\n"
                        "Or /cancel.",
                    )
                    return {"status": "ok", "message": "upi_need_button"}

            if flow_state == "awaiting_upi_provider":
                if not raw_text or raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        "Step 1/4: Which UPI app? Reply with a short name, e.g. phonepe, gpay, paytm\n"
                        "Or /cancel.",
                    )
                    return {"status": "ok", "message": "upi_need_provider"}
                prov = re.sub(r"[^a-z0-9]+", "", raw_text.lower()).strip() or raw_text.strip().lower()
                if len(prov) < 2:
                    await self.send_message(chat_id, "Please send a valid app name (at least 2 characters). Or /cancel.")
                    return {"status": "ok", "message": "upi_provider_short"}
                payload["pending_upi_provider"] = prov[:32]
                kb = self._upi_account_pick_keyboard(user_ref)
                if not kb:
                    self._clear_upi_wizard_payload(payload)
                    self._save_session(telegram_user_id, "idle", payload)
                    await self.send_message(
                        chat_id,
                        "No asset/liability accounts found. Add a bank or digital account first, then try Link UPI again.",
                        keyboard=self._onboarding_keyboard(),
                    )
                    return {"status": "ok", "message": "upi_no_accounts"}
                self._save_session(telegram_user_id, "awaiting_upi_account_pick", payload)
                await self.send_message(
                    chat_id,
                    f"Step 2/4: Link {prov} to which account?\nTap a button below.",
                    keyboard=kb,
                )
                return {"status": "ok", "message": "upi_pick_account"}

            if flow_state == "awaiting_upi_profile_name":
                if not raw_text or raw_text.startswith("/"):
                    await self.send_message(
                        chat_id,
                        "Step 3/4: Short label for this link (e.g. PhonePe HDFC). Plain text. Or /cancel.",
                    )
                    return {"status": "ok", "message": "upi_need_profile_name"}
                payload["pending_upi_profile_name"] = raw_text.strip()[:120]
                self._save_session(telegram_user_id, "awaiting_upi_handle", payload)
                await self.send_message(
                    chat_id,
                    "Step 4/4 (optional): Your UPI ID (e.g. name@oksbi). Reply skip to omit.\n"
                    "Or /cancel.",
                )
                return {"status": "ok", "message": "upi_need_handle"}

            if flow_state == "awaiting_upi_handle":
                handle_val: str | None = None
                if raw_text and not raw_text.startswith("/"):
                    tstrip = raw_text.strip()
                    if tstrip.lower() not in ("skip", "no", "-", "none"):
                        handle_val = tstrip[:128]
                provider = payload.get("pending_upi_provider") or "upi"
                acct = payload.get("pending_upi_account_code")
                pname_human = payload.get("pending_upi_profile_name") or f"{provider}_main"
                profile_key = self._slugify_account_code(pname_human)[:64] or "profile"
                if not acct:
                    self._clear_upi_wizard_payload(payload)
                    self._save_session(telegram_user_id, "idle", payload)
                    await self.send_message(chat_id, "Session expired. Tap Link UPI App again. Or /start.")
                    return {"status": "ok", "message": "upi_expired"}
                profile = self.ledger_service.upsert_payment_profile(
                    PaymentProfileUpsertRequest(
                        user_ref=user_ref,
                        profile_type="upi",
                        provider=provider,
                        profile_name=profile_key,
                        linked_account_code=acct,
                        handle_ref=handle_val,
                    )
                )
                prov_out = str(profile.get("provider", provider)).lower()
                payload["payment_provider"] = prov_out
                self._clear_upi_wizard_payload(payload)
                self._save_session(telegram_user_id, "idle", payload)
                await self.send_message(
                    chat_id,
                    f"Linked UPI: {prov_out} → bank account {acct} (label: {pname_human}).\n"
                    "Receipts that detect this app will charge that account when you use Add Expense with the default or auto funding.",
                    keyboard=self._start_keyboard(),
                )
                return {"status": "ok", "message": "upi_linked_wizard"}

            if text in {"/start", "/add"}:
                if not payload.get("started"):
                    await self.send_message(
                        chat_id,
                        "Welcome to Fold. Tap Start Fold to open your dashboard.",
                        keyboard=self._prestart_keyboard(),
                    )
                    self._save_session(telegram_user_id, "awaiting_start", payload)
                    return {"status": "ok", "message": "prestart_sent"}

                onboarding = self.ledger_service.get_onboarding_status(user_ref)
                if not onboarding["ready"]:
                    await self.send_message(
                        chat_id,
                        self._onboarding_prompt_text(),
                        keyboard=self._onboarding_keyboard(),
                    )
                    return {"status": "ok", "message": "onboarding_required"}

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
                funding_code = payload.get("funding_account_code")
                funding_type = payload.get("funding_account_type")
                payment_provider = payload.get("payment_provider")
                onboarding = self.ledger_service.get_onboarding_status(user_ref)
                if not onboarding["ready"]:
                    await self.send_message(
                        chat_id,
                        "Please finish account setup first. Use /start and add at least one account with last 4 digits.",
                    )
                    return {"status": "ok", "message": "onboarding_required"}
                try:
                    result = self.ledger_service.post_expense(
                        ExpenseRequest(
                            user_ref=user_ref,
                            source="telegram",
                            description=description,
                            expense_account_code=POOLED_EXPENSE_CODE,
                            funding_account_code=funding_code,
                            funding_account_type=funding_type,
                            amount=amount,
                            external_ref=str(update.get("update_id")),
                            payment_provider=payment_provider,
                        )
                    )
                except ValueError as exc:
                    await self.send_message(chat_id, str(exc))
                    return {"status": "ok", "message": "expense_funding_unresolved"}
                jid = int(result["journal_id"])
                await self.send_message(
                    chat_id,
                    f"Recorded expense. Journal #{jid}.\nWrong category? Tap Change category.",
                    keyboard=self._keyboard_expense_recorded(jid),
                )
                return {"status": "ok", "result": result}

            if text == "/balance":
                balances = self.ledger_service.get_cash_snapshot(user_ref=user_ref)
                if not balances:
                    await self.send_message(chat_id, "No accounts yet. Add one via /start first.")
                    return {"status": "ok", "message": "no_balances"}

                lines = ["Balance Snapshot:"]
                for row in balances:
                    lines.append(f"  {row['code']}: ₹{row['balance_minor'] / 100:,.2f}")
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
                        destination_account_code=None,
                        destination_account_type=None,
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
                try:
                    result = self.ledger_service.post_investment(
                        InvestmentRequest(
                            user_ref=user_ref,
                            source="telegram",
                            description=parts[2],
                            amount=float(parts[1]),
                            investment_account_code=POOLED_INVESTMENT_CODE,
                            funding_account_code=payload.get("funding_account_code"),
                            funding_account_type=payload.get("funding_account_type"),
                            external_ref=str(update.get("update_id")),
                        )
                    )
                except ValueError as exc:
                    await self.send_message(chat_id, str(exc))
                    return {"status": "ok", "message": "investment_funding_unresolved"}
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

            if text.startswith("/add_account"):
                parts = text.split(" ", 5)
                if len(parts) < 6:
                    await self.send_message(
                        chat_id,
                        "Use: /add_account <code> <asset|liability> <last4> <institution> <digital|bank>",
                    )
                    return {"status": "ok", "message": "usage_sent"}
                code = parts[1]
                account_type = parts[2]
                last4 = parts[3]
                institution = parts[4]
                mode = parts[5]
                is_digital = mode == "digital"
                account = self.ledger_service.upsert_account(
                    AccountUpsertRequest(
                        user_ref=user_ref,
                        code=code,
                        name=code.replace("_", " ").title(),
                        account_type=account_type,  # type: ignore[arg-type]
                        institution_name=institution,
                        account_number_last4=last4,
                        is_digital=is_digital,
                    )
                )
                await self.send_message(
                    chat_id,
                    f"Account saved: {account['code']} ({institution}) ending {account['account_number_last4']}.",
                )
                return {"status": "ok", "message": "account_added"}

            if text.startswith("/link_upi"):
                parts = text.split(" ", 4)
                if len(parts) < 4:
                    await self.send_message(chat_id, "Use: /link_upi <provider> <account_code> <profile_name> [handle]")
                    return {"status": "ok", "message": "usage_sent"}
                provider = parts[1]
                account_code = parts[2]
                profile_name = parts[3]
                handle_ref = parts[4] if len(parts) > 4 else None
                profile = self.ledger_service.upsert_payment_profile(
                    PaymentProfileUpsertRequest(
                        user_ref=user_ref,
                        profile_type="upi",
                        provider=provider,
                        profile_name=profile_name,
                        linked_account_code=account_code,
                        handle_ref=handle_ref,
                    )
                )
                session_now = self._get_session(telegram_user_id)
                new_payload = dict(session_now.get("payload_json") or {})
                new_payload["payment_provider"] = provider.lower()
                self._save_session(telegram_user_id, "idle", new_payload)
                await self.send_message(
                    chat_id,
                    f"Linked {profile['provider']} ({profile['profile_name']}) to {account_code}.",
                )
                return {"status": "ok", "message": "upi_linked"}

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
                    "Fold:\n"
                    "/start — dashboard\n"
                    "Expenses: tap Add Expense, pick Cash/UPI/Card, then send plain text, a voice note, or a receipt photo.\n"
                    "Dashboard: Opening balance picks an account; new accounts ask for opening balance after the nickname step.\n"
                    "Optional: /expense, /income, /investment, /transfer, /balance, /opening, /link_upi, /add_account"
                ),
            )
            return {"status": "ok", "message": "help_sent"}

        if callback:
            chat_id = callback["message"]["chat"]["id"]
            telegram_user_id = callback["from"]["id"]
            user_ref = f"telegram:{telegram_user_id}"
            self.repository.get_or_create_user(user_ref)
            data = callback.get("data", "")
            cbq_id = callback.get("id")

            if data.startswith("dash:start"):
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                session_payload["started"] = True
                self._save_session(telegram_user_id, "idle", session_payload)
                onboarding = self.ledger_service.get_onboarding_status(user_ref)
                if not onboarding["ready"]:
                    await self.send_message(
                        chat_id,
                        self._onboarding_prompt_text(),
                        keyboard=self._onboarding_keyboard(),
                    )
                    await self.answer_callback_query(cbq_id)
                    return {"status": "ok", "message": "onboarding_prompted"}
                await self.send_message(
                    chat_id,
                    "Fold Dashboard:\nChoose an action.",
                    keyboard=self._start_keyboard(),
                )
                await self.answer_callback_query(cbq_id)
                return {"status": "ok", "message": "dashboard_sent"}
            elif data.startswith("catch:"):
                cqid = callback.get("id")
                try:
                    jid = int(data[len("catch:") :])
                except ValueError:
                    await self.answer_callback_query(cqid, "Invalid journal", show_alert=True)
                    return {"status": "ok", "message": "catch_bad"}
                mid = callback.get("message", {}).get("message_id")
                await self.answer_callback_query(cqid)
                if mid:
                    try:
                        await self.set_message_inline_keyboard(
                            chat_id, int(mid), self._keyboard_category_picker(jid)
                        )
                    except Exception:
                        logging.getLogger(__name__).exception("editMessageReplyMarkup catch failed")
                return {"status": "ok", "message": "catch_ok"}
            elif data.startswith("catback:"):
                cqid = callback.get("id")
                try:
                    jid = int(data[len("catback:") :])
                except ValueError:
                    await self.answer_callback_query(cqid, "Invalid journal", show_alert=True)
                    return {"status": "ok", "message": "catback_bad"}
                mid = callback.get("message", {}).get("message_id")
                await self.answer_callback_query(cqid)
                if mid:
                    try:
                        await self.set_message_inline_keyboard(
                            chat_id, int(mid), self._keyboard_expense_recorded(jid)
                        )
                    except Exception:
                        logging.getLogger(__name__).exception("editMessageReplyMarkup catback failed")
                return {"status": "ok", "message": "catback_ok"}
            elif data.startswith("c:"):
                parts = data.split(":", 2)
                cqid = callback.get("id")
                if len(parts) < 3:
                    await self.answer_callback_query(cqid, "Invalid button", show_alert=True)
                    return {"status": "ok", "message": "catfx_bad"}
                _, jid_s, cat = parts
                try:
                    jid = int(jid_s)
                except ValueError:
                    await self.answer_callback_query(cqid, "Invalid journal id", show_alert=True)
                    return {"status": "ok", "message": "catfx_bad_jid"}
                mid = callback.get("message", {}).get("message_id")
                try:
                    self.ledger_service.reassign_expense_category(user_ref, jid, cat)
                except Exception as exc:
                    await self.answer_callback_query(cqid, str(exc)[:200], show_alert=True)
                    return {"status": "ok", "message": "catfx_failed"}
                await self.answer_callback_query(cqid, f"Category: {cat}")
                if mid:
                    try:
                        await self.set_message_inline_keyboard(chat_id, int(mid), self._start_keyboard())
                    except Exception:
                        logging.getLogger(__name__).exception("editMessageReplyMarkup after catfx failed")
                await self.send_message(chat_id, f"Updated journal #{jid} to category: {cat}.")
                return {"status": "ok", "message": "catfx_ok"}
            elif data.startswith("dash:setup_menu"):
                await self.send_message(
                    chat_id,
                    "Add another bank or card, or link a UPI app to an existing account.\n"
                    "You can keep several banks on file; set the default under Accounts.",
                    keyboard=self._setup_menu_keyboard(),
                )
                await self.answer_callback_query(cbq_id)
                return {"status": "ok", "message": "setup_menu_sent"}
            elif data.startswith("setup:add_bank"):
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                session_payload["setup_kind"] = "bank"
                self._save_session(telegram_user_id, "awaiting_account_last4", session_payload)
                await self.send_message(
                    chat_id,
                    "Add bank account — Step 1/3\n"
                    "Send the last 4 digits of your account or card (numbers only).\n"
                    "Or /cancel.",
                )
            elif data.startswith("setup:add_digital"):
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                session_payload["setup_kind"] = "digital"
                self._save_session(telegram_user_id, "awaiting_account_last4", session_payload)
                await self.send_message(
                    chat_id,
                    "Add digital bank (e.g. Slice, Jupiter, Fi) — Step 1/3\n"
                    "Send the last 4 digits shown for that account/card.\n"
                    "Or /cancel.",
                )
            elif data.startswith("setup:link_upi"):
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                self._clear_upi_wizard_payload(session_payload)
                self._save_session(telegram_user_id, "awaiting_upi_provider", session_payload)
                await self.send_message(
                    chat_id,
                    "Link UPI — Step 1/4\n"
                    "Which app? Reply with a short name, e.g. phonepe, gpay, paytm, cred\n"
                    "Or /cancel.",
                )
            elif data.startswith("upilink:acct:"):
                parts = data.split(":", 2)
                acct_code = parts[2] if len(parts) > 2 else ""
                if not acct_code:
                    await self.send_message(chat_id, "Invalid selection. Try Link UPI again.")
                    await self.answer_callback_query(cbq_id)
                    return {"status": "ok", "message": "upi_bad_cb"}
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                if session.get("state") != "awaiting_upi_account_pick":
                    await self.send_message(
                        chat_id,
                        "No UPI link in progress. Tap “Link UPI App” from the setup menu or “Add bank / Link UPI” on the dashboard.",
                    )
                    await self.answer_callback_query(cbq_id)
                    return {"status": "ok", "message": "upi_wrong_state"}
                session_payload["pending_upi_account_code"] = acct_code
                self._save_session(telegram_user_id, "awaiting_upi_profile_name", session_payload)
                await self.send_message(
                    chat_id,
                    f"Step 3/4: Short label for this link (e.g. PhonePe {acct_code}).\n"
                    f"Reply with plain text. Or /cancel.",
                )
            elif data.startswith("setup:done"):
                onboarding = self.ledger_service.get_onboarding_status(user_ref)
                if not onboarding["ready"]:
                    await self.send_message(
                        chat_id,
                        "Add at least one account (last 4 digits) first. You can add more banks later from “Add bank / Link UPI”.",
                        keyboard=self._onboarding_keyboard(),
                    )
                else:
                    await self.send_message(
                        chat_id,
                        "Setup complete. You can add more banks or link UPI anytime from “Add bank / Link UPI”.\n"
                        "Fold Dashboard:",
                        keyboard=self._start_keyboard(),
                    )
            elif data.startswith("dash:add_expense"):
                rows: list[list[dict]] = [
                    [{"text": "Cash", "callback_data": "acct:funding:cash_wallet:asset"}],
                    [{"text": "UPI", "callback_data": "acct:funding:upi_wallet:asset"}],
                    [{"text": "Card", "callback_data": "acct:funding:card_liability:liability"}],
                ]
                for a in self.ledger_service.list_setup_funding_accounts(user_ref):
                    cb = f"acct:funding:{a['code']}:{a['account_type']}"
                    if len(cb.encode("utf-8")) <= 64:
                        label = str(a["code"])[:36]
                        rows.append([{"text": f"· {label}", "callback_data": cb}])
                await self.send_message(
                    chat_id,
                    "Pick funding: generic buckets (top) or your linked bank/card (below).",
                    keyboard=rows,
                )
            elif data.startswith("dash:add_income"):
                await self.send_message(chat_id, "Use /income <amount> <description> to record income.")
            elif data.startswith("dash:add_investment"):
                await self.send_message(chat_id, "Use /investment <amount> <description> to record investment.")
            elif data.startswith("dash:transfer"):
                await self.send_message(chat_id, "Use /transfer <amount> <from_account_code> <to_account_code>.")
            elif data.startswith("dash:balance"):
                balances = self.ledger_service.get_cash_snapshot(user_ref=user_ref)
                if not balances:
                    await self.send_message(chat_id, "No accounts yet. Add one via /start.")
                else:
                    lines = ["Balance Snapshot:"]
                    for row in balances:
                        lines.append(f"  {row['code']}: ₹{row['balance_minor'] / 100:,.2f}")
                    await self.send_message(chat_id, "\n".join(lines))
            elif data.startswith("report:weekly"):
                bundle = self.ledger_service.get_enriched_period_report(user_ref, "weekly")
                await self.send_message(chat_id, self._message_text_enriched_report(bundle))
            elif data.startswith("report:monthly"):
                bundle = self.ledger_service.get_enriched_period_report(user_ref, "monthly")
                await self.send_message(chat_id, self._message_text_enriched_report(bundle))
            elif data.startswith("acct:list"):
                real = self.ledger_service.list_setup_funding_accounts(user_ref)
                primary = self.ledger_service.describe_primary_funding(user_ref)
                if not real:
                    await self.send_message(chat_id, "No accounts found. Use /start to add one.")
                else:
                    lines = ["Accounts:"]
                    for a in real:
                        lines.append(f"- {a['code']} ({a['account_type']})")
                    if primary:
                        lines.append("")
                        lines.append(f"★ Default for spending/income: {primary}")
                    elif len(real) > 1:
                        lines.append("")
                        lines.append(
                            "★ No default — set one below so voice/receipt expenses know which account to use."
                        )
                    lines.append("")
                    lines.append("Add another bank: main menu → Add bank / Link UPI.")
                    kb: list[list[dict]] = []
                    for a in real:
                        cb = f"primset:{a['code']}:{a['account_type']}"
                        if len(cb.encode("utf-8")) <= 64:
                            kb.append([{"text": f"★ Default: {a['code']}", "callback_data": cb}])
                    await self.send_message(chat_id, "\n".join(lines), keyboard=kb or None)
            elif data.startswith("primset:"):
                parts = data.split(":", 2)
                if len(parts) < 3:
                    await self.send_message(chat_id, "Invalid button. Open Accounts and try again.")
                else:
                    _, acode, atyp = parts
                    try:
                        self.ledger_service.set_primary_funding_account(
                            user_ref, acode, atyp  # type: ignore[arg-type]
                        )
                        await self.send_message(
                            chat_id,
                            f"Default spending/income account set to {acode} ({atyp}).",
                            keyboard=self._start_keyboard(),
                        )
                    except ValueError as exc:
                        await self.send_message(chat_id, str(exc))
            elif data.startswith("dash:opening_balance"):
                kb = self._opening_balance_asset_keyboard(user_ref)
                if not kb:
                    await self.send_message(
                        chat_id,
                        "No asset accounts yet. Add a bank or digital account first.",
                        keyboard=self._onboarding_keyboard(),
                    )
                else:
                    await self.send_message(
                        chat_id,
                        "Opening balance — tap an account, then reply with the INR amount (or 0 / skip).",
                        keyboard=kb,
                    )
                await self.answer_callback_query(cbq_id)
                return {"status": "ok", "message": "opening_menu"}
            elif data.startswith("openbal:"):
                code = data[len("openbal:") :].strip()
                if not code:
                    await self.send_message(chat_id, "Invalid choice. Try Opening balance again.")
                    await self.answer_callback_query(cbq_id)
                    return {"status": "ok", "message": "opening_bad_cb"}
                session = self._get_session(telegram_user_id)
                session_payload = dict(session.get("payload_json") or {})
                session_payload["pending_opening_account_code"] = code
                session_payload["pending_opening_from_wizard"] = False
                session_payload.pop("pending_opening_account_label", None)
                session_payload.pop("pending_opening_last4", None)
                self._save_session(
                    telegram_user_id=telegram_user_id,
                    state="awaiting_account_opening_balance",
                    payload=session_payload,
                )
                await self.send_message(
                    chat_id,
                    f"Account {code}.\nReply with opening balance in INR (number only), or 0 / skip.",
                )
                await self.answer_callback_query(cbq_id)
                return {"status": "ok", "message": "opening_chosen"}
            elif data.startswith("acct:funding:"):
                _, _, code, acc_type = data.split(":", 3)
                session = self._get_session(telegram_user_id)
                existing_payload = dict(session.get("payload_json") or {})
                existing_payload["funding_account_code"] = code
                existing_payload["funding_account_type"] = acc_type
                existing_payload.pop("pending_expense_partial", None)
                self._save_session(
                    telegram_user_id=telegram_user_id,
                    state="awaiting_expense_entry",
                    payload=existing_payload,
                )
                await self.send_message(
                    chat_id,
                    f"Funding: {code}.\n"
                    "Send your expense as plain text (e.g. \"Swiggy 450\"), a voice note, or a receipt photo. "
                    "No slash command needed. /cancel to stop.",
                    keyboard=self._start_keyboard(),
                )
            else:
                await self.send_message(chat_id, "Unknown action. Use /start.")

            await self.answer_callback_query(cbq_id)
            return {"status": "ok", "message": "callback_handled"}

        return {"status": "ok", "message": "ignored"}
