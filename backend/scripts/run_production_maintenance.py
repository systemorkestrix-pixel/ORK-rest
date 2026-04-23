from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import load_settings
from app.database import SessionLocal, assert_production_migration_state, engine, run_startup_integrity_checks
from app.seed import bootstrap_production_maintenance
from application.master_engine.domain.provisioning import sync_all_tenant_tables


def main() -> int:
    settings = load_settings()
    if not settings.is_production:
        raise RuntimeError("run_production_maintenance.py requires APP_ENV=production.")

    assert_production_migration_state(
        engine,
        version_table=settings.migration_version_table,
        expected_revision=settings.schema_expected_revision,
    )

    db = SessionLocal()
    try:
        bootstrap_production_maintenance(db)
        synced_databases = sync_all_tenant_tables(db, table_names=["restaurant_employees"])
    finally:
        db.close()

    run_startup_integrity_checks(engine)
    print(
        json.dumps(
            {
                "status": "ok",
                "maintenance": "completed",
                "tenant_sync_count": len(synced_databases),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
