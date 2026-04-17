from __future__ import annotations

import json
import subprocess
import sys
import time
from http import cookiejar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
BASE_URL = "http://127.0.0.1:8130"
REPORT_PATH = ROOT / "PHASE8_E2E_LAST_RESULT.md"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


@dataclass
class SessionClient:
    cookie_jar: cookiejar.CookieJar
    opener: request.OpenerDirector

    @classmethod
    def create(cls) -> "SessionClient":
        jar = cookiejar.CookieJar()
        opener = request.build_opener(request.HTTPCookieProcessor(jar))
        return cls(cookie_jar=jar, opener=opener)

    def cookie_value(self, name: str) -> str:
        for item in self.cookie_jar:
            if item.name == name:
                return item.value
        return ""


def http_json(
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    client: SessionClient | None = None,
    include_csrf: bool = False,
) -> tuple[int, dict | list | str | None]:
    url = f"{BASE_URL}{path}"
    body: bytes | None = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    if include_csrf and client is not None:
        csrf_token = client.cookie_value("csrf_token")
        if csrf_token:
            headers["x-csrf-token"] = csrf_token
    req = request.Request(url=url, method=method.upper(), headers=headers, data=body)
    opener = client.opener if client is not None else request.build_opener()
    try:
        with opener.open(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            parsed: dict | list | str | None
            if not raw:
                parsed = None
            else:
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = raw
            return resp.status, parsed
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw or None
        return exc.code, parsed
    except error.URLError:
        return 0, None


def assert_status(
    checks: list[CheckResult],
    name: str,
    status_code: int,
    expected: int,
    payload: dict | list | str | None,
) -> None:
    if status_code == expected:
        checks.append(CheckResult(name=name, status="PASS", detail=f"HTTP {status_code}"))
        return
    detail = f"Expected {expected}, got {status_code}."
    if isinstance(payload, dict) and payload.get("detail"):
        detail = f"{detail} detail={payload['detail']}"
    checks.append(CheckResult(name=name, status="FAIL", detail=detail))


def login(checks: list[CheckResult], role: str, username: str, password: str) -> SessionClient | None:
    client = SessionClient.create()
    status_code, payload = http_json(
        "POST",
        "/api/auth/login",
        {"username": username, "password": password, "role": role},
        client=client,
    )
    assert_status(checks, f"Login {role}", status_code, 200, payload)
    if status_code != 200:
        return None
    access = client.cookie_value("access_token")
    refresh = client.cookie_value("refresh_token")
    csrf = client.cookie_value("csrf_token")
    if access and refresh and csrf:
        checks.append(CheckResult(name=f"Login cookies {role}", status="PASS", detail="Access/refresh/csrf cookies present."))
        return client
    checks.append(CheckResult(name=f"Login cookies {role}", status="FAIL", detail="Missing auth cookies in response."))
    return None


def write_report(checks: list[CheckResult], started_at: datetime, finished_at: datetime) -> None:
    passed = sum(1 for c in checks if c.status == "PASS")
    failed = sum(1 for c in checks if c.status == "FAIL")
    lines = [
        "# نتيجة فحص القبول التشغيلي (Phase 8 Smoke E2E)",
        "",
        f"- تاريخ التنفيذ: {finished_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- مدة التنفيذ: {int((finished_at - started_at).total_seconds())} ثانية",
        f"- الإجمالي: {len(checks)}",
        f"- الناجح: {passed}",
        f"- الفاشل: {failed}",
        "",
        "| الفحص | الحالة | الملاحظة |",
        "|---|---|---|",
    ]
    for item in checks:
        badge = "✅" if item.status == "PASS" else "❌"
        lines.append(f"| {item.name} | {badge} {item.status} | {item.detail} |")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not PYTHON_EXE.exists():
        print(f"Python executable not found: {PYTHON_EXE}")
        return 2

    started_at = datetime.now()
    checks: list[CheckResult] = []

    server = subprocess.Popen(
        [
            str(PYTHON_EXE),
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8130",
            "--app-dir",
            str(ROOT / "backend"),
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ready = False
        for _ in range(80):
            status_code, payload = http_json("GET", "/health")
            if status_code == 200 and isinstance(payload, dict) and payload.get("status") == "ok":
                ready = True
                checks.append(CheckResult(name="Health check", status="PASS", detail="HTTP 200"))
                break
            time.sleep(0.25)
        if not ready:
            checks.append(CheckResult(name="Health check", status="FAIL", detail="Service did not start on time."))
            write_report(checks, started_at, datetime.now())
            return 1

        public_checks = [
            ("Public products", "/api/public/products"),
            ("Public tables", "/api/public/tables"),
            ("Public delivery settings", "/api/public/delivery/settings"),
            ("Public operational capabilities", "/api/public/operational-capabilities"),
        ]
        for name, path in public_checks:
            status_code, payload = http_json("GET", path)
            assert_status(checks, name, status_code, 200, payload)

        manager_client = login(checks, "manager", "manager", "manager123")
        if manager_client is not None:
            manager_checks = [
                ("Manager me", "/api/auth/me"),
                ("Manager dashboard", "/api/manager/dashboard"),
                ("Manager orders paged", "/api/manager/orders/paged"),
                ("Manager tables", "/api/manager/tables"),
                ("Manager kitchen monitor", "/api/manager/kitchen/orders/paged"),
                ("Manager delivery settings", "/api/manager/delivery/settings"),
                ("Manager products paged", "/api/manager/products/paged"),
                ("Manager warehouse dashboard", "/api/manager/warehouse/dashboard"),
                ("Manager suppliers", "/api/manager/warehouse/suppliers"),
                ("Manager financial transactions", "/api/manager/financial/transactions"),
                ("Manager expenses", "/api/manager/expenses"),
                ("Manager reports daily", "/api/manager/reports/daily"),
                ("Manager reports profitability", "/api/manager/reports/profitability"),
                ("Manager users", "/api/manager/users"),
                ("Manager settings operational", "/api/manager/settings/operational"),
                ("Manager audit system", "/api/manager/audit/system"),
                ("Manager audit security", "/api/manager/audit/security"),
                ("Manager account sessions", "/api/manager/account/sessions"),
            ]
            for name, path in manager_checks:
                status_code, payload = http_json("GET", path, client=manager_client)
                assert_status(checks, name, status_code, 200, payload)

            status_code, payload = http_json(
                "POST",
                "/api/manager/system/backups/create",
                client=manager_client,
                include_csrf=True,
            )
            assert_status(checks, "Manager create backup", status_code, 200, payload)
            backup_filename = ""
            if status_code == 200 and isinstance(payload, dict):
                backup_filename = str(payload.get("filename", "")).strip()
            if backup_filename:
                status_code, payload = http_json(
                    "POST",
                    "/api/manager/system/backups/restore",
                    payload={"filename": backup_filename, "confirm_phrase": "RESTORE"},
                    client=manager_client,
                    include_csrf=True,
                )
                assert_status(checks, "Manager restore backup", status_code, 200, payload)
            else:
                checks.append(
                    CheckResult(
                        name="Manager restore backup",
                        status="FAIL",
                        detail="Backup filename not returned from create endpoint.",
                    )
                )

            status_code, payload = http_json(
                "POST",
                "/api/auth/refresh",
                client=manager_client,
                include_csrf=True,
            )
            assert_status(checks, "Manager refresh token", status_code, 200, payload)

            status_code, payload = http_json(
                "POST",
                "/api/auth/logout",
                client=manager_client,
                include_csrf=True,
            )
            assert_status(checks, "Manager logout", status_code, 200, payload)

        kitchen_client = login(checks, "kitchen", "kitchen", "kitchen123")
        if kitchen_client is not None:
            status_code, payload = http_json("GET", "/api/kitchen/orders", client=kitchen_client)
            assert_status(checks, "Kitchen own board", status_code, 200, payload)
            status_code, payload = http_json("GET", "/api/manager/dashboard", client=kitchen_client)
            assert_status(checks, "Kitchen blocked from manager dashboard", status_code, 403, payload)

            status_code, payload = http_json(
                "POST",
                "/api/auth/logout",
                client=kitchen_client,
                include_csrf=True,
            )
            assert_status(checks, "Kitchen logout", status_code, 200, payload)

        delivery_client = login(checks, "delivery", "delivery", "delivery123")
        if delivery_client is not None:
            status_code, payload = http_json("GET", "/api/delivery/orders", client=delivery_client)
            assert_status(checks, "Delivery own orders", status_code, 200, payload)
            status_code, payload = http_json("GET", "/api/delivery/assignments", client=delivery_client)
            assert_status(checks, "Delivery assignments", status_code, 200, payload)
            status_code, payload = http_json("GET", "/api/delivery/history", client=delivery_client)
            assert_status(checks, "Delivery history", status_code, 200, payload)
            status_code, payload = http_json("GET", "/api/manager/users", client=delivery_client)
            assert_status(checks, "Delivery blocked from manager users", status_code, 403, payload)

            status_code, payload = http_json(
                "POST",
                "/api/auth/logout",
                client=delivery_client,
                include_csrf=True,
            )
            assert_status(checks, "Delivery logout", status_code, 200, payload)

    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()

    finished_at = datetime.now()
    write_report(checks, started_at, finished_at)
    failed = sum(1 for c in checks if c.status == "FAIL")
    print(f"Smoke E2E finished. total={len(checks)} failed={failed}")
    print(f"Report: {REPORT_PATH}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
