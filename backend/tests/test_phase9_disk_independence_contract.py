import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

MASTER_DB_HANDLE = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
MASTER_DB_HANDLE.close()
MASTER_DB_PATH = Path(MASTER_DB_HANDLE.name)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "production"
os.environ["EXPOSE_DIAGNOSTIC_ENDPOINTS"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{MASTER_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "phase9-disk-audit-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-disk-audit-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
os.environ["MEDIA_STORAGE_BACKEND"] = "supabase_storage"
os.environ["MEDIA_STORAGE_BUCKET"] = "restaurants-media"
os.environ["MEDIA_STORAGE_PROJECT_URL"] = "https://example-project.supabase.co"
os.environ["MEDIA_STORAGE_PUBLIC_BASE_URL"] = (
    "https://example-project.supabase.co/storage/v1/object/public/restaurants-media"
)
os.environ["MEDIA_STORAGE_SERVICE_ROLE_KEY"] = "phase9-supabase-storage-service-role-key"

from app.database import SessionLocal, engine
from app.master_tenant_runtime_contract import (
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
    MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
)
from app.models import MasterClient, MasterTenant
from application.master_engine.domain.deployment_disk_audit import (
    audit_deployment_disk_dependence,
    is_local_media_reference,
)
from application.master_engine.domain.registry import create_master_tenant


class Phase9DiskIndependenceContractTests(unittest.TestCase):
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
                "alembic upgrade failed for phase 9 disk independence contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def test_new_tenant_creation_inherits_configured_remote_media_backend(self) -> None:
        db = SessionLocal()
        fake_target = SimpleNamespace()
        try:
            with patch(
                "application.master_engine.domain.registry.provision_tenant_database",
                return_value=fake_target,
            ), patch(
                "application.master_engine.domain.registry.SETTINGS",
                new=SimpleNamespace(media_storage_backend=MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE),
            ):
                result = create_master_tenant(
                    db,
                    client_mode="new",
                    existing_client_id=None,
                    client_owner_name="Owner Phase9",
                    client_brand_name="Brand Phase9",
                    client_phone="0555000030",
                    client_city="Algiers",
                    tenant_brand_name="Tenant Phase9",
                    tenant_code="phase9_disk_safe",
                    database_name="phase9_disk_safe",
                )
        finally:
            db.close()

        self.assertEqual(
            result["tenant"]["media_storage_backend"],
            MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
        )

    def test_audit_blocks_when_any_tenant_still_depends_on_local_disk(self) -> None:
        db = SessionLocal()
        try:
            client = MasterClient(
                owner_name="Phase9 Audit Owner",
                brand_name="Phase9 Audit Client",
                phone="0555000031",
                city="Algiers",
                active_plan_id="base",
                subscription_state="active",
            )
            db.add(client)
            db.flush()
            db.add_all(
                [
                    MasterTenant(
                        client_id=int(client.id),
                        code="phase9_local",
                        brand_name="Phase9 Local Tenant",
                        database_name="tenant_phase9_local",
                        manager_username="phase9_local.manager",
                        environment_state="ready",
                        plan_id="base",
                        paused_addons_json="[]",
                        runtime_storage_backend="sqlite_file",
                        media_storage_backend=MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC,
                    ),
                    MasterTenant(
                        client_id=int(client.id),
                        code="phase9_remote",
                        brand_name="Phase9 Remote Tenant",
                        database_name="tenant_phase9_remote",
                        manager_username="phase9_remote.manager",
                        environment_state="ready",
                        plan_id="base",
                        paused_addons_json="[]",
                        runtime_storage_backend="postgres_schema",
                        media_storage_backend=MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
                    ),
                ]
            )
            db.commit()

            with patch(
                "application.master_engine.domain.deployment_disk_audit.inspect_tenant_runtime_local_media_references",
                side_effect=[(2, 1), (0, 0)],
            ):
                report = audit_deployment_disk_dependence(db)
        finally:
            db.close()

        self.assertFalse(report["disk_independent"])
        self.assertEqual(report["runtime_tenants_on_local_disk"], 1)
        self.assertEqual(report["tenants_on_local_media_backend"], 1)
        self.assertEqual(report["tenants_with_local_media_references"], 1)
        self.assertEqual(len(report["tenants"]), 2)
        self.assertTrue(report["tenants"][0]["has_local_disk_dependency"])
        self.assertEqual(report["tenants"][0]["local_product_media_references"], 2)
        self.assertEqual(report["tenants"][0]["local_expense_media_references"], 1)
        self.assertFalse(report["tenants"][1]["has_local_disk_dependency"])

    def test_local_media_reference_helper_detects_static_upload_urls(self) -> None:
        self.assertTrue(is_local_media_reference("/static/uploads/products/demo.webp"))
        self.assertTrue(is_local_media_reference("/static/uploads/expenses/demo.pdf"))
        self.assertFalse(
            is_local_media_reference(
                "https://example-project.supabase.co/storage/v1/object/public/restaurants-media/tenants/demo/products/demo.webp"
            )
        )

    def test_phase9_source_files_keep_disk_independence_contract_fragments(self) -> None:
        registry_source = (BACKEND_DIR / "application" / "master_engine" / "domain" / "registry.py").read_text(
            encoding="utf-8"
        )
        audit_source = (
            BACKEND_DIR / "application" / "master_engine" / "domain" / "deployment_disk_audit.py"
        ).read_text(encoding="utf-8")
        script_source = (
            BACKEND_DIR / "scripts" / "run_deployment_disk_independence_audit.py"
        ).read_text(encoding="utf-8")

        self.assertIn("media_storage_backend=SETTINGS.media_storage_backend", registry_source)

        required_audit_fragments = [
            "MASTER_TENANT_RUNTIME_STORAGE_BACKEND_SQLITE_FILE",
            "MASTER_TENANT_MEDIA_STORAGE_BACKEND_LOCAL_STATIC",
            'Product.image_path.like(f"{_LOCAL_MEDIA_PREFIX}%")',
            'ExpenseAttachment.file_url.like(f"{_LOCAL_MEDIA_PREFIX}%")',
            '"disk_independent": disk_independent',
        ]
        for fragment in required_audit_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, audit_source)

        self.assertIn("return 0 if bool(report[\"disk_independent\"]) else 1", script_source)


if __name__ == "__main__":
    unittest.main()
