import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase2-test-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("ADMIN_USERNAME", "admin_test")
os.environ.setdefault("ADMIN_PASSWORD", "AdminTest12345")
os.environ.setdefault("ADMIN_NAME", "مدير النظام")

from app.database import Base, assert_production_migration_state, create_app_engine
from app.seed import bootstrap_production_data


class Phase2SchemaIntegrityTests(unittest.TestCase):
    def _build_temp_session(self) -> tuple[Session, Path, object]:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        engine = create_app_engine(f"sqlite:///{db_path.as_posix()}")
        maker = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        return maker(), db_path, engine

    def test_production_migration_state_requires_version_table(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            with self.assertRaises(RuntimeError) as failure:
                assert_production_migration_state(engine)
            self.assertIn("migration version table", str(failure.exception))
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_production_migration_state_accepts_stamped_revision(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
                connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('baseline_001')"))

            revision = assert_production_migration_state(
                engine,
                version_table="alembic_version",
                expected_revision="baseline_001",
            )
            self.assertEqual(revision, "baseline_001")
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_sqlite_connection_enforces_foreign_keys(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            with engine.connect() as connection:
                fk_state = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
            self.assertEqual(int(fk_state), 1)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_fk_violation_is_rejected(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            Base.metadata.create_all(bind=engine)
            with self.assertRaises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at) "
                            "VALUES (999999, 'phase2-bad-token', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                        )
                    )
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_production_bootstrap_requires_prebuilt_schema(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            with self.assertRaises(RuntimeError) as failure:
                bootstrap_production_data(db)
            self.assertIn("schema contract violation", str(failure.exception).lower())
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_fresh_database_builds_via_alembic_only(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        env = os.environ.copy()
        env["DATABASE_PATH"] = db_path.as_posix()
        env.setdefault("JWT_SECRET", "phase2-test-secret-0123456789abcdef0123456789")

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
        db = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
        try:
            revision = assert_production_migration_state(engine)
            self.assertTrue(bool(revision))
            users_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
            self.assertEqual(int(users_count), 0)
            bootstrap_production_data(db)
        finally:
            db.close()
            engine.dispose()
            if db_path.exists():
                db_path.unlink()


if __name__ == "__main__":
    unittest.main()
