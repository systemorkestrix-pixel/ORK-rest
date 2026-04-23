from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine

from .database import BASE_DIR, create_app_engine

TENANT_RUNTIME_SQLITE_BACKEND = "sqlite_file"
TENANT_RUNTIME_SQLITE_DIR = BASE_DIR / "tenants"


@dataclass(frozen=True)
class TenantRuntimeStorageTarget:
    database_name: str
    backend: str
    database_path: Path
    engine_url: str
    cache_key: str


def normalize_tenant_database_name(database_name: str) -> str:
    normalized = str(database_name or "").strip()
    if not normalized:
        raise ValueError("database_name is required")
    return normalized


def resolve_tenant_runtime_storage_backend(*, database_name: str) -> str:
    normalize_tenant_database_name(database_name)
    return TENANT_RUNTIME_SQLITE_BACKEND


def resolve_tenant_runtime_sqlite_path(database_name: str) -> Path:
    normalized = normalize_tenant_database_name(database_name)
    return (TENANT_RUNTIME_SQLITE_DIR / f"{normalized}.sqlite3").resolve()


def build_tenant_runtime_engine_url(*, database_name: str, database_path: Path | None = None) -> str:
    path = database_path or resolve_tenant_runtime_sqlite_path(database_name)
    return f"sqlite:///{path.as_posix()}"


def resolve_tenant_runtime_target(database_name: str) -> TenantRuntimeStorageTarget:
    normalized = normalize_tenant_database_name(database_name)
    backend = resolve_tenant_runtime_storage_backend(database_name=normalized)
    database_path = resolve_tenant_runtime_sqlite_path(normalized)
    return TenantRuntimeStorageTarget(
        database_name=normalized,
        backend=backend,
        database_path=database_path,
        engine_url=build_tenant_runtime_engine_url(database_name=normalized, database_path=database_path),
        cache_key=f"{backend}:{normalized}",
    )


def ensure_tenant_runtime_storage_root() -> Path:
    TENANT_RUNTIME_SQLITE_DIR.mkdir(parents=True, exist_ok=True)
    return TENANT_RUNTIME_SQLITE_DIR


def tenant_runtime_target_exists(target: TenantRuntimeStorageTarget) -> bool:
    return target.database_path.exists()


def tenant_runtime_exists(database_name: str) -> bool:
    return tenant_runtime_target_exists(resolve_tenant_runtime_target(database_name))


def create_tenant_runtime_engine(database_name_or_target: str | TenantRuntimeStorageTarget) -> Engine:
    target = (
        database_name_or_target
        if isinstance(database_name_or_target, TenantRuntimeStorageTarget)
        else resolve_tenant_runtime_target(database_name_or_target)
    )
    return create_app_engine(target.engine_url)


def infer_tenant_database_name_from_runtime_database(database: str | None) -> str | None:
    if not database:
        return None

    path = Path(str(database))
    try:
        resolved = path.resolve()
    except OSError:
        return None

    try:
        if resolved.parent != TENANT_RUNTIME_SQLITE_DIR.resolve():
            return None
    except OSError:
        return None

    if resolved.suffix != ".sqlite3":
        return None
    return resolved.stem
