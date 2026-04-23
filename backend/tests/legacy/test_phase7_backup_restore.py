import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase7-backup-restore-secret-0123456789abcdef0123456789")
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


class Phase7BackupRestoreTests(unittest.TestCase):
    def _run_alembic_upgrade(self, db_path: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        return subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    def _build_migrated_session(self, db_path: Path):
        proc = self._run_alembic_upgrade(db_path)
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"alembic upgrade failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
        session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
        return session, engine

    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _to_scalar(self, value):
        if value is None:
            return None
        if isinstance(value, float):
            return round(float(value), 6)
        if isinstance(value, datetime):
            normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
            return normalized.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def _critical_state_hash(self, db) -> str:
        payload = {
            "financial_transactions": [
                [
                    self._to_scalar(row.id),
                    self._to_scalar(row.order_id),
                    self._to_scalar(row.expense_id),
                    self._to_scalar(row.amount),
                    self._to_scalar(row.type),
                    self._to_scalar(row.created_by),
                    self._to_scalar(row.note),
                    self._to_scalar(row.created_at),
                ]
                for row in db.execute(
                    select(
                        FinancialTransaction.id,
                        FinancialTransaction.order_id,
                        FinancialTransaction.expense_id,
                        FinancialTransaction.amount,
                        FinancialTransaction.type,
                        FinancialTransaction.created_by,
                        FinancialTransaction.note,
                        FinancialTransaction.created_at,
                    ).order_by(FinancialTransaction.id.asc())
                ).all()
            ],
            "stock_balances": [
                [
                    self._to_scalar(row.item_id),
                    self._to_scalar(row.quantity),
                    self._to_scalar(row.avg_unit_cost),
                    self._to_scalar(row.updated_at),
                ]
                for row in db.execute(
                    select(
                        WarehouseStockBalance.item_id,
                        WarehouseStockBalance.quantity,
                        WarehouseStockBalance.avg_unit_cost,
                        WarehouseStockBalance.updated_at,
                    ).order_by(WarehouseStockBalance.item_id.asc())
                ).all()
            ],
            "stock_ledger": [
                [
                    self._to_scalar(row.id),
                    self._to_scalar(row.item_id),
                    self._to_scalar(row.movement_kind),
                    self._to_scalar(row.source_type),
                    self._to_scalar(row.source_id),
                    self._to_scalar(row.quantity),
                    self._to_scalar(row.unit_cost),
                    self._to_scalar(row.line_value),
                    self._to_scalar(row.balance_before),
                    self._to_scalar(row.balance_after),
                    self._to_scalar(row.created_by),
                    self._to_scalar(row.created_at),
                ]
                for row in db.execute(
                    select(
                        WarehouseStockLedger.id,
                        WarehouseStockLedger.item_id,
                        WarehouseStockLedger.movement_kind,
                        WarehouseStockLedger.source_type,
                        WarehouseStockLedger.source_id,
                        WarehouseStockLedger.quantity,
                        WarehouseStockLedger.unit_cost,
                        WarehouseStockLedger.line_value,
                        WarehouseStockLedger.balance_before,
                        WarehouseStockLedger.balance_after,
                        WarehouseStockLedger.created_by,
                        WarehouseStockLedger.created_at,
                    ).order_by(WarehouseStockLedger.id.asc())
                ).all()
            ],
            "order_cost_entries": [
                [
                    self._to_scalar(row.id),
                    self._to_scalar(row.order_id),
                    self._to_scalar(row.order_item_id),
                    self._to_scalar(row.product_id),
                    self._to_scalar(row.quantity_sold),
                    self._to_scalar(row.cogs_amount),
                    self._to_scalar(row.created_by),
                    self._to_scalar(row.created_at),
                ]
                for row in db.execute(
                    select(
                        OrderCostEntry.id,
                        OrderCostEntry.order_id,
                        OrderCostEntry.order_item_id,
                        OrderCostEntry.product_id,
                        OrderCostEntry.quantity_sold,
                        OrderCostEntry.cogs_amount,
                        OrderCostEntry.created_by,
                        OrderCostEntry.created_at,
                    ).order_by(OrderCostEntry.id.asc())
                ).all()
            ],
            "shift_closures": [
                [
                    self._to_scalar(row.id),
                    self._to_scalar(row.business_date),
                    self._to_scalar(row.opening_cash),
                    self._to_scalar(row.sales_total),
                    self._to_scalar(row.refunds_total),
                    self._to_scalar(row.expenses_total),
                    self._to_scalar(row.expected_cash),
                    self._to_scalar(row.actual_cash),
                    self._to_scalar(row.variance),
                    self._to_scalar(row.transactions_count),
                    self._to_scalar(row.closed_by),
                    self._to_scalar(row.closed_at),
                ]
                for row in db.execute(
                    select(
                        ShiftClosure.id,
                        ShiftClosure.business_date,
                        ShiftClosure.opening_cash,
                        ShiftClosure.sales_total,
                        ShiftClosure.refunds_total,
                        ShiftClosure.expenses_total,
                        ShiftClosure.expected_cash,
                        ShiftClosure.actual_cash,
                        ShiftClosure.variance,
                        ShiftClosure.transactions_count,
                        ShiftClosure.closed_by,
                        ShiftClosure.closed_at,
                    ).order_by(ShiftClosure.id.asc())
                ).all()
            ],
            "audit_logs": [
                [
                    self._to_scalar(row.id),
                    self._to_scalar(row.module),
                    self._to_scalar(row.action),
                    self._to_scalar(row.entity_type),
                    self._to_scalar(row.entity_id),
                    self._to_scalar(row.performed_by),
                    self._to_scalar(row.description),
                    self._to_scalar(row.timestamp),
                ]
                for row in db.execute(
                    select(
                        SystemAuditLog.id,
                        SystemAuditLog.module,
                        SystemAuditLog.action,
                        SystemAuditLog.entity_type,
                        SystemAuditLog.entity_id,
                        SystemAuditLog.performed_by,
                        SystemAuditLog.description,
                        SystemAuditLog.timestamp,
                    ).order_by(SystemAuditLog.id.asc())
                ).all()
            ],
        }
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _reconciliation_snapshot(self, db) -> dict[str, float | int | str]:
        sales_total = float(
            db.execute(
                select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                    FinancialTransaction.type == FinancialTransactionType.SALE.value
                )
            ).scalar_one()
            or 0.0
        )
        refunds_total = float(
            db.execute(
                select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                    FinancialTransaction.type == FinancialTransactionType.REFUND.value
                )
            ).scalar_one()
            or 0.0
        )
        expenses_total = float(
            db.execute(
                select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                    FinancialTransaction.type == FinancialTransactionType.EXPENSE.value
                )
            ).scalar_one()
            or 0.0
        )
        tx_count = int(db.execute(select(func.count(FinancialTransaction.id))).scalar_one() or 0)
        stock_balance_total = float(
            db.execute(select(func.coalesce(func.sum(WarehouseStockBalance.quantity), 0.0))).scalar_one()
            or 0.0
        )
        stock_ledger_count = int(db.execute(select(func.count(WarehouseStockLedger.id))).scalar_one() or 0)
        audit_count = int(db.execute(select(func.count(SystemAuditLog.id))).scalar_one() or 0)
        shift_closure_count = int(db.execute(select(func.count(ShiftClosure.id))).scalar_one() or 0)
        return {
            "cash_total": round(sales_total - refunds_total - expenses_total, 6),
            "tx_count": tx_count,
            "stock_balance_total": round(stock_balance_total, 6),
            "stock_ledger_count": stock_ledger_count,
            "audit_count": audit_count,
            "shift_closure_count": shift_closure_count,
            "critical_hash": self._critical_state_hash(db),
        }

    def _seed_financial_baseline(self, db) -> dict[str, int]:
        actor = User(
            name="P7 Finance Manager",
            username="p7_finance_manager",
            password_hash="$argon2id$seed",
            role="manager",
            active=True,
        )
        db.add(actor)
        db.flush()

        category = ProductCategory(name="P7 Meals", active=True, sort_order=0)
        db.add(category)
        db.flush()

        product = Product(
            name="P7 Integrity Burger",
            description="backup/restore integrity product",
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
            name="P7 Bread",
            unit="piece",
            alert_threshold=0.0,
            active=True,
        )
        db.add(wh_item)
        db.flush()
        db.add(
            WarehouseStockBalance(
                item_id=wh_item.id,
                quantity=20.0,
                avg_unit_cost=2.0,
            )
        )
        db.flush()

        order_sale = Order(
            type="takeaway",
            status=OrderStatus.READY.value,
            subtotal=20.0,
            delivery_fee=0.0,
            total=20.0,
            payment_status=PaymentStatus.UNPAID.value,
            payment_method="cash",
        )
        order_refund = Order(
            type="takeaway",
            status=OrderStatus.READY.value,
            subtotal=10.0,
            delivery_fee=0.0,
            total=10.0,
            payment_status=PaymentStatus.UNPAID.value,
            payment_method="cash",
        )
        db.add(order_sale)
        db.add(order_refund)
        db.flush()
        db.add_all(
            [
                OrderItem(
                    order_id=int(order_sale.id),
                    product_id=int(product.id),
                    quantity=2,
                    price=10.0,
                    product_name=product.name,
                ),
                OrderItem(
                    order_id=int(order_refund.id),
                    product_id=int(product.id),
                    quantity=1,
                    price=10.0,
                    product_name=product.name,
                ),
            ]
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
        refund_order(
            db,
            order_id=int(order_refund.id),
            refunded_by=int(actor.id),
            note="P7 restore baseline refund",
        )
        closure = close_cash_shift(
            db,
            closed_by=int(actor.id),
            opening_cash=100.0,
            actual_cash=120.0,
            note="P7 baseline closure",
        )
        db.commit()

        # Move baseline closure + transactions to previous day so cold start can create a new closure today.
        yesterday_day = datetime.now(UTC).date() - timedelta(days=1)
        yesterday_ts = datetime.now(UTC) - timedelta(days=1)
        closure.business_date = yesterday_day
        closure.closed_at = yesterday_ts
        for tx in db.execute(select(FinancialTransaction).order_by(FinancialTransaction.id.asc())).scalars().all():
            tx.created_at = yesterday_ts
        db.commit()

        return {
            "actor_id": int(actor.id),
            "product_id": int(product.id),
            "warehouse_item_id": int(wh_item.id),
            "baseline_closure_id": int(closure.id),
        }

    def _run_cold_start_script(self, db_path: Path) -> subprocess.CompletedProcess[str]:
        script = r"""
import asyncio
import json

from sqlalchemy import select

import main
from app.database import SessionLocal
from app.enums import OrderStatus, PaymentStatus
from app.models import FinancialTransaction, Order, OrderItem, Product, ShiftClosure, User

async def run():
    async with main.app.router.lifespan_context(main.app):
        db = SessionLocal()
        try:
            manager = db.execute(select(User).where(User.username == "p7_finance_manager")).scalar_one()
            product = db.execute(select(Product).where(Product.name == "P7 Integrity Burger")).scalar_one()
            previous = db.execute(select(ShiftClosure).order_by(ShiftClosure.business_date.desc(), ShiftClosure.id.desc())).scalar_one()

            new_order = Order(
                type="takeaway",
                status=OrderStatus.READY.value,
                subtotal=10.0,
                delivery_fee=0.0,
                total=10.0,
                payment_status=PaymentStatus.UNPAID.value,
                payment_method="cash",
            )
            db.add(new_order)
            db.flush()
            db.add(
                OrderItem(
                    order_id=int(new_order.id),
                    product_id=int(product.id),
                    quantity=1,
                    price=10.0,
                    product_name=product.name,
                )
            )
            db.commit()

            transition_order(
                db,
                order_id=int(new_order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(manager.id),
                collect_payment=True,
                amount_received=10.0,
            )
            closure = close_cash_shift(
                db,
                closed_by=int(manager.id),
                opening_cash=0.0,
                actual_cash=10.0,
                note="P7 cold-start closure",
            )
            db.commit()

            from sqlalchemy import func
            sale_count_today = int(
                db.execute(
                    select(func.count(FinancialTransaction.id)).where(
                        FinancialTransaction.order_id == int(new_order.id),
                        FinancialTransaction.type == "sale",
                    )
                ).scalar_one()
                or 0
            )
            payload = {
                "previous_business_date": previous.business_date.isoformat(),
                "new_business_date": closure.business_date.isoformat(),
                "new_closure_expected_cash": float(closure.expected_cash or 0.0),
                "new_closure_transactions_count": int(closure.transactions_count or 0),
                "new_sale_tx_count": sale_count_today,
            }
            print(json.dumps(payload, ensure_ascii=True))
        finally:
            db.close()

asyncio.run(run())
"""
        env = os.environ.copy()
        env["APP_ENV"] = "production"
        env["JWT_SECRET"] = "phase7-cold-start-production-secret-0123456789abcdef0123456789"
        env["SECRET_KEY"] = "phase7-cold-start-prod-secret-key-0123456789abcdef0123456789"
        env["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_backup_restore_reconciliation_and_cold_start_chain(self) -> None:
        src_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        bkp_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        rst_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        src_tmp.close()
        bkp_tmp.close()
        rst_tmp.close()
        source_db = Path(src_tmp.name)
        backup_db = Path(bkp_tmp.name)
        restored_db = Path(rst_tmp.name)

        try:
            db, engine = self._build_migrated_session(source_db)
            try:
                self._seed_financial_baseline(db)
                baseline_snapshot = self._reconciliation_snapshot(db)
            finally:
                db.close()
                engine.dispose()

            source_checksum = self._sha256_file(source_db)
            shutil.copy2(source_db, backup_db)
            backup_checksum = self._sha256_file(backup_db)
            self.assertEqual(source_checksum, backup_checksum, msg="backup checksum mismatch against source")

            shutil.copy2(backup_db, restored_db)
            restored_checksum = self._sha256_file(restored_db)
            self.assertEqual(backup_checksum, restored_checksum, msg="restore checksum mismatch against backup")

            restore_upgrade = self._run_alembic_upgrade(restored_db)
            self.assertEqual(
                restore_upgrade.returncode,
                0,
                msg=(
                    "restored database migration-to-head failed:\n"
                    f"STDOUT:\n{restore_upgrade.stdout}\nSTDERR:\n{restore_upgrade.stderr}"
                ),
            )

            restored_session, restored_engine = self._build_migrated_session(restored_db)
            try:
                restored_snapshot = self._reconciliation_snapshot(restored_session)
                self.assertEqual(
                    baseline_snapshot["cash_total"],
                    restored_snapshot["cash_total"],
                    msg="cash reconciliation mismatch after restore",
                )
                self.assertEqual(
                    baseline_snapshot["tx_count"],
                    restored_snapshot["tx_count"],
                    msg="financial transaction count mismatch after restore",
                )
                self.assertEqual(
                    baseline_snapshot["stock_balance_total"],
                    restored_snapshot["stock_balance_total"],
                    msg="stock balance mismatch after restore",
                )
                self.assertEqual(
                    baseline_snapshot["stock_ledger_count"],
                    restored_snapshot["stock_ledger_count"],
                    msg="warehouse movement count mismatch after restore",
                )
                self.assertEqual(
                    baseline_snapshot["audit_count"],
                    restored_snapshot["audit_count"],
                    msg="audit rows mismatch after restore",
                )
                self.assertEqual(
                    baseline_snapshot["critical_hash"],
                    restored_snapshot["critical_hash"],
                    msg="critical-state hash mismatch after restore",
                )

                # Financial smoke suite on restored DB (read-only assertions).
                sale_total = float(
                    restored_session.execute(
                        select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                            FinancialTransaction.type == FinancialTransactionType.SALE.value
                        )
                    ).scalar_one()
                    or 0.0
                )
                refund_total = float(
                    restored_session.execute(
                        select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                            FinancialTransaction.type == FinancialTransactionType.REFUND.value
                        )
                    ).scalar_one()
                    or 0.0
                )
                closure_count = int(restored_session.execute(select(func.count(ShiftClosure.id))).scalar_one() or 0)
                self.assertAlmostEqual(sale_total, 30.0, places=2)
                self.assertAlmostEqual(refund_total, 10.0, places=2)
                self.assertEqual(closure_count, 1)
            finally:
                restored_session.close()
                restored_engine.dispose()

            cold_start = self._run_cold_start_script(restored_db)
            self.assertEqual(
                cold_start.returncode,
                0,
                msg=f"cold start flow failed:\nSTDOUT:\n{cold_start.stdout}\nSTDERR:\n{cold_start.stderr}",
            )
            cold_result = None
            for line in reversed([ln.strip() for ln in cold_start.stdout.splitlines() if ln.strip()]):
                if line.startswith("{") and line.endswith("}"):
                    cold_result = json.loads(line)
                    break
            self.assertIsNotNone(cold_result, msg=f"cold start JSON result missing in stdout:\n{cold_start.stdout}")
            assert cold_result is not None
            self.assertLess(cold_result["previous_business_date"], cold_result["new_business_date"])
            self.assertAlmostEqual(float(cold_result["new_closure_expected_cash"]), 10.0, places=2)
            self.assertEqual(int(cold_result["new_closure_transactions_count"]), 1)
            self.assertEqual(int(cold_result["new_sale_tx_count"]), 1)
        finally:
            for path in (source_db, backup_db, restored_db):
                if path.exists():
                    path.unlink()

    def test_corrupted_restore_fails_migration_and_cold_start(self) -> None:
        src_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        bkp_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        bad_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        src_tmp.close()
        bkp_tmp.close()
        bad_tmp.close()
        source_db = Path(src_tmp.name)
        backup_db = Path(bkp_tmp.name)
        corrupt_db = Path(bad_tmp.name)

        try:
            db, engine = self._build_migrated_session(source_db)
            try:
                self._seed_financial_baseline(db)
            finally:
                db.close()
                engine.dispose()

            shutil.copy2(source_db, backup_db)
            raw = backup_db.read_bytes()
            self.assertGreater(len(raw), 1024, msg="backup file unexpectedly small")
            corrupt_db.write_bytes(raw[:512])

            corrupted_upgrade = self._run_alembic_upgrade(corrupt_db)
            self.assertNotEqual(corrupted_upgrade.returncode, 0, msg="corrupted restore unexpectedly migrated")
            combined_upgrade_output = f"{corrupted_upgrade.stdout}\n{corrupted_upgrade.stderr}".lower()
            self.assertTrue(
                any(marker in combined_upgrade_output for marker in ("malformed", "not a database", "database disk image")),
                msg=(
                    "corrupted restore did not fail with clear DB integrity signal:\n"
                    f"{corrupted_upgrade.stdout}\n{corrupted_upgrade.stderr}"
                ),
            )

            cold_start_fail = self._run_cold_start_script(corrupt_db)
            self.assertNotEqual(cold_start_fail.returncode, 0, msg="cold start unexpectedly succeeded on corrupt restore")
            combined_cold_output = f"{cold_start_fail.stdout}\n{cold_start_fail.stderr}".lower()
            self.assertTrue(
                any(marker in combined_cold_output for marker in ("malformed", "not a database", "production startup blocked")),
                msg=(
                    "cold start failure message is not explicit enough for corrupted restore:\n"
                    f"{cold_start_fail.stdout}\n{cold_start_fail.stderr}"
                ),
            )
        finally:
            for path in (source_db, backup_db, corrupt_db):
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
