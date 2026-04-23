import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase3-drop-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine


LEGACY_TABLES: tuple[str, ...] = (
    "suppliers",
    "inventory_warehouses",
    "inventory_balances",
    "inventory_movements",
    "supplier_receipts",
    "supplier_receipt_items",
)

LEGACY_CONTRACT_TABLES: tuple[str, ...] = (
    "product_resources",
    "kitchen_resource_components",
)

ALL_DROPPED_TABLES: tuple[str, ...] = LEGACY_TABLES + LEGACY_CONTRACT_TABLES
ARCHIVE_TABLES: tuple[str, ...] = tuple(f"legacy_archive_{name}" for name in ALL_DROPPED_TABLES)


class Phase3InventoryPhysicalDropTests(unittest.TestCase):
    def _run_alembic(self, db_path: Path, revision: str) -> None:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        env.setdefault("JWT_SECRET", "phase3-drop-secret-0123456789abcdef0123456789")
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"alembic upgrade {revision} failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )

    def _new_temp_db_path(self) -> Path:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        return Path(tmp.name)

    def test_head_schema_removes_legacy_tables_and_keeps_archives(self) -> None:
        db_path = self._new_temp_db_path()
        try:
            self._run_alembic(db_path, "head")
            engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
            try:
                with engine.connect() as connection:
                    tables = {str(row[0]) for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}

                for table in ALL_DROPPED_TABLES:
                    self.assertNotIn(table, tables)
                for table in ARCHIVE_TABLES:
                    self.assertIn(table, tables)
            finally:
                engine.dispose()
        finally:
            if db_path.exists():
                db_path.unlink()

    def test_upgrade_archives_legacy_data_before_drop(self) -> None:
        db_path = self._new_temp_db_path()
        try:
            self._run_alembic(db_path, "07038e084fcd")
            engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
            try:
                with engine.begin() as connection:
                    now = datetime.now(UTC).isoformat(sep=" ", timespec="seconds")
                    connection.execute(
                        text(
                            "INSERT INTO users (id, name, username, password_hash, role, active, failed_login_attempts, created_at) "
                            "VALUES (1, 'Legacy User', 'legacy_user', '$argon2id$seed', 'manager', 1, 0, :now)"
                        ),
                        {"now": now},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO resources (id, name, quantity, unit, alert_threshold, active, scope) "
                            "VALUES (1, 'Legacy Resource', 10, 'unit', 0, 1, 'kitchen')"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO resources (id, name, quantity, unit, alert_threshold, active, scope) "
                            "VALUES (2, 'Legacy Stock Resource', 5, 'unit', 0, 1, 'stock')"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO product_categories (id, name, active, sort_order) "
                            "VALUES (9001, 'Legacy Category', 1, 0)"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO products ("
                            "id, name, description, price, available, kind, category, category_id, image_path, is_archived"
                            ") VALUES (9001, 'Legacy Product', NULL, 9.0, 1, 'sellable', 'Legacy Category', 9001, NULL, 0)"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO product_resources (id, product_id, resource_id, quantity_per_unit) "
                            "VALUES (9001, 9001, 1, 2.0)"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO kitchen_resource_components (id, kitchen_resource_id, stock_resource_id, quantity_per_unit) "
                            "VALUES (9001, 1, 2, 1.0)"
                        )
                    )
                    connection.execute(
                        text(
                            "INSERT INTO suppliers (id, name, phone, email, address, active, created_at) "
                            "VALUES (1, 'Legacy Supplier', NULL, NULL, NULL, 1, :now)"
                        ),
                        {"now": now},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO inventory_warehouses (id, name, code, active, created_at) "
                            "VALUES (1, 'Legacy Warehouse', 'LEGACY-WH', 1, :now)"
                        ),
                        {"now": now},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO inventory_balances (id, warehouse_id, resource_id, quantity, updated_at) "
                            "VALUES (1, 1, 1, 25, :now)"
                        ),
                        {"now": now},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO inventory_movements ("
                            "id, warehouse_id, resource_id, supplier_id, movement_type, quantity, "
                            "balance_before, balance_after, reason, source_type, source_id, created_by, created_at"
                            ") VALUES (1, 1, 1, 1, 'inbound', 25, 0, 25, 'legacy seed', 'manual', 1, 1, :now)"
                        ),
                        {"now": now},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO supplier_receipts (id, supplier_id, warehouse_id, reference_no, note, received_by, received_at) "
                            "VALUES (1, 1, 1, 'RCPT-1', 'legacy receipt', 1, :now)"
                        ),
                        {"now": now},
                    )
                    connection.execute(
                        text(
                            "INSERT INTO supplier_receipt_items (id, receipt_id, resource_id, quantity, unit_cost) "
                            "VALUES (1, 1, 1, 25, 2.5)"
                        )
                    )
            finally:
                engine.dispose()

            self._run_alembic(db_path, "head")
            verify_engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
            try:
                with verify_engine.connect() as connection:
                    tables = {
                        str(row[0])
                        for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                    }
                    for table in ALL_DROPPED_TABLES:
                        self.assertNotIn(table, tables)
                    for table in ARCHIVE_TABLES:
                        self.assertIn(table, tables)

                    self.assertEqual(
                        int(connection.execute(text("SELECT COUNT(*) FROM legacy_archive_suppliers")).scalar_one()),
                        1,
                    )
                    self.assertEqual(
                        int(
                            connection.execute(
                                text("SELECT COUNT(*) FROM legacy_archive_inventory_warehouses")
                            ).scalar_one()
                        ),
                        1,
                    )
                    self.assertEqual(
                        int(
                            connection.execute(
                                text("SELECT COUNT(*) FROM legacy_archive_inventory_balances")
                            ).scalar_one()
                        ),
                        1,
                    )
                    self.assertEqual(
                        int(
                            connection.execute(
                                text("SELECT COUNT(*) FROM legacy_archive_inventory_movements")
                            ).scalar_one()
                        ),
                        1,
                    )
                    self.assertEqual(
                        int(
                            connection.execute(
                                text("SELECT COUNT(*) FROM legacy_archive_supplier_receipts")
                            ).scalar_one()
                        ),
                        1,
                    )
                    self.assertEqual(
                        int(
                            connection.execute(
                                text("SELECT COUNT(*) FROM legacy_archive_supplier_receipt_items")
                            ).scalar_one()
                        ),
                        1,
                    )
                    self.assertEqual(
                        int(connection.execute(text("SELECT COUNT(*) FROM legacy_archive_product_resources")).scalar_one()),
                        1,
                    )
                    self.assertEqual(
                        int(
                            connection.execute(
                                text("SELECT COUNT(*) FROM legacy_archive_kitchen_resource_components")
                            ).scalar_one()
                        ),
                        1,
                    )
            finally:
                verify_engine.dispose()
        finally:
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    unittest.main()

