import ast
import re
import unittest
from pathlib import Path


class Phase6ServiceBoundariesTests(unittest.TestCase):
    @staticmethod
    def _backend_root() -> Path:
        return Path(__file__).resolve().parents[1]

    @classmethod
    def _services_dir(cls) -> Path:
        return cls._backend_root() / "app" / "services"

    @classmethod
    def _domain_service_files(cls) -> list[Path]:
        return sorted(
            path
            for path in cls._services_dir().glob("*_service.py")
            if path.name != "shared.py"
        )

    def test_services_monolith_removed(self) -> None:
        self.assertFalse((self._backend_root() / "app" / "services.py").exists())

    def test_each_domain_service_within_line_budget(self) -> None:
        oversized: list[str] = []
        for path in self._domain_service_files():
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > 800:
                oversized.append(f"{path.name} ({line_count} lines)")
        self.assertEqual(
            oversized,
            [],
            msg=f"Domain services over 800 lines: {', '.join(oversized)}",
        )

    def test_no_direct_cross_domain_imports(self) -> None:
        violations: list[str] = []
        domain_names = {path.stem for path in self._domain_service_files()}

        for path in self._domain_service_files():
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            current_domain = path.stem
            other_domains = domain_names - {current_domain}

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if node.level == 1 and module in other_domains:
                        violations.append(f"{path.name}:{node.lineno} from .{module} import ...")
                    if node.level == 0 and re.search(r"\.services\.[a-z_]+_service$", module):
                        imported_domain = module.rsplit(".", 1)[-1]
                        if imported_domain in other_domains:
                            violations.append(f"{path.name}:{node.lineno} from {module} import ...")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                        if re.search(r"\.services\.[a-z_]+_service$", module):
                            imported_domain = module.rsplit(".", 1)[-1]
                            if imported_domain in other_domains:
                                violations.append(f"{path.name}:{node.lineno} import {module}")

        self.assertEqual(
            violations,
            [],
            msg="Direct cross-domain imports detected:\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
