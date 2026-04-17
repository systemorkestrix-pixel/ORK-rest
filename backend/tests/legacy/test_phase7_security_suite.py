import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET", "phase7-security-secret-0123456789abcdef0123456789")
os.environ.setdefault("APP_ENV", "development")

from app.database import Base, create_app_engine
from app.dependencies import get_current_user, require_route_capability
from app.enums import UserRole
from app.models import SecurityAuditEvent, User
from app.security import hash_password
from application.core_engine.domain.auth import LOGIN_MAX_FAILED_ATTEMPTS, login_user


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _tamper_access_token_subject(token: str, subject_value: str) -> str:
    header_b64, payload_b64, signature = token.split(".")
    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    payload["sub"] = subject_value
    tampered_payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{header_b64}.{tampered_payload_b64}.{signature}"


def _request_for(path: str, method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [(b"user-agent", b"phase7-security-suite"), (b"x-forwarded-for", b"10.20.30.40")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    return Request(scope)


class Phase7SecuritySuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        self._db_path = Path(tmp.name)
        self._engine = create_app_engine(f"sqlite:///{self._db_path.as_posix()}")
        Base.metadata.create_all(bind=self._engine)
        self._session_factory = sessionmaker(bind=self._engine, autocommit=False, autoflush=False)

        self._seed_user(
            name="Sec Manager",
            username="sec_manager",
            password="SecManagerPass123!",
            role=UserRole.MANAGER.value,
        )
        self._seed_user(
            name="Sec Kitchen",
            username="sec_kitchen",
            password="SecKitchenPass123!",
            role=UserRole.KITCHEN.value,
        )

    def tearDown(self) -> None:
        self._engine.dispose()
        if self._db_path.exists():
            self._db_path.unlink()

    def _seed_user(self, *, name: str, username: str, password: str, role: str) -> None:
        db = self._session_factory()
        try:
            db.add(
                User(
                    name=name,
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    active=True,
                )
            )
            db.commit()
        finally:
            db.close()

    def test_bruteforce_lockout_after_20_failed_attempts(self) -> None:
        db = self._session_factory()
        try:
            for _ in range(LOGIN_MAX_FAILED_ATTEMPTS):
                with self.assertRaises(HTTPException) as failed:
                    login_user(
                        db,
                        username="sec_manager",
                        password="WrongPassword!",
                        role=UserRole.MANAGER.value,
                    )
                self.assertEqual(failed.exception.status_code, 401)

            with self.assertRaises(HTTPException) as locked:
                login_user(
                    db,
                    username="sec_manager",
                    password="SecManagerPass123!",
                    role=UserRole.MANAGER.value,
                )
            self.assertEqual(locked.exception.status_code, 423)

            lockouts = int(
                db.execute(
                    select(func.count(SecurityAuditEvent.id)).where(
                        SecurityAuditEvent.event_type == "login_lockout",
                        SecurityAuditEvent.username == "sec_manager",
                    )
                ).scalar_one()
                or 0
            )
            self.assertGreaterEqual(lockouts, 1)
        finally:
            db.close()

    def test_privilege_escalation_blocked_on_manager_api_and_audited(self) -> None:
        db = self._session_factory()
        try:
            kitchen_user = db.execute(select(User).where(User.username == "sec_kitchen")).scalar_one()
            with self.assertRaises(HTTPException) as denied:
                require_route_capability(
                    request=_request_for("/api/manager/users", method="GET"),
                    current_user=kitchen_user,
                    db=db,
                )
            self.assertEqual(denied.exception.status_code, 403)

            denied_events = db.execute(
                select(SecurityAuditEvent).where(
                    SecurityAuditEvent.event_type == "access_denied",
                    SecurityAuditEvent.username == "sec_kitchen",
                )
            ).scalars().all()
            self.assertGreaterEqual(len(denied_events), 1)
            self.assertTrue(
                any("/manager/users" in str(event.detail or "") for event in denied_events),
                msg="access_denied event missing denied manager route detail",
            )
        finally:
            db.close()

    def test_jwt_tampering_is_rejected(self) -> None:
        db = self._session_factory()
        try:
            manager_user, access_token, _ = login_user(
                db,
                username="sec_manager",
                password="SecManagerPass123!",
                role=UserRole.MANAGER.value,
            )
            self.assertEqual(manager_user.username, "sec_manager")

            tampered = _tamper_access_token_subject(access_token, "999999")
            with self.assertRaises(HTTPException) as invalid:
                get_current_user(
                    request=_request_for("/api/auth/me", method="GET"),
                    authorization=f"Bearer {tampered}",
                    db=db,
                )
            self.assertEqual(invalid.exception.status_code, 401)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
