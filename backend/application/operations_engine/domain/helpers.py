from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Order, OrderTransitionLog, SystemAuditLog
from app.text_sanitizer import sanitize_text


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def resolve_standard_reason(
    *,
    reason_code: str | None,
    reasons_map: dict[str, str],
    error_detail: str,
) -> str:
    normalized_code = normalize_optional_text(reason_code)
    if not normalized_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)
    label = reasons_map.get(normalized_code)
    if label is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)
    return label


def compose_reason_text(reason_label: str, reason_note: str | None) -> str:
    normalized_note = normalize_optional_text(reason_note)
    if not normalized_note:
        return reason_label
    return f"{reason_label} - {normalized_note}"


def record_transition(
    db: Session,
    *,
    order_id: int,
    from_status: str,
    to_status: str,
    user_id: int,
) -> None:
    db.add(
        OrderTransitionLog(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            performed_by=user_id,
        )
    )


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
