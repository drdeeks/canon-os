#!/usr/bin/env python3
"""
Creative Studio Orchestrator
Ties together ACK (identity enforcement) + loop-enforcer (chain gates) + model-map (token optimization)
to drive the autonomous short drama production pipeline.

Flow:
  1. Load constitution + SOUL.md via ACK
  2. Check chain state via loop-enforcer
  3. Identify active stage → agent → model
  4. Dispatch agent work with identity context
  5. Validate artifact via chain verify
  6. Complete stage → next unlocks
  7. Loop until Director approves publication

Token optimization:
  - Each agent loads ONLY its own identity + input artifacts
  - Flash models for iteration, quality for final
  - ACK semantic search for context retrieval
  - Chain enforcement prevents wasteful re-work
"""
import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.resolve()
AGENT_DIR = PROJECT_DIR / ".agent" / "agents"
MODEL_MAP_PATH = PROJECT_DIR / ".agent" / "model-map.yaml"
CONSTITUTION_PATH = PROJECT_DIR / ".agent" / "constitution.yaml"
CHAIN_SCRIPT = PROJECT_DIR / "creative-pipeline-chain.py"

# ============================================================================
# ACK Integration
# ============================================================================

def aik_memory_log(message, tags=None, category="pipeline"):
    """Log an event to ACK memory system."""
    cmd = ["python3", "-m", "agent_identity_kit", "memory", "log", message]
    if tags:
        cmd.extend(["-t", ",".join(tags)])
    cmd.extend(["-c", category])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    return result.stdout.strip()

def aik_knowledge_add(name, entity_type, facts):
    """Add entity to ACK knowledge graph."""
    cmd = ["python3", "-m", "agent_identity_kit", "knowledge", "add", name,
           "--type", entity_type, "--facts", json.dumps(facts)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    return result.stdout.strip()

def aik_semantic_search(query):
    """Search indexed knowledge semantically."""
    cmd = ["python3", "-m", "agent_identity_kit", "semantic", "search", query]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    return result.stdout.strip()

def aik_enforcer_check(tool_name, tool_input, agent_id=None):
    """Check if a tool call is allowed by the enforcer."""
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    cmd = ["python3", "-m", "agent_identity_kit", "hook", "--framework", "hermes"]
    result = subprocess.run(cmd, input=payload, capture_output=True, text=True, cwd=str(PROJECT_DIR))
    try:
        decision = json.loads(result.stdout)
        return decision.get("permissionDecision", "deny") == "allow"
    except (json.JSONDecodeError, KeyError):
        return False  # fail-closed

# ============================================================================
# Chain Integration
# ============================================================================

def chain_status():
    """Get current pipeline chain status."""
    result = subprocess.run(
        ["python3", str(CHAIN_SCRIPT), "status"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def chain_check(file_path):
    """Check if a pipeline stage file is active (ready to work on)."""
    result = subprocess.run(
        ["python3", str(CHAIN_SCRIPT), "check", file_path],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def chain_verify(file_path):
    """Verify a completed artifact."""
    result = subprocess.run(
        ["python3", str(CHAIN_SCRIPT), "verify", file_path],
        capture_output=True, text=True
    )
    return result.returncode == 0

def chain_complete(file_path):
    """Mark a verified artifact as complete."""
    result = subprocess.run(
        ["python3", str(CHAIN_SCRIPT), "complete", file_path],
        capture_output=True, text=True
    )
    return result.returncode == 0

# ============================================================================
# Model Selection
# ============================================================================

def load_model_map():
    """Load the model assignment matrix."""
    try:
        import yaml
        with open(MODEL_MAP_PATH) as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: parse YAML manually for critical fields
        return None

def select_model(agent_id, phase="create"):
    """Select the optimal model for an agent's current phase."""
    model_map = load_model_map()
    if model_map and "agent_model_matrix" in model_map:
        agent_models = model_map["agent_model_matrix"].get(agent_id, {})
        return agent_models.get(phase, "qwen3.5-flash")
    # Hardcoded fallback
    fallback = {
        "executive-director": "qwen3-max",
        "narrative-architect": "qwen3.5-plus",
        "screenwriter": "qwen3.5-plus",
        "storyboard-artist": "qwen3-vl-flash",
        "cinematographer": "qwen3-vl-flash",
        "prompt-composer": "qwen3-max",
        "generation-engine": "wan2.6-i2v-flash",
        "quality-reviewer": "qwen3-vl-plus",
        "director": "qwen3-max",
        "assembly-engine": "qwen3.5-flash",
    }
    return fallback.get(agent_id, "qwen3.5-flash")

# ============================================================================
# Agent Context Builder
# ============================================================================

def build_agent_context(agent_id, input_artifacts=None):
    """
    Build minimal working context for an agent.
    Only loads: agent identity + input artifacts + relevant semantic search results.
    Never loads full project context.
    """
    context = {}
    
    # 1. Load agent identity
    agent_path = AGENT_DIR / f"{agent_id}.yaml"
    if agent_path.exists():
        context["identity"] = agent_path.read_text()
    
    # 2. Load only specified input artifacts
    if input_artifacts:
        context["inputs"] = {}
        for artifact_path in input_artifacts:
            full_path = PROJECT_DIR / artifact_path
            if full_path.exists():
                context["inputs"][artifact_path] = full_path.read_text()
    
    # 3. Semantic search for relevant context
    search_query = agent_id.replace("-", " ")
    semantic_results = aik_semantic_search(search_query)
    if semantic_results:
        context["relevant_knowledge"] = semantic_results
    
    return context

# ============================================================================
# Pipeline Orchestration
# ============================================================================

def run_pipeline_status():
    """Print comprehensive pipeline status."""
    print("=" * 60)
    print("CREATIVE STUDIO — Pipeline Status")
    print("=" * 60)
    print()
    
    # Chain status
    print("--- Chain State ---")
    print(chain_status())
    print()
    
    # Model assignments
    print("--- Model Assignments ---")
    agents = [
        "executive-director", "narrative-architect", "screenwriter",
        "storyboard-artist", "cinematographer", "prompt-composer",
        "generation-engine", "quality-reviewer", "director", "assembly-engine"
    ]
    for agent in agents:
        create_model = select_model(agent, "create")
        revise_model = select_model(agent, "revise")
        print(f"  {agent}: create={create_model}, revise={revise_model}")
    print()
    
    # ACK status
    print("--- ACK Memory ---")
    result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "memory", "status"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    print(result.stdout.strip() if result.stdout else "No memory entries yet")
    print()

def orchestrate_step(agent_id, phase="create"):
    """
    Orchestrate a single pipeline step:
    1. Build minimal context
    2. Select model
    3. Return dispatch configuration
    
    The actual LLM call is made by the agent framework (Hermes).
    This function returns the configuration for that call.
    """
    model = select_model(agent_id, phase)
    context = build_agent_context(agent_id)
    
    dispatch = {
        "agent": agent_id,
        "model": model,
        "phase": phase,
        "identity": context.get("identity", ""),
        "inputs": context.get("inputs", {}),
        "knowledge": context.get("relevant_knowledge", ""),
        "enforcer": "aik",
        "chain": "creative-pipeline",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Log to ACK memory
    aik_memory_log(
        f"Dispatched {agent_id} ({phase}) using model {model}",
        tags=["dispatch", agent_id, phase],
        category="orchestration"
    )
    
    return dispatch

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: orchestrator.py <command> [args]")
        print("Commands: status, dispatch <agent> [phase], context <agent>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        run_pipeline_status()
    elif cmd == "dispatch":
        agent = sys.argv[2] if len(sys.argv) > 2 else "executive-director"
        phase = sys.argv[3] if len(sys.argv) > 3 else "create"
        config = orchestrate_step(agent, phase)
        print(json.dumps(config, indent=2))
    elif cmd == "context":
        agent = sys.argv[2]
        ctx = build_agent_context(agent)
        print(json.dumps({k: (v[:200] + "..." if isinstance(v, str) and len(v) > 200 else v) 
                         for k, v in ctx.items()}, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
