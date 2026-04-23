import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = REPO_ROOT / "backend" / "main.py"
SEED_PY = REPO_ROOT / "backend" / "app" / "seed.py"
MAINTENANCE_SCRIPT = REPO_ROOT / "backend" / "scripts" / "run_production_maintenance.py"


class Phase9ProductionStartupSplitContractTests(unittest.TestCase):
    def test_main_gates_heavy_startup_work_behind_flags(self) -> None:
        source = MAIN_PY.read_text(encoding="utf-8")
        required_fragments = [
            "if SETTINGS.run_startup_maintenance:",
            "bootstrap_production_maintenance(db)",
            "if SETTINGS.run_startup_tenant_sync:",
            'sync_all_tenant_tables(db, table_names=["restaurant_employees"])',
            "if SETTINGS.run_startup_integrity_checks:",
            "run_startup_integrity_checks(engine)",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_production_bootstrap_is_lightweight_and_maintenance_stays_separate(self) -> None:
        source = SEED_PY.read_text(encoding="utf-8")
        self.assertIn("def bootstrap_production_maintenance(db: Session) -> None:", source)
        self.assertIn("def bootstrap_production_data(db: Session) -> None:", source)
        self.assertIn("_run_common_bootstrap(db, allow_schema_mutation=False)", source)
        self.assertIn("_assert_schema_matches_models(db)", source)

        bootstrap_body = source.split("def bootstrap_production_data(db: Session) -> None:", 1)[1]
        bootstrap_body = bootstrap_body.split("def seed_initial_data(db: Session) -> None:", 1)[0]
        self.assertNotIn("_run_common_bootstrap(db, allow_schema_mutation=False)", bootstrap_body)
        self.assertIn("_assert_schema_matches_models(db)", bootstrap_body)
        self.assertIn("_seed_initial_manager_for_production(db)", bootstrap_body)

    def test_manual_maintenance_script_runs_heavy_path_outside_startup(self) -> None:
        source = MAINTENANCE_SCRIPT.read_text(encoding="utf-8")
        required_fragments = [
            "assert_production_migration_state(",
            "bootstrap_production_maintenance(db)",
            'sync_all_tenant_tables(db, table_names=["restaurant_employees"])',
            "run_startup_integrity_checks(engine)",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
