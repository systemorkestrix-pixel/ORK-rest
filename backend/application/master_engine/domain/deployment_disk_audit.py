from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.master_tenant_runtime_contract import (
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
)
from app.models import ExpenseAttachment, MasterTenant, Product
from app.tenant_runtime import create_runtime_session

_LOCAL_MEDIA_PREFIX = "/static/uploads/"


@dataclass(frozen=True)
class TenantDeploymentDiskAuditResult:
    tenant_id: int
    tenant_code: str
    database_name: str
    runtime_storage_backend: str
    media_storage_backend: str
    runtime_depends_on_local_disk: bool
    media_backend_depends_on_local_disk: bool
    local_product_media_references: int
    local_expense_media_references: int
    errors: tuple[str, ...]

    @property
    def has_local_disk_dependency(self) -> bool:
        return any(
            (
                self.runtime_depends_on_local_disk,
                self.media_backend_depends_on_local_disk,
                self.local_product_media_references > 0,
                self.local_expense_media_references > 0,
                bool(self.errors),
            )
        )

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["errors"] = list(self.errors)
        payload["has_local_disk_dependency"] = self.has_local_disk_dependency
        return payload


def is_local_media_reference(file_url: str | None) -> bool:
    normalized = str(file_url or "").strip()
    return normalized.startswith(_LOCAL_MEDIA_PREFIX)


def audit_deployment_disk_dependence(master_db: Session) -> dict[str, object]:
    tenants = list(master_db.execute(select(MasterTenant).order_by(MasterTenant.id.asc())).scalars())
    tenant_results = [audit_tenant_deployment_disk_dependence(tenant) for tenant in tenants]
    disk_independent = all(not result.has_local_disk_dependency for result in tenant_results)
    runtime_local_count = sum(1 for result in tenant_results if result.runtime_depends_on_local_disk)
    media_backend_local_count = sum(1 for result in tenant_results if result.media_backend_depends_on_local_disk)
    local_reference_count = sum(
        1
        for result in tenant_results
        if result.local_product_media_references > 0 or result.local_expense_media_references > 0
    )
    error_count = sum(1 for result in tenant_results if result.errors)

    return {
        "status": "ok" if disk_independent else "blocked",
        "disk_independent": disk_independent,
        "tenant_count": len(tenant_results),
        "runtime_tenants_on_local_disk": runtime_local_count,
        "tenants_on_local_media_backend": media_backend_local_count,
        "tenants_with_local_media_references": local_reference_count,
        "tenants_with_audit_errors": error_count,
        "tenants": [result.to_dict() for result in tenant_results],
    }


def audit_tenant_deployment_disk_dependence(tenant: MasterTenant) -> TenantDeploymentDiskAuditResult:
    local_product_refs = 0
    local_expense_refs = 0
    errors: list[str] = []

    try:
        local_product_refs, local_expense_refs = inspect_tenant_runtime_local_media_references(tenant.database_name)
    except Exception as error:  # noqa: BLE001
        errors.append(str(error))

    return TenantDeploymentDiskAuditResult(
        tenant_id=int(tenant.id),
        tenant_code=str(tenant.code),
        database_name=str(tenant.database_name),
        runtime_storage_backend=str(tenant.runtime_storage_backend),
        media_storage_backend=str(tenant.media_storage_backend),
        runtime_depends_on_local_disk=tenant.runtime_storage_backend == MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
        media_backend_depends_on_local_disk=tenant.media_storage_backend == MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
        local_product_media_references=local_product_refs,
        local_expense_media_references=local_expense_refs,
        errors=tuple(errors),
    )


def inspect_tenant_runtime_local_media_references(database_name: str) -> tuple[int, int]:
    tenant_db = create_runtime_session(database_name)
    try:
        product_count = int(
            tenant_db.execute(
                select(func.count()).select_from(Product).where(Product.image_path.like(f"{_LOCAL_MEDIA_PREFIX}%"))
            ).scalar_one()
            or 0
        )
        attachment_count = int(
            tenant_db.execute(
                select(func.count())
                .select_from(ExpenseAttachment)
                .where(ExpenseAttachment.file_url.like(f"{_LOCAL_MEDIA_PREFIX}%"))
            ).scalar_one()
            or 0
        )
        return product_count, attachment_count
    finally:
        tenant_db.close()
