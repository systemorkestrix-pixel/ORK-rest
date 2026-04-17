from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str


def _collect_python_files(backend_root: Path) -> list[Path]:
    include_paths = [
        backend_root / "main.py",
        backend_root / "app",
        backend_root / "tests",
        backend_root / "alembic",
    ]
    files: list[Path] = []
    for include_path in include_paths:
        if include_path.is_file():
            files.append(include_path)
            continue
        if not include_path.exists():
            continue
        for file_path in include_path.rglob("*.py"):
            if "__pycache__" in file_path.parts:
                continue
            files.append(file_path)
    return sorted(files)


def _check_trailing_whitespace(path: Path, text: str, violations: list[Violation]) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.endswith(" ") or line.endswith("\t"):
            violations.append(Violation(path=path, line=line_number, message="trailing whitespace"))


def _check_ast_rules(path: Path, text: str, violations: list[Violation]) -> None:
    try:
        node = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        violations.append(Violation(path=path, line=exc.lineno or 1, message=f"syntax error: {exc.msg}"))
        return

    for item in ast.walk(node):
        if isinstance(item, ast.ImportFrom):
            for alias in item.names:
                if alias.name == "*":
                    violations.append(Violation(path=path, line=item.lineno, message="wildcard import is not allowed"))
        if isinstance(item, ast.Try):
            for handler in item.handlers:
                if handler.type is None:
                    violations.append(Violation(path=path, line=handler.lineno, message="bare except is not allowed"))


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    violations: list[Violation] = []

    for file_path in _collect_python_files(backend_root):
        text = file_path.read_text(encoding="utf-8-sig")
        _check_trailing_whitespace(file_path, text, violations)
        _check_ast_rules(file_path, text, violations)

    if violations:
        print(f"Backend lint gate failed with {len(violations)} violation(s):")
        for violation in violations:
            rel_path = violation.path.relative_to(backend_root.parent)
            print(f"- {rel_path}:{violation.line}: {violation.message}")
        return 1

    print("Backend lint gate passed with zero warnings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
