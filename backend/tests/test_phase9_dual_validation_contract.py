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
os.environ["JWT_SECRET"] = "phase9-dual-validation-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-dual-validation-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

from app.database import engine
from app.tenant_runtime_storage import create_tenant_runtime_engine, resolve_tenant_runtime_sqlite_path
from application.master_engine.domain.runtime_cutover_validation import (
    DUAL_VALIDATION_SAMPLE_TABLES,
    build_dual_validation_runtime_metadata,
    build_dual_validation_smoke_checks,
    validate_tenant_runtime_dual_state,
)


class Phase9DualValidationContractTests(unittest.TestCase):
    tenant_database_name = "phase9_dual_validation_contract"

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
                "alembic upgrade failed for phase 6 dual validation contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        tenant_path = resolve_tenant_runtime_sqlite_path(cls.tenant_database_name)
        if tenant_path.exists():
            tenant_path.unlink()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def setUp(self) -> None:
        tenant_path = resolve_tenant_runtime_sqlite_path(self.tenant_database_name)
        if tenant_path.exists():
            tenant_path.unlink()

        metadata = build_dual_validation_runtime_metadata()
        runtime_engine = create_tenant_runtime_engine(self.tenant_database_name)
        try:
            metadata.create_all(bind=runtime_engine)
            with runtime_engine.begin() as connection:
                connection.execute(
                    metadata.tables["users"].insert(),
                    [
                        {
                            "id": 1,
                            "name": "Manager",
                            "username": "manager",
                            "password_hash": "hashed",
                            "role": "manager",
                            "active": True,
                        }
                    ],
                )
                connection.execute(
                    metadata.tables["product_categories"].insert(),
                    [{"id": 1, "name": "Main", "active": True, "sort_order": 1}],
                )
                connection.execute(
                    metadata.tables["products"].insert(),
                    [
                        {
                            "id": 1,
                            "name": "Burger",
                            "description": "Classic",
                            "price": 900.0,
                            "available": True,
                            "kind": "primary",
                            "category": "Main",
                            "category_id": 1,
                            "image_path": None,
                            "is_archived": False,
                        }
                    ],
                )
                connection.execute(
                    metadata.tables["orders"].insert(),
                    [
                        {
                            "id": 1,
                            "type": "dine_in",
                            "status": "created",
                            "table_id": None,
                            "phone": None,
                            "address": None,
                            "delivery_location_key": None,
                            "delivery_location_label": None,
                            "delivery_location_level": None,
                            "delivery_location_snapshot_json": None,
                            "subtotal": 900.0,
                            "delivery_fee": 0.0,
                            "total": 900.0,
                            "notes": None,
                            "payment_status": "unpaid",
                            "paid_at": None,
                            "paid_by": None,
                            "amount_received": None,
                            "change_amount": None,
                            "payment_method": "cash",
                            "collected_by_channel": "cashier",
                            "collection_variance_amount": 0.0,
                            "collection_variance_reason": None,
                            "accounting_recognized_at": None,
                            "delivery_team_notified_at": None,
                            "delivery_team_notified_by": None,
                            "delivery_failure_resolution_status": None,
                            "delivery_failure_resolution_note": None,
                            "delivery_failure_resolved_at": None,
                            "delivery_failure_resolved_by": None,
                        }
                    ],
                )
                connection.execute(
                    metadata.tables["financial_transactions"].insert(),
                    [
                        {
                            "id": 1,
                            "order_id": None,
                            "delivery_settlement_id": None,
                            "expense_id": None,
                            "amount": 900.0,
                            "type": "sale",
                            "direction": "in",
                            "account_code": None,
                            "reference_group": "demo",
                            "created_by": 1,
                            "note": None,
                        }
                    ],
                )
        finally:
            runtime_engine.dispose()

    def test_dry_run_builds_source_parity_snapshot_and_smoke_manifest(self) -> None:
        report = validate_tenant_runtime_dual_state(
            database_name=self.tenant_database_name,
            tenant_code="phase9",
            sample_limit=3,
            dry_run=True,
        )

        self.assertTrue(report.dry_run)
        self.assertFalse(report.validation_passed)
        self.assertEqual(len(report.smoke_checks), 5)
        self.assertEqual({row.key for row in report.smoke_checks}, {
            "manager_login",
            "public_order",
            "tracking",
            "operations_page",
            "settings_read_write",
        })

        parity_by_table = {row.table_name: row for row in report.parity_reports}
        self.assertEqual(parity_by_table["users"].source_row_count, 1)
        self.assertIsNone(parity_by_table["users"].target_row_count)
        self.assertFalse(parity_by_table["users"].parity_ok)

        samples_by_table = {row.table_name: row for row in report.sample_reports}
        self.assertEqual(samples_by_table["users"].source_sample_rows[0]["username"], "manager")
        self.assertEqual(samples_by_table["products"].source_sample_rows[0]["name"], "Burger")
        self.assertEqual(samples_by_table["orders"].source_sample_rows[0]["status"], "created")

    def test_real_mode_requires_postgres_target_engine(self) -> None:
        with self.assertRaises(ValueError):
            validate_tenant_runtime_dual_state(database_name=self.tenant_database_name, dry_run=False)

    def test_smoke_manifest_paths_are_tenant_scoped(self) -> None:
        checks = build_dual_validation_smoke_checks(tenant_code="demo")
        paths = {row.key: row.path for row in checks}
        self.assertEqual(paths["manager_login"], "/t/demo/manager/login")
        self.assertEqual(paths["public_order"], "/t/demo/menu")
        self.assertEqual(paths["tracking"], "/t/demo/track")
        self.assertEqual(paths["operations_page"], "/t/demo/manager/operations/orders")
        self.assertEqual(paths["settings_read_write"], "/t/demo/manager/settings")

    def test_source_file_keeps_phase6_contract_fragments(self) -> None:
        source = (
            BACKEND_DIR / "application" / "master_engine" / "domain" / "runtime_cutover_validation.py"
        ).read_text(encoding="utf-8")
        required_fragments = [
            'DUAL_VALIDATION_SAMPLE_TABLES',
            'DUAL_VALIDATION_SMOKE_KEYS',
            'build_dual_validation_smoke_checks(',
            'validate_tenant_runtime_dual_state(',
            'sample_match=source_sample_rows == target_sample_rows',
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

        self.assertEqual(
            DUAL_VALIDATION_SAMPLE_TABLES,
            ("users", "products", "orders", "financial_transactions", "delivery_dispatches"),
        )


if __name__ == "__main__":
    unittest.main()
