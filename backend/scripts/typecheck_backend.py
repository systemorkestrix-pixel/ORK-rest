from __future__ import annotations

from pathlib import Path
import py_compile


def _collect_python_files(backend_root: Path) -> list[Path]:
    include_paths = [
        backend_root / "main.py",
        backend_root / "app",
        backend_root / "tests",
        backend_root / "alembic",
    ]
    collected: list[Path] = []
    for include_path in include_paths:
        if include_path.is_file():
            collected.append(include_path)
            continue
        if not include_path.exists():
            continue
        for file_path in include_path.rglob("*.py"):
            if "__pycache__" in file_path.parts:
                continue
            collected.append(file_path)
    return sorted(collected)


def main() -> int:
    backend_root = Path(__file__).resolve().parents[1]
    files = _collect_python_files(backend_root)
    errors: list[str] = []

    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(str(exc))

    if errors:
        print("Backend type/syntax gate failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Backend type/syntax gate passed. Compiled files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
