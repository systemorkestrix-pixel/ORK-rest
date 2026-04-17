import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase4-refund-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.enums import FinancialTransactionType, OrderStatus, ProductKind
from app.models import (
    FinancialTransaction,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    User,
    WarehouseItem,
    WarehouseStockBalance,
    WarehouseStockLedger,
)
from app.repositories.financial_repository import find_latest_order_transaction_by_type
from application.financial_engine.domain.delivery_accounting import (
    build_reference_group,
    record_financial_entry,
    reverse_delivery_detailed_entries,
)
from application.financial_engine.domain.refunds import refund_order as _refund_order
from application.operations_engine.domain.helpers import get_order_or_404
from application.operations_engine.domain.order_transitions import transition_order


def refund_order(
    db,
    *,
    order_id: int,
    refunded_by: int,
    note: str | None = None,
):
    return _refund_order(
        db,
        order_id=order_id,
        refunded_by=refunded_by,
        note=note,
        get_order=get_order_or_404,
        find_latest_order_transaction_by_type=find_latest_order_transaction_by_type,
        reverse_delivery_entries=reverse_delivery_detailed_entries,
        record_financial_entry=record_financial_entry,
        build_reference_group=build_reference_group,
    )


class Phase4RefundLifecycleTests(unittest.TestCase):
    def _build_migrated_session(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        env = os.environ.copy()
        env["DATABASE_PATH"] = db_path.as_posix()
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

    def _seed_context(self, db, *, stock_qty: float, sold_qty: int):
        actor = User(
            name="Refund Manager",
            username="refund_manager",
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
            name="Refund Burger",
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
            name="Refund Bread",
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
                avg_unit_cost=2.0,
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

    def test_refund_reverses_financial_effects_without_stock_movements(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, order, wh_item = self._seed_context(db, stock_qty=10.0, sold_qty=2)

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=True,
                amount_received=20.0,
            )
            refund_order(
                db,
                order_id=int(order.id),
                refunded_by=int(actor.id),
                note="customer request",
            )
            db.commit()

            refreshed = db.execute(select(Order).where(Order.id == int(order.id))).scalar_one()
            self.assertEqual(refreshed.payment_status, "refunded")

            refund_txs = db.execute(
                select(FinancialTransaction).where(
                    FinancialTransaction.order_id == int(order.id),
                    FinancialTransaction.type == FinancialTransactionType.REFUND.value,
                )
            ).scalars().all()
            self.assertEqual(len(refund_txs), 1)
            self.assertAlmostEqual(float(refund_txs[0].amount), 20.0, places=2)

            balance = db.execute(
                select(WarehouseStockBalance).where(WarehouseStockBalance.item_id == int(wh_item.id))
            ).scalar_one()
            self.assertAlmostEqual(float(balance.quantity), 10.0, places=4)

            outbound_count = int(
                db.execute(
                    select(func.count(WarehouseStockLedger.id)).where(
                        WarehouseStockLedger.source_type == "order_delivery",
                        WarehouseStockLedger.source_id == int(order.id),
                    )
                ).scalar_one()
                or 0
            )
            inbound_refund_count = int(
                db.execute(
                    select(func.count(WarehouseStockLedger.id)).where(
                        WarehouseStockLedger.source_type == "order_refund",
                        WarehouseStockLedger.source_id == int(order.id),
                        WarehouseStockLedger.movement_kind == "inbound",
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(outbound_count, 0)
            self.assertEqual(inbound_refund_count, 0)

            refund_order(
                db,
                order_id=int(order.id),
                refunded_by=int(actor.id),
                note="idempotent retry",
            )
            db.commit()
            refund_count_after_retry = int(
                db.execute(
                    select(func.count(FinancialTransaction.id)).where(
                        FinancialTransaction.order_id == int(order.id),
                        FinancialTransaction.type == FinancialTransactionType.REFUND.value,
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(refund_count_after_retry, 1)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_refund_rejected_for_unpaid_order(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, order, _ = self._seed_context(db, stock_qty=10.0, sold_qty=1)

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=False,
            )
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                refund_order(
                    db,
                    order_id=int(order.id),
                    refunded_by=int(actor.id),
                    note=None,
                )
            self.assertEqual(ctx.exception.status_code, 400)
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
