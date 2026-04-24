from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.master_tenant_runtime_contract import MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE
from app.tenant_runtime import create_runtime_session
from application.inventory_engine.domain.media_storage import migrate_tenant_media_references_to_remote


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate one tenant media catalog from local static files to remote media storage.")
    parser.add_argument(
        "--database-name",
        required=True,
        help="Tenant runtime database name whose product and expense media references will be migrated.",
    )
    parser.add_argument(
        "--target-backend",
        default=MASTER_TENANT_MEDIA_STORAGE_BACKEND_SUPABASE_STORAGE,
        help="Target media backend. Default: supabase_storage",
    )
    parser.add_argument(
        "--delete-local-files",
        action="store_true",
        help="Delete local files after successful remote upload. Default keeps local files for rollback safety.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    tenant = create_runtime_session(args.database_name)
    try:
        result = migrate_tenant_media_references_to_remote(
            db=tenant,
            target_backend=args.target_backend,
            keep_local_files=not args.delete_local_files,
        )
        tenant.commit()
    except Exception:
        tenant.rollback()
        raise
    finally:
        tenant.close()

    print(
        json.dumps(
            {
                "status": "ok",
                "database_name": args.database_name,
                "target_backend": args.target_backend,
                "delete_local_files": args.delete_local_files,
                **result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
