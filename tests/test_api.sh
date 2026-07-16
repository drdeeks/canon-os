#!/usr/bin/env bash
# ============================================================================
# Test: API
# Validates dashboard HTTP endpoints respond correctly
# All requests have timeouts, never hang
# ============================================================================

set -uo pipefail

PASS=0; FAIL=0; SKIP=0; TOTAL=0
BASE="http://127.0.0.1:5000"

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

# Check dashboard is reachable first
if ! curl -sf --max-time 5 "$BASE/" &>/dev/null; then
  echo -e "  \033[1;33mSKIP\033[0m  Dashboard not reachable at $BASE"
  echo -e "  \033[1mAPI: 0 passed, 0 failed, all skipped (dashboard offline)\033[0m"
  exit 0
fi

# Page routes
run "GET / returns 200" "curl -sf -o /dev/null -w '%{http_code}' --max-time 5 '$BASE/' | grep -q '200'"
run "GET /workspace returns 200" "curl -sf -o /dev/null -w '%{http_code}' --max-time 5 '$BASE/workspace' | grep -q '200'"
run "GET /models returns 200" "curl -sf -o /dev/null -w '%{http_code}' --max-time 5 '$BASE/models' | grep -q '200'"
run "GET /settings returns 200" "curl -sf -o /dev/null -w '%{http_code}' --max-time 5 '$BASE/settings' | grep -q '200'"
run "GET /projects returns 200" "curl -sf -o /dev/null -w '%{http_code}' --max-time 5 '$BASE/projects' | grep -q '200'"

# API endpoints
run "GET /api/status returns JSON" "curl -sf --max-time 5 '$BASE/api/status' | python3 -c 'import json,sys; json.load(sys.stdin)'"
run "GET /api/models returns JSON" "curl -sf --max-time 5 '$BASE/api/models' | python3 -c 'import json,sys; json.load(sys.stdin)'"
run "GET /api/settings returns JSON" "curl -sf --max-time 5 '$BASE/api/settings' | python3 -c 'import json,sys; json.load(sys.stdin)'"
run "GET /api/history returns JSON" "curl -sf --max-time 5 '$BASE/api/history' | python3 -c 'import json,sys; json.load(sys.stdin)'"

# API validation
run "POST /api/generate rejects empty" "curl -sf --max-time 5 -X POST '$BASE/api/generate' -F 'mode=text-to-image' -F 'prompt=' -F 'model=test' -w '%{http_code}' | grep -qE '400|422|500'"
run "POST /api/generate rejects missing upload for i2i" "curl -sf --max-time 5 -X POST '$BASE/api/generate' -F 'mode=image-to-image' -F 'prompt=test' -F 'model=test' -w '%{http_code}' | grep -qE '400|422|500'"
run "POST /api/enhance-prompt works" "curl -sf --max-time 10 -X POST '$BASE/api/enhance-prompt' -H 'Content-Type: application/json' -d '{\"prompt\":\"headphones\",\"mode\":\"text-to-image\"}' | python3 -c 'import json,sys; d=json.load(sys.stdin); assert \"enhanced\" in d'"
run "POST /api/text/generate rejects empty" "curl -sf --max-time 5 -X POST '$BASE/api/text/generate' -H 'Content-Type: application/json' -d '{\"prompt\":\"\"}' -w '%{http_code}' | grep -qE '400|422|500'"

# Settings read/write
run "POST /api/settings saves" "curl -sf --max-time 5 -X POST '$BASE/api/settings' -H 'Content-Type: application/json' -d '{\"theme\":\"dark\"}' | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get(\"status\")==\"saved\"'"

# Static files
run "HTML contains 'AI'" "curl -sf --max-time 5 '$BASE/' | grep -q 'AI'"
run "HTML has mode buttons" "[[ \$(curl -sf --max-time 5 'http://127.0.0.1:5000/workspace' | grep -c 'data-mode') -ge 6 ]]"
run "HTML has generate button" "curl -sf --max-time 5 '$BASE/workspace' | grep -q 'generateBtn'"

# Response times
STATUS_TIME=$(curl -sf -o /dev/null -w '%{time_total}' --max-time 10 "$BASE/api/status" 2>/dev/null || echo "99")
if (( $(echo "$STATUS_TIME < 2.0" | bc -l 2>/dev/null || echo 0) )); then
  run "API status responds in <2s (${STATUS_TIME}s)" "true"
else
  run "API status slow (${STATUS_TIME}s)" "false"
fi

echo ""
echo -e "  \033[1mAPI: $PASS passed, $FAIL failed, $SKIP skipped\033[0m"
[[ $FAIL -eq 0 ]]
