"""Foundation liveness contract for the dashboard container."""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app" / "dashboard"))

from app import app  # noqa: E402


class DashboardHealthTest(unittest.TestCase):
    def test_health_returns_ok(self):
        response = app.test_client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
