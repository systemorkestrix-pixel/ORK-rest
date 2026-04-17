from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import SystemAuditLog
from app.tx import transaction_scope


def record_event_audit(
    *,
    module: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
    actor_id: int | None,
    description: str,
    occurred_at: datetime | None,
    dedupe_minutes: int = 10,
) -> bool:
    if actor_id is None or entity_id is None:
        return False

    timestamp = occurred_at or datetime.now(UTC)
    window_start = timestamp - timedelta(minutes=max(1, int(dedupe_minutes)))

    db = SessionLocal()
    try:
        existing = db.execute(
            select(SystemAuditLog.id)
            .where(
                SystemAuditLog.module == module,
                SystemAuditLog.action == action,
                SystemAuditLog.entity_type == entity_type,
                SystemAuditLog.entity_id == entity_id,
                SystemAuditLog.performed_by == actor_id,
                SystemAuditLog.timestamp >= window_start,
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return False

        with transaction_scope(db):
            db.add(
                SystemAuditLog(
                    module=module,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    description=description,
                    performed_by=actor_id,
                    timestamp=timestamp,
                )
            )
        return True
    finally:
        db.close()
