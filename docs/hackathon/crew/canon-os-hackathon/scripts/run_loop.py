#!/usr/bin/env python3
"""Serialized hackathon loop runner.

This dispatches exactly one active chain item at a time into the shared crew
workspace. It does not mark work complete; verification remains explicit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
SHARED = CREW_ROOT / "shared"
CHAIN_FILE = HACKATHON_ROOT / ".chain" / "blueprint-Canon-OS-Hackathon.json"
CHECKLIST_FILE = HACKATHON_ROOT / "checklist.md"
CURRENT_TASK = SHARED / "current-task.md"
RUN_STATE = SHARED / "loop-state.json"
TOKEN_FILE = SHARED / "token-usage.json"
PHASE0_REVIEW = HACKATHON_ROOT / "reviews" / "phase-0-foundation-review.md"
PHASE0_EVIDENCE = [
    HACKATHON_ROOT / "PHASE_0_RUNBOOK.md",
    HACKATHON_ROOT / "HACKATHON_STANDARDS.md",
    HACKATHON_ROOT / "CODEX_BUILD_LOG.md",
    HACKATHON_ROOT / "provider-free-backends.json",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def task_title(step: dict) -> str:
    name = Path(step["path"]).name
    if "-" in name:
        return name.replace("-", " ")
    return name


def role_for(step: dict) -> str:
    title = task_title(step).lower()
    if "review" in title or "validation gate" in title:
        return "reviewer"
    if "director" in title or "phase 05" in title or "phase 5" in title:
        return "director"
    if "phase 00" in title and phase0_ready_for_review():
        return "reviewer"
    return "builder"


def phase0_ready_for_review() -> bool:
    if not all(path.exists() for path in PHASE0_EVIDENCE):
        return False
    if not PHASE0_REVIEW.exists():
        return False
    review = PHASE0_REVIEW.read_text(encoding="utf-8")
    return "pending independent peer review" in review


def run_self_heal() -> int:
    result = subprocess.run(
        [sys.executable, str(CREW_ROOT / "scripts" / "self_heal.py")],
        cwd=str(CREW_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout.strip())
    return result.returncode


def dispatch_once() -> int:
    if run_self_heal() != 0:
        return 2

    chain = load_json(CHAIN_FILE)
    tokens = load_json(TOKEN_FILE)
    if tokens.get("total_used", 0) >= tokens.get("hard_stop", 2250):
        print("BLOCKED: token hard stop reached")
        return 2

    active = [step for step in chain["steps"] if step.get("state") == "active"][0]
    role = role_for(active)
    now = datetime.now(timezone.utc).isoformat()
    title = task_title(active)

    packet = f"""# Current Crew Task

Dispatched: {now}
Crew: canon-os-hackathon
Role: {role}
Mode: serialized shared workspace
Token hard stop: {tokens.get("hard_stop", 2250)}

## Active Chain Item

- Index: {active["index"]}
- Title: {title}
- Marker: `{active["path"]}`

## Source Of Truth

- Hackathon blueprint: `{HACKATHON_ROOT / "CANON_OS_HACKATHON_BLUEPRINT.md"}`
- Checklist: `{CHECKLIST_FILE}`
- Standards: `{HACKATHON_ROOT / "HACKATHON_STANDARDS.md"}`

## Required Behavior

Work only on this active item. Do not unlock later phases. Do not mark the item
complete unless its gate evidence exists and peer/director verification has run.
Record evidence in `docs/hackathon/CODEX_BUILD_LOG.md`.
"""
    CURRENT_TASK.write_text(packet, encoding="utf-8")

    state = {
        "status": "running",
        "started_at": now,
        "active_agent": role,
        "active_step": active,
        "current_task": str(CURRENT_TASK),
        "token_usage": tokens,
    }
    write_json(RUN_STATE, state)
    print(f"DISPATCHED: {role} -> {title}")
    return 0


if __name__ == "__main__":
    sys.exit(dispatch_once())
