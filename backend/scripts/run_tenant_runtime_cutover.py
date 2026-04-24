from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from application.master_engine.domain.per_tenant_cutover import (
    cutover_tenant_runtime,
    mark_tenant_runtime_validated,
    rollback_tenant_runtime_cutover,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Perform phase 7 per-tenant gradual runtime cutover.")
    parser.add_argument("--database-name", required=True, help="Tenant runtime database name.")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the tenant from postgres_schema back to sqlite_file.",
    )
    parser.add_argument(
        "--mark-validated",
        action="store_true",
        help="Mark the tenant as validated in master_tenants before cutover.",
    )
    parser.add_argument(
        "--allow-revalidated-cutover",
        action="store_true",
        help="Allow cutover again after a rollback state once validation has been re-confirmed.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    db = SessionLocal()
    try:
        if args.mark_validated:
            result = mark_tenant_runtime_validated(db, database_name=args.database_name)
        elif args.rollback:
            result = rollback_tenant_runtime_cutover(db, database_name=args.database_name)
        else:
            result = cutover_tenant_runtime(
                db,
                database_name=args.database_name,
                allow_revalidated_cutover=args.allow_revalidated_cutover,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
