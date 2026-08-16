#!/usr/bin/env python3
"""Report full blueprint enforcement health as JSON."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / ".chain" / "blueprint-Canon-OS.json"
CHECKLIST = ROOT / "checklist-data.json"
BLUEPRINT = ROOT / "blueprint.md"
VALIDATORS = ROOT / ".blueprint-chain" / "validators"


def run(cmd):
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return {"code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def main():
    problems = []
    if not BLUEPRINT.exists():
        problems.append("missing blueprint.md")
    if not CHECKLIST.exists():
        problems.append("missing checklist-data.json")
    if not CHAIN.exists():
        problems.append("missing .chain/blueprint-Canon-OS.json")

    checklist = json.loads(CHECKLIST.read_text()) if CHECKLIST.exists() else {}
    chain = json.loads(CHAIN.read_text()) if CHAIN.exists() else {"steps": []}
    steps = chain.get("steps", [])
    counts = {}
    for step in steps:
        counts[step["state"]] = counts.get(step["state"], 0) + 1

    active = [s for s in steps if s.get("state") == "active"]
    verified = [s for s in steps if s.get("state") == "verified"]
    if len(active) > 1:
        problems.append(f"multiple active steps: {len(active)}")
    if not active and counts.get("complete") != len(steps):
        problems.append("no active step and chain is incomplete")

    validators = sorted(VALIDATORS.glob("validate_phase*_blueprint.py")) if VALIDATORS.exists() else []
    if len(validators) < len(checklist.get("phases", [])):
        problems.append("validator count is below phase count")

    blueprint_check = run([sys.executable, "utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py", "blueprint.md", "--json"])
    if blueprint_check["code"] != 0:
        problems.append("blueprint validator failed to run")
    else:
        try:
            summary = json.loads(blueprint_check["stdout"])["summary"]
            if summary.get("failed", 1) != 0:
                problems.append(f"blueprint validation failures: {summary.get('failed')}")
        except Exception as exc:
            problems.append(f"blueprint validator JSON parse failed: {exc}")

    result = {
        "ok": not problems,
        "chain": chain.get("name", "blueprint-Canon-OS"),
        "steps_total": len(steps),
        "counts": counts,
        "active": [Path(s["path"]).name for s in active],
        "verified_waiting_completion": [Path(s["path"]).name for s in verified],
        "checklist": {
            "phases": len(checklist.get("phases", [])),
            "tasks": sum(len(p.get("tasks", [])) for p in checklist.get("phases", [])),
            "modules": len(checklist.get("modules", [])),
            "screens": len(checklist.get("screens", [])),
        },
        "validators": len(validators),
        "problems": problems,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
