from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Order, SystemAuditLog
from app.text_sanitizer import sanitize_text


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_offset_limit(
    *,
    offset: int = 0,
    limit: int | None = None,
    max_limit: int = 500,
) -> tuple[int, int | None]:
    safe_offset = max(0, int(offset))
    if limit is None:
        return safe_offset, None
    safe_limit = max(1, min(int(limit), max_limit))
    return safe_offset, safe_limit


def record_system_audit(
    db: Session,
    *,
    module: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
    user_id: int,
    description: str,
) -> None:
    clean_description = sanitize_text(description, fallback="حدث نظامي")
    db.add(
        SystemAuditLog(
            module=module,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=clean_description[:255],
            performed_by=user_id,
        )
    )


def get_order_or_404(db: Session, order_id: int) -> Order:
    order = (
        db.execute(
            select(Order).where(Order.id == order_id).options(joinedload(Order.items))
        )
        .unique()
        .scalar_one_or_none()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطلب غير موجود.")
    return order
