from fastapi import APIRouter, Depends, Request

from api.middleware.telegram_security import verify_telegram_secret
from api.services.telegram_service import TelegramService

router = APIRouter(prefix="/api/v1/webhooks", tags=["telegram"])
telegram_service = TelegramService()


@router.post("/telegram", dependencies=[Depends(verify_telegram_secret)])
async def telegram_webhook(request: Request):
    payload = await request.json()
    result = await telegram_service.handle_update(payload)
    return {"status": "ok", "result": result}
