import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase7-button-delete-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.enums import FinancialTransactionType
from app.models import (
    Expense,
    ExpenseAttachment,
    ExpenseCostCenter,
    FinancialTransaction,
    Order,
    Product,
    ProductCategory,
    RestaurantTable,
    User,
)
from app.security import hash_password
from application.core_engine.domain.users import delete_user_permanently
from application.financial_engine.domain.expenses import delete_expense, delete_expense_attachment
from application.inventory_engine.domain.catalog import (
    archive_product as archive_product_service,
    delete_product_category as delete_product_category_service,
)
from application.operations_engine.domain.table_sessions import delete_table as delete_table_service


class Phase7ButtonDeleteIntegrityTests(unittest.TestCase):
    def _build_migrated_session(self) -> tuple[Session, object, Path]:
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

    def _create_user(
        self,
        db: Session,
        *,
        username: str,
        role: str = "manager",
        active: bool = True,
    ) -> User:
        user = User(
            name=f"User {username}",
            username=username,
            password_hash=hash_password("StrongPass123!"),
            role=role,
            active=active,
        )
        db.add(user)
        db.flush()
        return user

    def test_delete_table_rejects_when_orders_exist(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            table = RestaurantTable(qr_code="/menu?table=10", status="available")
            db.add(table)
            db.flush()
            db.add(
                Order(
                    type="dine-in",
                    status="created",
                    table_id=int(table.id),
                    subtotal=20.0,
                    delivery_fee=0.0,
                    total=20.0,
                    payment_status="unpaid",
                    payment_method="cash",
                )
            )
            db.commit()

            with self.assertRaises(HTTPException) as delete_error:
                delete_table_service(db, table_id=int(table.id))
            self.assertEqual(delete_error.exception.status_code, 400)
            db.rollback()

            still_exists = db.execute(
                select(RestaurantTable).where(RestaurantTable.id == int(table.id))
            ).scalar_one_or_none()
            self.assertIsNotNone(still_exists)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delete_table_succeeds_without_orders(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            table = RestaurantTable(qr_code="/menu?table=11", status="available")
            db.add(table)
            db.commit()
            table_id = int(table.id)

            delete_table_service(db, table_id=table_id)

            deleted = db.execute(
                select(RestaurantTable).where(RestaurantTable.id == table_id)
            ).scalar_one_or_none()
            self.assertIsNone(deleted)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delete_category_rejects_when_products_linked(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            category = ProductCategory(name="Test Category", active=True, sort_order=0)
            db.add(category)
            db.flush()
            db.add(
                Product(
                    name="Linked Product",
                    description=None,
                    price=12.5,
                    available=True,
                    kind="sellable",
                    category=category.name,
                    category_id=int(category.id),
                    is_archived=False,
                )
            )
            db.commit()

            with self.assertRaises(HTTPException) as delete_error:
                delete_product_category_service(db, category_id=int(category.id))
            self.assertEqual(delete_error.exception.status_code, 400)
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_archive_product_sets_archived_and_unavailable(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            category = ProductCategory(name="Archive Category", active=True, sort_order=1)
            db.add(category)
            db.flush()
            product = Product(
                name="Archive Target",
                description=None,
                price=10.0,
                available=True,
                kind="sellable",
                category=category.name,
                category_id=int(category.id),
                is_archived=False,
            )
            db.add(product)
            db.commit()
            product_id = int(product.id)

            archive_product_service(db, product_id=product_id)

            refreshed = db.execute(select(Product).where(Product.id == product_id)).scalar_one()
            self.assertTrue(bool(refreshed.is_archived))
            self.assertFalse(bool(refreshed.available))
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delete_expense_rejects_when_approved(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="expense_approver")
            center = ExpenseCostCenter(code="OPS", name="Operations", active=True)
            db.add(center)
            db.flush()
            expense = Expense(
                title="Approved Expense",
                category="operations",
                amount=30.0,
                note=None,
                cost_center_id=int(center.id),
                status="approved",
                created_by=int(actor.id),
            )
            db.add(expense)
            db.commit()

            with self.assertRaises(HTTPException) as delete_error:
                delete_expense(db, expense_id=int(expense.id))
            self.assertEqual(delete_error.exception.status_code, 400)
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delete_expense_removes_attachments_and_financial_rows(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="expense_creator")
            center = ExpenseCostCenter(code="HR", name="HR", active=True)
            db.add(center)
            db.flush()
            expense = Expense(
                title="Pending Expense",
                category="operations",
                amount=44.0,
                note="cleanup",
                cost_center_id=int(center.id),
                status="pending",
                created_by=int(actor.id),
            )
            db.add(expense)
            db.flush()
            db.add(
                ExpenseAttachment(
                    expense_id=int(expense.id),
                    file_name="proof.pdf",
                    file_url="/static/expenses/nonexistent-proof.pdf",
                    mime_type="application/pdf",
                    size_bytes=100,
                    uploaded_by=int(actor.id),
                )
            )
            db.add(
                FinancialTransaction(
                    expense_id=int(expense.id),
                    amount=44.0,
                    type=FinancialTransactionType.EXPENSE.value,
                    created_by=int(actor.id),
                    note="pending expense tx",
                )
            )
            db.commit()
            expense_id = int(expense.id)

            delete_expense(db, expense_id=expense_id)

            deleted_expense = db.execute(select(Expense).where(Expense.id == expense_id)).scalar_one_or_none()
            attachment_rows = db.execute(
                select(ExpenseAttachment).where(ExpenseAttachment.expense_id == expense_id)
            ).scalars().all()
            tx_rows = db.execute(
                select(FinancialTransaction).where(FinancialTransaction.expense_id == expense_id)
            ).scalars().all()
            self.assertIsNone(deleted_expense)
            self.assertEqual(len(attachment_rows), 0)
            self.assertEqual(len(tx_rows), 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delete_expense_attachment_rejects_when_expense_approved(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="attachment_actor")
            center = ExpenseCostCenter(code="QA", name="Quality", active=True)
            db.add(center)
            db.flush()
            expense = Expense(
                title="Approved With Attachment",
                category="operations",
                amount=10.0,
                note=None,
                cost_center_id=int(center.id),
                status="approved",
                created_by=int(actor.id),
            )
            db.add(expense)
            db.flush()
            attachment = ExpenseAttachment(
                expense_id=int(expense.id),
                file_name="doc.pdf",
                file_url="/static/expenses/nonexistent-doc.pdf",
                mime_type="application/pdf",
                size_bytes=50,
                uploaded_by=int(actor.id),
            )
            db.add(attachment)
            db.commit()

            with self.assertRaises(HTTPException) as delete_error:
                delete_expense_attachment(
                    db,
                    expense_id=int(expense.id),
                    attachment_id=int(attachment.id),
                    deleted_by=int(actor.id),
                )
            self.assertEqual(delete_error.exception.status_code, 400)
            db.rollback()
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_delete_user_rejects_self_and_allows_unreferenced_user(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = self._create_user(db, username="main_manager", role="manager", active=True)
            second_manager = self._create_user(db, username="backup_manager", role="manager", active=True)
            target = self._create_user(db, username="temp_delivery", role="delivery", active=False)
            db.commit()

            with self.assertRaises(HTTPException) as self_delete_error:
                delete_user_permanently(db, user_id=int(actor.id), actor_id=int(actor.id))
            self.assertEqual(self_delete_error.exception.status_code, 400)
            db.rollback()

            delete_user_permanently(db, user_id=int(target.id), actor_id=int(actor.id))
            removed = db.execute(select(User).where(User.id == int(target.id))).scalar_one_or_none()
            keep_actor = db.execute(select(User).where(User.id == int(actor.id))).scalar_one_or_none()
            keep_second = db.execute(select(User).where(User.id == int(second_manager.id))).scalar_one_or_none()
            self.assertIsNone(removed)
            self.assertIsNotNone(keep_actor)
            self.assertIsNotNone(keep_second)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
