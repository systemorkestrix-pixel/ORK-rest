import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase3-cogs-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.enums import OrderStatus, ProductKind
from app.models import (
    Order,
    OrderCostEntry,
    OrderItem,
    Product,
    ProductCategory,
    User,
    WarehouseItem,
    WarehouseStockBalance,
    WarehouseStockLedger,
)
from app.database import create_app_engine
from application.intelligence_engine.domain.reports import profitability_report
from application.operations_engine.domain.order_transitions import transition_order


class Phase3ActualCOGSTests(unittest.TestCase):
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

    def _seed_order_context(self, db, *, stock_qty: float, avg_unit_cost: float, sold_qty: int):
        actor = User(
            name="COGS Manager",
            username="cogs_manager",
            password_hash="$argon2id$seed",
            role="manager",
            active=True,
        )
        db.add(actor)
        db.flush()

        category = ProductCategory(name="Meals", active=True, sort_order=0)
        db.add(category)
        db.flush()

        product = Product(
            name="Burger",
            description="Test product",
            price=10.0,
            available=True,
            kind=ProductKind.SELLABLE.value,
            category=category.name,
            category_id=category.id,
            is_archived=False,
        )
        db.add(product)
        db.flush()

        wh_item = WarehouseItem(
            name="Bread",
            unit="piece",
            alert_threshold=0.0,
            active=True,
        )
        db.add(wh_item)
        db.flush()
        db.add(
            WarehouseStockBalance(
                item_id=wh_item.id,
                quantity=stock_qty,
                avg_unit_cost=avg_unit_cost,
            )
        )

        order = Order(
            type="takeaway",
            status=OrderStatus.READY.value,
            subtotal=float(sold_qty * 10),
            delivery_fee=0.0,
            total=float(sold_qty * 10),
            payment_status="unpaid",
            payment_method="cash",
        )
        db.add(order)
        db.flush()

        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=sold_qty,
                price=10.0,
                product_name=product.name,
            )
        )
        db.commit()
        return actor, order, wh_item

    def test_delivery_is_decoupled_from_warehouse_stock(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, order, wh_item = self._seed_order_context(db, stock_qty=20.0, avg_unit_cost=3.0, sold_qty=3)

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=False,
            )
            db.commit()

            balance = db.execute(
                select(WarehouseStockBalance).where(WarehouseStockBalance.item_id == int(wh_item.id))
            ).scalar_one()
            self.assertAlmostEqual(float(balance.quantity), 20.0, places=4)

            ledger_rows = db.execute(
                select(WarehouseStockLedger).where(
                    WarehouseStockLedger.source_type == "order_delivery",
                    WarehouseStockLedger.source_id == int(order.id),
                )
            ).scalars().all()
            self.assertEqual(len(ledger_rows), 0)

            cogs_rows = db.execute(
                select(OrderCostEntry).where(OrderCostEntry.order_id == int(order.id))
            ).scalars().all()
            self.assertEqual(len(cogs_rows), 0)

            report = profitability_report(db)
            self.assertAlmostEqual(float(report["total_revenue"]), 30.0, places=2)
            self.assertAlmostEqual(float(report["total_estimated_cost"]), 0.0, places=2)
            self.assertAlmostEqual(float(report["total_gross_profit"]), 30.0, places=2)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delivery_does_not_block_when_warehouse_stock_is_insufficient(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, order, wh_item = self._seed_order_context(db, stock_qty=3.0, avg_unit_cost=3.0, sold_qty=2)

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=False,
            )
            db.commit()

            pending_cogs = int(
                db.execute(select(func.count(OrderCostEntry.id)).where(OrderCostEntry.order_id == int(order.id))).scalar_one()
                or 0
            )
            self.assertEqual(pending_cogs, 0)

            stock_ledger_count = int(
                db.execute(
                    select(func.count(WarehouseStockLedger.id)).where(
                        WarehouseStockLedger.source_type == "order_delivery",
                        WarehouseStockLedger.source_id == int(order.id),
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(stock_ledger_count, 0)

            fresh_order = db.execute(select(Order).where(Order.id == int(order.id))).scalar_one()
            self.assertEqual(str(fresh_order.status), OrderStatus.DELIVERED.value)
            balance = db.execute(
                select(WarehouseStockBalance).where(WarehouseStockBalance.item_id == int(wh_item.id))
            ).scalar_one()
            self.assertAlmostEqual(float(balance.quantity), 3.0, places=4)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delivery_does_not_require_product_to_warehouse_item_mapping(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, order, wh_item = self._seed_order_context(db, stock_qty=10.0, avg_unit_cost=3.0, sold_qty=1)
            wh_item.name = "Unrelated Item"
            db.commit()

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=False,
            )
            db.commit()

            refreshed = db.execute(select(Order).where(Order.id == int(order.id))).scalar_one()
            self.assertEqual(refreshed.status, OrderStatus.DELIVERED.value)
            cogs_count = int(
                db.execute(select(func.count(OrderCostEntry.id)).where(OrderCostEntry.order_id == int(order.id))).scalar_one()
                or 0
            )
            self.assertEqual(cogs_count, 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_concurrent_delivery_keeps_stock_consistent(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, order_a, wh_item = self._seed_order_context(db, stock_qty=5.0, avg_unit_cost=3.0, sold_qty=2)
            product_id = int(
                db.execute(
                    select(OrderItem.product_id).where(OrderItem.order_id == int(order_a.id))
                ).scalar_one()
            )

            order_b = Order(
                type="takeaway",
                status=OrderStatus.READY.value,
                subtotal=20.0,
                delivery_fee=0.0,
                total=20.0,
                payment_status="unpaid",
                payment_method="cash",
            )
            db.add(order_b)
            db.flush()
            db.add(
                OrderItem(
                    order_id=int(order_b.id),
                    product_id=product_id,
                    quantity=2,
                    price=10.0,
                    product_name="Burger",
                )
            )
            db.commit()

            barrier = threading.Barrier(3)
            results: dict[int, str] = {}
            lock = threading.Lock()

            def worker(order_id: int) -> None:
                local = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
                try:
                    barrier.wait(timeout=5)
                    transition_order(
                        local,
                        order_id=order_id,
                        target_status=OrderStatus.DELIVERED,
                        performed_by=int(actor.id),
                        collect_payment=False,
                    )
                    local.commit()
                    outcome = "delivered"
                except HTTPException as exc:
                    local.rollback()
                    outcome = f"error:{exc.status_code}"
                finally:
                    local.close()
                    with lock:
                        results[order_id] = outcome

            t1 = threading.Thread(target=worker, args=(int(order_a.id),))
            t2 = threading.Thread(target=worker, args=(int(order_b.id),))
            t1.start()
            t2.start()
            barrier.wait(timeout=5)
            t1.join()
            t2.join()

            verify = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
            try:
                delivered_count = int(
                    verify.execute(
                        select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED.value)
                    ).scalar_one()
                    or 0
                )
                self.assertEqual(delivered_count, 2)

                balance = verify.execute(
                    select(WarehouseStockBalance).where(WarehouseStockBalance.item_id == int(wh_item.id))
                ).scalar_one()
                self.assertAlmostEqual(float(balance.quantity), 5.0, places=4)
                self.assertGreaterEqual(float(balance.quantity), 0.0)
            finally:
                verify.close()

            outcomes = list(results.values())
            self.assertEqual(outcomes.count("delivered"), 2)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
