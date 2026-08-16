"""Delivery contract for the PHASE-0.2 foundation project tree."""

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Phase02ProjectStructureTest(unittest.TestCase):
    def test_required_project_directories_exist(self):
        """The Phase 0.2 tree gate requires source, test, and docs roots."""
        for directory in ("src", "tests", "docs"):
            with self.subTest(directory=directory):
                self.assertTrue((PROJECT_ROOT / directory).is_dir())

    def test_source_root_is_retained_in_version_control(self):
        source_readme = PROJECT_ROOT / "src" / "README.md"

        self.assertTrue(source_readme.is_file())
        self.assertTrue(source_readme.read_text().strip())


if __name__ == "__main__":
    unittest.main()
