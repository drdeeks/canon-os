#!/usr/bin/env python3
"""Validate the Phase 0 peer-review gate without authoring a review decision.

The Phase 0 blueprint gate is "reviewer confirms runnable".  This command
only verifies that an independent PASS decision already exists and re-runs the
reproducible checks prepared for that decision.  It never creates or edits a
review record.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_RECORD = (
    PROJECT_ROOT
    / "docs"
    / "autonomy"
    / "reviews"
    / "11-phase-00-step-11-PHASE-0.11-reviews-phase-0-verify.md.md"
)
RUNNABLE_VERIFIER = PROJECT_ROOT / "scripts" / "verify_phase_0_runnable.py"


def validate_review_record(record: Path) -> tuple[bool, str]:
    """Confirm a non-empty, independent Phase 0 PASS record is available."""
    if not record.is_file():
        return False, f"FAIL: independent review record not found: {record}"

    content = record.read_text(encoding="utf-8").strip()
    if not content:
        return False, f"FAIL: independent review record is empty: {record}"
    if "reviewer confirms runnable" not in content:
        return False, "FAIL: review record does not cover the Phase 0 validation gate"
    if "VERDICT: PASS" not in content:
        return False, "FAIL: independent review record has no PASS verdict"

    try:
        display_path = record.relative_to(PROJECT_ROOT)
    except ValueError:
        display_path = record
    return True, f"PASS: independent Phase 0 review record: {display_path}"


def run_runnable_checks() -> tuple[bool, str]:
    """Run the pre-existing reproducible checks used by the reviewer."""
    python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not python.is_file():
        return False, "FAIL: .venv/bin/python is required for dashboard checks"

    result = subprocess.run(
        [str(python), str(RUNNABLE_VERIFIER)],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode:
        return False, f"FAIL: Phase 0 runnable checks exited {result.returncode}"
    return True, "PASS: Phase 0 runnable checks"


def main() -> int:
    review_ok, review_message = validate_review_record(REVIEW_RECORD)
    print(review_message)
    if not review_ok:
        return 1

    checks_ok, checks_message = run_runnable_checks()
    print(checks_message)
    if not checks_ok:
        return 1

    print("PASS: Phase 0 validation gate satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
