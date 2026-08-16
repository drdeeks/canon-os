"""Static delivery contracts for the PHASE-0.1 Docker and CI assets."""

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Phase01DeliveryTest(unittest.TestCase):
    def test_dashboard_image_checks_the_liveness_endpoint(self):
        dockerfile = (PROJECT_ROOT / "app" / "dashboard" / "Dockerfile").read_text()

        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("http://localhost:5000/health", dockerfile)
        self.assertIn('CMD ["gunicorn"', dockerfile)

    def test_ci_validates_blueprint_and_exercises_container_health(self):
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()

        self.assertIn("validate_blueprint.py blueprint.md", workflow)
        self.assertIn("docker build --tag canon-os-dashboard:ci app/dashboard", workflow)
        self.assertIn("docker run --detach --rm --name canon-os-dashboard-ci", workflow)
        self.assertIn("http://127.0.0.1:5000/health", workflow)


if __name__ == "__main__":
    unittest.main()
