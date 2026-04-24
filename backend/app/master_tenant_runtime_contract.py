from __future__ import annotations

import hashlib
import re

MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE = "sqlite_file"
MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA = "postgres_schema"

MASTER_TENANT_RUNTIME_MIGRATION_STATE_NOT_STARTED = "not_started"
MASTER_TENANT_RUNTIME_MIGRATION_STATE_EXPORTING = "exporting"
MASTER_TENANT_RUNTIME_MIGRATION_STATE_IMPORTED = "imported"
MASTER_TENANT_RUNTIME_MIGRATION_STATE_VALIDATED = "validated"
MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER = "cutover"
MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK = "rollback"

MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC = "local_static"
MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE = "supabase_storage"

_SCHEMA_INVALID_CHARS = re.compile(r"[^a-z0-9_]+")


def build_master_tenant_runtime_schema_name(database_name: str) -> str:
    normalized = str(database_name or "").strip().lower()
    if not normalized:
        raise ValueError("database_name is required")

    normalized = _SCHEMA_INVALID_CHARS.sub("_", normalized).strip("_")
    if not normalized:
        raise ValueError("database_name must produce a non-empty schema name")
    if normalized[0].isdigit():
        normalized = f"tenant_{normalized}"
    if not normalized.startswith("tenant_"):
        normalized = f"tenant_{normalized}"

    if len(normalized) <= 63:
        return normalized

    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    prefix = normalized[:54].rstrip("_")
    if not prefix:
        prefix = "tenant"
    return f"{prefix}_{digest}"
