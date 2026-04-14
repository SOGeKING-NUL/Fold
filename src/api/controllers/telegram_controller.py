import logging

from fastapi import APIRouter, Depends, Request

from api.middleware.telegram_security import verify_telegram_secret
from api.services.telegram_service import TelegramService

router = APIRouter(prefix="/api/v1/webhooks", tags=["telegram"])
telegram_service = TelegramService()
_log = logging.getLogger(__name__)


@router.post("/telegram", dependencies=[Depends(verify_telegram_secret)])
async def telegram_webhook(request: Request):
    payload = await request.json()
    try:
        result = await telegram_service.handle_update(payload)
    except Exception:
        _log.exception("telegram webhook handler failed (returning 200 to stop retries)")
        return {"status": "error", "detail": "internal_error"}
    return {"status": "ok", "result": result}
