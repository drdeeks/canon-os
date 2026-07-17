#!/usr/bin/env python3
"""Deliverable validator for the active Canon OS hackathon phase."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
REPO_ROOT = HACKATHON_ROOT.parents[1]
CHAIN_FILE = HACKATHON_ROOT / ".chain" / "blueprint-Canon-OS-Hackathon.json"
STATUS_FILE = CREW_ROOT / "shared" / "validation-status.json"
ARTIFACTS = HACKATHON_ROOT / "artifacts"


PHASE_CONTRACTS = {
    1: {
        "name": "Campaign Core",
        "files": [
            "phase-1/brand-profile.json",
            "phase-1/commercial-script.md",
            "phase-1/storyboard.md",
            "reviews/phase-1-campaign-core-review.md",
        ],
        "needles": {
            "phase-1/brand-profile.json": ["Canon OS Coffee", "brand_name"],
            "phase-1/commercial-script.md": ["Canon OS Coffee", "remote workers"],
            "phase-1/storyboard.md": ["Scene", "script"],
        },
    },
    2: {
        "name": "Creative and Platform Outputs",
        "files": [
            "phase-2/draft-creative-asset.md",
            "phase-2/short-commercial-fixture.md",
            "phase-2/platform-variants.json",
            "reviews/phase-2-creative-review.md",
        ],
        "needles": {
            "phase-2/draft-creative-asset.md": ["Demo fixture", "Canon OS Coffee"],
            "phase-2/short-commercial-fixture.md": ["Demo fixture", "provenance"],
            "phase-2/platform-variants.json": ["Instagram Reels", "TikTok", "LinkedIn"],
        },
    },
    3: {
        "name": "Campaign Results and Provenance",
        "files": [
            "phase-3/campaign-calendar.json",
            "phase-3/metrics-and-recommendation.md",
            "phase-3/backend-selection-status.md",
            "reviews/phase-3-provenance-review.md",
        ],
        "needles": {
            "phase-3/campaign-calendar.json": ["Instagram Reels", "TikTok", "LinkedIn"],
            "phase-3/metrics-and-recommendation.md": ["sample", "provenance"],
            "phase-3/backend-selection-status.md": ["demo-text", "demo-image", "demo-video"],
        },
    },
    4: {
        "name": "Product Quality and Evidence",
        "files": [
            "phase-4/responsive-accessibility-smoke.md",
            "phase-4/test-evidence.md",
            "phase-4/codex-gpt-evidence.md",
            "reviews/phase-4-quality-review.md",
        ],
        "needles": {
            "phase-4/responsive-accessibility-smoke.md": ["keyboard", "narrow viewport"],
            "phase-4/test-evidence.md": ["happy path", "failure path"],
            "phase-4/codex-gpt-evidence.md": ["Codex", "GPT-5.6"],
        },
    },
    5: {
        "name": "Submission and Director Review",
        "files": [
            "phase-5/demo-video-plan.md",
            "phase-5/devpost-submission-checklist.md",
            "phase-5/release-runbook.md",
            "reviews/phase-5-director-review.md",
        ],
        "needles": {
            "phase-5/demo-video-plan.md": ["three-minute", "Codex"],
            "phase-5/devpost-submission-checklist.md": ["Repository URL", "Demo video URL"],
            "phase-5/release-runbook.md": ["judge", "run"],
        },
    },
}


def write_status(payload: dict) -> None:
    payload["checked_at"] = datetime.now(timezone.utc).isoformat()
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def active_phase() -> int:
    chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    for step in chain.get("steps", []):
        if step.get("state") == "active":
            match = re.search(r"phase[-_](\d+)", Path(step.get("path", "")).name.lower())
            if match:
                return int(match.group(1))
    return 0


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
        non_demo = {k: v for k, v in data.get("backends", {}).items() if not str(v).startswith("demo-")}
        if non_demo:
            missing.append(f"provider-free config contains non-demo backends: {non_demo}")

    review_path = HACKATHON_ROOT / "reviews" / "phase-0-foundation-review.md"
    review = review_path.read_text(encoding="utf-8") if review_path.exists() else ""
    if "Reviewer status: approved" in review:
        return "ready_to_complete", missing, warnings
    warnings.append("PHASE-0.4 pending independent reviewer verification")
    return "pending_review", missing, warnings


def validate_contract(phase: int) -> tuple[str, list[str], list[str]]:
    if phase == 0:
        return phase0()

    contract = PHASE_CONTRACTS.get(phase)
    if not contract:
        return "blocked", [f"no validation contract for PHASE-{phase}"], []

    missing = []
    warnings = []
    for rel in contract["files"]:
        root = HACKATHON_ROOT if rel.startswith("reviews/") else ARTIFACTS
        path = root / rel
        if not path.exists():
            missing.append(str(path.relative_to(REPO_ROOT)))
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in contract.get("needles", {}).get(rel, []):
            if needle not in text:
                missing.append(f"{path.relative_to(REPO_ROOT)} missing {needle}")

    review_rel = contract["files"][-1]
    review_path = HACKATHON_ROOT / review_rel
    review = review_path.read_text(encoding="utf-8", errors="replace") if review_path.exists() else ""
    if missing:
        return "blocked", missing, warnings
    if "Reviewer status: approved" in review or "Director status: approved" in review:
        return "ready_to_complete", missing, warnings
    warnings.append(f"PHASE-{phase} pending automated reviewer verification")
    return "pending_review", missing, warnings


def main() -> int:
    phase = active_phase()
    status, missing, warnings = validate_contract(phase)
    if missing:
        status = "blocked"
    payload = {
        "phase": f"PHASE-{phase}",
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
