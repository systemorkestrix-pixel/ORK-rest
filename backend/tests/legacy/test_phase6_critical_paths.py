import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase6-critical-path-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.enums import FinancialTransactionType, OrderStatus, PaymentStatus
from app.models import (
    Expense,
    ExpenseCostCenter,
    FinancialTransaction,
    Order,
    RefreshToken,
    SystemAuditLog,
    User,
)
from app.security import hash_password
from application.core_engine.domain.auth import issue_tokens, refresh_user_tokens
from application.financial_engine.domain.collections import collect_order_payment as _collect_order_payment
from application.financial_engine.domain.expenses import (
    approve_expense,
    create_expense,
    reject_expense,
)
from application.financial_engine.domain.shifts import close_cash_shift as _close_cash_shift
from application.intelligence_engine.domain.reports import financial_snapshot
from application.operations_engine.domain.helpers import get_order_or_404


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


def collect_order_payment(
    db,
    *,
    order_id: int,
    collected_by: int,
    amount_received: float | None,
):
    return _collect_order_payment(
        db,
        order_id=order_id,
        collected_by=collected_by,
        amount_received=amount_received,
        get_order=get_order_or_404,
    )


class Phase6CriticalPathTests(unittest.TestCase):
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

    def _create_user(self, db, *, username: str) -> User:
        user = User(
            name=f"User {username}",
            username=username,
            password_hash=hash_password("StrongPass123!"),
            role="manager",
            active=True,
        )
        db.add(user)
        db.flush()
        return user

    def _create_order(self, db, *, status: str, payment_status: str, total: float) -> Order:
        order = Order(
            type="takeaway",
            status=status,
            subtotal=total,
            delivery_fee=0.0,
            total=total,
            payment_status=payment_status,
            payment_method="cash",
        )
        db.add(order)
        db.flush()
        return order

    def test_collect_order_payment_posts_sale_and_blocks_duplicate(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="collector")
            order = self._create_order(
                db,
                status=OrderStatus.DELIVERED.value,
                payment_status=PaymentStatus.UNPAID.value,
                total=35.0,
            )
            db.commit()

            paid = collect_order_payment(
                db,
                order_id=int(order.id),
                collected_by=int(actor.id),
                amount_received=40.0,
            )
            self.assertEqual(paid.payment_status, PaymentStatus.PAID.value)
            self.assertAlmostEqual(float(paid.amount_received or 0.0), 40.0, places=2)
            self.assertAlmostEqual(float(paid.change_amount or 0.0), 5.0, places=2)

            sale_txs = db.execute(
                select(FinancialTransaction).where(
                    FinancialTransaction.order_id == int(order.id),
                    FinancialTransaction.type == FinancialTransactionType.SALE.value,
                )
            ).scalars().all()
            self.assertEqual(len(sale_txs), 1)
            self.assertAlmostEqual(float(sale_txs[0].amount), 35.0, places=2)

            audit = db.execute(
                select(SystemAuditLog).where(
                    SystemAuditLog.action == "collect_order_payment",
                    SystemAuditLog.entity_type == "order",
                    SystemAuditLog.entity_id == int(order.id),
                )
            ).scalar_one_or_none()
            self.assertIsNotNone(audit)

            with self.assertRaises(HTTPException) as second_collect:
                collect_order_payment(
                    db,
                    order_id=int(order.id),
                    collected_by=int(actor.id),
                    amount_received=40.0,
                )
            self.assertEqual(second_collect.exception.status_code, 400)
            db.rollback()

            sale_count_after_retry = db.execute(
                select(FinancialTransaction).where(
                    FinancialTransaction.order_id == int(order.id),
                    FinancialTransaction.type == FinancialTransactionType.SALE.value,
                )
            ).scalars().all()
            self.assertEqual(len(sale_count_after_retry), 1)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_collect_order_payment_requires_delivered_order(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="collector_blocked")
            order = self._create_order(
                db,
                status=OrderStatus.READY.value,
                payment_status=PaymentStatus.UNPAID.value,
                total=25.0,
            )
            db.commit()

            with self.assertRaises(HTTPException) as context:
                collect_order_payment(
                    db,
                    order_id=int(order.id),
                    collected_by=int(actor.id),
                    amount_received=25.0,
                )
            self.assertEqual(context.exception.status_code, 400)
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_expense_approval_and_rejection_affect_financial_ledger(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="expense_actor")
            center = ExpenseCostCenter(code="OPS", name="Operations", active=True)
            db.add(center)
            db.commit()

            expense = create_expense(
                db,
                title="Generator Fuel",
                category="utilities",
                cost_center_id=int(center.id),
                amount=120.0,
                note="night shift",
                created_by=int(actor.id),
            )
            approved = approve_expense(
                db,
                expense_id=int(expense.id),
                approved_by=int(actor.id),
                note="approved",
            )
            self.assertEqual(approved.status, "approved")

            expense_tx = db.execute(
                select(FinancialTransaction).where(
                    FinancialTransaction.expense_id == int(expense.id),
                    FinancialTransaction.type == FinancialTransactionType.EXPENSE.value,
                )
            ).scalars().all()
            self.assertEqual(len(expense_tx), 1)
            self.assertAlmostEqual(float(expense_tx[0].amount), 120.0, places=2)

            with self.assertRaises(HTTPException) as reject_approved:
                reject_expense(
                    db,
                    expense_id=int(expense.id),
                    rejected_by=int(actor.id),
                    note="should fail",
                )
            self.assertEqual(reject_approved.exception.status_code, 400)
            db.rollback()

            expense_to_reject = create_expense(
                db,
                title="Unplanned Purchase",
                category="operations",
                cost_center_id=int(center.id),
                amount=35.0,
                note=None,
                created_by=int(actor.id),
            )
            db.add(
                FinancialTransaction(
                    expense_id=int(expense_to_reject.id),
                    amount=35.0,
                    type=FinancialTransactionType.EXPENSE.value,
                    created_by=int(actor.id),
                    note="pending expense transaction",
                )
            )
            db.commit()

            rejected = reject_expense(
                db,
                expense_id=int(expense_to_reject.id),
                rejected_by=int(actor.id),
                note="rejected",
            )
            self.assertEqual(rejected.status, "rejected")

            rejected_tx = db.execute(
                select(FinancialTransaction).where(
                    FinancialTransaction.expense_id == int(expense_to_reject.id),
                    FinancialTransaction.type == FinancialTransactionType.EXPENSE.value,
                )
            ).scalars().all()
            self.assertEqual(len(rejected_tx), 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_close_cash_shift_computes_expected_cash_and_blocks_duplicate(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="shift_manager")
            order = self._create_order(
                db,
                status=OrderStatus.DELIVERED.value,
                payment_status=PaymentStatus.PAID.value,
                total=100.0,
            )
            center = ExpenseCostCenter(code="ADM", name="Admin", active=True)
            db.add(center)
            db.flush()
            expense = Expense(
                title="Utilities",
                category="ops",
                amount=15.0,
                cost_center_id=int(center.id),
                status="approved",
                created_by=int(actor.id),
                reviewed_by=int(actor.id),
                reviewed_at=datetime.now(UTC),
            )
            db.add(expense)
            db.flush()

            db.add_all(
                [
                    FinancialTransaction(
                        order_id=int(order.id),
                        amount=100.0,
                        type=FinancialTransactionType.SALE.value,
                        created_by=int(actor.id),
                    ),
                    FinancialTransaction(
                        order_id=int(order.id),
                        amount=20.0,
                        type=FinancialTransactionType.REFUND.value,
                        created_by=int(actor.id),
                    ),
                    FinancialTransaction(
                        expense_id=int(expense.id),
                        amount=15.0,
                        type=FinancialTransactionType.EXPENSE.value,
                        created_by=int(actor.id),
                    ),
                ]
            )
            db.commit()

            closure = close_cash_shift(
                db,
                closed_by=int(actor.id),
                opening_cash=50.0,
                actual_cash=115.0,
                note="end of day",
            )
            self.assertAlmostEqual(float(closure.sales_total), 100.0, places=2)
            self.assertAlmostEqual(float(closure.refunds_total), 20.0, places=2)
            self.assertAlmostEqual(float(closure.expenses_total), 15.0, places=2)
            self.assertAlmostEqual(float(closure.expected_cash), 115.0, places=2)
            self.assertAlmostEqual(float(closure.variance), 0.0, places=2)
            self.assertEqual(int(closure.transactions_count), 3)

            with self.assertRaises(HTTPException) as duplicate_close:
                close_cash_shift(
                    db,
                    closed_by=int(actor.id),
                    opening_cash=50.0,
                    actual_cash=115.0,
                    note="retry",
                )
            self.assertEqual(duplicate_close.exception.status_code, 400)
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_refresh_token_rotation_revokes_previous_refresh_token(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            user = self._create_user(db, username="token_user")
            db.commit()

            _access, refresh = issue_tokens(db, user)
            db.commit()

            refreshed_user, _next_access, next_refresh = refresh_user_tokens(db, refresh)
            self.assertEqual(int(refreshed_user.id), int(user.id))
            self.assertNotEqual(refresh, next_refresh)

            with self.assertRaises(HTTPException) as reused:
                refresh_user_tokens(db, refresh)
            self.assertEqual(reused.exception.status_code, 401)
            db.rollback()

            active_sessions = db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == int(user.id),
                    RefreshToken.revoked_at.is_(None),
                )
            ).scalars().all()
            self.assertEqual(len(active_sessions), 1)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()

