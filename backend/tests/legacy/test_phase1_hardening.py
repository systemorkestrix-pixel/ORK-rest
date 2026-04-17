import json
import os
import hashlib
from dataclasses import replace
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure security/config modules can load in test process.
os.environ.setdefault("JWT_SECRET", "phase1-test-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.config import load_settings
from app.database import Base
from app.models import SecurityAuditEvent, User
from app.seed import bootstrap_production_data
from app.security import SETTINGS as SECURITY_SETTINGS, hash_password
from application.core_engine.domain.auth import LOGIN_MAX_FAILED_ATTEMPTS, login_user


class Phase1HardeningTests(unittest.TestCase):
    def _build_temp_session(self) -> tuple[Session, Path, object]:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db_path = Path(tmp.name)
        engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        maker = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        return maker(), db_path, engine

    def test_settings_require_jwt_secret_or_keyring(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "JWT_SECRET": "",
                "JWT_KEYRING_JSON": "",
                "JWT_ACTIVE_KID": "v1",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                load_settings()

    def test_settings_support_key_rotation_keyring(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "JWT_SECRET": "",
                "JWT_KEYRING_JSON": json.dumps({"v1": "x" * 48, "v2": "y" * 48}),
                "JWT_ACTIVE_KID": "v2",
            },
            clear=False,
        ):
            settings = load_settings()
        self.assertEqual(settings.jwt_active_kid, "v2")
        self.assertIn("v1", settings.jwt_keyring)
        self.assertIn("v2", settings.jwt_keyring)

    def test_production_startup_fails_without_secret(self) -> None:
        env = os.environ.copy()
        env["APP_ENV"] = "production"
        # Force empty secrets so a local .env cannot backfill production startup.
        env["JWT_SECRET"] = ""
        env["JWT_KEYRING_JSON"] = ""
        proc = subprocess.run(
            [sys.executable, "-c", "import main"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        combined = f"{proc.stdout}\n{proc.stderr}"
        self.assertIn("JWT secret is required", combined)

    def test_production_bootstrap_does_not_create_default_users(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            bootstrap_production_data(db)
            users = db.execute(select(User)).scalars().all()
            self.assertEqual(len(users), 0)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_production_bootstrap_does_not_reactivate_users(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            user = User(
                name="inactive manager",
                username="inactive_manager",
                password_hash=hash_password("inactive-pass-123"),
                role="manager",
                active=False,
            )
            db.add(user)
            db.commit()

            bootstrap_production_data(db)
            refreshed = db.execute(select(User).where(User.username == "inactive_manager")).scalar_one()
            self.assertFalse(refreshed.active)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_login_lockout_after_repeated_failures(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            user = User(
                name="manager",
                username="manager",
                password_hash=hash_password("CorrectPass123"),
                role="manager",
                active=True,
            )
            db.add(user)
            db.commit()

            for _ in range(LOGIN_MAX_FAILED_ATTEMPTS):
                with self.assertRaises(HTTPException) as auth_error:
                    login_user(db, username="manager", password="WrongPass123", role="manager")
                self.assertEqual(auth_error.exception.status_code, 401)

            with self.assertRaises(HTTPException) as locked_error:
                login_user(db, username="manager", password="CorrectPass123", role="manager")
            self.assertEqual(locked_error.exception.status_code, 423)

            lock_events = db.execute(
                select(SecurityAuditEvent).where(SecurityAuditEvent.event_type == "login_lockout")
            ).scalars().all()
            self.assertGreaterEqual(len(lock_events), 1)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()

    def test_hash_password_uses_argon2id_format(self) -> None:
        hashed = hash_password("StrongPassword123")
        self.assertTrue(hashed.startswith("$argon2id$"))

    def test_legacy_sha256_hash_migrates_to_argon2_on_login(self) -> None:
        db, path, engine = self._build_temp_session()
        try:
            raw_password = "MigrateMe123"
            legacy_hash = hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
            user = User(
                name="legacy",
                username="legacy_manager",
                password_hash=legacy_hash,
                role="manager",
                active=True,
            )
            db.add(user)
            db.commit()

            with mock.patch("app.security.SETTINGS", replace(SECURITY_SETTINGS, allow_legacy_password_login=True)):
                login_user(db, username="legacy_manager", password=raw_password, role="manager")
            migrated = db.execute(select(User).where(User.username == "legacy_manager")).scalar_one()
            self.assertTrue(migrated.password_hash.startswith("$argon2id$"))
            self.assertNotEqual(migrated.password_hash, legacy_hash)

            migration_events = db.execute(
                select(SecurityAuditEvent).where(SecurityAuditEvent.event_type == "password_hash_migrated")
            ).scalars().all()
            self.assertGreaterEqual(len(migration_events), 1)
        finally:
            db.close()
            engine.dispose()
            if path.exists():
                path.unlink()



if __name__ == "__main__":
    unittest.main()
