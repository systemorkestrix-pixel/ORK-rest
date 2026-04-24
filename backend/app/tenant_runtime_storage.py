from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .database import BASE_DIR, DATABASE_URL, SessionLocal, create_app_engine
from .master_tenant_runtime_contract import (
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
)

TENANT_RUNTIME_SQLITE_BACKEND = MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE
TENANT_RUNTIME_POSTGRES_BACKEND = MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA
TENANT_RUNTIME_SQLITE_DIR = BASE_DIR / "tenants"


@dataclass(frozen=True)
class TenantRuntimeStorageTarget:
    database_name: str
    backend: str
    database_path: Path | None
    schema_name: str | None
    engine_url: str
    cache_key: str


def normalize_tenant_database_name(database_name: str) -> str:
    normalized = str(database_name or "").strip()
    if not normalized:
        raise ValueError("database_name is required")
    return normalized


def resolve_tenant_runtime_storage_backend(*, database_name: str) -> str:
    normalized = normalize_tenant_database_name(database_name)
    backend, _schema_name = _resolve_master_tenant_runtime_binding(normalized)
    return backend


def resolve_tenant_runtime_sqlite_path(database_name: str) -> Path:
    normalized = normalize_tenant_database_name(database_name)
    return (TENANT_RUNTIME_SQLITE_DIR / f"{normalized}.sqlite3").resolve()


def build_tenant_runtime_engine_url(*, database_name: str, database_path: Path | None = None) -> str:
    path = database_path or resolve_tenant_runtime_sqlite_path(database_name)
    return f"sqlite:///{path.as_posix()}"


def build_tenant_runtime_target(
    *,
    database_name: str,
    backend: str,
    schema_name: str | None = None,
) -> TenantRuntimeStorageTarget:
    normalized = normalize_tenant_database_name(database_name)
    normalized_backend = str(backend or "").strip() or TENANT_RUNTIME_SQLITE_BACKEND
    if normalized_backend == TENANT_RUNTIME_POSTGRES_BACKEND:
        normalized_schema_name = str(schema_name or "").strip()
        if not normalized_schema_name:
            raise RuntimeError(f"Tenant {normalized!r} is configured for postgres_schema without runtime_schema_name.")
        return TenantRuntimeStorageTarget(
            database_name=normalized,
            backend=normalized_backend,
            database_path=None,
            schema_name=normalized_schema_name,
            engine_url=DATABASE_URL,
            cache_key=f"{normalized_backend}:{normalized_schema_name}",
        )

    database_path = resolve_tenant_runtime_sqlite_path(normalized)
    return TenantRuntimeStorageTarget(
        database_name=normalized,
        backend=normalized_backend,
        database_path=database_path,
        schema_name=None,
        engine_url=build_tenant_runtime_engine_url(database_name=normalized, database_path=database_path),
        cache_key=f"{normalized_backend}:{normalized}",
    )


def resolve_tenant_runtime_target(database_name: str) -> TenantRuntimeStorageTarget:
    normalized = normalize_tenant_database_name(database_name)
    backend, schema_name = _resolve_master_tenant_runtime_binding(normalized)
    return build_tenant_runtime_target(database_name=normalized, backend=backend, schema_name=schema_name)


def ensure_tenant_runtime_storage_root() -> Path:
    TENANT_RUNTIME_SQLITE_DIR.mkdir(parents=True, exist_ok=True)
    return TENANT_RUNTIME_SQLITE_DIR


def tenant_runtime_target_exists(target: TenantRuntimeStorageTarget) -> bool:
    if target.backend == TENANT_RUNTIME_POSTGRES_BACKEND:
        if not target.schema_name:
            return False
        engine = create_tenant_runtime_engine(target)
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema_name)"),
                    {"schema_name": target.schema_name},
                ).scalar_one()
            return bool(row)
        finally:
            engine.dispose()

    return bool(target.database_path and target.database_path.exists())


def tenant_runtime_exists(database_name: str) -> bool:
    return tenant_runtime_target_exists(resolve_tenant_runtime_target(database_name))


def create_tenant_runtime_engine(database_name_or_target: str | TenantRuntimeStorageTarget) -> Engine:
    target = (
        database_name_or_target
        if isinstance(database_name_or_target, TenantRuntimeStorageTarget)
        else resolve_tenant_runtime_target(database_name_or_target)
    )
    if target.backend == TENANT_RUNTIME_POSTGRES_BACKEND:
        if not target.schema_name:
            raise RuntimeError(f"Tenant {target.database_name!r} is configured for postgres_schema without schema_name.")
        engine = create_app_engine(target.engine_url)
        _attach_postgres_search_path(engine, schema_name=target.schema_name)
        return engine
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


def _resolve_master_tenant_runtime_binding(database_name: str) -> tuple[str, str | None]:
    normalized = normalize_tenant_database_name(database_name)
    try:
        from .models import MasterTenant
    except Exception:  # noqa: BLE001
        return TENANT_RUNTIME_SQLITE_BACKEND, None

    master_db = SessionLocal()
    try:
        tenant = master_db.execute(
            select(
                MasterTenant.runtime_storage_backend,
                MasterTenant.runtime_schema_name,
            ).where(MasterTenant.database_name == normalized)
        ).first()
    except SQLAlchemyError:
        return TENANT_RUNTIME_SQLITE_BACKEND, None
    finally:
        master_db.close()

    if tenant is None:
        return TENANT_RUNTIME_SQLITE_BACKEND, None
    backend = str(tenant[0] or "").strip() or TENANT_RUNTIME_SQLITE_BACKEND
    schema_name = str(tenant[1] or "").strip() or None
    return backend, schema_name


def _attach_postgres_search_path(engine: Engine, *, schema_name: str) -> None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("PostgreSQL tenant runtime backend requires a PostgreSQL engine.")
    if getattr(engine, "_tenant_runtime_search_path_attached", None) == schema_name:
        return

    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f'SET search_path TO "{schema_name}", public')
        finally:
            cursor.close()

    setattr(engine, "_tenant_runtime_search_path_attached", schema_name)
