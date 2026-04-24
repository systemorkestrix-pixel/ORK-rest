from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.database import SessionLocal
from app.master_tenant_runtime_contract import MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA
from app.models import MasterTenant
from app.tenant_runtime_storage import build_tenant_runtime_target, tenant_runtime_target_exists
from application.master_engine.domain.provisioning import provision_tenant_database


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repair a tenant recorded as postgres_schema when its runtime schema was never provisioned."
    )
    parser.add_argument("--tenant-code", help="Tenant code to repair.")
    parser.add_argument("--database-name", help="Tenant runtime database name to repair.")
    parser.add_argument("--manager-password", required=True, help="New manager password to seed into the repaired runtime.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if not args.tenant_code and not args.database_name:
        raise SystemExit("Either --tenant-code or --database-name is required.")

    db = SessionLocal()
    try:
        statement = select(MasterTenant)
        if args.tenant_code:
            statement = statement.where(MasterTenant.code == str(args.tenant_code).strip().lower())
        else:
            statement = statement.where(MasterTenant.database_name == str(args.database_name).strip())

        tenant = db.execute(statement).scalar_one_or_none()
        if tenant is None:
            raise SystemExit("Tenant not found.")
        if tenant.runtime_storage_backend != MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA:
            raise SystemExit("Tenant is not configured for postgres_schema.")
        if not tenant.runtime_schema_name:
            raise SystemExit("Tenant has no runtime_schema_name.")

        runtime_target = build_tenant_runtime_target(
            database_name=tenant.database_name,
            backend=tenant.runtime_storage_backend,
            schema_name=tenant.runtime_schema_name,
        )
        existed_before = tenant_runtime_target_exists(runtime_target)
        if not existed_before:
            manager_name = tenant.client.owner_name if tenant.client is not None else tenant.brand_name
            provision_tenant_database(
                database_name=tenant.database_name,
                tenant_code=tenant.code,
                tenant_brand_name=tenant.brand_name,
                manager_username=tenant.manager_username,
                manager_password=args.manager_password,
                manager_name=manager_name,
                target_override=runtime_target,
            )
            tenant.environment_state = "ready"
            db.commit()

        report = {
            "status": "ok",
            "tenant_code": tenant.code,
            "database_name": tenant.database_name,
            "runtime_storage_backend": tenant.runtime_storage_backend,
            "runtime_schema_name": tenant.runtime_schema_name,
            "schema_existed_before": existed_before,
            "schema_exists_now": tenant_runtime_target_exists(runtime_target),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
