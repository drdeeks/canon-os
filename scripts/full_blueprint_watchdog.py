#!/usr/bin/env python3
"""Agent watchdog for the full Canon OS blueprint chain."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / ".agent" / "runtime" / "full-blueprint-watchdog-status.json"


def status_once():
    p = subprocess.run([sys.executable, "scripts/full_blueprint_status.py"], cwd=ROOT, text=True, capture_output=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "command": "scripts/full_blueprint_status.py",
        "exit_code": p.returncode,
        "ok": p.returncode == 0,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }
    try:
        payload["status"] = json.loads(payload["stdout"]) if payload["stdout"] else {}
    except json.JSONDecodeError as exc:
        payload["ok"] = False
        payload["parse_error"] = str(exc)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--cycles", type=int, default=1, help="0 means run forever")
    args = ap.parse_args()

    count = 0
    worst = 0
    while args.cycles == 0 or count < args.cycles:
        worst = max(worst, status_once())
        count += 1
        if args.cycles == 0 or count < args.cycles:
            time.sleep(args.interval)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
