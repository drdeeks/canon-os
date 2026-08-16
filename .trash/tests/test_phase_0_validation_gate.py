"""Contracts for the Phase 0 validation-gate command."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "validate_phase_0_gate.py"
SPEC = importlib.util.spec_from_file_location("phase_0_gate", SCRIPT)
assert SPEC and SPEC.loader
phase_0_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase_0_gate)


class Phase0ValidationGateTest(unittest.TestCase):
    def test_review_record_requires_the_exact_gate_and_independent_pass(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            record = Path(temporary_directory) / "review.md"

            record.write_text("reviewer confirms runnable\nVERDICT: PASS\n")
            self.assertTrue(phase_0_gate.validate_review_record(record)[0])

            record.write_text("reviewer confirms runnable\n")
            self.assertFalse(phase_0_gate.validate_review_record(record)[0])

            record.write_text("VERDICT: PASS\n")
            self.assertFalse(phase_0_gate.validate_review_record(record)[0])

    def test_gate_is_read_only_with_respect_to_the_reviewer_record(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("It never creates or edits a\nreview record", source)
        self.assertNotIn("write_text(", source)
        self.assertNotIn("open(REVIEW_RECORD", source)


if __name__ == "__main__":
    unittest.main()
