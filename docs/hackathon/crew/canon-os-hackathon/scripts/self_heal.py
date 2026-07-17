#!/usr/bin/env python3
"""Safe self-healing checks for the Canon OS hackathon crew."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
HACKATHON_ROOT = CREW_ROOT.parents[1]
SHARED = CREW_ROOT / "shared"
TOKEN_FILE = SHARED / "token-usage.json"
STATUS_FILE = SHARED / "self-healing-status.json"
KNOWLEDGE_FILE = SHARED / "knowledge-index.json"
CHAIN_FILE = HACKATHON_ROOT / ".chain" / "blueprint-Canon-OS-Hackathon.json"


def load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> int:
    repaired = []
    blocked = []

    if not KNOWLEDGE_FILE.exists():
        write_json(
            KNOWLEDGE_FILE,
            {
                "crew_id": "canon-os-hackathon",
                "shared_workspace": str(CREW_ROOT),
                "notes": [],
            },
        )
        repaired.append("restored missing shared knowledge index")

    tokens = load_json(
        TOKEN_FILE,
        {
            "total_used": 0,
            "hard_stop": 2250,
            "status": "within_budget",
            "by_agent": {"builder": 0, "reviewer": 0, "director": 0},
        },
    )
    if tokens.get("total_used", 0) >= tokens.get("hard_stop", 2250):
        blocked.append("token use is at or above hard stop")

    chain = load_json(CHAIN_FILE, {"steps": []})
    active_steps = [step for step in chain.get("steps", []) if step.get("state") == "active"]
    if len(active_steps) != 1:
        blocked.append(f"expected exactly one active chain step, found {len(active_steps)}")

    status = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blocked else "ready",
        "blocked": blocked,
        "repaired": repaired,
        "active_step": active_steps[0] if len(active_steps) == 1 else None,
        "token_usage": tokens,
    }
    write_json(STATUS_FILE, status)

    if blocked:
        print("BLOCKED: " + "; ".join(blocked))
        return 2
    print("READY: self-healing checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
