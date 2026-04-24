import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MASTER_DB_HANDLE = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
MASTER_DB_HANDLE.close()
MASTER_DB_PATH = Path(MASTER_DB_HANDLE.name)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "production"
os.environ["EXPOSE_DIAGNOSTIC_ENDPOINTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{MASTER_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "phase9-stop-sqlite-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-stop-sqlite-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

from app.database import SessionLocal, engine
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
    build_master_tenant_runtime_schema_name,
)
from app.tenant_runtime_storage import TenantRuntimeStorageTarget, resolve_tenant_runtime_target
from application.master_engine.domain.registry import create_master_tenant


class Phase9StopSqliteProvisioningContractTests(unittest.TestCase):
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
                "alembic upgrade failed for phase 8 stop-sqlite provisioning contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def test_new_tenant_creation_records_postgres_schema_as_the_runtime_backend(self) -> None:
        db = SessionLocal()
        fake_target = TenantRuntimeStorageTarget(
            database_name="tenant_phase9_new_postgres",
            backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
            database_path=None,
            schema_name=build_master_tenant_runtime_schema_name("tenant_phase9_new_postgres"),
            engine_url="postgresql+psycopg://example",
            cache_key="postgres_schema:tenant_phase9_new_postgres",
        )
        try:
            with patch(
                "application.master_engine.domain.registry.provision_tenant_database",
                return_value=fake_target,
            ):
                result = create_master_tenant(
                    db,
                    client_mode="new",
                    existing_client_id=None,
                    client_owner_name="Owner Phase8",
                    client_brand_name="Brand Phase8",
                    client_phone="0555000020",
                    client_city="Algiers",
                    tenant_brand_name="Tenant Phase8",
                    tenant_code="phase8_demo",
                    database_name="phase9_new_postgres",
                )
        finally:
            db.close()

        tenant_payload = result["tenant"]
        self.assertEqual(tenant_payload["runtime_storage_backend"], MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA)
        self.assertEqual(tenant_payload["runtime_migration_state"], MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER)
        self.assertEqual(
            tenant_payload["runtime_schema_name"],
            build_master_tenant_runtime_schema_name("tenant_phase9_new_postgres"),
        )
        self.assertIsNotNone(tenant_payload["runtime_migrated_at"])

        runtime_target = resolve_tenant_runtime_target("tenant_phase9_new_postgres")
        self.assertEqual(runtime_target.backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA)
        self.assertEqual(
            runtime_target.schema_name,
            build_master_tenant_runtime_schema_name("tenant_phase9_new_postgres"),
        )

    def test_source_files_keep_phase8_contract_fragments(self) -> None:
        registry_source = (BACKEND_DIR / "application" / "master_engine" / "domain" / "registry.py").read_text(
            encoding="utf-8"
        )
        provisioning_source = (
            BACKEND_DIR / "application" / "master_engine" / "domain" / "provisioning.py"
        ).read_text(encoding="utf-8")

        required_registry_fragments = [
            "MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA",
            "runtime_storage_backend=MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA",
            "runtime_migration_state=MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER",
            "provisioned_runtime_target = provision_tenant_database(",
        ]
        for fragment in required_registry_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, registry_source)

        required_provisioning_fragments = [
            "resolve_tenant_runtime_target(database_name)",
            "provision_postgres_tenant_runtime_schema(",
            "cleanup_provisioned_tenant_runtime(",
            'if target.backend == MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA',
        ]
        for fragment in required_provisioning_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, provisioning_source)


if __name__ == "__main__":
    unittest.main()
