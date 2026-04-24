import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect

MASTER_DB_HANDLE = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
MASTER_DB_HANDLE.close()
MASTER_DB_PATH = Path(MASTER_DB_HANDLE.name)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "production"
os.environ["EXPOSE_DIAGNOSTIC_ENDPOINTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{MASTER_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "phase9-master-runtime-contract-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-master-runtime-contract-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

from app.database import SessionLocal, engine
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_NOT_STARTED,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
    build_master_tenant_runtime_schema_name,
)
from app.models import MasterClient, MasterTenant
from application.master_engine.domain.registry import serialize_master_tenant


class Phase9MasterTenantRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        if migrated.returncode != 0:
            raise AssertionError(
                "alembic upgrade failed for master tenant runtime contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def test_master_tenants_table_includes_runtime_contract_columns(self) -> None:
        columns = {column["name"] for column in inspect(engine).get_columns("master_tenants")}
        self.assertTrue(
            {
                "runtime_storage_backend",
                "runtime_schema_name",
                "runtime_migration_state",
                "runtime_migrated_at",
                "media_storage_backend",
            }.issubset(columns)
        )

    def test_master_tenant_defaults_and_serializer_expose_phase2_contract(self) -> None:
        db = SessionLocal()
        try:
            client = MasterClient(
                owner_name="Phase9 Owner",
                brand_name="Phase9 Client",
                phone="0555000001",
                city="Algiers",
                active_plan_id="base",
                subscription_state="active",
            )
            db.add(client)
            db.flush()
            tenant = MasterTenant(
                client_id=int(client.id),
                code="phase9_runtime_contract",
                brand_name="Phase9 Runtime Tenant",
                database_name="tenant_phase9_runtime_contract",
                manager_username="phase9_runtime.manager",
                environment_state="ready",
                plan_id="base",
                paused_addons_json="[]",
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            db.refresh(client)
            serialized = serialize_master_tenant(tenant)
        finally:
            db.close()

        self.assertEqual(tenant.runtime_storage_backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE)
        self.assertEqual(
            tenant.runtime_schema_name,
            build_master_tenant_runtime_schema_name("tenant_phase9_runtime_contract"),
        )
        self.assertEqual(tenant.runtime_migration_state, MASTER_TENANT_RUNTIME_MIGRATION_STATE_NOT_STARTED)
        self.assertIsNone(tenant.runtime_migrated_at)
        self.assertEqual(tenant.media_storage_backend, MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC)

        self.assertEqual(serialized["runtime_storage_backend"], MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE)
        self.assertEqual(
            serialized["runtime_schema_name"],
            build_master_tenant_runtime_schema_name("tenant_phase9_runtime_contract"),
        )
        self.assertEqual(serialized["runtime_migration_state"], MASTER_TENANT_RUNTIME_MIGRATION_STATE_NOT_STARTED)
        self.assertIsNone(serialized["runtime_migrated_at"])
        self.assertEqual(serialized["media_storage_backend"], MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC)


if __name__ == "__main__":
    unittest.main()
