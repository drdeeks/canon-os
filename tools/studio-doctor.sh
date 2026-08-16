#!/usr/bin/env bash
# ============================================================================
# AI Creative Studio - Doctor
# ============================================================================
# The user-facing Swiss army knife. Browse models, check health, validate
# system, optimize settings, generate reports.
#
# Usage:
#   studio-doctor                   # Full diagnostic
#   studio-doctor health            # Quick health check
#   studio-doctor models            # Browse models
#   studio-doctor models --use-case product-shots
#   studio-doctor models --pull llama-3.1-8b
#   studio-doctor backends          # Show backend status
#   studio-doctor optimize          # Optimization check
#   studio-doctor validate          # End-to-end validation
#   studio-doctor cleanup           # Clean temp/logs/images
#   studio-doctor backup            # Backup configs
#   studio-doctor report            # Full system report
#   studio-doctor --json            # JSON output
#   studio-doctor --dry-run         # Preview only
#   studio-doctor --offline         # Skip network-dependent checks
#   studio-doctor --timeout 10      # Override default timeouts (seconds)
# ============================================================================

set -uo pipefail

VERSION="1.1.0"
STUDIO_BASE="/opt/ai-studio"
STUDIO_MOUNT="/mnt/studio"
CONFIG_DIR="$STUDIO_BASE/config"
BACKENDS_JSON="$CONFIG_DIR/backends.json"
MODEL_STATE="$CONFIG_DIR/model-state.json"
CATALOG_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../app/dashboard" && pwd)/model_catalog.py"

# Default timeouts (seconds)
TIMEOUT_CHECK=5
TIMEOUT_DOCKER_COMPOSE=10
TIMEOUT_PYTHON=5
TIMEOUT_HEALTH=3

# Flags
JSON_OUT=false
DRY_RUN=false
VERBOSE=false
OFFLINE=false

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'
B='\033[1m'; D='\033[0;90m'; N='\033[0m'

# ============================================================================
# Output helpers
# ============================================================================
_pass() { echo -e "  ${G}PASS${N}  $*"; }
_fail() { echo -e "  ${R}FAIL${N}  $*"; FAILURES=$((FAILURES+1)); }
_warn() { echo -e "  ${Y}WARN${N}  $*"; WARNINGS=$((WARNINGS+1)); }
_info() { echo -e "  ${C}INFO${N}  $*"; }
_tip()  { echo -e "  ${D}TIP${N}   $*"; }
_section() { echo -e "\n${C}${B}━━━ $* ━━━${N}"; }

FAILURES=0; WARNINGS=0; SCORE=0; MAX_SCORE=0

_score() { SCORE=$((SCORE+$1)); MAX_SCORE=$((MAX_SCORE+$2)); }

# ============================================================================
# Timeout wrapper - uses coreutils timeout if available, else perl fallback
# ============================================================================
_timeout() {
  local secs="$1"; shift
  if command -v timeout &>/dev/null; then
    timeout "${secs}" "$@"
  elif command -v perl &>/dev/null; then
    perl -e "alarm ${secs}; exec @ARGV" "$@" 2>/dev/null
  else
    "$@"
  fi
}

# ============================================================================
# JSON parsing: python3 with jq fallback
# ============================================================================
_json_get() {
  # Usage: _json_get <file> <dotted.key>
  local file="$1" key="$2"
  if command -v python3 &>/dev/null; then
    _timeout "$TIMEOUT_PYTHON" python3 -c "
import json, sys
with open('${file}') as f:
    d = json.load(f)
keys = '${key}'.split('.')
for k in keys:
    if isinstance(d, dict):
        d = d.get(k, '')
    else:
        d = ''
        break
print(d if d else '')
" 2>/dev/null || echo ""
  elif command -v jq &>/dev/null; then
    local jq_key
    jq_key=".${key//./.}"
    jq -r "${jq_key} // empty" "$file" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

_json_dump() {
  # Usage: _json_dump <python-expression>
  if command -v python3 &>/dev/null; then
    _timeout "$TIMEOUT_PYTHON" python3 -c "import json,sys; json.dump($1, sys.stdout, indent=2)" 2>/dev/null || echo "$1"
  else
    echo "$1"
  fi
}

_json_out() {
  if $JSON_OUT; then
    _json_dump "$1"
    exit 0
  fi
}

# ============================================================================
# Args
# ============================================================================
COMMAND="full"
SUB_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)     JSON_OUT=true; shift ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --verbose)  VERBOSE=true; shift ;;
    --offline)  OFFLINE=true; shift ;;
    --timeout)
      if [[ -n "${2:-}" ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
        TIMEOUT_CHECK="$2"
        TIMEOUT_DOCKER_COMPOSE="$2"
        TIMEOUT_PYTHON="$2"
        TIMEOUT_HEALTH="$2"
        shift 2
      else
        echo "Error: --timeout requires a numeric argument (seconds)" >&2
        exit 1
      fi
      ;;
    --help|-h)  head -30 "${BASH_SOURCE[0]}" | grep "^#" | sed 's/^# \?//'; exit 0 ;;
    --version)  echo "studio-doctor v$VERSION"; exit 0 ;;
    health|models|backends|optimize|validate|cleanup|backup|report|full)
      COMMAND="$1"; shift ;;
    --use-case|--pull|--remove)
      SUB_ARGS+=("$1" "$2"); shift 2 ;;
    *)
      SUB_ARGS+=("$1"); shift ;;
  esac
done

# ============================================================================
# Health Check
# ============================================================================
cmd_health() {
  _section "System Health"
  local healthy=0; local total=0

  # Docker
  ((total++))
  if command -v docker &>/dev/null && _timeout "$TIMEOUT_CHECK" docker info &>/dev/null 2>&1; then
    _pass "Docker running ($(docker --version | awk '{print $3}'))"
    ((healthy++))
  elif ! command -v docker &>/dev/null; then
    _fail "Docker not installed"
    _tip "Install: curl -fsSL https://get.docker.com | sh"
  else
    _fail "Docker not running"
    _tip "Fix: sudo systemctl start docker"
  fi

  # Containers (handles partial Docker: running but compose not started)
  ((total++))
  if command -v docker &>/dev/null && _timeout "$TIMEOUT_CHECK" docker info &>/dev/null 2>&1; then
    local running=$(_timeout "$TIMEOUT_CHECK" docker ps --format '{{.Names}}' 2>/dev/null | grep -c "studio-" || echo 0)
    local expected=0
    if [[ -f "$STUDIO_BASE/docker-compose.yaml" ]]; then
      expected=$(_timeout "$TIMEOUT_DOCKER_COMPOSE" docker compose -f "$STUDIO_BASE/docker-compose.yaml" config --services 2>/dev/null | wc -l || echo 0)
    elif [[ -f "$STUDIO_BASE/docker-compose.yml" ]]; then
      expected=$(_timeout "$TIMEOUT_DOCKER_COMPOSE" docker compose -f "$STUDIO_BASE/docker-compose.yml" config --services 2>/dev/null | wc -l || echo 0)
    fi
    if [[ $running -gt 0 ]]; then
      _pass "$running/$expected containers running"
      ((healthy++))
    elif [[ $expected -gt 0 ]]; then
      _fail "No studio containers running ($expected expected)"
      _tip "Fix: cd $STUDIO_BASE && docker compose up -d"
    else
      _warn "No compose file found or no services defined"
      _tip "Fix: ensure docker-compose.yaml exists at $STUDIO_BASE"
    fi
  else
    _fail "Cannot check containers: Docker not running"
    _tip "Fix: sudo systemctl start docker"
  fi

  # Storage
  ((total++))
  if mountpoint -q "$STUDIO_MOUNT" 2>/dev/null; then
    local avail=$(df -h "$STUDIO_MOUNT" --output=avail 2>/dev/null | tail -1 | tr -d ' ')
    _pass "Storage mounted ($avail free)"
    ((healthy++))
  else
    _warn "Storage not mounted at $STUDIO_MOUNT"
    _tip "Fix: sudo mount $STUDIO_MOUNT (check /etc/fstab)"
  fi

  # SSH
  ((total++))
  if ss -tlnp 2>/dev/null | grep -q ':2222 ' || pgrep -x sshd &>/dev/null; then
    _pass "SSH listening"
    ((healthy++))
  else
    _fail "SSH not listening on port 2222"
    _tip "Fix: sudo systemctl enable --now sshd"
  fi

  # GPU
  ((total++))
  if command -v nvidia-smi &>/dev/null; then
    local gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    _pass "GPU: $gpu"
    ((healthy++))
  elif uname -r | grep -qi "darwin"; then
    _pass "Apple Silicon detected"
    ((healthy++))
  else
    _warn "No GPU detected (CPU-only)"
  fi

  # Network (skip if offline)
  ((total++))
  if $OFFLINE; then
    _info "Network check skipped (--offline)"
    ((healthy++))
  elif ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    _pass "Network connectivity"
    ((healthy++))
  else
    _warn "No internet connectivity"
    _tip "Fix: check network config, firewall, or DNS settings"
  fi

  _score $healthy $total
  echo ""
  echo -e "  Health: ${B}$healthy/$total${N} checks passed"
}

# ============================================================================
# Models Browser
# ============================================================================
cmd_models() {
  _section "Model Browser"

  local use_case=""
  local action=""
  local model_id=""

  # Parse sub-args
  local i=0
  while [[ $i -lt ${#SUB_ARGS[@]} ]]; do
    case "${SUB_ARGS[$i]}" in
      --use-case) use_case="${SUB_ARGS[$((i+1))]}"; ((i+=2)) ;;
      --pull)     action="pull"; model_id="${SUB_ARGS[$((i+1))]}"; ((i+=2)) ;;
      --remove)   action="remove"; model_id="${SUB_ARGS[$((i+1))]}"; ((i+=2)) ;;
      *) ((i++)) ;;
    esac
  done

  # Pull action
  if [[ "$action" == "pull" ]]; then
    echo "  Pulling model: $model_id"
    if $DRY_RUN; then
      _info "[dry-run] Would download $model_id"
    else
      if [[ -x "/usr/local/bin/studio-model" ]]; then
        /usr/local/bin/studio-model pull "$model_id"
      else
        _fail "studio-model CLI not installed"
        _tip "Fix: run setup-master.sh to install CLI tools"
      fi
    fi
    return
  fi

  # List installed models
  echo -e "  ${B}Installed models:${N}"
  local installed=0
  for type_dir in text image video audio; do
    local dir="$STUDIO_MOUNT/models/$type_dir"
    [[ "$type_dir" == "audio" ]] && dir="$STUDIO_MOUNT/models/audio/tts"
    if [[ -d "$dir" ]]; then
      while IFS= read -r f; do
        local size=$(du -sh "$f" 2>/dev/null | cut -f1)
        local name=$(basename "$f")
        echo -e "    ${G}installed${N}  $name  ${D}($size)${N}"
        ((installed++))
      done < <(find "$dir" -maxdepth 2 \( -name "*.gguf" -o -name "*.safetensors" -o -name "*.onnx" -o -name "*.bin" \) 2>/dev/null)
    fi
  done

  if [[ $installed -eq 0 ]]; then
    _warn "No models installed"
    _tip "Fix: studio-model pull llama-3.1-8b"
  fi

  # Show available by use case
  echo ""
  echo -e "  ${B}Available for download:${N}"
  if [[ -n "$use_case" ]]; then
    echo "  (filtered by use case: $use_case)"
  fi

  # Catalog summary from the Python catalog
  if [[ -f "$CATALOG_PATH" ]]; then
    _timeout "$TIMEOUT_PYTHON" python3 -c "
import sys
sys.path.insert(0, '$(dirname "$CATALOG_PATH")')
from model_catalog import DEFAULT_CATALOG
uc = '$use_case'
for mtype, models in DEFAULT_CATALOG.items():
    for m in models:
        tags = m.get('tags', [])
        if uc and uc not in tags:
            continue
        print(f\\\"    {m['name']:30s}  {m['size_gb']:5.1f}GB  {mtype:6s}  {m.get('description','')[:50]}\\\")
" 2>/dev/null || _info "Install Python catalog for full model listing"
  fi

  _score $installed 5
}

# ============================================================================
# Backends Status
# ============================================================================
cmd_backends() {
  _section "Backend Status"

  if [[ ! -f "$BACKENDS_JSON" ]]; then
    _fail "Backend config not found at $BACKENDS_JSON"
    _tip "Fix: run setup-master.sh to generate config"
    return
  fi

  _pass "Config found: $BACKENDS_JSON"

  # Parse and display - try python3 first, fall back to jq
  if command -v python3 &>/dev/null; then
    _timeout "$TIMEOUT_PYTHON" python3 -c "
import json, urllib.request, sys

with open('$BACKENDS_JSON') as f:
    cfg = json.load(f)

backends = cfg.get('backends', {})
urls = cfg.get('urls', {})

for btype, bname in backends.items():
    url = urls.get(bname, 'unknown')
    # Health check
    try:
        req = urllib.request.urlopen(url + '/health', timeout=$TIMEOUT_HEALTH)
        status = 'HEALTHY'
    except:
        try:
            req = urllib.request.urlopen(url, timeout=$TIMEOUT_HEALTH)
            status = 'REACHABLE'
        except:
            status = 'OFFLINE'

    icon = 'PASS' if status in ('HEALTHY', 'REACHABLE') else 'FAIL'
    print(f'  {icon:4s}  {btype:6s}  {bname:20s}  {status:10s}  {url}')
" 2>/dev/null || _fail "Failed to parse backends config"
  elif command -v jq &>/dev/null; then
    local backends
    backends=$(jq -r '.backends // {} | to_entries[] | "\(.key)|\(.value)"' "$BACKENDS_JSON" 2>/dev/null || echo "")
    if [[ -n "$backends" ]]; then
      while IFS='|' read -r btype bname; do
        local url
        url=$(jq -r ".urls.\"${bname}\" // \"unknown\"" "$BACKENDS_JSON" 2>/dev/null || echo "unknown")
        if $OFFLINE; then
          echo "  SKIP  ${btype:6s}  ${bname:20s}  SKIPPED     ${url}"
        elif _timeout "$TIMEOUT_CHECK" curl -sf --max-time "$TIMEOUT_HEALTH" "${url}/health" &>/dev/null; then
          echo "  PASS  ${btype:6s}  ${bname:20s}  HEALTHY     ${url}"
        elif _timeout "$TIMEOUT_CHECK" curl -sf --max-time "$TIMEOUT_HEALTH" "${url}" &>/dev/null; then
          echo "  PASS  ${btype:6s}  ${bname:20s}  REACHABLE   ${url}"
        else
          echo "  FAIL  ${btype:6s}  ${bname:20s}  OFFLINE     ${url}"
        fi
      done <<< "$backends"
    fi
  else
    _warn "Neither python3 nor jq available for JSON parsing"
    _tip "Fix: install python3 or jq (apt install jq)"
  fi

  # Show hardware info
  echo ""
  if command -v python3 &>/dev/null; then
    _timeout "$TIMEOUT_PYTHON" python3 -c "
import json
with open('$BACKENDS_JSON') as f:
    cfg = json.load(f)
hw = cfg.get('hardware', {})
if hw:
    print(f\"  Hardware: {hw.get('gpu_type','unknown')} | {hw.get('ram_gb','?')}GB RAM | {hw.get('tier','?')} tier\")
" 2>/dev/null || true
  elif command -v jq &>/dev/null; then
    local hw_gpu hw_ram hw_tier
    hw_gpu=$(jq -r '.hardware.gpu_type // empty' "$BACKENDS_JSON" 2>/dev/null || echo "")
    if [[ -n "$hw_gpu" ]]; then
      hw_ram=$(jq -r '.hardware.ram_gb // "?"' "$BACKENDS_JSON" 2>/dev/null || echo "?")
      hw_tier=$(jq -r '.hardware.tier // "?"' "$BACKENDS_JSON" 2>/dev/null || echo "?")
      echo "  Hardware: ${hw_gpu} | ${hw_ram}GB RAM | ${hw_tier} tier"
    fi
  fi

  _score 1 1
}

# ============================================================================
# Optimization Check
# ============================================================================
cmd_optimize() {
  _section "Optimization Check"

  local optimized=0; local checks=0

  # VRAM budget
  ((checks++))
  if command -v nvidia-smi &>/dev/null; then
    local total_vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    local used_vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    local pct=$((used_vram * 100 / total_vram))
    if [[ $pct -lt 80 ]]; then
      _pass "VRAM usage: ${used_vram}MB / ${total_vram}MB (${pct}%)"
      ((optimized++))
    else
      _warn "VRAM usage high: ${pct}%"
      _tip "Fix: studio-model unload (offload unused models)"
    fi
  else
    _info "No NVIDIA GPU (skipping VRAM check)"
    ((optimized++))
  fi

  # Disk space
  ((checks++))
  local avail_gb=$(df "$STUDIO_MOUNT" --output=avail -BG 2>/dev/null | tail -1 | tr -dc '0-9')
  if [[ ${avail_gb:-0} -gt 50 ]]; then
    _pass "Disk space: ${avail_gb}GB free"
    ((optimized++))
  elif [[ ${avail_gb:-0} -gt 10 ]]; then
    _warn "Disk space: ${avail_gb}GB free (low)"
    _tip "Fix: studio-doctor cleanup"
  else
    _fail "Disk space critical: ${avail_gb:-0}GB free"
    _tip "Fix: free up space or expand storage"
  fi

  # Swap
  ((checks++))
  local swappiness=$(cat /proc/sys/vm/swappiness 2>/dev/null || echo 60)
  if [[ $swappiness -le 20 ]]; then
    _pass "Swappiness: $swappiness (good)"
    ((optimized++))
  else
    _warn "Swappiness: $swappiness (high, set to 10 for AI workloads)"
    _tip "Fix: echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf && sudo sysctl -p"
  fi

  # Docker log rotation
  ((checks++))
  if [[ -f /etc/docker/daemon.json ]] && grep -q "log-opts" /etc/docker/daemon.json 2>/dev/null; then
    _pass "Docker log rotation configured"
    ((optimized++))
  else
    _warn "Docker log rotation not configured"
    _tip "Fix: add 'log-opts' to /etc/docker/daemon.json (max-size: 10m, max-file: 3)"
  fi

  # Keep-alive service
  ((checks++))
  if systemctl is-active studio-keep-alive &>/dev/null 2>&1; then
    _pass "Keep-alive service running"
    ((optimized++))
  else
    _warn "Keep-alive service not running"
    _tip "Fix: sudo systemctl enable --now studio-keep-alive"
  fi

  # Resource monitor
  ((checks++))
  if systemctl is-active studio-resource-monitor &>/dev/null 2>&1; then
    _pass "Resource monitor running"
    ((optimized++))
  else
    _warn "Resource monitor not running"
    _tip "Fix: sudo systemctl enable --now studio-resource-monitor"
  fi

  _score $optimized $checks
  echo ""
  echo -e "  Optimization: ${B}$optimized/$checks${N} checks passed"
}

# ============================================================================
# Full Validation
# ============================================================================
cmd_validate() {
  _section "End-to-End Validation"

  if $DRY_RUN; then
    _info "[dry-run] Would validate all components"
    return
  fi

  # Run test suite
  if [[ -x "$STUDIO_BASE/../tests/run-all.sh" ]]; then
    "$STUDIO_BASE/../tests/run-all.sh" --verbose
  elif [[ -x "$(cd "$(dirname "${BASH_SOURCE[0]}")/../tests" && pwd)/run-all.sh" ]]; then
    "$(cd "$(dirname "${BASH_SOURCE[0]}")/../tests" && pwd)/run-all.sh" --verbose
  else
    _fail "Test suite not found"
    _tip "Fix: ensure tests/ directory exists in the project root"
  fi
}

# ============================================================================
# Cleanup
# ============================================================================
cmd_cleanup() {
  _section "Cleanup"

  local freed=0

  # Docker dangling images
  if command -v docker &>/dev/null && _timeout "$TIMEOUT_CHECK" docker info &>/dev/null 2>&1; then
    local dangling=$(_timeout "$TIMEOUT_DOCKER_COMPOSE" docker images -f "dangling=true" -q 2>/dev/null | wc -l)
    if [[ $dangling -gt 0 ]]; then
      echo "  Found $dangling dangling Docker images"
      if $DRY_RUN; then
        _info "[dry-run] Would remove $dangling images"
      else
        _timeout "$TIMEOUT_DOCKER_COMPOSE" docker image prune -f &>/dev/null
        _pass "Removed $dangling dangling images"
      fi
    else
      _pass "No dangling Docker images"
    fi
  else
    _warn "Docker not running, skipping image cleanup"
    _tip "Fix: sudo systemctl start docker"
  fi

  # Old logs (>30 days)
  if [[ -d "$STUDIO_MOUNT/logs" ]]; then
    local old_logs=$(find "$STUDIO_MOUNT/logs" -name "*.log" -mtime +30 2>/dev/null | wc -l)
    if [[ $old_logs -gt 0 ]]; then
      echo "  Found $old_logs old log files (>30 days)"
      if $DRY_RUN; then
        _info "[dry-run] Would remove $old_logs log files"
      else
        find "$STUDIO_MOUNT/logs" -name "*.log" -mtime +30 -delete 2>/dev/null
        _pass "Removed $old_logs old log files"
      fi
    fi
  fi

  # Temp files
  if [[ -d "$STUDIO_MOUNT/cache" ]]; then
    local cache_size=$(du -sh "$STUDIO_MOUNT/cache" 2>/dev/null | cut -f1)
    _info "Cache size: $cache_size"
    if [[ "$cache_size" == *G* ]]; then
      _warn "Cache is large ($cache_size). Consider clearing."
      _tip "Fix: rm -rf $STUDIO_MOUNT/cache/* (if safe)"
    fi
  fi

  _pass "Cleanup complete"
}

# ============================================================================
# Backup
# ============================================================================
cmd_backup() {
  _section "Backup"

  local backup_dir="$STUDIO_MOUNT/backups/$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$backup_dir"

  if $DRY_RUN; then
    _info "[dry-run] Would backup to $backup_dir"
    return
  fi

  # Config files
  [[ -f "$BACKENDS_JSON" ]] && cp "$BACKENDS_JSON" "$backup_dir/" && _pass "Backed up backends.json"
  [[ -f "$MODEL_STATE" ]] && cp "$MODEL_STATE" "$backup_dir/" && _pass "Backed up model-state.json"

  # Creator settings
  if [[ -d "/home/creator/ai-studio/config" ]]; then
    cp -r "/home/creator/ai-studio/config" "$backup_dir/creator-config" 2>/dev/null
    _pass "Backed up creator settings"
  fi

  # Docker compose
  [[ -f "$STUDIO_BASE/docker-compose.yaml" ]] && cp "$STUDIO_BASE/docker-compose.yaml" "$backup_dir/" && _pass "Backed up docker-compose"

  echo ""
  echo -e "  Backup saved to: ${B}$backup_dir${N}"
}

# ============================================================================
# Full Report
# ============================================================================
cmd_report() {
  _section "System Report"
  echo "  Generated: $(date -Iseconds)"
  echo "  Hostname: $(hostname)"
  echo "  Kernel: $(uname -r)"
  echo ""

  cmd_health
  cmd_backends
  cmd_models
  cmd_optimize

  echo ""
  echo -e "  Overall Score: ${B}$SCORE/$MAX_SCORE${N}"
  if [[ $FAILURES -gt 0 ]]; then
    echo -e "  ${R}$FAILURES failures, $WARNINGS warnings${N}"
  elif [[ $WARNINGS -gt 0 ]]; then
    echo -e "  ${Y}$WARNINGS warnings${N}"
  else
    echo -e "  ${G}All checks passed${N}"
  fi
}

# ============================================================================
# Main
# ============================================================================
case "$COMMAND" in
  health)    cmd_health ;;
  models)    cmd_models ;;
  backends)  cmd_backends ;;
  optimize)  cmd_optimize ;;
  validate)  cmd_validate ;;
  cleanup)   cmd_cleanup ;;
  backup)    cmd_backup ;;
  report)    cmd_report ;;
  full)      cmd_report ;;
  *)         echo "Unknown command: $COMMAND"; exit 1 ;;
esac

exit $FAILURES
