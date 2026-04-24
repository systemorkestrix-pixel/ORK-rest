import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MASTER_DB_HANDLE = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
MASTER_DB_HANDLE.close()
MASTER_DB_PATH = Path(MASTER_DB_HANDLE.name)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "production"
os.environ["EXPOSE_DIAGNOSTIC_ENDPOINTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{MASTER_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "phase9-postgres-schema-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-postgres-schema-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

from app.database import SessionLocal, engine
from app.master_tenant_runtime_contract import build_master_tenant_runtime_schema_name
from app.models import MasterClient, MasterTenant


class Phase9PostgresSchemaProvisioningContractTests(unittest.TestCase):
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
                "alembic upgrade failed for postgres schema provisioning contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def test_schema_name_builder_is_stable_and_postgres_safe(self) -> None:
        self.assertEqual(build_master_tenant_runtime_schema_name("tenant_demo"), "tenant_demo")
        self.assertEqual(build_master_tenant_runtime_schema_name("Demo Branch"), "tenant_demo_branch")

        long_input = "tenant_" + ("very_long_branch_name_" * 10)
        schema_name = build_master_tenant_runtime_schema_name(long_input)
        self.assertLessEqual(len(schema_name), 63)
        self.assertTrue(schema_name.startswith("tenant_"))

    def test_master_tenant_defaults_to_planned_runtime_schema_name(self) -> None:
        db = SessionLocal()
        try:
            client = MasterClient(
                owner_name="Schema Owner",
                brand_name="Schema Client",
                phone="0555000002",
                city="Algiers",
                active_plan_id="base",
                subscription_state="active",
            )
            db.add(client)
            db.flush()
            tenant = MasterTenant(
                client_id=int(client.id),
                code="phase9_pg_schema",
                brand_name="Schema Tenant",
                database_name="tenant_phase9_pg_schema",
                manager_username="phase9_pg_schema.manager",
                environment_state="ready",
                plan_id="base",
                paused_addons_json="[]",
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        finally:
            db.close()

        self.assertEqual(tenant.runtime_schema_name, "tenant_phase9_pg_schema")

    def test_postgres_provisioning_module_keeps_schema_scoped_template_contract(self) -> None:
        source = (BACKEND_DIR / "application" / "master_engine" / "domain" / "postgres_runtime_provisioning.py").read_text(
            encoding="utf-8"
        )
        required_fragments = [
            'CREATE SCHEMA IF NOT EXISTS',
            'table.to_metadata(metadata, schema=normalized_schema_name)',
            'CREATE TABLE IF NOT EXISTS "{normalized_schema_name}".alembic_version',
            'return f"{normalized},public"',
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
