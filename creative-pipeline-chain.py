#!/usr/bin/env python3
"""
Creative Pipeline Chain — Sequential dependency enforcement
Uses loop-enforcer chain.py to gate the creative pipeline stages.

Each stage must be completed and verified before the next unlocks.
"""
import subprocess
import sys
import os

CHAIN_NAME = "creative-pipeline"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Pipeline stages in strict dependency order
STAGES = [
    # Stage 1: Identity
    {"file": "artifacts/creative-brief.yaml",       "agent": "executive-director",  "phase": "identity"},
    # Stage 2: Structure  
    {"file": "artifacts/beat-sheet.yaml",            "agent": "narrative-architect", "phase": "structure"},
    # Stage 3: Writing
    {"file": "artifacts/screenplay.yaml",            "agent": "screenwriter",        "phase": "writing"},
    # Stage 4: Visual planning
    {"file": "artifacts/storyboard.yaml",            "agent": "storyboard-artist",   "phase": "visual"},
    # Stage 5: Camera/lighting
    {"file": "artifacts/shot-list.yaml",             "agent": "cinematographer",     "phase": "camera"},
    # Stage 6: Prompt engineering
    {"file": "artifacts/prompt-graph.yaml",          "agent": "prompt-composer",     "phase": "prompts"},
    # Stage 7: Generation (iteration)
    {"file": "artifacts/renders/iteration-complete", "agent": "generation-engine",   "phase": "render-iter"},
    # Stage 8: Quality review
    {"file": "artifacts/evaluation-report.yaml",     "agent": "quality-reviewer",    "phase": "evaluation"},
    # Stage 9: Generation (final)
    {"file": "artifacts/renders/final-complete",     "agent": "generation-engine",   "phase": "render-final"},
    # Stage 10: Assembly
    {"file": "artifacts/assembled/final-video.mp4",  "agent": "assembly-engine",     "phase": "assembly"},
    # Stage 11: Director review
    {"file": "artifacts/director-review.yaml",       "agent": "director",            "phase": "review"},
    # Stage 12: Publication
    {"file": "artifacts/published/release-marker",   "agent": "director",            "phase": "publish"},
]

CHAIN_SCRIPT = os.path.join(PROJECT_DIR, "chain.py")

def run_chain(cmd):
    """Run a chain.py command and return the result."""
    full_cmd = ["python3", CHAIN_SCRIPT] + cmd
    result = subprocess.run(full_cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def create_chain():
    """Create the creative pipeline chain with all stages."""
    files = [os.path.join(PROJECT_DIR, s["file"]) for s in STAGES]
    stdout, stderr, rc = run_chain(["create", PROJECT_DIR, CHAIN_NAME] + files)
    print(f"Chain created: {CHAIN_NAME}")
    print(f"  Stages: {len(STAGES)}")
    if rc != 0:
        print(f"  Error: {stderr}")
    return rc == 0

def status():
    """Show current chain status."""
    stdout, stderr, rc = run_chain(["status", PROJECT_DIR, CHAIN_NAME])
    print(stdout)
    if stderr:
        print(f"Errors: {stderr}")
    return stdout

def check(file_path):
    """Check if a file is ready to be worked on."""
    stdout, stderr, rc = run_chain(["check", PROJECT_DIR, CHAIN_NAME, file_path])
    print(stdout)
    return stdout

def verify(file_path):
    """Mark a file as verified after quality check."""
    stdout, stderr, rc = run_chain(["verify", PROJECT_DIR, CHAIN_NAME, file_path])
    print(stdout)
    return rc == 0

def complete(file_path):
    """Mark a verified file as complete, unlocking the next stage."""
    stdout, stderr, rc = run_chain(["complete", PROJECT_DIR, CHAIN_NAME, file_path])
    print(stdout)
    return rc == 0

def get_active_stage():
    """Return which stage is currently active (unlocked and ready)."""
    stdout, stderr, rc = run_chain(["status", PROJECT_DIR, CHAIN_NAME])
    # Parse status output to find active stage
    return stdout

def get_agent_for_stage(stage_index):
    """Return the agent assigned to a given stage index."""
    if 0 <= stage_index < len(STAGES):
        return STAGES[stage_index]
    return None

def get_model_for_agent(agent_id, phase="create"):
    """Look up the model assignment for an agent from model-map.yaml."""
    import yaml
    model_map_path = os.path.join(PROJECT_DIR, ".agent", "model-map.yaml")
    with open(model_map_path) as f:
        model_map = yaml.safe_load(f)
    
    matrix = model_map.get("agent_model_matrix", {})
    agent_models = matrix.get(agent_id, {})
    return agent_models.get(phase, "qwen3.5-flash")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: creative-pipeline-chain.py <command> [args]")
        print("Commands: create, status, check, verify, complete, active, agent, model")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "create":
        create_chain()
    elif cmd == "status":
        status()
    elif cmd == "check":
        check(sys.argv[2])
    elif cmd == "verify":
        verify(sys.argv[2])
    elif cmd == "complete":
        complete(sys.argv[2])
    elif cmd == "active":
        get_active_stage()
    elif cmd == "agent":
        stage = int(sys.argv[2])
        info = get_agent_for_stage(stage)
        if info:
            print(f"Stage {stage}: {info['agent']} ({info['phase']})")
        else:
            print(f"Invalid stage: {stage}")
    elif cmd == "model":
        agent = sys.argv[2]
        phase = sys.argv[3] if len(sys.argv) > 3 else "create"
        model = get_model_for_agent(agent, phase)
        print(f"Model for {agent}/{phase}: {model}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
