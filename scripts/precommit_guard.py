from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            files.append(REPO_ROOT / line)
    return files


def _is_binary(payload: bytes) -> bool:
    return b"\x00" in payload


def _validate_file(path: Path) -> list[str]:
    violations: list[str] = []
    if not path.exists() or path.is_dir():
        return violations
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        violations.append(f"{path}: BOM is forbidden")
    if _is_binary(raw):
        return violations
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        violations.append(f"{path}: non-UTF8 encoding is forbidden")
        return violations

    if "from " in text and " import *" in text:
        for lineno, line in enumerate(text.splitlines(), start=1):
            if " import *" in line and line.lstrip().startswith("from "):
                violations.append(f"{path}:{lineno}: wildcard import is forbidden")

    if path.suffix in {".ts", ".tsx"}:
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "queryKey:" in line and ("'" in line or '"' in line):
                violations.append(f"{path}:{lineno}: string literal queryKey is forbidden")
            if "console.log(" in line and "/src/" in path.as_posix():
                violations.append(f"{path}:{lineno}: console.log is forbidden in production frontend code")
    return violations


def main() -> int:
    violations: list[str] = []
    for file_path in _staged_files():
        violations.extend(_validate_file(file_path))
    if violations:
        print("Pre-commit guard failed:")
        for item in violations:
            print(f"- {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

