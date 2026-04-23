import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_DIR / "alembic" / "versions"


class Phase9PostgresMigrationContractTests(unittest.TestCase):
    def _read(self, filename: str) -> str:
        return (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")

    def test_partial_unique_indexes_define_postgresql_predicates(self) -> None:
        source = self._read("82bb321c5322_p2_2_constraints_indexes.py")
        self.assertIn("postgresql_where=EXPENSE_PARTIAL_PREDICATE", source)
        self.assertIn("postgresql_where=REFUND_PARTIAL_PREDICATE", source)
        self.assertIn("postgresql_where=SALE_PARTIAL_PREDICATE", source)
        self.assertNotIn("drop_index('ux_financial_transactions_sale_order', sqlite_where=", source)
        self.assertIn("SELECT :default_name, TRUE, 9999", source)

    def test_boolean_defaults_use_true_false_literals(self) -> None:
        files = [
            "d5e6f7a8b9c0_p5_1_primary_secondary_products_and_consumption_links.py",
            "e60afb356e90_add_delivery_zone_pricing.py",
            "f1a2b3c4d5e6_p6_1_manual_delivery_address_nodes.py",
        ]
        combined = "\n".join(self._read(filename) for filename in files)
        self.assertNotIn('server_default=sa.text("1")', combined)
        self.assertNotIn('server_default=sa.text("0")', combined)
        self.assertIn('server_default=sa.text("false")', combined)
        self.assertIn('server_default=sa.text("true")', combined)

    def test_postgres_safe_boolean_updates_and_insert_returning(self) -> None:
        pricing_fix = self._read("0a1e2e9b1656_fix_delivery_zone_pricing.py")
        provider_seed = self._read("b7c8d9e0f1a2_p6_3_delivery_providers_internal_default.py")
        self.assertIn("SET active = COALESCE(active, is_active, TRUE)", pricing_fix)
        self.assertIn("SET active = TRUE", pricing_fix)
        self.assertIn("is_internal_default = TRUE", provider_seed)
        self.assertIn("RETURNING id", provider_seed)
        self.assertNotIn("lastrowid", provider_seed)


if __name__ == "__main__":
    unittest.main()
