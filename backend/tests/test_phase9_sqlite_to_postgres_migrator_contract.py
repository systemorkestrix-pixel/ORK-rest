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
os.environ["JWT_SECRET"] = "phase9-sqlite-to-postgres-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-sqlite-to-postgres-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

from app.database import engine
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA,
    MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE,
    build_master_tenant_runtime_schema_name,
)
from app.tenant_runtime_storage import resolve_tenant_runtime_sqlite_path
from application.master_engine.domain.sqlite_to_postgres_migrator import (
    build_sqlite_tenant_runtime_metadata,
    list_tenant_runtime_migration_tables,
    migrate_sqlite_tenant_runtime_to_postgres,
)


class Phase9SqliteToPostgresMigratorContractTests(unittest.TestCase):
    tenant_database_name = "phase9_sqlite_to_postgres_contract"

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
                "alembic upgrade failed for sqlite->postgres migrator contract tests:\n"
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

        metadata = build_sqlite_tenant_runtime_metadata()

        from app.tenant_runtime_storage import create_tenant_runtime_engine

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
                    metadata.tables["tables"].insert(),
                    [{"id": 1, "qr_code": "/t/demo/menu?table=1", "status": "available"}],
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
                            "table_id": 1,
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
                    metadata.tables["order_items"].insert(),
                    [
                        {
                            "id": 1,
                            "order_id": 1,
                            "product_id": 1,
                            "quantity": 1,
                            "price": 900.0,
                            "product_name": "Burger",
                        }
                    ],
                )
                connection.execute(
                    metadata.tables["system_settings"].insert(),
                    [{"key": "store_name", "value": "Phase9 Demo", "updated_by": 1}],
                )
        finally:
            runtime_engine.dispose()

    def test_migration_order_covers_all_non_master_runtime_tables(self) -> None:
        expected = {table.name for table in build_sqlite_tenant_runtime_metadata().sorted_tables}
        self.assertEqual(set(list_tenant_runtime_migration_tables()), expected)

    def test_dry_run_reads_source_sqlite_and_builds_postgres_target_report(self) -> None:
        report = migrate_sqlite_tenant_runtime_to_postgres(
            database_name=self.tenant_database_name,
            dry_run=True,
        )

        self.assertTrue(report.dry_run)
        self.assertFalse(report.validation_passed)
        self.assertEqual(report.source_backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE)
        self.assertEqual(report.target_backend, MASTER_TENANT_RUNTIME_STORAGE_BACKEND_POSTGRES_SCHEMA)
        self.assertEqual(
            report.target_schema_name,
            build_master_tenant_runtime_schema_name(self.tenant_database_name),
        )

        rows_by_table = {row.table_name: row for row in report.table_reports}
        self.assertEqual(rows_by_table["users"].source_row_count, 1)
        self.assertEqual(rows_by_table["products"].source_row_count, 1)
        self.assertEqual(rows_by_table["orders"].source_row_count, 1)
        self.assertEqual(rows_by_table["order_items"].source_row_count, 1)
        self.assertEqual(rows_by_table["system_settings"].source_row_count, 1)

    def test_real_mode_requires_postgres_target_engine(self) -> None:
        with self.assertRaises(ValueError):
            migrate_sqlite_tenant_runtime_to_postgres(database_name=self.tenant_database_name, dry_run=False)

    def test_source_file_keeps_phase4_contract_fragments(self) -> None:
        source = (
            BACKEND_DIR / "application" / "master_engine" / "domain" / "sqlite_to_postgres_migrator.py"
        ).read_text(encoding="utf-8")
        required_fragments = [
            "TENANT_RUNTIME_MIGRATION_TABLE_ORDER",
            "provision_postgres_tenant_runtime_schema(",
            "build_postgres_runtime_search_path(",
            "target_connection.execute(target_table.insert(), batch)",
            "validation_passed = _validate_target_row_counts(",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
