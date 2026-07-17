#!/usr/bin/env python3
"""Project poller that invokes the actual Codex runtime for active work."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
REPO_ROOT = HACKATHON_ROOT.parents[1]
SHARED = CREW_ROOT / "shared"
VALIDATION_STATUS = SHARED / "validation-status.json"
POLLER_STATUS = SHARED / "poller-status.json"
MODEL_MAP = SHARED / "agent-model-map.json"
TOKEN_FILE = SHARED / "token-usage.json"


PHASE_PROMPTS = {
    "PHASE-1": """Create the Phase 1 Campaign Core deliverables only.

Required files:
- docs/hackathon/artifacts/phase-1/brand-profile.json
- docs/hackathon/artifacts/phase-1/commercial-script.md
- docs/hackathon/artifacts/phase-1/storyboard.md
- docs/hackathon/reviews/phase-1-campaign-core-review.md

Use sample input: docs/Canon-Brand.PNG, brand Canon OS Coffee, brief "Launch a cozy morning subscription for local remote workers." Keep outputs provider-free and truthful. The review file should remain pending reviewer approval; the watcher approves after validation.""",
    "PHASE-2": """Create the Phase 2 Creative and Platform Outputs deliverables only.

Required files:
- docs/hackathon/artifacts/phase-2/draft-creative-asset.md
- docs/hackathon/artifacts/phase-2/short-commercial-fixture.md
- docs/hackathon/artifacts/phase-2/platform-variants.json
- docs/hackathon/reviews/phase-2-creative-review.md

Use explicit Demo fixture/sample provenance. Include Instagram Reels, TikTok, and LinkedIn variants. The review file should remain pending reviewer approval.""",
    "PHASE-3": """Create the Phase 3 Campaign Results and Provenance deliverables only.

Required files:
- docs/hackathon/artifacts/phase-3/campaign-calendar.json
- docs/hackathon/artifacts/phase-3/metrics-and-recommendation.md
- docs/hackathon/artifacts/phase-3/backend-selection-status.md
- docs/hackathon/reviews/phase-3-provenance-review.md

Use sample metrics only and label provenance. Include demo-text, demo-image, and demo-video backend status. The review file should remain pending reviewer approval.""",
    "PHASE-4": """Create the Phase 4 Product Quality and Evidence deliverables only.

Required files:
- docs/hackathon/artifacts/phase-4/responsive-accessibility-smoke.md
- docs/hackathon/artifacts/phase-4/test-evidence.md
- docs/hackathon/artifacts/phase-4/codex-gpt-evidence.md
- docs/hackathon/reviews/phase-4-quality-review.md

Document keyboard and narrow viewport checks, happy path and failure path evidence, and Codex/GPT-5.6 evidence. The review file should remain pending reviewer approval.""",
    "PHASE-5": """Create the Phase 5 Submission and Director Review deliverables only.

Required files:
- docs/hackathon/artifacts/phase-5/demo-video-plan.md
- docs/hackathon/artifacts/phase-5/devpost-submission-checklist.md
- docs/hackathon/artifacts/phase-5/release-runbook.md
- docs/hackathon/reviews/phase-5-director-review.md

Do not claim external URLs exist unless present. Use placeholders for repository URL, demo video URL, and Devpost fields that still need real external publication.""",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(payload: dict) -> None:
    payload["heartbeat_at"] = now()
    POLLER_STATUS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_phase() -> str | None:
    tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    if tokens.get("total_used", 0) >= tokens.get("hard_stop", 2250):
        return None
    if not VALIDATION_STATUS.exists():
        return None
    status = json.loads(VALIDATION_STATUS.read_text(encoding="utf-8"))
    if status.get("completion_allowed"):
        return None
    if status.get("status") != "blocked":
        return None
    return status.get("phase")


def invoke_codex(phase: str) -> dict:
    prompt = PHASE_PROMPTS.get(phase)
    if not prompt:
        return {"returncode": 2, "output": f"no runtime prompt for {phase}"}

    model_map = json.loads(MODEL_MAP.read_text(encoding="utf-8"))
    agent = model_map["agents"]["builder"]
    if agent.get("runtime") != "codex":
        return {"returncode": 2, "output": "builder runtime is not codex"}

    full_prompt = (
        "You are the Canon OS hackathon builder. Follow AGENTS.md and the "
        "hackathon checklist. Do not touch docs/Canon-Brand.PNG. Do not modify "
        "the master blueprint. Make only the requested phase deliverables. "
        "Commit nothing. Keep the work provider-free and evidence-backed.\n\n"
        + prompt
    )
    cmd = [
        "codex",
        "--ask-for-approval",
        "never",
        "exec",
        "--cd",
        str(REPO_ROOT),
        "--sandbox",
        "workspace-write",
        full_prompt,
    ]
    result = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=900,
        check=False,
    )
    output = result.stdout[-4000:]
    record_tokens(result.stdout)
    return {"returncode": result.returncode, "output": output}


def record_tokens(output: str) -> None:
    match = re.search(r"tokens used\s+([0-9,]+)", output, re.IGNORECASE)
    if not match:
        return
    used = int(match.group(1).replace(",", ""))
    tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    tokens["total_used"] = tokens.get("total_used", 0) + used
    tokens.setdefault("by_agent", {}).setdefault("builder", 0)
    tokens["by_agent"]["builder"] += used
    tokens["status"] = "hard_stop_exceeded" if tokens["total_used"] >= tokens.get("hard_stop", 2250) else "within_budget"
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    phase = load_phase()
    if not phase:
        payload = {"status": "idle", "reason": "no blocked active phase requiring runtime or token hard stop reached"}
        write_status(payload)
        print(json.dumps(payload, indent=2))
        return 0

    payload = {"status": "running", "phase": phase, "started_at": now()}
    write_status(payload)
    runtime = invoke_codex(phase)
    payload = {
        "status": "runtime_succeeded" if runtime["returncode"] == 0 else "runtime_failed",
        "phase": phase,
        "runtime": runtime,
    }
    write_status(payload)
    print(json.dumps(payload, indent=2))
    return 0 if runtime["returncode"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
