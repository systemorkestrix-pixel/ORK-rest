from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP_DIR = REPO_ROOT / "backend" / "app"
SERVICES_DIR = BACKEND_APP_DIR / "services"


def _iter_py_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def test_no_db_session_outside_repository_layer() -> None:
    violations: list[str] = []
    for path in _iter_py_files(BACKEND_APP_DIR):
        rel = path.relative_to(BACKEND_APP_DIR).as_posix()
        if "/repositories/" in f"/{rel}":
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "session":
                base = node.value
                if isinstance(base, ast.Name) and base.id == "db":
                    violations.append(f"{rel}:{node.lineno}")
    assert not violations, f"Direct db.session usage outside repository layer: {violations}"


def test_services_do_not_import_other_services_directly() -> None:
    violations: list[str] = []
    service_module_names = {path.stem for path in SERVICES_DIR.glob("*.py") if path.stem != "__init__"}
    for path in _iter_py_files(SERVICES_DIR):
        rel = path.relative_to(SERVICES_DIR).as_posix()
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("app.services") or module.startswith("backend.app.services"):
                    violations.append(f"{rel}:{node.lineno}")
                if module.startswith("."):
                    leaf = module.split(".")[-1]
                    if leaf in service_module_names and leaf != path.stem:
                        violations.append(f"{rel}:{node.lineno}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    if mod.startswith("app.services") or mod.startswith("backend.app.services"):
                        violations.append(f"{rel}:{node.lineno}")
    assert not violations, f"Service-to-service imports detected: {violations}"

