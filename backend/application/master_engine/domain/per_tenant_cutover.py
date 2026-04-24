from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.master_tenant_runtime_contract import (
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER,
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK,
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_VALIDATED,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
)
from app.models import MasterTenant
from app.tenant_runtime import dispose_tenant_runtime


@dataclass(frozen=True)
class TenantCutoverResult:
    tenant_id: int
    tenant_code: str
    database_name: str
    runtime_storage_backend: str
    runtime_schema_name: str | None
    runtime_migration_state: str
    runtime_migrated_at: str | None


def cutover_tenant_runtime(
    db: Session,
    *,
    database_name: str,
    allow_revalidated_cutover: bool = False,
) -> TenantCutoverResult:
    tenant = _get_master_tenant(db, database_name=database_name)
    if tenant.runtime_storage_backend == MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA:
        if tenant.runtime_migration_state == MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER:
            return _serialize_cutover_result(tenant)
        raise RuntimeError(
            f"Tenant {tenant.database_name!r} already points to postgres_schema with state "
            f"{tenant.runtime_migration_state!r}."
        )
    if not str(tenant.runtime_schema_name or "").strip():
        raise RuntimeError(f"Tenant {tenant.database_name!r} cannot cut over without runtime_schema_name.")

    allowed_states = {MASTER_TENANT_RUNTIME_MIGRATION_STATE_VALIDATED}
    if allow_revalidated_cutover:
        allowed_states.add(MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK)
    if tenant.runtime_migration_state not in allowed_states:
        raise RuntimeError(
            f"Tenant {tenant.database_name!r} must be in validated state before cutover. "
            f"current={tenant.runtime_migration_state!r}"
        )

    dispose_tenant_runtime(tenant.database_name)
    tenant.runtime_storage_backend = MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA
    tenant.runtime_migration_state = MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER
    tenant.runtime_migrated_at = _utc_now()
    tenant.updated_at = _utc_now()
    db.flush()
    dispose_tenant_runtime(tenant.database_name)
    return _serialize_cutover_result(tenant)


def rollback_tenant_runtime_cutover(db: Session, *, database_name: str) -> TenantCutoverResult:
    tenant = _get_master_tenant(db, database_name=database_name)
    if tenant.runtime_storage_backend == MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE:
        if tenant.runtime_migration_state == MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK:
            return _serialize_cutover_result(tenant)
        raise RuntimeError(
            f"Tenant {tenant.database_name!r} already points to sqlite_file with state "
            f"{tenant.runtime_migration_state!r}."
        )

    dispose_tenant_runtime(tenant.database_name)
    tenant.runtime_storage_backend = MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE
    tenant.runtime_migration_state = MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK
    tenant.updated_at = _utc_now()
    db.flush()
    dispose_tenant_runtime(tenant.database_name)
    return _serialize_cutover_result(tenant)


def mark_tenant_runtime_validated(db: Session, *, database_name: str) -> TenantCutoverResult:
    tenant = _get_master_tenant(db, database_name=database_name)
    tenant.runtime_migration_state = MASTER_TENANT_RUNTIME_MIGRATION_STATE_VALIDATED
    tenant.updated_at = _utc_now()
    db.flush()
    return _serialize_cutover_result(tenant)


def _get_master_tenant(db: Session, *, database_name: str) -> MasterTenant:
    normalized = str(database_name or "").strip()
    if not normalized:
        raise ValueError("database_name is required")
    tenant = db.execute(select(MasterTenant).where(MasterTenant.database_name == normalized)).scalar_one_or_none()
    if tenant is None:
        raise RuntimeError(f"Tenant {normalized!r} was not found in master_tenants.")
    return tenant


def _serialize_cutover_result(tenant: MasterTenant) -> TenantCutoverResult:
    migrated_at = tenant.runtime_migrated_at.isoformat() if tenant.runtime_migrated_at else None
    return TenantCutoverResult(
        tenant_id=int(tenant.id),
        tenant_code=str(tenant.code),
        database_name=str(tenant.database_name),
        runtime_storage_backend=str(tenant.runtime_storage_backend),
        runtime_schema_name=str(tenant.runtime_schema_name) if tenant.runtime_schema_name else None,
        runtime_migration_state=str(tenant.runtime_migration_state),
        runtime_migrated_at=migrated_at,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
