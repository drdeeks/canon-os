"""Contract tests for the reproducible Phase 0 runnable-check command."""

import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "verify_phase_0_runnable.py"


class Phase011RunnableCheckTest(unittest.TestCase):
    def test_dry_run_lists_all_independent_review_checks(self):
        result = subprocess.run(
            [str(PROJECT_ROOT / ".venv" / "bin" / "python"), str(VERIFY_SCRIPT), "--dry-run"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("API unit and integration tests: npm test", result.stdout)
        self.assertIn("Dashboard and Phase 0 Python tests:", result.stdout)
        self.assertIn("docker compose config --quiet", result.stdout)
        self.assertIn("Phase 0 runnable checks: PASS", result.stdout)

    def test_tool_explicitly_preserves_independent_reviewer_authority(self):
        source = VERIFY_SCRIPT.read_text()

        self.assertIn("does not create the\nPhase 0 peer-review record", source)
        self.assertIn("independent reviewer", source)


if __name__ == "__main__":
    unittest.main()
