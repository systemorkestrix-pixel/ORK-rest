import re
import unittest
from pathlib import Path


class Phase6DeadCodeCleanupTests(unittest.TestCase):
    @staticmethod
    def _src_root() -> Path:
        return Path(__file__).resolve().parents[2] / "src"

    def test_no_orphan_frontend_query_invalidations(self) -> None:
        src_root = self._src_root()
        query_keys: set[str] = set()
        invalidation_keys: set[str] = set()

        query_pattern = re.compile(r"^\s*queryKey:\s*\['([^']+)'", re.MULTILINE)
        invalidate_pattern = re.compile(r"invalidateQueries\(\{\s*queryKey:\s*\['([^']+)'")

        for file_path in src_root.rglob("*.ts*"):
            text = file_path.read_text(encoding="utf-8")
            query_keys.update(match.group(1) for match in query_pattern.finditer(text))
            invalidation_keys.update(match.group(1) for match in invalidate_pattern.finditer(text))

        orphan_keys = sorted(key for key in invalidation_keys if key not in query_keys)
        self.assertEqual(
            orphan_keys,
            [],
            msg=f"Found invalidation keys with no matching query key definitions: {orphan_keys}",
        )

    def test_deprecated_kitchen_orders_client_method_removed(self) -> None:
        client_file = self._src_root() / "shared" / "api" / "client.ts"
        text = client_file.read_text(encoding="utf-8")
        self.assertNotIn("kitchenOrders:", text)
        self.assertIn("kitchenOrdersPaged:", text)

    def test_delivery_panel_uses_shared_invalidation_helper(self) -> None:
        panel_file = self._src_root() / "modules" / "delivery" / "DeliveryPanelPage.tsx"
        text = panel_file.read_text(encoding="utf-8")
        self.assertIn("const invalidateDeliveryViews", text)
        self.assertNotIn("queryKey: ['manager-orders']", text)


if __name__ == "__main__":
    unittest.main()
