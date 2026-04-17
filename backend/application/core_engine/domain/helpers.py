from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import SystemAuditLog
from app.text_sanitizer import sanitize_text


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


def parse_non_negative_float(value: str, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed < 0:
        return default
    return parsed


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return default


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


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


def require_setting_value(value: str | None) -> str:
    normalized = normalize_optional_text(value)
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="قيمة الإعداد مطلوبة.")
    return normalized
