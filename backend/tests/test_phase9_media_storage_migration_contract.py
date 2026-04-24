import base64
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
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
os.environ["JWT_SECRET"] = "phase9-media-migration-jwt-secret-0123456789abcdef0123456789"
os.environ["SECRET_KEY"] = "phase9-media-migration-secret-key-0123456789abcdef0123456789"
os.environ["MASTER_ADMIN_USERNAME"] = "phase9-master-admin"
os.environ["MASTER_ADMIN_PASSWORD"] = "Phase9MasterAdmin!2026"
os.environ["ADMIN_USERNAME"] = "phase9_manager"
os.environ["ADMIN_PASSWORD"] = "Phase9ManagerAdmin123"
os.environ["ALLOW_LEGACY_PASSWORD_LOGIN"] = "false"
os.environ["MEDIA_STORAGE_BACKEND"] = "local_static"
os.environ["MEDIA_STORAGE_BUCKET"] = "restaurants-media"
os.environ["MEDIA_STORAGE_PROJECT_URL"] = "https://example-project.supabase.co"
os.environ["MEDIA_STORAGE_PUBLIC_BASE_URL"] = (
    "https://example-project.supabase.co/storage/v1/object/public/restaurants-media"
)
os.environ["MEDIA_STORAGE_SERVICE_ROLE_KEY"] = "phase9-supabase-storage-service-role-key"

from app.database import engine
from app.master_tenant_runtime_contract import MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE
from application.inventory_engine.domain.media_storage import (
    build_media_object_key,
    extract_supabase_object_key,
    store_media_bytes,
)


class _DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return b"{}"


class Phase9MediaStorageMigrationContractTests(unittest.TestCase):
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
                "alembic upgrade failed for media storage migration contract tests:\n"
                f"STDOUT:\n{migrated.stdout}\nSTDERR:\n{migrated.stderr}"
            )

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if MASTER_DB_PATH.exists():
            MASTER_DB_PATH.unlink()

    def test_media_object_key_is_tenant_scoped(self) -> None:
        self.assertEqual(
            build_media_object_key(tenant_code="demo", namespace="products", file_name="image.webp"),
            "tenants/demo/products/image.webp",
        )

    def test_supabase_public_url_roundtrip_extracts_object_key(self) -> None:
        object_key = "tenants/demo/products/image.webp"
        file_url = (
            "https://example-project.supabase.co/storage/v1/object/public/restaurants-media/" + object_key
        )
        self.assertEqual(
            extract_supabase_object_key(
                file_url=file_url,
                public_base_url=os.environ["MEDIA_STORAGE_PUBLIC_BASE_URL"],
            ),
            object_key,
        )

    def test_store_media_bytes_supports_supabase_backend_without_local_disk_write(self) -> None:
        with patch("application.inventory_engine.domain.media_storage.urlopen", return_value=_DummyResponse()) as mocked:
            stored = store_media_bytes(
                db=None,
                namespace="products",
                file_name="image.webp",
                content_type="image/webp",
                data=b"WEBP_DATA",
                backend_override=MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
                tenant_code_override="tenant_demo",
            )

        self.assertEqual(
            stored.file_url,
            "https://example-project.supabase.co/storage/v1/object/public/restaurants-media/"
            "tenants/tenant_demo/products/image.webp",
        )
        self.assertEqual(stored.storage_backend, MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE)
        self.assertEqual(mocked.call_count, 1)

    def test_media_source_files_keep_phase5_contract_fragments(self) -> None:
        media_source = (BACKEND_DIR / "application" / "inventory_engine" / "domain" / "media.py").read_text(
            encoding="utf-8"
        )
        storage_source = (
            BACKEND_DIR / "application" / "inventory_engine" / "domain" / "media_storage.py"
        ).read_text(encoding="utf-8")
        script_source = (BACKEND_DIR / "scripts" / "run_media_storage_migration.py").read_text(encoding="utf-8")

        self.assertIn("store_media_bytes(", media_source)
        self.assertNotIn("PRODUCT_UPLOAD_DIR.mkdir", media_source)
        self.assertNotIn("EXPENSE_ATTACHMENT_UPLOAD_DIR.mkdir", media_source)

        required_storage_fragments = [
            'MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE',
            'build_media_object_key(',
            'url=f"{target.project_url}/storage/v1/object/',
            "migrate_tenant_media_references_to_remote(",
        ]
        for fragment in required_storage_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, storage_source)

        self.assertIn("--delete-local-files", script_source)


if __name__ == "__main__":
    unittest.main()
