from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import engine as master_engine
from application.master_engine.domain.runtime_cutover_validation import validate_tenant_runtime_dual_state


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run phase 6 dual validation before tenant runtime cutover.")
    parser.add_argument("--database-name", required=True, help="Tenant runtime SQLite database name.")
    parser.add_argument("--schema-name", default=None, help="Optional PostgreSQL schema override.")
    parser.add_argument("--tenant-code", default=None, help="Optional tenant code for smoke manifest paths.")
    parser.add_argument("--sample-limit", type=int, default=5, help="How many primary-key ordered rows to compare.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read SQLite source and build the validation manifest without querying PostgreSQL.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    report = validate_tenant_runtime_dual_state(
        database_name=args.database_name,
        target_engine=None if args.dry_run else master_engine,
        target_schema_name=args.schema_name,
        tenant_code=args.tenant_code,
        sample_limit=args.sample_limit,
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
