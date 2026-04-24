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
os.environ["JWT_SECRET"] = "phase9-cutover-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-cutover-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

from app.database import SessionLocal, engine
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER,
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK,
    MASTER_TENANT_RUNTIME_MIGRATION_STATE_VALIDATED,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
    build_master_tenant_runtime_schema_name,
)
from app.models import MasterClient, MasterTenant
from app.tenant_runtime_storage import resolve_tenant_runtime_target
from application.master_engine.domain.per_tenant_cutover import (
    cutover_tenant_runtime,
    mark_tenant_runtime_validated,
    rollback_tenant_runtime_cutover,
)


class Phase9PerTenantCutoverContractTests(unittest.TestCase):
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
                "alembic upgrade failed for phase 7 cutover contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def setUp(self) -> None:
        self.db = SessionLocal()
        client = MasterClient(
            owner_name="Cutover Owner",
            brand_name="Cutover Client",
            phone="0555000010",
            city="Algiers",
            active_plan_id="base",
            subscription_state="active",
        )
        self.db.add(client)
        self.db.flush()
        tenant = MasterTenant(
            client_id=int(client.id),
            code=f"phase9_cutover_{client.id}",
            brand_name="Cutover Tenant",
            database_name=f"tenant_phase9_cutover_{client.id}",
            manager_username=f"phase9_cutover_{client.id}.manager",
            environment_state="ready",
            plan_id="base",
            paused_addons_json="[]",
        )
        self.db.add(tenant)
        self.db.commit()
        self.database_name = tenant.database_name

    def tearDown(self) -> None:
        self.db.close()

    def test_cutover_and_rollback_follow_master_tenant_contract(self) -> None:
        validated = mark_tenant_runtime_validated(self.db, database_name=self.database_name)
        self.db.commit()
        self.assertEqual(validated.runtime_migration_state, MASTER_TENANT_RUNTIME_MIGRATION_STATE_VALIDATED)

        cutover = cutover_tenant_runtime(self.db, database_name=self.database_name)
        self.db.commit()
        self.assertEqual(cutover.runtime_storage_backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA)
        self.assertEqual(cutover.runtime_migration_state, MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER)
        self.assertIsNotNone(cutover.runtime_migrated_at)

        rollback = rollback_tenant_runtime_cutover(self.db, database_name=self.database_name)
        self.db.commit()
        self.assertEqual(rollback.runtime_storage_backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE)
        self.assertEqual(rollback.runtime_migration_state, MASTER_TENANT_RUNTIME_MIGRATION_STATE_ROLLBACK)

    def test_runtime_target_follows_master_tenant_backend_after_cutover(self) -> None:
        mark_tenant_runtime_validated(self.db, database_name=self.database_name)
        cutover_tenant_runtime(self.db, database_name=self.database_name)
        self.db.commit()

        target = resolve_tenant_runtime_target(self.database_name)
        self.assertEqual(target.backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA)
        expected_schema = build_master_tenant_runtime_schema_name(self.database_name)
        self.assertEqual(target.schema_name, expected_schema)
        self.assertEqual(target.cache_key, f"postgres_schema:{expected_schema}")

    def test_cutover_source_files_keep_phase7_contract_fragments(self) -> None:
        cutover_source = (
            BACKEND_DIR / "application" / "master_engine" / "domain" / "per_tenant_cutover.py"
        ).read_text(encoding="utf-8")
        storage_source = (BACKEND_DIR / "app" / "tenant_runtime_storage.py").read_text(encoding="utf-8")
        runtime_source = (BACKEND_DIR / "app" / "tenant_runtime.py").read_text(encoding="utf-8")

        for fragment in [
            "cutover_tenant_runtime(",
            "rollback_tenant_runtime_cutover(",
            "tenant.runtime_storage_backend = MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA",
            "tenant.runtime_migration_state = MASTER_TENANT_RUNTIME_MIGRATION_STATE_CUTOVER",
            "dispose_tenant_runtime(tenant.database_name)",
        ]:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, cutover_source)

        for fragment in [
            "MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA",
            "_resolve_master_tenant_runtime_binding(",
            'cache_key=f"{backend}:{normalized_schema_name}"',
        ]:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, storage_source)

        self.assertIn('"tenant_database_name": normalized', runtime_source)


if __name__ == "__main__":
    unittest.main()
