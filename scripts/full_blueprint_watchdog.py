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
AUTONOMY_STATUS = ROOT / ".agent" / "runtime" / "full-blueprint-autonomy-status.json"
STALE_AFTER_SECONDS = 180


def read_autonomy_status():
    if not AUTONOMY_STATUS.exists():
        return {"ok": False, "reason": "missing autonomy status"}
    try:
        payload = json.loads(AUTONOMY_STATUS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "reason": f"invalid autonomy status: {exc}"}

    heartbeat = payload.get("heartbeat_at")
    if not heartbeat:
        return {"ok": False, "reason": "missing autonomy heartbeat", "status": payload}

    try:
        heartbeat_dt = datetime.fromisoformat(heartbeat.replace("Z", "+00:00"))
    except ValueError as exc:
        return {"ok": False, "reason": f"invalid autonomy heartbeat: {exc}", "status": payload}

    age = int((datetime.now(timezone.utc) - heartbeat_dt).total_seconds())
    return {
        "ok": age <= STALE_AFTER_SECONDS,
        "heartbeat_age_seconds": age,
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "status": payload,
    }


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
    payload["autonomy"] = read_autonomy_status()
    payload["ok"] = payload["ok"] and payload["autonomy"].get("ok", False)
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
