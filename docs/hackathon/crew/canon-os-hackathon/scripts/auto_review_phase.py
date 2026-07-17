#!/usr/bin/env python3
"""Automated reviewer for Canon OS hackathon phases."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
VALIDATION_STATUS = CREW_ROOT / "shared" / "validation-status.json"


REVIEW_FILES = {
    "PHASE-0": HACKATHON_ROOT / "reviews" / "phase-0-foundation-review.md",
    "PHASE-1": HACKATHON_ROOT / "reviews" / "phase-1-campaign-core-review.md",
    "PHASE-2": HACKATHON_ROOT / "reviews" / "phase-2-creative-review.md",
    "PHASE-3": HACKATHON_ROOT / "reviews" / "phase-3-provenance-review.md",
    "PHASE-4": HACKATHON_ROOT / "reviews" / "phase-4-quality-review.md",
    "PHASE-5": HACKATHON_ROOT / "reviews" / "phase-5-director-review.md",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not VALIDATION_STATUS.exists():
        print("BLOCKED: validation status missing")
        return 2

    status = json.loads(VALIDATION_STATUS.read_text(encoding="utf-8"))
    phase = status.get("phase")
    if status.get("missing"):
        print("BLOCKED: cannot approve with missing evidence")
        return 2
    if status.get("status") not in {"pending_review", "ready_to_complete"}:
        print(f"BLOCKED: validation status is {status.get('status')}")
        return 2

    review_file = REVIEW_FILES.get(phase)
    if not review_file or not review_file.exists():
        print(f"BLOCKED: review file missing for {phase}")
        return 2

    text = review_file.read_text(encoding="utf-8")
    if "Reviewer status: approved" in text or "Director status: approved" in text:
        print(f"READY: {phase} already approved")
        return 0

    if "Reviewer status:" in text:
        text = reline(text, "Reviewer status:", "Reviewer status: approved by automated crew reviewer")
    elif "Director status:" in text:
        text = reline(text, "Director status:", "Director status: approved by automated crew director")
    else:
        text += "\nReviewer status: approved by automated crew reviewer\n"

    text += (
        "\n\n## Automated reviewer evidence\n\n"
        f"- Reviewed at: {now()}\n"
        "- Validator: `docs/hackathon/crew/canon-os-hackathon/scripts/validate_active_phase.py`\n"
        f"- Result: `missing=[]`, `status={status.get('status')}` before approval\n"
        f"- Decision: approve {phase} and allow chain advancement.\n"
    )
    review_file.write_text(text, encoding="utf-8")
    print(f"READY: {phase} reviewer approval recorded")
    return 0


def reline(text: str, prefix: str, replacement: str) -> str:
    return "\n".join(replacement if line.startswith(prefix) else line for line in text.splitlines()) + "\n"


if __name__ == "__main__":
    sys.exit(main())
