from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_CLIENT = REPO_ROOT / "src" / "shared" / "api" / "client.ts"
FRONTEND_TYPES = REPO_ROOT / "src" / "shared" / "api" / "types.ts"
BACKEND_ENUMS = BACKEND_DIR / "app" / "enums.py"


def _is_placeholder(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}")


def _split_path(path: str) -> list[str]:
    return [part for part in path.strip("/").split("/") if part]


def _path_matches(frontend_path: str, backend_path: str) -> bool:
    a = _split_path(frontend_path)
    b = _split_path(backend_path)
    if len(a) != len(b):
        return False
    for left, right in zip(a, b):
        if _is_placeholder(left) or _is_placeholder(right):
            continue
        if left != right:
            return False
    return True


def _normalize_frontend_path(raw: str) -> str:
    value = raw.strip()
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        value = value[1:-1]
    elif value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    value = re.sub(r"\$\{[^}]+\}", "{param}", value)
    value = value.split("?", 1)[0]
    # Query suffix templates like `/path${suffix}` should not be treated as path segments.
    value = re.sub(r"(?<!/)\{param\}$", "", value)
    if not value.startswith("/"):
        return ""
    if not value.startswith("/api/"):
        value = f"/api{value}"
    return value


def _extract_call_content(text: str, start: int) -> tuple[str, int] | None:
    open_paren = text.find("(", start)
    if open_paren < 0:
        return None
    depth = 0
    for idx in range(open_paren, len(text)):
        ch = text[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1 : idx], idx + 1
    return None


def _extract_frontend_endpoints(client_source: str) -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    idx = 0
    while True:
        pos = client_source.find("request", idx)
        if pos < 0:
            break
        if pos > 0 and (client_source[pos - 1].isalnum() or client_source[pos - 1] == "_"):
            idx = pos + 7
            continue
        content_info = _extract_call_content(client_source, pos)
        if content_info is None:
            idx = pos + 7
            continue
        args_content, next_idx = content_info
        idx = next_idx
        # split top-level arguments
        depth = 0
        split_at = -1
        for i, ch in enumerate(args_content):
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                split_at = i
                break
        first_arg = args_content if split_at < 0 else args_content[:split_at]
        second_arg = "" if split_at < 0 else args_content[split_at + 1 :]
        first_arg = first_arg.strip()
        if not (first_arg.startswith("'") or first_arg.startswith('"') or first_arg.startswith("`")):
            continue
        path = _normalize_frontend_path(first_arg)
        if not path:
            continue
        method_match = re.search(r"method\s*:\s*'([A-Z]+)'", second_arg)
        method = method_match.group(1) if method_match else "GET"
        endpoints.add((method, path))
    return endpoints


def _extract_backend_endpoints() -> set[tuple[str, str]]:
    sys.path.insert(0, str(BACKEND_DIR))
    import main as backend_main  # noqa: PLC0415

    schema = backend_main.app.openapi()
    endpoints: set[tuple[str, str]] = set()
    for path, methods in schema.get("paths", {}).items():
        for method in methods.keys():
            endpoints.add((method.upper(), path))
    return endpoints


def _extract_backend_enum_values(enum_name: str) -> set[str]:
    tree = ast.parse(BACKEND_ENUMS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == enum_name:
            values: set[str] = set()
            for child in node.body:
                if isinstance(child, ast.Assign) and isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                    values.add(child.value.value)
            return values
    return set()


def _extract_ts_union(type_source: str, type_name: str) -> set[str]:
    match = re.search(rf"export type {re.escape(type_name)}\s*=\s*(.*?);", type_source, flags=re.S)
    if not match:
        return set()
    return set(re.findall(r"'([^']+)'", match.group(1)))


def _extract_interface_field_union(type_source: str, interface_name: str, field_name: str) -> set[str]:
    interface_match = re.search(
        rf"export interface {re.escape(interface_name)}\s*\{{(.*?)\n\}}",
        type_source,
        flags=re.S,
    )
    if not interface_match:
        return set()
    body = interface_match.group(1)
    field_match = re.search(rf"{re.escape(field_name)}\??\s*:\s*([^;]+);", body)
    if not field_match:
        return set()
    return set(re.findall(r"'([^']+)'", field_match.group(1)))


def main() -> int:
    backend_endpoints = _extract_backend_endpoints()
    frontend_endpoints = _extract_frontend_endpoints(FRONTEND_CLIENT.read_text(encoding="utf-8"))

    endpoint_errors: list[str] = []
    for method, fpath in sorted(frontend_endpoints):
        candidates = [bpath for m, bpath in backend_endpoints if m == method]
        if not any(_path_matches(fpath, bpath) for bpath in candidates):
            endpoint_errors.append(f"{method} {fpath}")

    types_source = FRONTEND_TYPES.read_text(encoding="utf-8")
    enum_errors: list[str] = []

    enum_pairs = [
        ("UserRole", _extract_ts_union(types_source, "UserRole")),
        ("OrderType", _extract_ts_union(types_source, "OrderType")),
        ("OrderStatus", _extract_ts_union(types_source, "OrderStatus")),
    ]
    for backend_enum, frontend_values in enum_pairs:
        backend_values = _extract_backend_enum_values(backend_enum)
        if backend_values != frontend_values:
            enum_errors.append(
                f"{backend_enum} mismatch: backend={sorted(backend_values)} frontend={sorted(frontend_values)}"
            )

    payment_frontend = _extract_interface_field_union(types_source, "Order", "payment_status")
    payment_backend = _extract_backend_enum_values("PaymentStatus")
    if payment_frontend != payment_backend:
        enum_errors.append(
            f"PaymentStatus mismatch: backend={sorted(payment_backend)} frontend={sorted(payment_frontend)}"
        )

    tx_frontend = _extract_interface_field_union(types_source, "FinancialTransaction", "type")
    tx_backend = _extract_backend_enum_values("FinancialTransactionType")
    if tx_frontend != tx_backend:
        enum_errors.append(
            f"FinancialTransactionType mismatch: backend={sorted(tx_backend)} frontend={sorted(tx_frontend)}"
        )

    print("Contract compatibility report:")
    print(f"- Frontend endpoints discovered: {len(frontend_endpoints)}")
    print(f"- Backend endpoints discovered: {len(backend_endpoints)}")

    if endpoint_errors:
        print("- Endpoint mismatches:")
        for item in endpoint_errors:
            print(f"  - {item}")
    if enum_errors:
        print("- Enum mismatches:")
        for item in enum_errors:
            print(f"  - {item}")

    if endpoint_errors or enum_errors:
        print("Contract compatibility gate failed.")
        return 1
    print("Contract compatibility gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
