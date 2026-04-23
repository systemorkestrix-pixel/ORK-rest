import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase4-actor-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.enums import OrderType, ProductKind, UserRole
from app.database import create_app_engine
from app.models import OrderTransitionLog, Product, ProductCategory, User
from app.routers.manager import list_users as manager_list_users
from app.schemas import CreateOrderInput, CreateOrderItemInput
from app.repositories.orders_repository import fetch_available_sellable_products
from app.security import hash_password
from app.tx import transaction_scope
from application.core_engine.domain.settings import (
    get_delivery_fee_setting,
    get_delivery_policy_settings,
)
from application.operations_engine.domain.constants import SYSTEM_ORDER_ACTOR_PREFIX
from application.operations_engine.domain.helpers import record_transition
from application.operations_engine.domain.operational import (
    ensure_delivery_operational,
    resolve_order_creator_id,
)
from application.operations_engine.domain.orders import create_order as _create_order
from application.operations_engine.domain.table_sessions import get_table_or_404


def create_order(
    db,
    *,
    payload,
    created_by: int | None = None,
    source_actor: str = "system",
):
    def _resolve_creator(db, created_by: int | None, fallback_actor: str) -> int | None:
        return resolve_order_creator_id(
            db,
            created_by,
            fallback_actor=fallback_actor,
            transaction_scope=transaction_scope,
            hash_password=hash_password,
        )

    with transaction_scope(db):
        return _create_order(
            db,
            payload=payload,
            created_by=created_by,
            source_actor=source_actor,
            ensure_delivery_operational=ensure_delivery_operational,
            fetch_products=fetch_available_sellable_products,
            get_table=get_table_or_404,
            resolve_order_creator_id=_resolve_creator,
            get_delivery_policy_settings=get_delivery_policy_settings,
            get_delivery_fee_setting=get_delivery_fee_setting,
            record_transition=record_transition,
        )


class Phase4ActorAttributionTests(unittest.TestCase):
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

    def test_public_order_actor_not_assigned_to_default_manager(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            manager = User(
                name="Main Manager",
                username="manager_main",
                password_hash="$argon2id$seed",
                role=UserRole.MANAGER.value,
                active=True,
            )
            db.add(manager)
            db.flush()

            category = ProductCategory(name="Meals", active=True, sort_order=0)
            db.add(category)
            db.flush()

            product = Product(
                name="Public Pizza",
                description="Public test product",
                price=12.0,
                available=True,
                kind=ProductKind.SELLABLE.value,
                category=category.name,
                category_id=category.id,
                is_archived=False,
            )
            db.add(product)
            db.commit()

            payload = CreateOrderInput(
                type=OrderType.TAKEAWAY,
                phone="0555000111",
                address=None,
                notes="Public order",
                items=[CreateOrderItemInput(product_id=int(product.id), quantity=1)],
            )
            order = create_order(db, payload=payload, source_actor="public")
            db.commit()

            transition = db.execute(
                select(OrderTransitionLog).where(OrderTransitionLog.order_id == int(order.id))
            ).scalar_one()
            actor_user = db.execute(select(User).where(User.id == int(transition.performed_by))).scalar_one()

            self.assertNotEqual(int(actor_user.id), int(manager.id))
            self.assertEqual(actor_user.username, "__actor__:public")
            self.assertFalse(bool(actor_user.active))

            visible_users = manager_list_users(page=1, page_size=50, _=manager, db=db)
            usernames = [user.username for user in visible_users]
            self.assertIn("manager_main", usernames)
            self.assertTrue(all(not username.startswith(SYSTEM_ORDER_ACTOR_PREFIX) for username in usernames))
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()


if __name__ == "__main__":
    unittest.main()
