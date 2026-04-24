import sys
import unittest
from pathlib import Path

from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.tenant_runtime import TENANTS_DIR, infer_tenant_database_name_from_session
from app.tenant_runtime_storage import (
    TENANT_RUNTIME_SQLITE_BACKEND,
    TENANT_RUNTIME_SQLITE_DIR,
    create_tenant_runtime_engine,
    resolve_tenant_runtime_target,
)
from application.master_engine.domain.provisioning import resolve_tenant_database_path


class Phase9TenantRuntimeStorageContractTests(unittest.TestCase):
    def test_storage_target_keeps_current_sqlite_runtime_contract(self) -> None:
        target = resolve_tenant_runtime_target("phase9_storage_contract")
        self.assertEqual(target.backend, TENANT_RUNTIME_SQLITE_BACKEND)
        self.assertEqual(target.database_name, "phase9_storage_contract")
        self.assertEqual(target.database_path, resolve_tenant_database_path("phase9_storage_contract"))
        self.assertEqual(target.database_path.parent, TENANT_RUNTIME_SQLITE_DIR.resolve())
        self.assertEqual(target.cache_key, "sqlite_file:phase9_storage_contract")
        self.assertEqual(TENANTS_DIR.resolve(), TENANT_RUNTIME_SQLITE_DIR.resolve())

    def test_runtime_session_inference_still_maps_sqlite_bind_back_to_database_name(self) -> None:
        target = resolve_tenant_runtime_target("phase9_storage_infer")
        engine = create_tenant_runtime_engine(target)
        runtime_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        try:
            session = runtime_session_factory()
            try:
                self.assertEqual(infer_tenant_database_name_from_session(session), "phase9_storage_infer")
            finally:
                session.close()
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
