import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase7-prod-contract-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")


class Phase7ProductionContractTests(unittest.TestCase):
    def _run_python_script(self, *, script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    def _run_alembic_upgrade(self, db_path: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["DATABASE_PATH"] = db_path.as_posix()
        return subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    def _parse_last_json_line(self, output: str) -> dict[str, object]:
        for line in reversed([segment.strip() for segment in output.splitlines() if segment.strip()]):
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
        raise AssertionError(f"No JSON object found in output:\n{output}")

    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def test_production_runtime_contract_and_autogenerate_block(self) -> None:
        runtime_script = r"""
import json
from fastapi.middleware.cors import CORSMiddleware

import main
from app.config import load_settings

settings = load_settings()
cors_origins = []
for middleware in main.app.user_middleware:
    if middleware.cls is CORSMiddleware:
        cors_origins = list(middleware.kwargs.get("allow_origins", []))
        break

payload = {
    "debug": bool(main.app.debug),
    "settings_debug": bool(settings.debug),
    "secret_key_len": len(settings.secret_key),
    "allow_legacy_password_login": bool(settings.allow_legacy_password_login),
    "has_health": any(getattr(route, "path", "") == "/health" for route in main.app.routes),
    "docs_url": main.app.docs_url,
    "openapi_url": main.app.openapi_url,
    "cors_origins": cors_origins,
}
print(json.dumps(payload, ensure_ascii=True))
"""
        env = os.environ.copy()
        env["APP_ENV"] = "production"
        env["JWT_SECRET"] = "phase7-prod-runtime-jwt-secret-0123456789abcdef0123456789"
        env["SECRET_KEY"] = "phase7-prod-runtime-secret-key-0123456789abcdef0123456789"
        env["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
        env.pop("CORS_ALLOW_ORIGINS", None)
        runtime = self._run_python_script(script=runtime_script, env=env)
        self.assertEqual(
            runtime.returncode,
            0,
            msg=f"production runtime contract script failed:\nSTDOUT:\n{runtime.stdout}\nSTDERR:\n{runtime.stderr}",
        )
        payload = self._parse_last_json_line(runtime.stdout)
        self.assertFalse(bool(payload["debug"]))
        self.assertFalse(bool(payload["settings_debug"]))
        self.assertFalse(bool(payload["allow_legacy_password_login"]))
        self.assertGreaterEqual(int(payload["secret_key_len"]), 32)
        self.assertFalse(bool(payload["has_health"]))
        self.assertIsNone(payload["docs_url"])
        self.assertIsNone(payload["openapi_url"])
        self.assertEqual(payload["cors_origins"], [])

        temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        temp_db.close()
        versions_dir = BACKEND_DIR / "alembic" / "versions"
        before_files = {path.name for path in versions_dir.glob("*.py")}
        try:
            env_autogen = os.environ.copy()
            env_autogen["APP_ENV"] = "production"
            env_autogen["JWT_SECRET"] = "phase7-prod-autogen-jwt-secret-0123456789abcdef0123456789"
            env_autogen["SECRET_KEY"] = "phase7-prod-autogen-secret-key-0123456789abcdef0123456789"
            env_autogen["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
            env_autogen["DATABASE_PATH"] = Path(temp_db.name).as_posix()
            blocked = subprocess.run(
                [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "prod_autogen_block_probe"],
                cwd=BACKEND_DIR,
                env=env_autogen,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(blocked.returncode, 0, msg="autogenerate unexpectedly succeeded in production")
            combined = f"{blocked.stdout}\n{blocked.stderr}"
            self.assertIn("autogenerate is blocked in production", combined)
            after_files = {path.name for path in versions_dir.glob("*.py")}
            self.assertEqual(before_files, after_files, msg="autogenerate created migration artifact despite policy")
        finally:
            db_file = Path(temp_db.name)
            if db_file.exists():
                db_file.unlink()

    def test_financial_paths_have_no_print_or_debug_logging(self) -> None:
        services_dir = BACKEND_DIR / "app" / "services"
        for services_path in sorted(services_dir.glob("*.py")):
            source = services_path.read_text(encoding="utf-8")
            self.assertNotIn("print(", source, msg=f"print() found in {services_path.name}")
            self.assertNotIn("logging.debug(", source, msg=f"logging.debug() found in {services_path.name}")
            self.assertNotIn("logger.debug(", source, msg=f"logger.debug() found in {services_path.name}")

    def test_clean_environment_sequence_migrate_seed_sale_close_backup_restore_sale_close_shutdown(self) -> None:
        source_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        backup_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        restored_tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        source_tmp.close()
        backup_tmp.close()
        restored_tmp.close()
        source_db = Path(source_tmp.name)
        backup_db = Path(backup_tmp.name)
        restored_db = Path(restored_tmp.name)

        try:
            migrated = self._run_alembic_upgrade(source_db)
            self.assertEqual(
                migrated.returncode,
                0,
                msg=f"clean env migration failed:\nSTDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}",
            )

            first_boot_script = r"""
import asyncio
import json
import warnings
from datetime import UTC, datetime, timedelta

warnings.simplefilter("error", DeprecationWarning)

import main
from sqlalchemy import select
from app.database import SessionLocal
from app.enums import OrderStatus, PaymentStatus, ProductKind
from app.models import (
    FinancialTransaction,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    ShiftClosure,
    User,
    WarehouseItem,
    WarehouseStockBalance,
)
from application.financial_engine.domain.shifts import close_cash_shift as _close_cash_shift
from application.intelligence_engine.domain.reports import financial_snapshot
from application.operations_engine.domain.order_transitions import transition_order

def close_cash_shift(db, *, closed_by, opening_cash, actual_cash, note=None):
    return _close_cash_shift(
        db,
        closed_by=closed_by,
        opening_cash=opening_cash,
        actual_cash=actual_cash,
        note=note,
        financial_snapshot=financial_snapshot,
    )

async def run():
    async with main.app.router.lifespan_context(main.app):
        db = SessionLocal()
        try:
            actor = User(
                name="Clean Env Manager",
                username="clean_env_manager",
                password_hash="$argon2id$seed",
                role="manager",
                active=True,
            )
            db.add(actor)
            db.flush()

            category = ProductCategory(name="CleanEnv Meals", active=True, sort_order=0)
            db.add(category)
            db.flush()
            product = Product(
                name="CleanEnv Burger",
                description="clean env flow product",
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
                name="CleanEnv Bread",
                unit="piece",
                alert_threshold=0.0,
                active=True,
            )
            db.add(wh_item)
            db.flush()
            db.add(
                WarehouseStockBalance(
                    item_id=int(wh_item.id),
                    quantity=20.0,
                    avg_unit_cost=2.0,
                )
            )
            db.flush()

            order = Order(
                type="takeaway",
                status=OrderStatus.READY.value,
                subtotal=10.0,
                delivery_fee=0.0,
                total=10.0,
                payment_status=PaymentStatus.UNPAID.value,
                payment_method="cash",
            )
            db.add(order)
            db.flush()
            db.add(
                OrderItem(
                    order_id=int(order.id),
                    product_id=int(product.id),
                    quantity=1,
                    price=10.0,
                    product_name=product.name,
                )
            )
            db.commit()

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=True,
                amount_received=10.0,
            )
            closure = close_cash_shift(
                db,
                closed_by=int(actor.id),
                opening_cash=100.0,
                actual_cash=110.0,
                note="clean-env first close",
            )
            db.commit()

            yesterday_ts = datetime.now(UTC) - timedelta(days=1)
            closure.business_date = yesterday_ts.date()
            closure.closed_at = yesterday_ts
            for tx in db.execute(select(FinancialTransaction).order_by(FinancialTransaction.id.asc())).scalars().all():
                tx.created_at = yesterday_ts
            db.commit()

            payload = {
                "first_closure_id": int(closure.id),
                "first_business_date": closure.business_date.isoformat(),
            }
            print(json.dumps(payload, ensure_ascii=True))
        finally:
            db.close()

asyncio.run(run())
"""
            env_first = os.environ.copy()
            env_first["APP_ENV"] = "production"
            env_first["JWT_SECRET"] = "phase7-clean-first-jwt-secret-0123456789abcdef0123456789"
            env_first["SECRET_KEY"] = "phase7-clean-first-secret-key-0123456789abcdef0123456789"
            env_first["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
            env_first["DATABASE_PATH"] = source_db.as_posix()
            first_boot = self._run_python_script(script=first_boot_script, env=env_first)
            self.assertEqual(
                first_boot.returncode,
                0,
                msg=f"clean env first boot flow failed:\nSTDOUT:\n{first_boot.stdout}\nSTDERR:\n{first_boot.stderr}",
            )
            first_payload = self._parse_last_json_line(first_boot.stdout)
            self.assertIn("first_closure_id", first_payload)

            source_checksum = self._sha256_file(source_db)
            shutil.copy2(source_db, backup_db)
            backup_checksum = self._sha256_file(backup_db)
            self.assertEqual(source_checksum, backup_checksum, msg="backup checksum mismatch")

            shutil.copy2(backup_db, restored_db)
            restored_checksum = self._sha256_file(restored_db)
            self.assertEqual(backup_checksum, restored_checksum, msg="restore checksum mismatch")

            restored_migrate = self._run_alembic_upgrade(restored_db)
            self.assertEqual(
                restored_migrate.returncode,
                0,
                msg=(
                    "restored migration failed:\n"
                    f"STDOUT:\n{restored_migrate.stdout}\nSTDERR:\n{restored_migrate.stderr}"
                ),
            )

            second_boot_script = r"""
import asyncio
import json
import warnings

warnings.simplefilter("error", DeprecationWarning)

import main
from sqlalchemy import select
from app.database import SessionLocal
from app.enums import OrderStatus, PaymentStatus
from app.models import Order, OrderItem, Product, ShiftClosure, User, FinancialTransaction
from sqlalchemy import func
from application.financial_engine.domain.shifts import close_cash_shift as _close_cash_shift
from application.intelligence_engine.domain.reports import financial_snapshot
from application.operations_engine.domain.order_transitions import transition_order

def close_cash_shift(db, *, closed_by, opening_cash, actual_cash, note=None):
    return _close_cash_shift(
        db,
        closed_by=closed_by,
        opening_cash=opening_cash,
        actual_cash=actual_cash,
        note=note,
        financial_snapshot=financial_snapshot,
    )

async def run():
    async with main.app.router.lifespan_context(main.app):
        db = SessionLocal()
        try:
            actor = db.execute(select(User).where(User.username == "clean_env_manager")).scalar_one()
            product = db.execute(select(Product).where(Product.name == "CleanEnv Burger")).scalar_one()
            previous = db.execute(
                select(ShiftClosure).order_by(ShiftClosure.business_date.desc(), ShiftClosure.id.desc())
            ).scalar_one()

            order = Order(
                type="takeaway",
                status=OrderStatus.READY.value,
                subtotal=10.0,
                delivery_fee=0.0,
                total=10.0,
                payment_status=PaymentStatus.UNPAID.value,
                payment_method="cash",
            )
            db.add(order)
            db.flush()
            db.add(
                OrderItem(
                    order_id=int(order.id),
                    product_id=int(product.id),
                    quantity=1,
                    price=10.0,
                    product_name=product.name,
                )
            )
            db.commit()

            transition_order(
                db,
                order_id=int(order.id),
                target_status=OrderStatus.DELIVERED,
                performed_by=int(actor.id),
                collect_payment=True,
                amount_received=10.0,
            )
            closure = close_cash_shift(
                db,
                closed_by=int(actor.id),
                opening_cash=0.0,
                actual_cash=10.0,
                note="clean-env second close",
            )
            db.commit()

            sale_tx_count = int(
                db.execute(
                    select(func.count(FinancialTransaction.id)).where(
                        FinancialTransaction.order_id == int(order.id),
                        FinancialTransaction.type == "sale",
                    )
                ).scalar_one()
                or 0
            )
            payload = {
                "previous_business_date": previous.business_date.isoformat(),
                "new_business_date": closure.business_date.isoformat(),
                "new_closure_id": int(closure.id),
                "new_sale_tx_count": sale_tx_count,
            }
            print(json.dumps(payload, ensure_ascii=True))
        finally:
            db.close()

asyncio.run(run())
"""
            env_second = os.environ.copy()
            env_second["APP_ENV"] = "production"
            env_second["JWT_SECRET"] = "phase7-clean-second-jwt-secret-0123456789abcdef0123456789"
            env_second["SECRET_KEY"] = "phase7-clean-second-secret-key-0123456789abcdef0123456789"
            env_second["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
            env_second["DATABASE_PATH"] = restored_db.as_posix()
            second_boot = self._run_python_script(script=second_boot_script, env=env_second)
            self.assertEqual(
                second_boot.returncode,
                0,
                msg=f"clean env second boot flow failed:\nSTDOUT:\n{second_boot.stdout}\nSTDERR:\n{second_boot.stderr}",
            )
            second_payload = self._parse_last_json_line(second_boot.stdout)
            self.assertLess(second_payload["previous_business_date"], second_payload["new_business_date"])
            self.assertEqual(int(second_payload["new_sale_tx_count"]), 1)
        finally:
            for path in (source_db, backup_db, restored_db):
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
