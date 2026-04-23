import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase5-pagination-secret-0123456789abcdef012345")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.models import (
    DeliveryAssignment,
    DeliveryDriver,
    Order,
    Product,
    ProductCategory,
    RestaurantTable,
    User,
    WarehouseSupplier,
)
from app.routers.delivery import my_assignments
from app.routers.manager import (
    list_users,
    manager_list_table_sessions,
    manager_list_tables,
)
from app.routers.public import list_public_products
from app.routers.warehouse import get_warehouse_suppliers


class Phase5PaginationTests(unittest.TestCase):
    def _build_migrated_session(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"alembic upgrade failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
        session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
        return session, engine, db_path

    def _seed_manager(self, db) -> User:
        manager = User(
            name="Manager",
            username="manager_main",
            password_hash="$argon2id$seed",
            role="manager",
            active=True,
        )
        db.add(manager)
        db.commit()
        db.refresh(manager)
        return manager

    def test_manager_users_endpoint_enforces_default_pagination(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            manager = self._seed_manager(db)
            for idx in range(120):
                db.add(
                    User(
                        name=f"User {idx}",
                        username=f"manager_user_{idx}",
                        password_hash="$argon2id$seed",
                        role="manager",
                        active=True,
                    )
                )
            db.commit()

            page1 = list_users(page=1, page_size=50, _=manager, db=db)
            page3 = list_users(page=3, page_size=50, _=manager, db=db)

            self.assertEqual(len(page1), 50)
            self.assertEqual(len(page3), 21)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_public_products_endpoint_enforces_default_pagination(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            category = ProductCategory(name="Main", active=True, sort_order=0)
            db.add(category)
            db.flush()
            for idx in range(70):
                db.add(
                    Product(
                        name=f"Product {idx}",
                        description=None,
                        price=10.0 + idx,
                        available=True,
                        kind="sellable",
                        category="Main",
                        category_id=int(category.id),
                        image_path=None,
                        is_archived=False,
                    )
                )
            db.commit()

            page1 = list_public_products(page=1, page_size=24, db=db)
            page3 = list_public_products(page=3, page_size=24, db=db)

            self.assertEqual(len(page1), 24)
            self.assertEqual(len(page3), 22)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delivery_assignments_endpoint_enforces_default_pagination_for_manager(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            manager = self._seed_manager(db)
            driver = DeliveryDriver(
                name="Driver",
                phone="0500000000",
                vehicle="Bike",
                active=True,
                status="available",
            )
            db.add(driver)
            db.flush()

            for idx in range(65):
                order = Order(
                    type="delivery",
                    status="IN_PREPARATION",
                    table_id=None,
                    phone="0500000000",
                    address=f"Addr {idx}",
                    subtotal=20.0,
                    delivery_fee=5.0,
                    total=25.0,
                    payment_status="unpaid",
                    payment_method="cash",
                )
                db.add(order)
                db.flush()
                db.add(
                    DeliveryAssignment(
                        order_id=int(order.id),
                        driver_id=int(driver.id),
                        status="assigned",
                    )
                )
            db.commit()

            page1 = my_assignments(page=1, page_size=30, current_user=manager, db=db)
            page3 = my_assignments(page=3, page_size=30, current_user=manager, db=db)

            self.assertEqual(len(page1), 30)
            self.assertEqual(len(page3), 5)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_warehouse_suppliers_endpoint_enforces_default_pagination(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            manager = self._seed_manager(db)
            for idx in range(120):
                db.add(
                    WarehouseSupplier(
                        name=f"Supplier {idx}",
                        phone=None,
                        email=None,
                        address=None,
                        payment_term_days=0,
                        credit_limit=None,
                        quality_rating=4.0,
                        lead_time_days=1,
                        notes=None,
                        active=True,
                    )
                )
            db.commit()

            page1 = get_warehouse_suppliers(page=1, page_size=50, _=manager, db=db)
            page3 = get_warehouse_suppliers(page=3, page_size=50, _=manager, db=db)

            self.assertEqual(len(page1), 50)
            self.assertEqual(len(page3), 20)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_manager_tables_and_sessions_endpoints_enforce_default_pagination(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            manager = self._seed_manager(db)

            for idx in range(135):
                table = RestaurantTable(qr_code=f"/menu?table={idx}", status="available")
                db.add(table)
                db.flush()
                if idx < 70:
                    db.add(
                        Order(
                            type="dine-in",
                            status="CREATED",
                            table_id=int(table.id),
                            phone=None,
                            address=None,
                            subtotal=10.0,
                            delivery_fee=0.0,
                            total=10.0,
                            payment_status="unpaid",
                            payment_method="cash",
                        )
                    )
            db.commit()

            table_page1 = manager_list_tables(page=1, page_size=50, _=manager, db=db)
            table_page3 = manager_list_tables(page=3, page_size=50, _=manager, db=db)
            session_page1 = manager_list_table_sessions(page=1, page_size=50, _=manager, db=db)
            session_page2 = manager_list_table_sessions(page=2, page_size=50, _=manager, db=db)

            self.assertEqual(len(table_page1), 50)
            self.assertEqual(len(table_page3), 35)
            self.assertEqual(len(session_page1), 50)
            self.assertEqual(len(session_page2), 20)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
