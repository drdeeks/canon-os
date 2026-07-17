#!/usr/bin/env python3
"""Autonomous builder/reviewer loop for the Canon OS full blueprint.

The loop owns one active blueprint-chain item at a time.  A builder Codex
session implements it, a fresh reviewer Codex session checks it, and only an
explicit PASS review permits the chain to advance.  It is safe to leave this
process running: incomplete work remains active and is retried with evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAIN_NAME = "blueprint-Canon-OS"
CHAIN_FILE = ROOT / ".chain" / f"{CHAIN_NAME}.json"
RUNTIME = ROOT / ".agent" / "runtime"
STATUS_FILE = RUNTIME / "full-blueprint-autonomy-status.json"
RETRY_FILE = RUNTIME / "full-blueprint-autonomy-retries.json"
ENV_CACHE_FILE = RUNTIME / "full-blueprint-environment-cache.json"
EVIDENCE_DIR = ROOT / "docs" / "autonomy" / "evidence"
REVIEW_DIR = ROOT / "docs" / "autonomy" / "reviews"
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
DASHBOARD_REQUIREMENTS = ROOT / "app" / "dashboard" / "requirements.txt"
MAX_ATTEMPTS = 3
CHILD_HEARTBEAT_SECONDS = 15
TERMINATE_GRACE_SECONDS = 10
BUILDER_TIMEOUT_SECONDS = 1200
REVIEWER_TIMEOUT_SECONDS = 900


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_chain() -> dict:
    return json.loads(CHAIN_FILE.read_text(encoding="utf-8"))


def load_retries() -> dict:
    if not RETRY_FILE.exists():
        return {}
    try:
        return json.loads(RETRY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_env_cache() -> dict:
    if not ENV_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(ENV_CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def retries_for(step: dict) -> int:
    return int(load_retries().get(str(step["index"]), 0))


def increment_retry(step: dict) -> int:
    retries = load_retries()
    key = str(step["index"])
    retries[key] = int(retries.get(key, 0)) + 1
    write_json(RETRY_FILE, retries)
    return retries[key]


def clear_retry(step: dict) -> None:
    retries = load_retries()
    retries.pop(str(step["index"]), None)
    write_json(RETRY_FILE, retries)


def active_step(chain: dict) -> dict | None:
    active = [step for step in chain.get("steps", []) if step.get("state") == "active"]
    if len(active) != 1:
        return None
    return active[0]


def slug(step: dict) -> str:
    return f"{step['index']:02d}-{Path(step['path']).name}"


def compact_title(step: dict) -> str:
    return Path(step["path"]).name.replace("-", " ")


def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_local(command: list[str], timeout: int = 120) -> dict:
    started = now()
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "started_at": started,
            "finished_at": now(),
            "returncode": result.returncode,
            "output": result.stdout[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "started_at": started,
            "finished_at": now(),
            "returncode": 124,
            "output": (exc.stdout or "")[-4000:],
            "error": "timeout",
        }


def provision_environment() -> dict:
    """Provision validation tools the builder/reviewer need before delegation."""
    RUNTIME.mkdir(parents=True, exist_ok=True)
    checks: dict[str, dict] = {}
    cache = load_env_cache()

    if not VENV_PYTHON.exists():
        checks["venv_create"] = run_local([sys.executable, "-m", "venv", str(ROOT / ".venv")], timeout=180)

    if VENV_PYTHON.exists() and DASHBOARD_REQUIREMENTS.exists():
        requirements_hash = file_sha256(DASHBOARD_REQUIREMENTS)
        if cache.get("dashboard_requirements_hash") == requirements_hash:
            checks["dashboard_requirements"] = {
                "command": [str(VENV_PYTHON), "-m", "pip", "install", "--requirement", str(DASHBOARD_REQUIREMENTS)],
                "started_at": now(),
                "finished_at": now(),
                "returncode": 0,
                "output": "cached: requirements unchanged",
            }
        else:
            checks["dashboard_requirements"] = run_local(
                [str(VENV_PYTHON), "-m", "pip", "install", "--requirement", str(DASHBOARD_REQUIREMENTS)],
                timeout=300,
            )
            if checks["dashboard_requirements"]["returncode"] == 0:
                cache["dashboard_requirements_hash"] = requirements_hash
        checks["dashboard_health_test"] = run_local(
            [str(VENV_PYTHON), "-m", "unittest", "-v", "tests/test_dashboard_health.py"],
            timeout=120,
        )

    docker_cache_age = 0
    if cache.get("docker_checked_at"):
        try:
            docker_cache_age = int((datetime.now(timezone.utc) - datetime.fromisoformat(cache["docker_checked_at"].replace("Z", "+00:00"))).total_seconds())
        except ValueError:
            docker_cache_age = 999999
    if cache.get("docker_returncode") == 0 and docker_cache_age < 300:
        checks["docker"] = {
            "command": ["docker", "version", "--format", "{{.Server.Version}}"],
            "started_at": now(),
            "finished_at": now(),
            "returncode": 0,
            "output": cache.get("docker_output", "cached"),
        }
    else:
        checks["docker"] = run_local(["docker", "version", "--format", "{{.Server.Version}}"], timeout=30)
        cache["docker_checked_at"] = now()
        cache["docker_returncode"] = checks["docker"].get("returncode")
        cache["docker_output"] = checks["docker"].get("output", "")
    write_json(ENV_CACHE_FILE, cache)
    write_json(RUNTIME / "full-blueprint-environment.json", {"timestamp": now(), "checks": checks})
    return checks


def environment_summary(checks: dict) -> str:
    lines = []
    for name, result in checks.items():
        status = "ok" if result.get("returncode") == 0 else "failed"
        lines.append(f"- {name}: {status}")
    return "\n".join(lines) if lines else "- no preflight checks recorded"


def tail_text(path: Path, limit: int = 8000) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    return data[-limit:].decode("utf-8", errors="replace")


def run_codex(role: str, prompt: str, output_file: Path, timeout: int, heartbeat_payload: dict) -> dict:
    """Run an isolated Codex session; output is retained for watchdog diagnosis."""
    command = [
        "codex", "exec", "--cd", str(ROOT),
        "--dangerously-bypass-approvals-and-sandbox",
        "--output-last-message", str(output_file), prompt,
    ]
    started = now()
    stdout_log = output_file.with_name(f"{output_file.name}.stdout.log")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with stdout_log.open("w", encoding="utf-8") as out:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                text=True,
                stdout=out,
                stderr=subprocess.STDOUT,
            )

            while process.poll() is None:
                elapsed = int((datetime.now(timezone.utc) - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds())
                payload = dict(heartbeat_payload)
                payload.update({
                    "status": f"{role}_running",
                    "heartbeat_at": now(),
                    "child": {
                        "role": role,
                        "pid": process.pid,
                        "started_at": started,
                        "elapsed_seconds": elapsed,
                        "timeout_seconds": timeout,
                        "stdout_log": str(stdout_log.relative_to(ROOT)),
                        "last_message": str(output_file.relative_to(ROOT)),
                    },
                })
                write_json(STATUS_FILE, payload)
                if elapsed >= timeout:
                    process.terminate()
                    try:
                        process.wait(timeout=TERMINATE_GRACE_SECONDS)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=TERMINATE_GRACE_SECONDS)
                    return {
                        "role": role,
                        "started_at": started,
                        "finished_at": now(),
                        "returncode": 124,
                        "output": tail_text(stdout_log),
                        "stdout_log": str(stdout_log.relative_to(ROOT)),
                        "error": "timeout",
                    }
                time.sleep(CHILD_HEARTBEAT_SECONDS)

        return {
            "role": role,
            "started_at": started,
            "finished_at": now(),
            "returncode": process.returncode,
            "output": tail_text(stdout_log),
            "stdout_log": str(stdout_log.relative_to(ROOT)),
        }
    except OSError as exc:
        return {"role": role, "started_at": started, "finished_at": now(), "returncode": 127, "output": tail_text(stdout_log), "stdout_log": str(stdout_log.relative_to(ROOT)), "error": str(exc)}


def builder_prompt(step: dict, evidence: Path, review: Path, preflight: dict) -> str:
    validation_python = VENV_PYTHON.relative_to(ROOT)
    requirements = DASHBOARD_REQUIREMENTS.relative_to(ROOT)
    preflight_text = environment_summary(preflight)
    review_feedback = ""
    if review.exists() and not review_passed(review):
        review_feedback = f"""

Previous independent review failed. Read `{review.relative_to(ROOT)}` first and
fix those exact blocking findings before doing anything else. Do not rewrite
unrelated working code or broaden scope while repairing a failed review.
"""
    return f"""You are the autonomous Canon OS builder. Work without asking a human questions.

Read AGENTS.md first, then blueprint.md and checklist-data.json. The blueprint is
immutable source of truth. Your sole assignment is chain item {step['index']}:
`{compact_title(step)}`.

Credit budget is tight. Use the smallest production-quality implementation that
satisfies this exact chain item and its validation gate. Prefer focused contract
tests and existing architecture over broad rewrites, optional polish, generated
scaffolding, or speculative future-phase work.
When a choice exists, follow docs/autonomy/DEMO_VERTICAL_SLICE.md: functional
commercial builder, real generation pipeline, local/API model routing, social
handoff, and scaffolded future modules take priority over non-demo breadth.

Locate its exact requirement and validation gate in the blueprint. Implement it
fully in this repository, integrate with existing code rather than replacing
working functionality, and add or improve automated tests appropriate to the
requirement. Run the relevant checks. Do not alter blueprint.md, checklist data,
chain state, the user-owned docs/Canon-Brand.PNG, or any constitution file.
Do not work on later chain items and do not write a review verdict.
When Python dashboard checks are relevant, use `{validation_python}`. If it does
not exist or cannot import declared dependencies, create it with `python3 -m venv
.venv` and install `{requirements}` into it before running tests.
The supervisor already ran this environment preflight:
{preflight_text}
You may use Docker, git commit, package installers, and local servers as needed
to satisfy and verify the active blueprint item. Keep all durable project
changes inside this repository, except normal package caches.
{review_feedback}

Before finishing, write `{evidence.relative_to(ROOT)}` containing: requirement,
files changed, commands run with results, known limitations, and `builder_status:
ready_for_independent_review` only when the gate is genuinely met. Commit the
completed item and its tests with a focused commit. If the gate cannot be met,
write `builder_status: blocked` with the concrete reason and leave the chain
unchanged.
"""


def reviewer_prompt(step: dict, evidence: Path, review: Path, preflight: dict) -> str:
    validation_python = VENV_PYTHON.relative_to(ROOT)
    requirements = DASHBOARD_REQUIREMENTS.relative_to(ROOT)
    preflight_text = environment_summary(preflight)
    return f"""You are the independent Canon OS reviewer. Work without asking a human.

Read AGENTS.md, blueprint.md, the active item `{compact_title(step)}`, and
`{evidence.relative_to(ROOT)}`. Inspect the actual implementation and run the
relevant tests or probes yourself. You must not edit application source, chain
state, blueprint.md, checklist data, or user-owned assets. You may only create
or update this review record: `{review.relative_to(ROOT)}`.
Credit budget is tight. Review only this active chain item. Run the smallest
set of probes that can prove or disprove the validation gate, then write the
verdict. Do not perform broad code review of unrelated future phases.
Also verify the work preserves docs/autonomy/DEMO_VERTICAL_SLICE.md when the
active item touches the dashboard, commercial pipeline, model routing, or social
handoff.
When Python dashboard checks are relevant, use `{validation_python}`. If it does
not exist or cannot import declared dependencies, create it with `python3 -m venv
.venv` and install `{requirements}` into it before running tests.
The supervisor already ran this environment preflight:
{preflight_text}
You may use Docker, package installers, and local servers as needed to verify the
active blueprint item. Do not commit review-only changes.

Use exactly one final line: `VERDICT: PASS` only if the specified blueprint
requirement and validation gate are demonstrably satisfied. Otherwise use
`VERDICT: FAIL` followed by concrete missing evidence or failures. Never pass
on file presence alone and never claim an external integration was exercised
unless it actually was.
"""


def review_passed(review: Path) -> bool:
    if not review.exists():
        return False
    return bool(re.search(r"^VERDICT: PASS\s*$", review.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))


def complete(step: dict) -> dict:
    verify = subprocess.run(
        [sys.executable, "chain.py", "verify", str(ROOT), CHAIN_NAME, step["path"]],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if verify.returncode != 0:
        return {"ok": False, "stage": "verify", "output": verify.stdout + verify.stderr}
    payload = json.loads(verify.stdout)
    if not payload.get("ok"):
        return {"ok": False, "stage": "verify", "output": payload}
    finish = subprocess.run(
        [sys.executable, "chain.py", "complete", str(ROOT), CHAIN_NAME, step["path"]],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if finish.returncode != 0:
        return {"ok": False, "stage": "complete", "output": finish.stdout + finish.stderr}
    return {"ok": True, "output": json.loads(finish.stdout)}


def cycle() -> int:
    chain = load_chain()
    if chain.get("steps") and all(step.get("state") == "complete" for step in chain["steps"]):
        write_json(STATUS_FILE, {"status": "complete", "heartbeat_at": now(), "steps": len(chain["steps"])})
        return 0

    step = active_step(chain)
    if not step:
        write_json(STATUS_FILE, {"status": "blocked", "heartbeat_at": now(), "reason": "expected exactly one active step"})
        return 2

    item_slug = slug(step)
    evidence = EVIDENCE_DIR / f"{item_slug}.md"
    review = REVIEW_DIR / f"{item_slug}.md"
    attempts = retries_for(step)
    base = {"heartbeat_at": now(), "active_step": step, "evidence": str(evidence.relative_to(ROOT)), "review": str(review.relative_to(ROOT))}
    preflight = provision_environment()
    base["environment"] = {
        name: {"returncode": result.get("returncode"), "output": result.get("output")}
        for name, result in preflight.items()
    }

    if attempts >= MAX_ATTEMPTS and not review_passed(review):
        write_json(STATUS_FILE, {"status": "blocked_after_retries", "attempt_limit": MAX_ATTEMPTS, **base})
        return 2

    builder_result = None
    evidence_ready = evidence.exists() and "builder_status: ready_for_independent_review" in evidence.read_text(encoding="utf-8", errors="replace")
    # A failed independent review is actionable feedback for a fresh builder
    # session; it must not be retried as a review of unchanged code.
    needs_builder = not evidence_ready or (review.exists() and not review_passed(review))
    if needs_builder:
        write_json(STATUS_FILE, {"status": "building", **base})
        builder_result = run_codex(
            "builder",
            builder_prompt(step, evidence, review, preflight),
            RUNTIME / f"builder-{item_slug}.txt",
            BUILDER_TIMEOUT_SECONDS,
            base,
        )
        if builder_result["returncode"] != 0:
            retries = increment_retry(step)
            write_json(STATUS_FILE, {"status": "builder_failed", "retry_count": retries, "builder": builder_result, **base})
            return 2

    write_json(STATUS_FILE, {"status": "reviewing", "builder": builder_result, **base})
    reviewer_result = run_codex(
        "reviewer",
        reviewer_prompt(step, evidence, review, preflight),
        RUNTIME / f"reviewer-{item_slug}.txt",
        REVIEWER_TIMEOUT_SECONDS,
        {"builder": builder_result, **base},
    )
    if reviewer_result["returncode"] != 0 or not review_passed(review):
        retries = increment_retry(step)
        write_json(STATUS_FILE, {"status": "review_failed", "retry_count": retries, "reviewer": reviewer_result, **base})
        return 2

    advanced = complete(step)
    write_json(STATUS_FILE, {"status": "advanced" if advanced["ok"] else "chain_advance_failed", "reviewer": reviewer_result, "advance": advanced, **base})
    if advanced["ok"]:
        clear_retry(step)
    return 0 if advanced["ok"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=20)
    parser.add_argument("--cycles", type=int, default=1, help="0 runs until the chain is complete or blocked")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        chain = load_chain()
        step = active_step(chain)
        print(json.dumps({"active": compact_title(step) if step else None, "complete": all(s.get("state") == "complete" for s in chain.get("steps", []))}, indent=2))
        return 0

    count = 0
    last = 0
    while args.cycles == 0 or count < args.cycles:
        last = cycle()
        count += 1
        if args.cycles != 0 and count >= args.cycles:
            break
        if args.cycles == 0 and last == 2:
            # Keep the autonomous watchdog alive while honoring retry limits.
            time.sleep(max(args.interval, 60))
            continue
        time.sleep(args.interval)
    return last


if __name__ == "__main__":
    raise SystemExit(main())
