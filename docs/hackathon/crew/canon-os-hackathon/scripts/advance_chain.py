#!/usr/bin/env python3
"""Advance the Canon OS hackathon chain after validator approval."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
CHAIN_FILE = HACKATHON_ROOT / ".chain" / "blueprint-Canon-OS-Hackathon.json"
VALIDATION_STATUS = CREW_ROOT / "shared" / "validation-status.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    status = json.loads(VALIDATION_STATUS.read_text(encoding="utf-8"))
    if not status.get("completion_allowed"):
        print("BLOCKED: validation has not allowed completion")
        return 2

    chain = json.loads(CHAIN_FILE.read_text(encoding="utf-8"))
    steps = chain.get("steps", [])
    if len(steps) < 7:
        print("BLOCKED: chain does not contain expected Phase 0/Phase 1 steps")
        return 2

    changed = False
    stamp = now()
    # Phase 0 container + four tasks + validation gate.
    for index in range(0, 6):
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

    if steps[6].get("state") != "active":
        steps[6]["state"] = "active"
        steps[6]["activated_at"] = stamp
        changed = True

    if changed:
        CHAIN_FILE.write_text(json.dumps(chain, indent=2) + "\n", encoding="utf-8")
        print("READY: completed Phase 0 and activated Phase 1")
    else:
        print("READY: chain already advanced past Phase 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
