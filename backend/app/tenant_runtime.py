from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import MasterTenant

from .database import BASE_DIR, SessionLocal, create_app_engine
from .security import decode_access_token

TENANTS_DIR = BASE_DIR / "tenants"
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


def _tenant_database_path(database_name: str) -> Path:
    normalized = str(database_name or "").strip()
    if not normalized:
        raise ValueError("database_name is required")
    return (TENANTS_DIR / f"{normalized}.sqlite3").resolve()


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

    factory = _TENANT_SESSIONMAKERS.get(normalized)
    if factory is not None:
        return factory

    database_path = _tenant_database_path(normalized)
    if not database_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="قاعدة النسخة غير متاحة حاليًا.",
        )

    engine = create_app_engine(f"sqlite:///{database_path.as_posix()}")
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _TENANT_SESSIONMAKERS[normalized] = factory
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
    factory = _TENANT_SESSIONMAKERS.pop(normalized, None)
    if factory is None:
        return
    bind = factory.kw.get("bind")
    if bind is not None:
        bind.dispose()


def infer_tenant_database_name_from_session(db: Session) -> str | None:
    bind = db.get_bind()
    database = getattr(getattr(bind, "url", None), "database", None)
    if not database:
        return None

    path = Path(str(database))
    try:
        resolved = path.resolve()
    except OSError:
        return None

    try:
        if resolved.parent != TENANTS_DIR.resolve():
            return None
    except OSError:
        return None

    if resolved.suffix != ".sqlite3":
        return None
    return resolved.stem


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
