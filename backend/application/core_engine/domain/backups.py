from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database import engine, resolve_sqlite_database_path
from application.core_engine.domain.helpers import normalize_offset_limit, record_system_audit

BACKUP_DIR = Path(__file__).resolve().parents[4] / "app" / "backups"


def _backup_file_row(path: Path) -> dict[str, object]:
    stats = path.stat()
    return {
        "filename": path.name,
        "size_bytes": int(stats.st_size),
        "created_at": datetime.fromtimestamp(stats.st_mtime, UTC),
    }


def _require_sqlite_database_path(*, action_label: str) -> Path:
    database_path = resolve_sqlite_database_path(engine)
    if database_path is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"النسخ {action_label} متاح فقط عند العمل على SQLite المحلي.",
        )
    return database_path


def list_system_backups(
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, object]]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rows = [item for item in BACKUP_DIR.glob("*.sqlite3") if item.is_file()]
    rows.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    safe_offset, safe_limit = normalize_offset_limit(offset=offset, limit=limit, max_limit=200)
    if safe_limit is None:
        selected = rows[safe_offset:]
    else:
        selected = rows[safe_offset : safe_offset + safe_limit]
    return [_backup_file_row(item) for item in selected]


def create_system_backup(db: Session, *, actor_id: int) -> dict[str, object]:
    database_path = _require_sqlite_database_path(action_label="الاحتياطي")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"restaurant_backup_{timestamp}.sqlite3"
    shutil.copy2(database_path, backup_file)
    record_system_audit(
        db,
        module="settings",
        action="create_backup",
        entity_type="system_backup",
        entity_id=None,
        user_id=actor_id,
        description=f"إنشاء نسخة احتياطية للنظام باسم {backup_file.name}",
    )
    return _backup_file_row(backup_file)


def restore_system_backup(
    db: Session,
    *,
    filename: str,
    confirm_phrase: str,
    actor_id: int,
) -> dict[str, object]:
    database_path = _require_sqlite_database_path(action_label="الاستعادة")
    if confirm_phrase != "RESTORE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="عبارة تأكيد الاستعادة غير صحيحة.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_file = (BACKUP_DIR / filename).resolve()
    if not backup_file.exists() or not backup_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ملف النسخة الاحتياطية غير موجود.")
    if backup_file.suffix.lower() != ".sqlite3":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="نوع ملف النسخة الاحتياطية غير مدعوم.")
    if BACKUP_DIR.resolve() not in backup_file.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="مسار ملف النسخة الاحتياطية غير صالح.")

    engine.dispose()
    shutil.copy2(backup_file, database_path)
    record_system_audit(
        db,
        module="settings",
        action="restore_backup",
        entity_type="system_backup",
        entity_id=None,
        user_id=actor_id,
        description=f"استعادة نسخة احتياطية للنظام من الملف {backup_file.name}",
    )
    return _backup_file_row(backup_file)
