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
from application.master_engine.domain.sqlite_to_postgres_migrator import (
    migrate_sqlite_tenant_runtime_to_postgres,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate one tenant runtime from SQLite into PostgreSQL schema.")
    parser.add_argument("--database-name", required=True, help="Current tenant runtime SQLite database name.")
    parser.add_argument("--schema-name", default=None, help="Optional PostgreSQL schema override.")
    parser.add_argument("--batch-size", type=int, default=500, help="Insert batch size for table copy.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read the SQLite source and print a migration report without writing to PostgreSQL.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    report = migrate_sqlite_tenant_runtime_to_postgres(
        database_name=args.database_name,
        target_engine=None if args.dry_run else master_engine,
        target_schema_name=args.schema_name,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
