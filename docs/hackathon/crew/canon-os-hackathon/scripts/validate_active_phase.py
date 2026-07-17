#!/usr/bin/env python3
"""Deliverable validator for the active Canon OS hackathon phase."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
REPO_ROOT = HACKATHON_ROOT.parents[1]
STATUS_FILE = CREW_ROOT / "shared" / "validation-status.json"


def write_status(payload: dict) -> None:
    payload["checked_at"] = datetime.now(timezone.utc).isoformat()
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def phase0() -> tuple[str, list[str], list[str]]:
    missing = []
    warnings = []

    required = [
        HACKATHON_ROOT / "PHASE_0_RUNBOOK.md",
        HACKATHON_ROOT / "HACKATHON_STANDARDS.md",
        HACKATHON_ROOT / "CODEX_BUILD_LOG.md",
        HACKATHON_ROOT / "provider-free-backends.json",
        HACKATHON_ROOT / "reviews" / "phase-0-foundation-review.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "app" / "dashboard" / "backends" / "demo.py",
        REPO_ROOT / "docs" / "Canon-Brand.PNG",
    ]
    for path in required:
        if not path.exists():
            missing.append(str(path.relative_to(REPO_ROOT)))

    provider_file = HACKATHON_ROOT / "provider-free-backends.json"
    if provider_file.exists():
        data = json.loads(provider_file.read_text(encoding="utf-8"))
        backends = data.get("backends", {})
        non_demo = {key: value for key, value in backends.items() if not str(value).startswith("demo-")}
        if non_demo:
            missing.append(f"provider-free config contains non-demo backends: {non_demo}")

    runbook = (HACKATHON_ROOT / "PHASE_0_RUNBOOK.md").read_text(encoding="utf-8") if (HACKATHON_ROOT / "PHASE_0_RUNBOOK.md").exists() else ""
    for needle in ["STUDIO_CONFIG", "provider-free-backends.json", "docs/Canon-Brand.PNG", "curl -fsS"]:
        if needle not in runbook:
            missing.append(f"PHASE_0_RUNBOOK.md missing {needle}")

    build_log = (HACKATHON_ROOT / "CODEX_BUILD_LOG.md").read_text(encoding="utf-8") if (HACKATHON_ROOT / "CODEX_BUILD_LOG.md").exists() else ""
    if "PHASE-0.1, PHASE-0.2, and PHASE-0.3 have creator evidence" not in build_log:
        missing.append("CODEX_BUILD_LOG.md missing Phase 0 creator-evidence status")

    review_path = HACKATHON_ROOT / "reviews" / "phase-0-foundation-review.md"
    review = review_path.read_text(encoding="utf-8") if review_path.exists() else ""
    if "Reviewer status: pending independent peer review" in review:
        warnings.append("PHASE-0.4 pending independent reviewer verification")
        return "pending_review", missing, warnings
    if "Reviewer status: approved" in review or "Independent review result: approved" in review:
        return "ready_to_complete", missing, warnings
    warnings.append("Phase 0 review status is unclear")
    return "pending_review", missing, warnings


def main() -> int:
    status, missing, warnings = phase0()
    if missing:
        status = "blocked"
    payload = {
        "phase": "PHASE-0",
        "status": status,
        "missing": missing,
        "warnings": warnings,
        "completion_allowed": status == "ready_to_complete" and not missing,
    }
    write_status(payload)
    print(json.dumps(payload, indent=2))
    return 0 if status != "blocked" else 2


if __name__ == "__main__":
    sys.exit(main())
