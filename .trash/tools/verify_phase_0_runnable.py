#!/usr/bin/env python3
"""Run the reproducible checks an independent Phase 0 reviewer needs.

This tool deliberately reports test results only.  It does not create the
Phase 0 peer-review record or make a reviewer decision; that remains the
responsibility of the independent reviewer required by the blueprint.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    """A named, reproducible Phase 0 verification command."""

    name: str
    command: tuple[str, ...]


CHECKS = (
    Check("API unit and integration tests", ("npm", "test")),
    Check(
        "Dashboard and Phase 0 Python tests",
        (
            str(PROJECT_ROOT / ".venv" / "bin" / "python"),
            "-m",
            "unittest",
            "discover",
            "--start-directory",
            "tests",
            "--pattern",
            "test_*.py",
            "--verbose",
        ),
    ),
    Check("Compose configuration", ("docker", "compose", "config", "--quiet")),
)


def run_check(check: Check, *, dry_run: bool) -> bool:
    """Run one check and return whether it passed."""
    command_text = " ".join(check.command)
    print(f"{check.name}: {command_text}")
    if dry_run:
        return True

    working_directory = PROJECT_ROOT / "api" if check.command[:2] == ("npm", "test") else PROJECT_ROOT
    result = subprocess.run(check.command, cwd=working_directory, check=False)
    status = "PASS" if result.returncode == 0 else f"FAIL (exit {result.returncode})"
    print(f"{check.name}: {status}")
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print checks without executing them")
    args = parser.parse_args()

    if not (PROJECT_ROOT / ".venv" / "bin" / "python").is_file():
        print("FAIL: .venv/bin/python is required for dashboard checks", file=sys.stderr)
        return 1

    passed = all(run_check(check, dry_run=args.dry_run) for check in CHECKS)
    print("Phase 0 runnable checks: PASS" if passed else "Phase 0 runnable checks: FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
