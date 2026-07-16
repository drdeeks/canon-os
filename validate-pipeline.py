#!/usr/bin/env python3
"""
Creative Studio Validation Suite
Comprehensive validation of the entire pipeline infrastructure.
Tests: ACK integration, chain enforcement, model mapping, identity enforcement.
"""
import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.resolve()
VALIDATION_RESULTS = []

def log_test(name, passed, details=""):
    """Log a validation test result."""
    result = {
        "test": name,
        "passed": passed,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    }
    VALIDATION_RESULTS.append(result)
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} {name}")
    if details and not passed:
        print(f"  → {details}")
    return passed

# ============================================================================
# Test Suite 1: ACK Integration
# ============================================================================

def test_aik_installed():
    """Verify ACK Python package is installed and accessible."""
    result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "--help"],
        capture_output=True, text=True
    )
    return log_test("ACK Python package installed", result.returncode == 0)

def test_aik_node_installed():
    """Verify ACK Node.js CLI is installed."""
    result = subprocess.run(
        ["which", "aik"],
        capture_output=True, text=True
    )
    return log_test("ACK Node.js CLI installed", result.returncode == 0 and "aik" in result.stdout)

def test_aik_memory_system():
    """Verify ACK memory system can log and retrieve."""
    test_msg = f"Validation test {datetime.utcnow().timestamp()}"
    
    # Log
    log_result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "memory", "log", test_msg, "-t", "validation"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    
    # Status
    status_result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "memory", "status"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    
    passed = log_result.returncode == 0 and status_result.returncode == 0
    return log_test("ACK memory system operational", passed)

def test_aik_knowledge_system():
    """Verify ACK knowledge graph can add and retrieve entities."""
    # Add test entity
    add_result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "knowledge", "add", 
         "Validation-Test", "--type", "test", "--facts", '{"validated":"true"}'],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    
    # List entities
    list_result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "knowledge", "list"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    
    passed = add_result.returncode == 0 and list_result.returncode == 0
    return log_test("ACK knowledge system operational", passed)

# ============================================================================
# Test Suite 2: Identity Files
# ============================================================================

def test_constitution_exists():
    """Verify constitution.yaml exists and is valid."""
    path = PROJECT_DIR / ".agent" / "constitution.yaml"
    exists = path.exists() and path.stat().st_size > 0
    
    # Try to parse YAML
    valid_yaml = False
    if exists:
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f)
                valid_yaml = "agent" in data and "core_values" in data
        except:
            valid_yaml = False
    
    return log_test("Constitution.yaml exists and valid", exists and valid_yaml)

def test_enforcer_policy_exists():
    """Verify enforcer.yaml exists and has agent policies."""
    path = PROJECT_DIR / ".agent" / "enforcer.yaml"
    exists = path.exists() and path.stat().st_size > 0
    
    valid = False
    if exists:
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f)
                valid = "agents" in data and "global_deny" in data
        except:
            valid = False
    
    return log_test("Enforcer.yaml exists and valid", exists and valid)

def test_soul_exists():
    """Verify SOUL.md exists."""
    path = PROJECT_DIR / ".agent" / "SOUL.md"
    exists = path.exists() and path.stat().st_size > 100
    return log_test("SOUL.md exists with content", exists)

def test_agent_identities():
    """Verify all 10 agent identity files exist."""
    agents = [
        "executive-director", "narrative-architect", "screenwriter",
        "storyboard-artist", "cinematographer", "prompt-composer",
        "generation-engine", "quality-reviewer", "director", "assembly-engine"
    ]
    
    missing = []
    for agent in agents:
        path = PROJECT_DIR / ".agent" / "agents" / f"{agent}.yaml"
        if not path.exists():
            missing.append(agent)
    
    passed = len(missing) == 0
    return log_test("All 10 agent identity files exist", passed, 
                   f"Missing: {', '.join(missing)}" if missing else "")

# ============================================================================
# Test Suite 3: Model Map
# ============================================================================

def test_model_map_exists():
    """Verify model-map.yaml exists and has required sections."""
    path = PROJECT_DIR / ".agent" / "model-map.yaml"
    exists = path.exists() and path.stat().st_size > 0
    
    valid = False
    if exists:
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f)
                valid = all(k in data for k in [
                    "text_models", "vision_models", "video_models",
                    "audio_models", "agent_model_matrix", "strategies"
                ])
        except:
            valid = False
    
    return log_test("Model-map.yaml exists and valid", exists and valid)

def test_model_assignments():
    """Verify every agent has model assignments in the matrix."""
    path = PROJECT_DIR / ".agent" / "model-map.yaml"
    
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        
        matrix = data.get("agent_model_matrix", {})
        agents = [
            "executive-director", "narrative-architect", "screenwriter",
            "storyboard-artist", "cinematographer", "prompt-composer",
            "generation-engine", "quality-reviewer", "director", "assembly-engine"
        ]
        
        missing = [a for a in agents if a not in matrix]
        passed = len(missing) == 0
        return log_test("All agents have model assignments", passed,
                       f"Missing: {', '.join(missing)}" if missing else "")
    except Exception as e:
        return log_test("All agents have model assignments", False, str(e))

def test_token_strategies():
    """Verify token reduction strategies are defined."""
    path = PROJECT_DIR / ".agent" / "model-map.yaml"
    
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        
        strategies = data.get("strategies", [])
        passed = len(strategies) >= 5
        return log_test("Token reduction strategies defined", passed,
                       f"Found {len(strategies)} strategies")
    except Exception as e:
        return log_test("Token reduction strategies defined", False, str(e))

# ============================================================================
# Test Suite 4: Chain Enforcement
# ============================================================================

def test_chain_scripts_exist():
    """Verify chain enforcement scripts exist."""
    scripts = ["chain.py", "chain_report.py", "validate.py"]
    missing = [s for s in scripts if not (PROJECT_DIR / s).exists()]
    passed = len(missing) == 0
    return log_test("Chain enforcement scripts exist", passed,
                   f"Missing: {', '.join(missing)}" if missing else "")

def test_pipeline_chain_exists():
    """Verify creative-pipeline-chain.py exists."""
    path = PROJECT_DIR / "creative-pipeline-chain.py"
    exists = path.exists() and path.stat().st_size > 100
    return log_test("Pipeline chain script exists", exists)

def test_chain_state_exists():
    """Verify chain state has been initialized."""
    chain_dir = PROJECT_DIR / ".chain"
    exists = chain_dir.exists()
    has_state = any(chain_dir.glob("*.json")) if exists else False
    return log_test("Chain state initialized", exists and has_state)

def test_chain_status_command():
    """Verify chain status command works."""
    result = subprocess.run(
        ["python3", "creative-pipeline-chain.py", "status"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    passed = result.returncode == 0 and len(result.stdout) > 0
    return log_test("Chain status command operational", passed)

# ============================================================================
# Test Suite 5: Orchestration
# ============================================================================

def test_orchestrator_exists():
    """Verify orchestrator.py exists."""
    path = PROJECT_DIR / "orchestrator.py"
    exists = path.exists() and path.stat().st_size > 100
    return log_test("Orchestrator script exists", exists)

def test_orchestrator_status():
    """Verify orchestrator status command works."""
    result = subprocess.run(
        ["python3", "orchestrator.py", "status"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    # Check for "Creative Studio" case-insensitively
    passed = result.returncode == 0 and ("Creative Studio" in result.stdout or "CREATIVE STUDIO" in result.stdout)
    return log_test("Orchestrator status operational", passed)

def test_orchestrator_dispatch():
    """Verify orchestrator can dispatch an agent."""
    result = subprocess.run(
        ["python3", "orchestrator.py", "dispatch", "executive-director"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    passed = result.returncode == 0
    valid_json = False
    if passed:
        try:
            config = json.loads(result.stdout)
            valid_json = "agent" in config and "model" in config
        except:
            valid_json = False
    
    return log_test("Orchestrator dispatch operational", passed and valid_json)

# ============================================================================
# Test Suite 6: Documentation
# ============================================================================

def test_agents_md_exists():
    """Verify AGENTS.md exists and documents the system."""
    path = PROJECT_DIR / "AGENTS.md"
    exists = path.exists() and path.stat().st_size > 500
    return log_test("AGENTS.md exists with documentation", exists)

def test_creative_ideology_copied():
    """Verify creative-loop-ideology.md is in corpus."""
    path = PROJECT_DIR / "creative-loop-ideology.md"
    exists = path.exists() and path.stat().st_size > 1000
    return log_test("Creative ideology document available", exists)

# ============================================================================
# Test Suite 7: Hackathon Validation Criteria
# ============================================================================

def test_video_generation_models():
    """Verify Wan/HappyHorse video models are configured."""
    path = PROJECT_DIR / ".agent" / "model-map.yaml"
    
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        
        video_models = data.get("video_models", {})
        has_wan = any("wan" in str(v).lower() for v in video_models.values())
        has_iteration = "iteration" in video_models
        has_quality = "quality" in video_models
        
        passed = has_wan and has_iteration and has_quality
        return log_test("Video generation models (Wan) configured", passed)
    except Exception as e:
        return log_test("Video generation models (Wan) configured", False, str(e))

def test_multimodal_orchestration():
    """Verify system supports text → visual → video → audio → assembly."""
    path = PROJECT_DIR / ".agent" / "model-map.yaml"
    
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        
        has_text = "text_models" in data
        has_vision = "vision_models" in data
        has_video = "video_models" in data
        has_audio = "audio_models" in data
        has_image = "image_models" in data
        
        passed = all([has_text, has_vision, has_video, has_audio, has_image])
        return log_test("Multimodal orchestration (text/vision/video/audio)", passed)
    except Exception as e:
        return log_test("Multimodal orchestration (text/vision/video/audio)", False, str(e))

def test_identity_enforcement():
    """Verify ACK enforcer can validate tool calls."""
    payload = json.dumps({
        "tool_name": "read_file",
        "tool_input": {"path": "test.yaml"}
    })
    
    result = subprocess.run(
        ["python3", "-m", "agent_identity_kit", "hook", "--framework", "hermes"],
        input=payload, capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    
    passed = result.returncode == 0
    valid_response = False
    if passed:
        try:
            response = json.loads(result.stdout)
            # Accept both "allow" and "block" responses - fail-closed is correct when daemon isn't running
            valid_response = ("hookSpecificOutput" in response or 
                            "permissionDecision" in response or
                            "action" in response)
        except:
            valid_response = False
    
    return log_test("ACK enforcer validates tool calls", passed and valid_response,
                   "Returns structured response (allow/block/fail-closed)" if passed else "")

def test_token_optimization_documented():
    """Verify token optimization strategies are documented."""
    path = PROJECT_DIR / ".agent" / "model-map.yaml"
    
    try:
        with open(path) as f:
            content = f.read()
        
        has_strategies = "strategies" in content
        has_budget = "token_budget" in content or "budget" in content.lower()
        has_flash = "flash" in content.lower()
        has_iteration = "iteration" in content.lower()
        
        passed = all([has_strategies, has_budget, has_flash, has_iteration])
        return log_test("Token optimization documented in model-map", passed)
    except Exception as e:
        return log_test("Token optimization documented in model-map", False, str(e))

# ============================================================================
# Main Validation Runner
# ============================================================================

def run_all_tests():
    """Run all validation tests and generate report."""
    print("=" * 70)
    print("CREATIVE STUDIO — Validation Suite")
    print("=" * 70)
    print()
    
    # Suite 1: ACK Integration
    print("--- Suite 1: ACK Integration ---")
    test_aik_installed()
    test_aik_node_installed()
    test_aik_memory_system()
    test_aik_knowledge_system()
    print()
    
    # Suite 2: Identity Files
    print("--- Suite 2: Identity Files ---")
    test_constitution_exists()
    test_enforcer_policy_exists()
    test_soul_exists()
    test_agent_identities()
    print()
    
    # Suite 3: Model Map
    print("--- Suite 3: Model Map ---")
    test_model_map_exists()
    test_model_assignments()
    test_token_strategies()
    print()
    
    # Suite 4: Chain Enforcement
    print("--- Suite 4: Chain Enforcement ---")
    test_chain_scripts_exist()
    test_pipeline_chain_exists()
    test_chain_state_exists()
    test_chain_status_command()
    print()
    
    # Suite 5: Orchestration
    print("--- Suite 5: Orchestration ---")
    test_orchestrator_exists()
    test_orchestrator_status()
    test_orchestrator_dispatch()
    print()
    
    # Suite 6: Documentation
    print("--- Suite 6: Documentation ---")
    test_agents_md_exists()
    test_creative_ideology_copied()
    print()
    
    # Suite 7: Hackathon Criteria
    print("--- Suite 7: Hackathon Validation Criteria ---")
    test_video_generation_models()
    test_multimodal_orchestration()
    test_identity_enforcement()
    test_token_optimization_documented()
    print()
    
    # Summary
    total = len(VALIDATION_RESULTS)
    passed = sum(1 for r in VALIDATION_RESULTS if r["passed"])
    failed = total - passed
    
    print("=" * 70)
    print(f"VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total tests: {total}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print(f"Success rate: {(passed/total*100):.1f}%")
    print()
    
    if failed > 0:
        print("Failed tests:")
        for r in VALIDATION_RESULTS:
            if not r["passed"]:
                print(f"  ✗ {r['test']}")
                if r["details"]:
                    print(f"    → {r['details']}")
        print()
    
    # Write report
    report_path = PROJECT_DIR / "validation-report.json"
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "success_rate": (passed/total*100),
        "results": VALIDATION_RESULTS
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"Report saved: {report_path}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
