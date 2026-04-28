"""
Ollama OCR Text Structurer
==========================
Takes raw OCR text and returns structured transaction fields via
locally hosted Ollama model.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

_log = logging.getLogger(__name__)


class OllamaStructurer:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:3b-instruct",
        timeout_seconds: int = 25,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def structure_from_ocr(
        self,
        *,
        raw_text: str,
        text_source: str,
        hints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _log.info(
            "[Ollama] structuring start source=%s text_len=%d hints_keys=%s",
            text_source,
            len(raw_text or ""),
            sorted((hints or {}).keys()),
        )
        prompt = self._build_prompt(raw_text=raw_text, text_source=text_source, hints=hints or {})
        url = f"{self.base_url}/api/chat"
        schema = {
            "type": "object",
            "properties": {
                "amount": {"type": ["number", "null"]},
                "payment_method": {"type": ["string", "null"]},
                "payment_provider": {"type": ["string", "null"]},
                "bank_account": {"type": ["string", "null"]},
                "cash_flow": {"type": ["string", "null"]},
                "description": {"type": "string"},
                "card_network": {"type": ["string", "null"]},
                "card_last4": {"type": ["string", "null"]},
                "transaction_ref": {"type": ["string", "null"]},
                "occurred_at": {"type": ["string", "null"]},
            },
            "required": [
                "amount",
                "payment_method",
                "payment_provider",
                "bank_account",
                "cash_flow",
                "description",
                "card_network",
                "card_last4",
                "transaction_ref",
                "occurred_at",
            ],
        }
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
        }
        resp = requests.post(url, json=body, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        raw_out = data.get("message", {}).get("content", "")
        _log.debug("[Ollama] raw response preview=%s", (raw_out or "")[:300].replace("\n", " "))
        parsed = self._parse_json(raw_out)
        normalized = self._normalize(parsed)
        _log.info(
            "[Ollama] structuring done amount=%s pm=%s provider=%s bank=%s cash_flow=%s",
            normalized.get("amount"),
            normalized.get("payment_method"),
            normalized.get("payment_provider"),
            normalized.get("bank_account"),
            normalized.get("cash_flow"),
        )
        return normalized

    @staticmethod
    def _build_prompt(*, raw_text: str, text_source: str, hints: dict[str, Any]) -> str:
        hint_lines = "\n".join([f"- {k}: {v}" for k, v in hints.items() if v is not None]) or "- none"
        return (
            "You are a financial extraction parser for India-focused OCR text.\n"
            "Return strict JSON using the provided schema.\n\n"
            f"text_source: {text_source}\n"
            "Allowed payment_method: upi, card, cash, null\n"
            "Allowed cash_flow: expense, income, null\n"
            "Rules:\n"
            "1) Use ₹, Rs, Pay, INR, R-prefixed amounts (e.g. R500.00 => 500.00).\n"
            "2) Never use dates/times/IDs as amount.\n"
            "3) If source is upi_ocr, prioritize paid/received amount and app/provider clues.\n"
            "4) If source is receipt_ocr, prioritize final total/payable amount.\n"
            "5) If card evidence exists (visa/mastercard/amex/rupay/debit/credit), set payment_method=card and card_network.\n\n"
            "Hints from OCR pipeline:\n"
            f"{hint_lines}\n\n"
            "Raw OCR text:\n"
            f"{raw_text[:6000]}"
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        t = (raw or "").strip()
        if not t:
            _log.warning("[Ollama] empty response body")
            return {}
        if t.startswith("```"):
            t = re.sub(r"^```(?:json)?\s*", "", t)
            t = re.sub(r"\s*```$", "", t)
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", t, flags=re.DOTALL)
            if not m:
                _log.warning("[Ollama] no JSON object found in response")
                return {}
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                _log.warning("[Ollama] JSON parse failed even after object extraction")
                return {}

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {
            "amount": None,
            "payment_method": None,
            "payment_provider": None,
            "bank_account": None,
            "cash_flow": None,
            "description": "",
            "card_network": None,
            "card_last4": None,
            "transaction_ref": None,
            "occurred_at": None,
        }
        out.update({k: v for k, v in data.items() if k in out})

        amt = out.get("amount")
        try:
            out["amount"] = float(amt) if amt is not None else None
            if out["amount"] is not None and out["amount"] <= 0:
                out["amount"] = None
        except (TypeError, ValueError):
            out["amount"] = None

        pm = str(out.get("payment_method") or "").lower().strip()
        out["payment_method"] = pm if pm in {"upi", "card", "cash"} else None
        cf = str(out.get("cash_flow") or "").lower().strip()
        out["cash_flow"] = cf if cf in {"expense", "income"} else None

        for k in ("payment_provider", "bank_account", "card_network", "transaction_ref", "occurred_at"):
            v = out.get(k)
            if v is None:
                continue
            s = str(v).strip()
            out[k] = s if s and s.lower() not in {"none", "null", "unknown", "n/a"} else None

        d = out.get("description")
        out["description"] = (str(d).strip() if d is not None else "")[:500]

        last4 = out.get("card_last4")
        if last4 is not None:
            digits = re.sub(r"\D", "", str(last4))
            out["card_last4"] = digits[-4:] if len(digits) >= 4 else None
        else:
            out["card_last4"] = None

        return out

