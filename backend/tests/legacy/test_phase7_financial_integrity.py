import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase7-financial-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.enums import FinancialTransactionType, OrderStatus, PaymentStatus, ProductKind
from app.models import (
    FinancialTransaction,
    Order,
    OrderCostEntry,
    OrderItem,
    Product,
    ProductCategory,
    ShiftClosure,
    SystemAuditLog,
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
from application.financial_engine.domain.shifts import close_cash_shift as _close_cash_shift
from application.intelligence_engine.domain.reports import financial_snapshot
from application.operations_engine.domain.helpers import get_order_or_404
from application.operations_engine.domain.order_transitions import transition_order


def close_cash_shift(
    db,
    *,
    closed_by: int,
    opening_cash: float,
    actual_cash: float,
    note: str | None = None,
):
    return _close_cash_shift(
        db,
        closed_by=closed_by,
        opening_cash=opening_cash,
        actual_cash=actual_cash,
        note=note,
        financial_snapshot=financial_snapshot,
    )


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


class Phase7FinancialIntegritySuiteTests(unittest.TestCase):
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

    def _seed_catalog_and_stock(self, db, *, stock_qty: float, avg_unit_cost: float):
        actor = User(
            name="Financial QA Manager",
            username="financial_qa_manager",
            password_hash="$argon2id$seed",
            role="manager",
            active=True,
        )
        db.add(actor)
        db.flush()

        category = ProductCategory(name="Financial Meals", active=True, sort_order=0)
        db.add(category)
        db.flush()

        product = Product(
            name="Integrity Burger",
            description="Financial integrity test product",
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
            name="Integrity Bread",
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
        db.flush()
        return actor, product, wh_item

    def _create_order(self, db, *, product: Product, qty: int, status: str) -> Order:
        order_total = float(qty * 10)
        order = Order(
            type="takeaway",
            status=status,
            subtotal=order_total,
            delivery_fee=0.0,
            total=order_total,
            payment_status=PaymentStatus.UNPAID.value,
            payment_method="cash",
        )
        db.add(order)
        db.flush()
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                price=10.0,
                product_name=product.name,
            )
        )
        db.flush()
        return order

    def test_sale_cancel_refund_and_shift_close_reconcile_cash_and_stock(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, product, wh_item = self._seed_catalog_and_stock(db, stock_qty=20.0, avg_unit_cost=2.0)

            order_sale = self._create_order(
                db,
                product=product,
                qty=2,
                status=OrderStatus.READY.value,
            )
            order_refund = self._create_order(
                db,
                product=product,
                qty=1,
                status=OrderStatus.READY.value,
            )
            order_canceled = self._create_order(
                db,
                product=product,
                qty=1,
                status=OrderStatus.CREATED.value,
            )
            db.commit()

            transition_order(
                db,
                order_id=int(order_sale.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=True,
                amount_received=20.0,
            )
            transition_order(
                db,
                order_id=int(order_refund.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=True,
                amount_received=10.0,
            )
            transition_order(
                db,
                order_id=int(order_canceled.id),
                target_status=OrderStatus.CANCELED,
                performed_by=int(actor.id),
                reason_code="customer_request",
                reason_note="financial-integrity-suite",
            )
            refund_order(
                db,
                order_id=int(order_refund.id),
                refunded_by=int(actor.id),
                note="customer return",
            )

            closure = close_cash_shift(
                db,
                closed_by=int(actor.id),
                opening_cash=100.0,
                actual_cash=120.0,
                note="phase7 financial integrity close",
            )
            db.commit()

            sale_order = db.execute(select(Order).where(Order.id == int(order_sale.id))).scalar_one()
            refunded_order = db.execute(select(Order).where(Order.id == int(order_refund.id))).scalar_one()
            canceled_order = db.execute(select(Order).where(Order.id == int(order_canceled.id))).scalar_one()

            self.assertEqual(sale_order.status, OrderStatus.DELIVERED.value)
            self.assertEqual(sale_order.payment_status, PaymentStatus.PAID.value)
            self.assertEqual(refunded_order.status, OrderStatus.DELIVERED.value)
            self.assertEqual(refunded_order.payment_status, PaymentStatus.REFUNDED.value)
            self.assertEqual(canceled_order.status, OrderStatus.CANCELED.value)
            self.assertEqual(canceled_order.payment_status, PaymentStatus.UNPAID.value)

            sale_total = float(
                db.execute(
                    select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                        FinancialTransaction.type == FinancialTransactionType.SALE.value
                    )
                ).scalar_one()
                or 0.0
            )
            refund_total = float(
                db.execute(
                    select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                        FinancialTransaction.type == FinancialTransactionType.REFUND.value
                    )
                ).scalar_one()
                or 0.0
            )
            sale_count = int(
                db.execute(
                    select(func.count(FinancialTransaction.id)).where(
                        FinancialTransaction.type == FinancialTransactionType.SALE.value
                    )
                ).scalar_one()
                or 0
            )
            refund_count = int(
                db.execute(
                    select(func.count(FinancialTransaction.id)).where(
                        FinancialTransaction.type == FinancialTransactionType.REFUND.value
                    )
                ).scalar_one()
                or 0
            )

            self.assertEqual(sale_count, 2)
            self.assertAlmostEqual(sale_total, 30.0, places=2)
            self.assertEqual(refund_count, 1)
            self.assertAlmostEqual(refund_total, 10.0, places=2)

            canceled_financial_count = int(
                db.execute(
                    select(func.count(FinancialTransaction.id)).where(
                        FinancialTransaction.order_id == int(order_canceled.id)
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(canceled_financial_count, 0)

            canceled_cogs_count = int(
                db.execute(
                    select(func.count(OrderCostEntry.id)).where(
                        OrderCostEntry.order_id == int(order_canceled.id)
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(canceled_cogs_count, 0)

            canceled_stock_count = int(
                db.execute(
                    select(func.count(WarehouseStockLedger.id)).where(
                        WarehouseStockLedger.source_id == int(order_canceled.id),
                        WarehouseStockLedger.source_type.in_(("order_delivery", "order_refund")),
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(canceled_stock_count, 0)

            delivery_ledger_count = int(
                db.execute(
                    select(func.count(WarehouseStockLedger.id)).where(
                        WarehouseStockLedger.source_type == "order_delivery",
                        WarehouseStockLedger.source_id.in_((int(order_sale.id), int(order_refund.id))),
                    )
                ).scalar_one()
                or 0
            )
            refund_ledger_count = int(
                db.execute(
                    select(func.count(WarehouseStockLedger.id)).where(
                        WarehouseStockLedger.source_type == "order_refund",
                        WarehouseStockLedger.source_id == int(order_refund.id),
                        WarehouseStockLedger.movement_kind == "inbound",
                    )
                ).scalar_one()
                or 0
            )
            self.assertEqual(delivery_ledger_count, 0)
            self.assertEqual(refund_ledger_count, 0)

            balance = db.execute(
                select(WarehouseStockBalance).where(WarehouseStockBalance.item_id == int(wh_item.id))
            ).scalar_one()
            self.assertAlmostEqual(float(balance.quantity or 0.0), 20.0, places=4)

            self.assertIsInstance(closure, ShiftClosure)
            self.assertAlmostEqual(float(closure.sales_total or 0.0), 30.0, places=2)
            self.assertAlmostEqual(float(closure.refunds_total or 0.0), 10.0, places=2)
            self.assertAlmostEqual(float(closure.expenses_total or 0.0), 0.0, places=2)
            self.assertAlmostEqual(float(closure.expected_cash or 0.0), 120.0, places=2)
            self.assertAlmostEqual(float(closure.actual_cash or 0.0), 120.0, places=2)
            self.assertAlmostEqual(float(closure.variance or 0.0), 0.0, places=2)
            self.assertEqual(int(closure.transactions_count or 0), 3)

            cancel_audit = db.execute(
                select(SystemAuditLog).where(
                    SystemAuditLog.action == "cancel_order",
                    SystemAuditLog.entity_type == "order",
                    SystemAuditLog.entity_id == int(order_canceled.id),
                )
            ).scalar_one_or_none()
            refund_audit = db.execute(
                select(SystemAuditLog).where(
                    SystemAuditLog.action == "refund_order",
                    SystemAuditLog.entity_type == "order",
                    SystemAuditLog.entity_id == int(order_refund.id),
                )
            ).scalar_one_or_none()
            cogs_audit_count = int(
                db.execute(
                    select(func.count(SystemAuditLog.id)).where(
                        SystemAuditLog.action == "post_order_cogs",
                        SystemAuditLog.entity_type == "order",
                        SystemAuditLog.entity_id.in_((int(order_sale.id), int(order_refund.id))),
                    )
                ).scalar_one()
                or 0
            )
            self.assertIsNotNone(cancel_audit)
            self.assertIsNotNone(refund_audit)
            self.assertEqual(cogs_audit_count, 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_cancel_only_day_has_zero_financial_and_stock_effect(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor, product, wh_item = self._seed_catalog_and_stock(db, stock_qty=9.0, avg_unit_cost=3.0)
            canceled_order = self._create_order(
                db,
                product=product,
                qty=2,
                status=OrderStatus.CREATED.value,
            )
            db.commit()

            transition_order(
                db,
                order_id=int(canceled_order.id),
                target_status=OrderStatus.CANCELED,
                performed_by=int(actor.id),
                reason_code="duplicate_order",
                reason_note="cancel-only-shift",
            )
            closure = close_cash_shift(
                db,
                closed_by=int(actor.id),
                opening_cash=50.0,
                actual_cash=50.0,
                note="cancel-only close",
            )
            db.commit()

            financial_count = int(
                db.execute(select(func.count(FinancialTransaction.id))).scalar_one()
                or 0
            )
            cogs_count = int(
                db.execute(select(func.count(OrderCostEntry.id))).scalar_one()
                or 0
            )
            stock_ledger_count = int(
                db.execute(select(func.count(WarehouseStockLedger.id))).scalar_one()
                or 0
            )
            balance = db.execute(
                select(WarehouseStockBalance).where(WarehouseStockBalance.item_id == int(wh_item.id))
            ).scalar_one()

            self.assertEqual(financial_count, 0)
            self.assertEqual(cogs_count, 0)
            self.assertEqual(stock_ledger_count, 0)
            self.assertAlmostEqual(float(balance.quantity or 0.0), 9.0, places=4)

            self.assertAlmostEqual(float(closure.sales_total or 0.0), 0.0, places=2)
            self.assertAlmostEqual(float(closure.refunds_total or 0.0), 0.0, places=2)
            self.assertAlmostEqual(float(closure.expenses_total or 0.0), 0.0, places=2)
            self.assertAlmostEqual(float(closure.expected_cash or 0.0), 50.0, places=2)
            self.assertAlmostEqual(float(closure.variance or 0.0), 0.0, places=2)
            self.assertEqual(int(closure.transactions_count or 0), 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
