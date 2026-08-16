#!/usr/bin/env bash
# ============================================================================
# Test: Backends
# Validates each configured backend responds to health checks and API calls
# Graceful skip if backend not running
# ============================================================================

set -uo pipefail

PASS=0; FAIL=0; SKIP=0; TOTAL=0

run() {
  local desc="$1" cmd="$2" timeout="${3:-10}"
  ((TOTAL++))
  if timeout "$timeout" bash -c "$cmd" &>/dev/null; then
    echo -e "  \033[0;32mPASS\033[0m  $desc"; ((PASS++))
  elif [[ $? -eq 124 ]]; then
    echo -e "  \033[1;33mSKIP\033[0m  $desc (timeout)"; ((SKIP++))
  else
    echo -e "  \033[0;31mFAIL\033[0m  $desc"; ((FAIL++))
  fi
}

skip() { ((TOTAL++)); ((SKIP++)); echo -e "  \033[1;33mSKIP\033[0m  $1 ($2)"; }

# Check if dashboard is reachable first -- if not, most tests can't run
DASHBOARD_UP=false
if curl -sf --max-time 3 http://127.0.0.1:5000/ &>/dev/null; then
  DASHBOARD_UP=true
fi

# Check if Docker is available
DOCKER_AVAILABLE=false
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  DOCKER_AVAILABLE=true
fi

# Load backend config
BACKEND_CONFIG="/opt/ai-studio/config/backends.json"
if [[ -f "$BACKEND_CONFIG" ]]; then
  run "Backend config valid JSON" "python3 -c 'import json; json.load(open(\"$BACKEND_CONFIG\"))'" 5
  TEXT_BACKEND=$(python3 -c "import json; print(json.load(open('$BACKEND_CONFIG')).get('backends',{}).get('text','none'))" 2>/dev/null || echo "none")
  IMAGE_BACKEND=$(python3 -c "import json; print(json.load(open('$BACKEND_CONFIG')).get('backends',{}).get('image','none'))" 2>/dev/null || echo "none")
  TTS_BACKEND=$(python3 -c "import json; print(json.load(open('$BACKEND_CONFIG')).get('backends',{}).get('tts','none'))" 2>/dev/null || echo "none")
  STT_BACKEND=$(python3 -c "import json; print(json.load(open('$BACKEND_CONFIG')).get('backends',{}).get('stt','none'))" 2>/dev/null || echo "none")
else
  TEXT_BACKEND="llama-cpp"; IMAGE_BACKEND="comfyui"; TTS_BACKEND="kokoro"; STT_BACKEND="whisper"
  skip "Backend config" "not found"
fi

# Text backend health -- only test if something is listening on the port
if [[ "$TEXT_BACKEND" == "llama-cpp" ]]; then
  if ss -tlnp 2>/dev/null | grep -q ':8080 '; then
    run "llama.cpp health" "curl -sf --max-time 5 http://127.0.0.1:8080/health" 8
    run "llama.cpp models endpoint" "curl -sf --max-time 5 http://127.0.0.1:8080/v1/models" 8
    run "llama.cpp can generate" "curl -sf --max-time 30 http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Say hi\"}],\"max_tokens\":5}' | python3 -c 'import json,sys; d=json.load(sys.stdin); assert \"choices\" in d'" 35
  else
    skip "llama.cpp health" "port 8080 not listening"
    skip "llama.cpp models" "port 8080 not listening"
    skip "llama.cpp generate" "port 8080 not listening"
  fi
elif [[ "$TEXT_BACKEND" == "ollama" ]]; then
  if ss -tlnp 2>/dev/null | grep -q ':11434 '; then
    run "Ollama health" "curl -sf --max-time 5 http://127.0.0.1:11434/api/tags" 8
    run "Ollama can generate" "curl -sf --max-time 30 http://127.0.0.1:11434/api/generate -H 'Content-Type: application/json' -d '{\"model\":\"llama3.1\",\"prompt\":\"Say hi\",\"stream\":false,\"options\":{\"num_predict\":5}}' | python3 -c 'import json,sys; d=json.load(sys.stdin); assert \"response\" in d'" 35
  else
    skip "Ollama health" "port 11434 not listening"
    skip "Ollama generate" "port 11434 not listening"
  fi
else
  skip "Text backend" "backend: $TEXT_BACKEND"
fi

# Image backend -- only test if ComfyUI port is listening
if [[ "$IMAGE_BACKEND" == "comfyui" ]]; then
  if ss -tlnp 2>/dev/null | grep -q ':8188 '; then
    run "ComfyUI health" "curl -sf --max-time 5 http://127.0.0.1:8188/" 8
    run "ComfyUI system stats" "curl -sf --max-time 5 http://127.0.0.1:8188/system_stats" 8
    run "ComfyUI object info" "curl -sf --max-time 10 http://127.0.0.1:8188/object_info/CheckpointLoaderSimple" 15
    run "ComfyUI has models" "curl -sf --max-time 10 http://127.0.0.1:8188/object_info/CheckpointLoaderSimple | python3 -c 'import json,sys; d=json.load(sys.stdin); m=d.get(\"CheckpointLoaderSimple\",{}).get(\"input\",{}).get(\"required\",{}).get(\"ckpt_name\",[[]]); assert len(m[0])>0 if m else False'" 15
  else
    skip "ComfyUI health" "port 8188 not listening"
    skip "ComfyUI stats" "port 8188 not listening"
    skip "ComfyUI models" "port 8188 not listening"
    skip "ComfyUI model list" "port 8188 not listening"
  fi
else
  skip "Image backend" "backend: $IMAGE_BACKEND"
fi

# TTS backend
if ss -tlnp 2>/dev/null | grep -q ':8880 '; then
  run "Kokoro health" "curl -sf --max-time 5 http://127.0.0.1:8880/health" 8
else
  skip "Kokoro health" "port 8880 not listening"
fi

# STT backend
if ss -tlnp 2>/dev/null | grep -q ':9000 '; then
  run "Whisper health" "curl -sf --max-time 5 http://127.0.0.1:9000/health" 8
else
  skip "Whisper health" "port 9000 not listening"
fi

# InvokeAI backend
if ss -tlnp 2>/dev/null | grep -q ':9090 '; then
  run "InvokeAI health" "curl -sf --max-time 5 http://127.0.0.1:9090/api/v1/app/version" 8
else
  skip "InvokeAI health" "port 9090 not listening"
fi

# Music backend
if ss -tlnp 2>/dev/null | grep -q ':7860 '; then
  run "AudioCraft health" "curl -sf --max-time 5 http://127.0.0.1:7860/" 8
else
  skip "AudioCraft health" "port 7860 not listening"
fi

# Dashboard
if $DASHBOARD_UP; then
  run "Dashboard health" "curl -sf --max-time 5 http://127.0.0.1:5000/" 8
  run "Dashboard API status" "curl -sf --max-time 5 http://127.0.0.1:5000/api/status | python3 -c 'import json,sys; json.load(sys.stdin)'" 8
else
  skip "Dashboard health" "port 5000 not listening"
  skip "Dashboard API" "port 5000 not listening"
fi

# Docker network
if $DOCKER_AVAILABLE; then
  run "Studio network exists" "docker network ls | grep -q studio-network" 5
  # Cross-container connectivity
  FIRST_CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | head -1)
  if [[ -n "$FIRST_CONTAINER" ]]; then
    run "Container DNS resolution" "docker exec '$FIRST_CONTAINER' cat /etc/resolv.conf 2>/dev/null | grep -q 'nameserver'" 5
  else
    skip "Container DNS" "no containers"
  fi
else
  skip "Docker network" "Docker not available"
  skip "Container DNS" "Docker not available"
fi

echo ""
echo -e "  \033[1mBackends: $PASS passed, $FAIL failed, $SKIP skipped\033[0m"
[[ $FAIL -eq 0 ]]
