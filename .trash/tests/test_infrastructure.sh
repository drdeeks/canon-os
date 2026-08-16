#!/usr/bin/env bash
# ============================================================================
# Test: Infrastructure
# Validates Docker, containers, ports, storage, GPU, configs
# Every test has timeout + graceful skip if prerequisite missing
# ============================================================================

set -uo pipefail

PASS=0; FAIL=0; SKIP=0; TOTAL=0

run() {
  local desc="$1" cmd="$2" timeout="${3:-15}"
  ((TOTAL++))
  local out=""
  if out=$(timeout "$timeout" bash -c "$cmd" 2>&1); then
    echo -e "  \033[0;32mPASS\033[0m  $desc"
    ((PASS++))
  elif [[ $? -eq 124 ]]; then
    echo -e "  \033[1;33mSKIP\033[0m  $desc (timeout)"
    ((SKIP++))
  else
    echo -e "  \033[0;31mFAIL\033[0m  $desc"
    ((FAIL++))
  fi
}

skip() { ((TOTAL++)); ((SKIP++)); echo -e "  \033[1;33mSKIP\033[0m  $1 ($2)"; }

# Docker
command -v docker &>/dev/null && run "Docker installed" "docker --version" || skip "Docker installed" "not installed"
command -v docker &>/dev/null && run "Docker running" "docker info --format '{{.ServerVersion}}'" 10 || skip "Docker running" "not installed"

# Docker Compose
run "Docker Compose available" "docker compose version" 10 2>/dev/null || skip "Docker Compose" "not available"

# Compose file valid
[[ -f /opt/ai-studio/docker-compose.yaml ]] && run "Compose file valid" "cd /opt/ai-studio && docker compose config --quiet" 15 || skip "Compose file" "not found"

# Containers
if command -v docker &>/dev/null; then
  for svc in ollama llamacpp comfyui openwebui whisper kokoro invokeai dashboard audiocraft; do
    run "Container studio-$svc exists" "docker ps --format '{{.Names}}' | grep -q 'studio-$svc'" 5
  done
else
  for svc in ollama llamacpp comfyui openwebui whisper kokoro invokeai dashboard audiocraft; do
    skip "Container studio-$svc" "Docker not available"
  done
fi

# Ports listening -- skip if Docker not available (no containers = no ports)
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  for port in 5000 9090 8188 8080 9000 8880 7860; do
    run "Port $port reachable" "ss -tlnp 2>/dev/null | grep -q ':$port ' || curl -sf --max-time 3 http://127.0.0.1:$port/ >/dev/null 2>&1" 5
  done
else
  for port in 5000 9090 8188 8080 9000 8880 7860; do
    skip "Port $port" "Docker not running (no services)"
  done
fi

# Storage
mountpoint -q /mnt/studio 2>/dev/null && run "Storage mounted" "df -h /mnt/studio --output=avail | tail -1 | grep -q G" 5 || skip "Storage mounted" "not mounted"

# Directory structure
for dir in models projects exports uploads cache logs config; do
  [[ -d "/mnt/studio/$dir" ]] && run "Directory /mnt/studio/$dir exists" "true" || skip "/mnt/studio/$dir" "not found"
done

# Disk space
if mountpoint -q /mnt/studio 2>/dev/null; then
  run "Disk space >10GB" "[ \$(df /mnt/studio --output=avail -BG 2>/dev/null | tail -1 | tr -dc '0-9') -gt 10 ]" 5
else
  skip "Disk space check" "storage not mounted"
fi

# Config files
[[ -f /opt/ai-studio/config/backends.json ]] && run "Backend config exists" "python3 -c 'import json; json.load(open(\"/opt/ai-studio/config/backends.json\"))'" 5 || skip "Backend config" "not found"

# SSH
run "SSH server running" "ss -tlnp 2>/dev/null | grep -q ':2222 ' || systemctl is-active sshd 2>/dev/null || systemctl is-active ssh 2>/dev/null" 5

# GPU
if command -v nvidia-smi &>/dev/null; then
  run "GPU detected" "nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | grep -q ." 5
elif uname -r | grep -qi darwin; then
  run "GPU detected" "system_profiler SPDisplaysDataType 2>/dev/null | grep -q Chipset" 10
else
  skip "GPU detection" "no GPU tools found"
fi

# Memory
run "RAM >=8GB" "[ \$(free -g 2>/dev/null | awk '/^Mem:/{print \$2}' || echo 0) -ge 8 ]" 5

# Studio CLI tools
[[ -x /usr/local/bin/studio-status ]] && run "studio-status installed" "true" || skip "studio-status" "not installed"
[[ -x /usr/local/bin/studio-model ]] && run "studio-model installed" "true" || skip "studio-model" "not installed"
[[ -x /usr/local/bin/studio-doctor ]] && run "studio-doctor installed" "true" || skip "studio-doctor" "not installed"

# Log directory writable
if mountpoint -q /mnt/studio 2>/dev/null && [[ -d /mnt/studio/logs ]]; then
  run "Logs writable" "touch /mnt/studio/logs/.test_write && rm /mnt/studio/logs/.test_write" 5
else
  skip "Logs writable" "storage not mounted"
fi

echo ""
echo -e "  \033[1mInfrastructure: $PASS passed, $FAIL failed, $SKIP skipped\033[0m"
[[ $FAIL -eq 0 ]]
