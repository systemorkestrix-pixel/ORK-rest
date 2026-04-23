import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

MASTER_DB_HANDLE = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
MASTER_DB_HANDLE.close()
MASTER_DB_PATH = Path(MASTER_DB_HANDLE.name)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "production"
os.environ["EXPOSE_DIAGNOSTIC_ENDPOINTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{MASTER_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "phase9-base-closure-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-base-closure-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"

import main
from app.database import SessionLocal, engine
from app.models import MasterClient, MasterTenant
from app.security import create_access_token


class Phase9BaseClosureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        migrated = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        if migrated.returncode != 0:
            raise AssertionError(
                "alembic upgrade failed for base closure contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

        db = SessionLocal()
        try:
            client = MasterClient(
                owner_name="Base Closure Owner",
                brand_name="Base Closure Client",
                phone="0555000000",
                city="Algiers",
                active_plan_id="base",
                subscription_state="active",
            )
            db.add(client)
            db.flush()
            db.add(
                MasterTenant(
                    client_id=int(client.id),
                    code="phase9_base",
                    brand_name="Base Closure Tenant",
                    database_name="phase9_base_runtime",
                    manager_username="phase9_manager",
                    environment_state="active",
                    plan_id="base",
                    paused_addons_json="[]",
                )
            )
            db.commit()
        finally:
            db.close()

        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def test_root_and_health_follow_render_contract(self) -> None:
        root_response = self.client.get("/")
        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(
            root_response.json(),
            {
                "status": "ok",
                "service": "restaurants-api",
                "entry": "/manager/login",
            },
        )

        health_response = self.client.get("/health")
        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

    def test_public_tenant_entry_remains_the_only_unscoped_public_entry(self) -> None:
        response = self.client.get("/api/public/tenant-entry", params={"tenant": "phase9-base"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["tenant_code"], "phase9_base")
        self.assertEqual(payload["manager_login_path"], "/t/phase9_base/manager/login")
        self.assertEqual(payload["public_order_path"], "/t/phase9_base/order")
        self.assertEqual(payload["public_menu_path"], "/t/phase9_base/menu")

    def test_unscoped_public_api_rejects_requests_even_with_legacy_cookie_or_token(self) -> None:
        legacy_token = create_access_token(
            user_id=999,
            role="manager",
            username="legacy_manager",
            tenant_database="legacy_cookie_db",
        )
        cases = [
            {"label": "plain", "cookie": None, "auth": None},
            {"label": "legacy_cookie", "cookie": "legacy_cookie_db", "auth": None},
            {"label": "legacy_token", "cookie": None, "auth": f"Bearer {legacy_token}"},
            {"label": "legacy_cookie_and_token", "cookie": "legacy_cookie_db", "auth": f"Bearer {legacy_token}"},
        ]

        for case in cases:
            with self.subTest(case=case["label"]):
                self.client.cookies.clear()
                if case["cookie"]:
                    self.client.cookies.set("tenant_database", str(case["cookie"]))
                headers = {"Authorization": str(case["auth"])} if case["auth"] else {}
                response = self.client.get("/api/public/products", headers=headers)
                self.assertEqual(response.status_code, 404)
                self.assertIn("رابط المطعم المباشر", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
