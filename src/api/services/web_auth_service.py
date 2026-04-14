"""
Web Dashboard Authentication
=============================
Issues time-limited, HMAC-signed magic-link tokens from the Telegram bot.
The Next.js frontend exchanges a token for a secure session cookie.
Tokens are single-use and expire after 5 minutes.
"""

import hashlib
import hmac
import json
import time
import os
import secrets
from typing import Optional

_SIGNING_SECRET: str | None = None
_USED_TOKENS: dict[str, float] = {}
_SESSIONS: dict[str, dict] = {}

TOKEN_TTL_SECONDS = 300  # 5 minutes
SESSION_TTL_SECONDS = 86400 * 7  # 7 days


def _get_signing_secret() -> str:
    global _SIGNING_SECRET
    if _SIGNING_SECRET is None:
        _SIGNING_SECRET = os.getenv("FOLD_WEB_SIGNING_SECRET", "")
        if not _SIGNING_SECRET:
            _SIGNING_SECRET = secrets.token_hex(32)
    return _SIGNING_SECRET


def _sign(payload: str) -> str:
    return hmac.new(
        _get_signing_secret().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def _cleanup_expired() -> None:
    now = time.time()
    expired_tokens = [k for k, v in _USED_TOKENS.items() if now - v > TOKEN_TTL_SECONDS * 2]
    for k in expired_tokens:
        del _USED_TOKENS[k]
    expired_sessions = [k for k, v in _SESSIONS.items() if now > v.get("expires_at", 0)]
    for k in expired_sessions:
        del _SESSIONS[k]


def issue_magic_token(telegram_user_id: int) -> str:
    """Create a signed, single-use token the bot sends as a URL parameter."""
    _cleanup_expired()
    payload = json.dumps(
        {"tg": telegram_user_id, "ts": int(time.time()), "nonce": secrets.token_hex(8)},
        separators=(",", ":"),
    )
    sig = _sign(payload)
    import base64
    token = base64.urlsafe_b64encode(f"{payload}.{sig}".encode()).decode()
    return token


def exchange_token(token: str) -> Optional[dict]:
    """
    Validate and consume a magic-link token.
    Returns {"user_ref": "telegram:<id>", "session_id": "..."} on success, None on failure.
    """
    _cleanup_expired()
    import base64
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
    except Exception:
        return None

    parts = decoded.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload_str, sig = parts

    expected_sig = _sign(payload_str)
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        data = json.loads(payload_str)
    except Exception:
        return None

    ts = data.get("ts", 0)
    now = time.time()
    if now - ts > TOKEN_TTL_SECONDS:
        return None

    token_id = f"{data.get('tg')}:{data.get('nonce')}"
    if token_id in _USED_TOKENS:
        return None
    _USED_TOKENS[token_id] = now

    telegram_user_id = data["tg"]
    user_ref = f"telegram:{telegram_user_id}"

    session_id = secrets.token_urlsafe(32)
    _SESSIONS[session_id] = {
        "user_ref": user_ref,
        "telegram_user_id": telegram_user_id,
        "created_at": now,
        "expires_at": now + SESSION_TTL_SECONDS,
    }

    return {"user_ref": user_ref, "session_id": session_id, "telegram_user_id": telegram_user_id}


def validate_session(session_id: str) -> Optional[dict]:
    """Return session data if the session_id is valid and not expired."""
    _cleanup_expired()
    session = _SESSIONS.get(session_id)
    if session is None:
        return None
    if time.time() > session.get("expires_at", 0):
        del _SESSIONS[session_id]
        return None
    return session


def destroy_session(session_id: str) -> bool:
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
        return True
    return False
