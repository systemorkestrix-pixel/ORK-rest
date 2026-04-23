import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RENDER_YAML = REPO_ROOT / "render.yaml"
BACKEND_ENV_EXAMPLE = REPO_ROOT / "backend" / ".env.example"


class Phase9RenderBlueprintContractTests(unittest.TestCase):
    def test_render_yaml_declares_required_api_environment(self) -> None:
        source = RENDER_YAML.read_text(encoding="utf-8")
        required_fragments = [
            "name: restaurants-api",
            "healthCheckPath: /health",
            "buildCommand: ./build.sh",
            "startCommand: ./start.sh",
            "- key: APP_ENV",
            "value: production",
            "- key: EXPOSE_DIAGNOSTIC_ENDPOINTS",
            'value: "true"',
            "- key: RUN_STARTUP_MAINTENANCE",
            "- key: RUN_STARTUP_TENANT_SYNC",
            "- key: RUN_STARTUP_INTEGRITY_CHECKS",
            "- key: DATABASE_URL",
            "- key: JWT_SECRET",
            "- key: SECRET_KEY",
            "- key: MASTER_ADMIN_USERNAME",
            "- key: MASTER_ADMIN_PASSWORD",
            "- key: ADMIN_USERNAME",
            "- key: ADMIN_PASSWORD",
            "name: restaurants-console",
            "VITE_API_BASE_URL",
            "https://restaurants-api.onrender.com/api",
            "source: /*",
            "destination: /index.html",
        ]
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_backend_env_example_matches_production_bootstrap_requirements(self) -> None:
        source = BACKEND_ENV_EXAMPLE.read_text(encoding="utf-8")
        required_assignments = [
            "APP_ENV=production",
            "EXPOSE_DIAGNOSTIC_ENDPOINTS=true",
            "JWT_SECRET=",
            "SECRET_KEY=",
            "MASTER_ADMIN_USERNAME=",
            "MASTER_ADMIN_PASSWORD=",
            "ADMIN_USERNAME=",
            "ADMIN_PASSWORD=",
            "DATABASE_URL=postgresql+psycopg://postgres:[PASSWORD]@[HOST]:6543/postgres?sslmode=require",
            "RUN_STARTUP_MAINTENANCE=false",
            "RUN_STARTUP_TENANT_SYNC=false",
            "RUN_STARTUP_INTEGRITY_CHECKS=false",
            "python backend/scripts/run_production_maintenance.py",
            "CORS_ALLOW_ORIGINS=https://restaurants-console.onrender.com",
        ]
        for assignment in required_assignments:
            with self.subTest(assignment=assignment):
                self.assertIn(assignment, source)

    def test_render_blueprint_keeps_console_and_api_names_stable(self) -> None:
        source = RENDER_YAML.read_text(encoding="utf-8")
        api_name_match = re.search(r"name:\s+restaurants-api", source)
        console_name_match = re.search(r"name:\s+restaurants-console", source)
        self.assertIsNotNone(api_name_match)
        self.assertIsNotNone(console_name_match)


if __name__ == "__main__":
    unittest.main()
