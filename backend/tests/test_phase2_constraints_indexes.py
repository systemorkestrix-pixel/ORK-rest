import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase2-test-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.models import (
    Expense,
    ExpenseCostCenter,
    FinancialTransaction,
    Order,
    Product,
    ShiftClosure,
    User,
)


class Phase2ConstraintsIndexesTests(unittest.TestCase):
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

    def _seed_actor(self, db) -> User:
        actor = User(
            name="Manager",
            username="manager_seed",
            password_hash="$argon2id$seed",
            role="manager",
            active=True,
        )
        db.add(actor)
        db.commit()
        db.refresh(actor)
        return actor

    def test_products_category_id_is_not_null(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            with self.assertRaises(IntegrityError):
                db.add(
                    Product(
                        name="Bad Product",
                        description=None,
                        price=10.0,
                        available=True,
                        kind="sellable",
                        category="عام",
                        category_id=None,
                        is_archived=False,
                    )
                )
                db.commit()
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_shift_closure_business_date_is_unique(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._seed_actor(db)
            db.add(ShiftClosure(business_date=date(2026, 3, 1), closed_by=actor.id))
            db.commit()

            with self.assertRaises(IntegrityError):
                db.add(ShiftClosure(business_date=date(2026, 3, 1), closed_by=actor.id))
                db.commit()
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_financial_partial_unique_indexes_enforced(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._seed_actor(db)
            order = Order(
                type="takeaway",
                status="DELIVERED",
                subtotal=50.0,
                delivery_fee=0.0,
                total=50.0,
                payment_status="paid",
                payment_method="cash",
            )
            db.add(order)
            db.flush()

            center = ExpenseCostCenter(code="GEN", name="General", active=True)
            db.add(center)
            db.flush()
            expense = Expense(
                title="Gas",
                category="operational",
                amount=20.0,
                cost_center_id=center.id,
                status="approved",
                created_by=actor.id,
            )
            db.add(expense)
            db.flush()

            db.add(
                FinancialTransaction(
                    order_id=order.id,
                    amount=50.0,
                    type="sale",
                    created_by=actor.id,
                )
            )
            db.commit()

            with self.assertRaises(IntegrityError):
                db.add(
                    FinancialTransaction(
                        order_id=order.id,
                        amount=50.0,
                        type="sale",
                        created_by=actor.id,
                    )
                )
                db.commit()
            db.rollback()

            db.add(
                FinancialTransaction(
                    order_id=order.id,
                    amount=5.0,
                    type="refund",
                    created_by=actor.id,
                )
            )
            db.commit()

            with self.assertRaises(IntegrityError):
                db.add(
                    FinancialTransaction(
                        order_id=order.id,
                        amount=1.0,
                        type="refund",
                        created_by=actor.id,
                    )
                )
                db.commit()
            db.rollback()

            db.add(
                FinancialTransaction(
                    expense_id=expense.id,
                    amount=20.0,
                    type="expense",
                    created_by=actor.id,
                )
            )
            db.commit()

            with self.assertRaises(IntegrityError):
                db.add(
                    FinancialTransaction(
                        expense_id=expense.id,
                        amount=20.0,
                        type="expense",
                        created_by=actor.id,
                    )
                )
                db.commit()
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_critical_indexes_exist(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            index_rows = db.execute(text("PRAGMA index_list('orders')")).all()
            order_indexes = {row[1] for row in index_rows}
            self.assertIn("ix_orders_status_created_at", order_indexes)
            self.assertIn("ix_orders_table_status_created_at", order_indexes)

            tx_index_rows = db.execute(text("PRAGMA index_list('financial_transactions')")).all()
            tx_indexes = {row[1] for row in tx_index_rows}
            self.assertIn("ix_financial_transactions_type_created_at", tx_indexes)
            self.assertIn("ux_financial_transactions_sale_order", tx_indexes)
            self.assertIn("ux_financial_transactions_refund_order", tx_indexes)
            self.assertIn("ux_financial_transactions_expense_expense", tx_indexes)

            wh_event_index_rows = db.execute(text("PRAGMA index_list('wh_integration_events')")).all()
            wh_event_indexes = {row[1] for row in wh_event_index_rows}
            self.assertIn("ix_wh_integration_events_status_created_at", wh_event_indexes)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
