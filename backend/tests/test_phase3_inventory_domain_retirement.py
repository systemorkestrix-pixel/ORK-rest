from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"


class Phase3InventoryDomainRetirementTests(unittest.TestCase):
    @staticmethod
    def _service_files() -> list[Path]:
        services_dir = APP_DIR / "services"
        if not services_dir.exists():
            return []
        return sorted(services_dir.glob("*.py"))

    def test_services_no_longer_reference_legacy_inventory_models(self) -> None:
        service_files = self._service_files()
        if not service_files:
            self.assertFalse((APP_DIR / "services").exists())
            return
        content = "\n".join(path.read_text(encoding="utf-8") for path in service_files)
        self.assertNotIn("InventoryMovement", content)
        self.assertNotIn("SupplierReceipt", content)
        self.assertNotIn("WarehouseInboundVoucher", content)
        self.assertNotIn("WarehouseOutboundVoucher", content)
        self.assertNotIn("WarehouseStockLedger", content)
        self.assertNotIn("WarehouseStockCount", content)

    def test_seed_no_longer_bootstraps_legacy_inventory_domain(self) -> None:
        content = (APP_DIR / "seed.py").read_text(encoding="utf-8")
        self.assertNotIn("_seed_inventory_core", content)
        self.assertNotIn("InventoryWarehouse", content)
        self.assertNotIn("InventoryBalance", content)
        self.assertNotIn("Supplier(", content)

    def test_active_backend_modules_have_no_legacy_inventory_table_references(self) -> None:
        files_to_scan = [APP_DIR / "seed.py", APP_DIR / "warehouse_services.py"]
        files_to_scan.extend(self._service_files())
        files_to_scan.extend((APP_DIR / "routers").glob("*.py"))
        legacy_markers = (
            "inventory_warehouses",
            "inventory_balances",
            "inventory_movements",
            "supplier_receipts",
            "supplier_receipt_items",
        )
        for file_path in files_to_scan:
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8")
            for marker in legacy_markers:
                self.assertNotIn(
                    marker,
                    content,
                    msg=f"Legacy marker {marker!r} found in {file_path.relative_to(BACKEND_DIR)}",
                )

    def test_backend_no_longer_uses_product_resource_or_kitchen_component_contracts(self) -> None:
        files_to_scan = [
            APP_DIR / "models.py",
            APP_DIR / "schemas.py",
            APP_DIR / "seed.py",
            APP_DIR / "warehouse_services.py",
        ]
        files_to_scan.extend(self._service_files())
        files_to_scan.extend((APP_DIR / "routers").glob("*.py"))
        retired_markers = (
            "ProductResource",
            "KitchenResourceComponent",
            "product_resources",
            "kitchen_resource_components",
        )
        for file_path in files_to_scan:
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8")
            for marker in retired_markers:
                self.assertNotIn(
                    marker,
                    content,
                    msg=f"Retired contract marker {marker!r} found in {file_path.relative_to(BACKEND_DIR)}",
                )


if __name__ == "__main__":
    unittest.main()
