#!/usr/bin/env python3
"""Canon OS hackathon crew watcher.

Runs the autonomous-crew monitor contract for this repo:
- self-heal infrastructure
- dispatch exactly one active chain item
- validate active-phase deliverables
- write heartbeat/status for monitoring
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


CREW_ROOT = Path(__file__).resolve().parents[1]
SHARED = CREW_ROOT / "shared"
WATCHER_STATUS = SHARED / "watcher-status.json"


def run(cmd: list[str]) -> dict:
    result = subprocess.run(
        cmd,
        cwd=str(CREW_ROOT.parents[2]),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": result.returncode,
        "output": result.stdout.strip()[-2000:],
    }


def write_status(payload: dict) -> None:
    payload["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
    WATCHER_STATUS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def cycle() -> int:
    self_heal = run([sys.executable, str(CREW_ROOT / "scripts" / "self_heal.py")])
    dispatched = None
    validation = None

    if self_heal["returncode"] == 0:
        dispatched = run([sys.executable, str(CREW_ROOT / "scripts" / "run_loop.py")])
        validation = run([sys.executable, str(CREW_ROOT / "scripts" / "validate_active_phase.py")])

    status = "running"
    if self_heal["returncode"] != 0:
        status = "blocked_self_heal"
    elif dispatched and dispatched["returncode"] != 0:
        status = "blocked_dispatch"
    elif validation and validation["returncode"] != 0:
        status = "blocked_validation"

    payload = {
        "status": status,
        "self_heal": self_heal,
        "dispatch": dispatched,
        "validation": validation,
    }
    write_status(payload)
    print(json.dumps(payload, indent=2))
    return 0 if status == "running" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--cycles", type=int, default=1)
    args = parser.parse_args()

    count = 0
    last_rc = 0
    while args.cycles == 0 or count < args.cycles:
        last_rc = cycle()
        count += 1
        if args.cycles != 0 and count >= args.cycles:
            break
        time.sleep(args.interval)
    return last_rc


if __name__ == "__main__":
    sys.exit(main())
