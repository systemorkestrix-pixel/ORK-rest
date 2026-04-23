import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase5-polling-secret-0123456789abcdef01234")
os.environ.setdefault("APP_ENV", "development")

from app.database import create_app_engine
from app.models import SystemSetting, User
from application.core_engine.domain.settings import get_order_polling_ms, update_operational_setting


class Phase5PollingOptimizationTests(unittest.TestCase):
    def _build_migrated_session(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"alembic upgrade failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
        session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
        return session, engine, db_path

    def test_order_polling_runtime_bounds_enforced(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            self.assertEqual(get_order_polling_ms(db), 5000)

            db.add(SystemSetting(key="order_polling_ms", value="2000"))
            db.commit()
            self.assertEqual(get_order_polling_ms(db), 5000)

            row = db.get(SystemSetting, "order_polling_ms")
            self.assertIsNotNone(row)
            assert row is not None
            row.value = "4500"
            db.commit()
            self.assertEqual(get_order_polling_ms(db), 4500)

            row.value = "70000"
            db.commit()
            self.assertEqual(get_order_polling_ms(db), 5000)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_operational_setting_rejects_polling_under_minimum(self) -> None:
        db, engine, path = self._build_migrated_session()
        try:
            actor = User(
                name="Polling Actor",
                username="polling_actor",
                password_hash="$argon2id$seed",
                role="manager",
                active=True,
            )
            db.add(actor)
            db.commit()
            db.refresh(actor)

            with self.assertRaises(HTTPException) as error_ctx:
                update_operational_setting(
                    db,
                    key="order_polling_ms",
                    value="2500",
                    actor_id=int(actor.id),
                )
            self.assertEqual(error_ctx.exception.status_code, 400)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_frontend_polling_uses_adaptive_wrapper_everywhere(self) -> None:
        src_root = BACKEND_DIR.parent / "src"
        helper_file = src_root / "shared" / "utils" / "polling.ts"
        self.assertTrue(helper_file.exists(), msg="adaptive polling helper file missing")

        helper_text = helper_file.read_text(encoding="utf-8")
        self.assertIn("pauseWhenHidden", helper_text)
        self.assertIn("pauseWhenOffline", helper_text)

        refetch_lines: list[tuple[Path, int, str]] = []
        for path in src_root.rglob("*.tsx"):
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if "refetchInterval:" in line:
                    refetch_lines.append((path, line_no, line.strip()))

        self.assertGreaterEqual(len(refetch_lines), 20, msg="expected polling references not found")

        violations = [
            f"{path}:{line_no}: {line}"
            for path, line_no, line in refetch_lines
            if "adaptiveRefetchInterval(" not in line
        ]
        self.assertEqual(
            violations,
            [],
            msg="\n".join(["Found non-adaptive polling usages:", *violations]),
        )

        raw_ms_literals = []
        ms_pattern = re.compile(r"refetchInterval:\s*\d")
        for path in src_root.rglob("*.tsx"):
            text = path.read_text(encoding="utf-8")
            if ms_pattern.search(text):
                raw_ms_literals.append(str(path))
        self.assertEqual(raw_ms_literals, [], msg=f"Raw numeric polling intervals found: {raw_ms_literals}")


if __name__ == "__main__":
    unittest.main()
