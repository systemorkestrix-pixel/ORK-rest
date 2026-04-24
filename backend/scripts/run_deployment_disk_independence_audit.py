from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from application.master_engine.domain.deployment_disk_audit import audit_deployment_disk_dependence


def main() -> int:
    db = SessionLocal()
    try:
        report = audit_deployment_disk_dependence(db)
    finally:
        db.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if bool(report["disk_independent"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
