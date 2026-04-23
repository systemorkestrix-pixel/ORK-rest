from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPO_ROOT / "RENDER_LIVE_SMOKE_LAST_RESULT.md"
JSON_PATH = REPO_ROOT / "RENDER_LIVE_SMOKE_LAST_RESULT.json"


@dataclass
class SmokeCheck:
    name: str
    url: str
    expected_status: int


def http_fetch(url: str) -> tuple[int | None, Any]:
    req = request.Request(url, headers={"User-Agent": "codex-render-smoke"})
    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def write_reports(*, captured_at: str, checks: list[dict[str, object]]) -> None:
    passed = sum(1 for item in checks if item["status"] == "PASS")
    failed = sum(1 for item in checks if item["status"] == "FAIL")

    JSON_PATH.write_text(
        json.dumps({"captured_at_utc": captured_at, "checks": checks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Render Live Smoke",
        "",
        f"- captured_at_utc: {captured_at}",
        f"- total: {len(checks)}",
        f"- passed: {passed}",
        f"- failed: {failed}",
        "",
        "| check | status | expected | actual | detail |",
        "|---|---|---|---|---|",
    ]
    for item in checks:
        lines.append(
            f"| {item['name']} | {item['status']} | {item['expected_status']} | {item['actual_status']} | {item['detail']} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the governed Render live smoke checks.")
    parser.add_argument("--api-base", default="https://restaurants-api.onrender.com", help="API base URL")
    parser.add_argument("--console-base", default="https://restaurants-console.onrender.com", help="Console base URL")
    parser.add_argument("--tenant", default="phase9-base", help="Tenant code probe for tenant-entry")
    args = parser.parse_args()

    checks = [
        SmokeCheck(name="API root", url=f"{args.api_base}/", expected_status=200),
        SmokeCheck(name="API health", url=f"{args.api_base}/health", expected_status=200),
        SmokeCheck(
            name="Tenant entry",
            url=f"{args.api_base}/api/public/tenant-entry?tenant={args.tenant}",
            expected_status=200,
        ),
        SmokeCheck(name="Unscoped public reject", url=f"{args.api_base}/api/public/products", expected_status=404),
        SmokeCheck(name="Console root", url=f"{args.console_base}/", expected_status=200),
        SmokeCheck(name="Manager login", url=f"{args.console_base}/manager/login", expected_status=200),
    ]

    captured_at = datetime.now(UTC).isoformat()
    results: list[dict[str, object]] = []
    exit_code = 0

    for check in checks:
        actual_status, payload = http_fetch(check.url)
        detail = str(payload).replace("\n", " ").strip()[:160]
        status = "PASS" if actual_status == check.expected_status else "FAIL"
        if status == "FAIL":
            exit_code = 1
        results.append(
            {
                "name": check.name,
                "url": check.url,
                "status": status,
                "expected_status": check.expected_status,
                "actual_status": actual_status,
                "detail": detail,
            }
        )

    write_reports(captured_at=captured_at, checks=results)
    print(json.dumps({"captured_at_utc": captured_at, "checks": results}, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
