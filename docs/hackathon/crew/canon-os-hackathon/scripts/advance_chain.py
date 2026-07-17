#!/usr/bin/env python3
"""Advance the Canon OS hackathon chain after validator approval."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
CHAIN_FILE = HACKATHON_ROOT / ".chain" / "blueprint-Canon-OS-Hackathon.json"
VALIDATION_STATUS = CREW_ROOT / "shared" / "validation-status.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def step_phase(step: dict) -> int | None:
    match = re.search(r"phase[-_](\d+)", Path(step.get("path", "")).name.lower())
    return int(match.group(1)) if match else None


def main() -> int:
    status = json.loads(VALIDATION_STATUS.read_text(encoding="utf-8"))
    if not status.get("completion_allowed"):
        print("BLOCKED: validation has not allowed completion")
        return 2
    phase = int(str(status["phase"]).split("-")[-1])

    chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    steps = chain.get("steps", [])
    matching = [index for index, step in enumerate(steps) if step_phase(step) == phase]
    if not matching:
        print(f"BLOCKED: no chain steps found for PHASE-{phase}")
        return 2

    stamp = now()
    changed = False
    for index in matching:
        step = steps[index]
        if step.get("state") != "complete":
            step["state"] = "complete"
            step["verified_at"] = stamp
            step["completed_at"] = stamp
            step["attempts"] = step.get("attempts", 0) + 1
            marker = Path(step["path"])
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(f"completed by autonomous crew watcher at {stamp}\n", encoding="utf-8")
            changed = True

    next_phase = phase + 1
    for step in steps:
        if step_phase(step) == next_phase and "step-" not in Path(step.get("path", "")).name.lower():
            if step.get("state") != "active":
                step["state"] = "active"
                step["activated_at"] = stamp
                changed = True
            break

    if changed:
        CHAIN_FILE.write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")
        print(f"READY: completed Phase {phase} and activated Phase {next_phase}")
    else:
        print(f"READY: Phase {phase} chain already advanced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
