from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from application.bot_engine.domain.telegram_delivery_bot import process_delivery_bot_update
from application.core_engine.domain.settings import get_telegram_bot_settings

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/telegram/{webhook_secret}")
async def telegram_delivery_webhook(
    webhook_secret: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    settings = get_telegram_bot_settings(db)
    db.commit()
    expected_secret = str(settings.get("webhook_secret") or "").strip()
    if not expected_secret or webhook_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")

    update = await request.json()
    result = process_delivery_bot_update(db=db, update=update)
    return {"ok": True, "result": result}
