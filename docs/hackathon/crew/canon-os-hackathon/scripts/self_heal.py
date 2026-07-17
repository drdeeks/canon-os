#!/usr/bin/env python3
"""Safe self-healing checks for the Canon OS hackathon crew."""

from __future__ import annotations

import json
import os
import socket
import subprocess
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
ACK_ENV_FILE = SHARED / ".env"
ACK_AGENT_DIR = SHARED / ".agent"


def load_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def ack_health() -> dict:
    env = load_env_file(ACK_ENV_FILE)
    workspace = Path(env.get("AGENT_WORKSPACE", SHARED)).resolve()
    sock = Path(env.get("ENFORCER_SOCKET", workspace / ".agent" / "enforcer.sock"))
    constitution = workspace / ".agent" / "constitution.yaml"
    habits = workspace / ".agent" / "habits"
    enforcer = workspace / ".agent" / "enforcer.yaml"
    ack_log = Path(env.get("ACK_ACK_LOG", workspace / ".agent" / "ack.jsonl"))

    reachable = False
    socket_error = None
    if sock.exists():
        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(1)
            client.connect(str(sock))
            client.sendall(b'{"method":"heartbeat","params":{}}\n')
            reachable = bool(client.recv(4096))
            client.close()
        except OSError as exc:
            socket_error = str(exc)

    return {
        "workspace": str(workspace),
        "env_file_exists": ACK_ENV_FILE.exists(),
        "constitution_exists": constitution.exists(),
        "habits_count": len(list(habits.glob("*.yaml"))) if habits.exists() else 0,
        "enforcer_config_exists": enforcer.exists(),
        "ack_log_exists": ack_log.exists(),
        "socket_exists": sock.exists(),
        "daemon_reachable": reachable,
        "socket_error": socket_error,
    }


def repair_ack_daemon(env: dict) -> str:
    repair_env = dict(os.environ)
    repair_env.update(env)
    result = subprocess.run(
        ["ack", "repair", "daemon"],
        cwd=str(HACKATHON_ROOT.parents[1]),
        env=repair_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return "ok" if result.returncode == 0 else f"exit_{result.returncode}"


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

    ack = ack_health()
    if not ack["daemon_reachable"]:
        ack_env = load_env_file(ACK_ENV_FILE)
        repair_output = repair_ack_daemon(ack_env)
        repaired.append("attempted ACK daemon repair")
        ack = ack_health()
        ack["repair_output"] = repair_output
    if not ack["env_file_exists"]:
        blocked.append("ACK environment file is missing")
    if not ack["constitution_exists"] or ack["habits_count"] == 0:
        blocked.append("ACK character files are incomplete")
    if not ack["enforcer_config_exists"]:
        blocked.append("ACK enforcer config is missing")
    if not ack["daemon_reachable"]:
        blocked.append("ACK daemon is not reachable")

    status = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blocked else "ready",
        "blocked": blocked,
        "repaired": repaired,
        "active_step": active_steps[0] if len(active_steps) == 1 else None,
        "token_usage": tokens,
        "ack": ack,
    }
    write_json(STATUS_FILE, status)

    if blocked:
        print("BLOCKED: " + "; ".join(blocked))
        return 2
    print("READY: self-healing checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
