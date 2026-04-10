from fastapi import Header, HTTPException

from api.config import get_settings


async def verify_telegram_secret(x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    settings = get_settings()
    expected = settings.telegram_webhook_secret
    if not expected:
        return
    if x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=401, detail="Invalid telegram webhook secret")
