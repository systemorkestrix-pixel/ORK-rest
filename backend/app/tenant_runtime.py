from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import MasterTenant

from .database import SessionLocal
from .security import decode_access_token
from .tenant_runtime_storage import (
    TENANT_RUNTIME_SQLITE_DIR,
    create_tenant_runtime_engine,
    infer_tenant_database_name_from_runtime_database,
    resolve_tenant_runtime_sqlite_path,
    resolve_tenant_runtime_target,
    tenant_runtime_target_exists,
)

TENANTS_DIR = TENANT_RUNTIME_SQLITE_DIR
_TENANT_SESSIONMAKERS: dict[str, sessionmaker] = {}


def is_master_request_path(path: str) -> bool:
    normalized = (path or "").strip()
    return normalized.startswith("/api/master") or normalized.startswith("/api/master-auth")


def is_public_request_path(path: str) -> bool:
    normalized = (path or "").strip()
    return normalized.startswith("/api/public") or normalized.startswith("/public")


def is_public_registry_path(path: str) -> bool:
    normalized = (path or "").strip()
    return normalized in {"/api/public/tenant-entry", "/public/tenant-entry"}


def _tenant_database_path(database_name: str):
    return resolve_tenant_runtime_sqlite_path(database_name)


def _resolve_master_tenant_by_database_name(master_db: Session, database_name: str) -> MasterTenant | None:
    normalized = str(database_name or "").strip()
    if not normalized:
        return None
    return master_db.execute(select(MasterTenant).where(MasterTenant.database_name == normalized)).scalar_one_or_none()


def resolve_tenant_record_for_database_name(*, database_name: str) -> MasterTenant | None:
    normalized = str(database_name or "").strip()
    if not normalized:
        return None
    master_db = SessionLocal()
    try:
        tenant = _resolve_master_tenant_by_database_name(master_db, normalized)
        if tenant is None:
            return None
        master_db.expunge(tenant)
        return tenant
    finally:
        master_db.close()


def _assert_tenant_runtime_available(tenant: MasterTenant | None) -> str | None:
    if tenant is None:
        return None
    if tenant.environment_state == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذه النسخة موقوفة حاليًا.")
    return tenant.database_name


def get_tenant_sessionmaker(database_name: str) -> sessionmaker:
    normalized = str(database_name or "").strip()
    if not normalized:
        raise ValueError("database_name is required")

    target = resolve_tenant_runtime_target(normalized)
    factory = _TENANT_SESSIONMAKERS.get(target.cache_key)
    if factory is not None:
        return factory

    if not tenant_runtime_target_exists(target):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="قاعدة النسخة غير متاحة حاليًا.",
        )

    engine = create_tenant_runtime_engine(target)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _TENANT_SESSIONMAKERS[target.cache_key] = factory
    return factory


def create_runtime_session(database_name: str | None) -> Session:
    normalized = str(database_name or "").strip()
    if not normalized:
        return SessionLocal()
    return get_tenant_sessionmaker(normalized)()


def dispose_tenant_runtime(database_name: str | None) -> None:
    normalized = str(database_name or "").strip()
    if not normalized:
        return
    target = resolve_tenant_runtime_target(normalized)
    factory = _TENANT_SESSIONMAKERS.pop(target.cache_key, None)
    if factory is None:
        return
    bind = factory.kw.get("bind")
    if bind is not None:
        bind.dispose()


def infer_tenant_database_name_from_session(db: Session) -> str | None:
    bind = db.get_bind()
    database = getattr(getattr(bind, "url", None), "database", None)
    return infer_tenant_database_name_from_runtime_database(database)


def infer_tenant_record_from_session(db: Session) -> MasterTenant | None:
    database_name = infer_tenant_database_name_from_session(db)
    if not database_name:
        return None
    return resolve_tenant_record_for_database_name(database_name=database_name)


def infer_tenant_code_from_session(db: Session) -> str | None:
    tenant = infer_tenant_record_from_session(db)
    if tenant is None:
        return None
    return str(tenant.code or "").strip() or None


def resolve_tenant_database_name_for_login(*, username: str) -> str | None:
    normalized = str(username or "").strip().lower()
    if not normalized:
        return None

    master_db = SessionLocal()
    try:
        tenant = master_db.execute(select(MasterTenant).where(MasterTenant.manager_username == normalized)).scalar_one_or_none()
        return _assert_tenant_runtime_available(tenant)
    finally:
        master_db.close()


def resolve_tenant_database_name_for_code(*, tenant_code: str) -> str | None:
    normalized = str(tenant_code or "").strip().lower()
    if not normalized:
        return None

    master_db = SessionLocal()
    try:
        tenant = master_db.execute(select(MasterTenant).where(MasterTenant.code == normalized)).scalar_one_or_none()
        return _assert_tenant_runtime_available(tenant)
    finally:
        master_db.close()


def resolve_tenant_database_name_from_request(
    *,
    path: str,
    authorization: str | None,
    access_token_cookie: str | None,
    tenant_database_cookie: str | None,
    tenant_code_header: str | None,
) -> str | None:
    if is_master_request_path(path):
        return None

    if is_public_request_path(path):
        if is_public_registry_path(path):
            return None
        if not tenant_code_header:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="هذه الواجهة مرتبطة بمطعم محدد. استخدم رابط المطعم المباشر.",
            )
        return resolve_tenant_database_name_for_code(tenant_code=tenant_code_header)

    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif access_token_cookie:
        token = access_token_cookie.strip()

    if token:
        try:
            payload = decode_access_token(token)
            database_name = str(payload.get("tenant_database") or "").strip()
            if database_name:
                master_db = SessionLocal()
                try:
                    return _assert_tenant_runtime_available(
                        _resolve_master_tenant_by_database_name(master_db, database_name)
                    )
                finally:
                    master_db.close()
        except Exception:
            pass

    if tenant_database_cookie:
        database_name = str(tenant_database_cookie).strip()
        if database_name:
            master_db = SessionLocal()
            try:
                return _assert_tenant_runtime_available(
                    _resolve_master_tenant_by_database_name(master_db, database_name)
                )
            finally:
                master_db.close()

    if tenant_code_header:
        return resolve_tenant_database_name_for_code(tenant_code=tenant_code_header)

    return None
