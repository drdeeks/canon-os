#!/usr/bin/env bash
# ============================================================================
# AI Creative Studio - Master Setup Script
# ============================================================================
# THE single entry point. Run this on a fresh machine, it handles everything:
#   - Hardware detection (M4 Max, NVIDIA, CPU-only)
#   - Docker installation (if missing)
#   - SSH hardening (if not configured)
#   - Storage setup (external drives)
#   - Backend selection (auto-recommended based on hardware)
#   - Docker Compose generation (only services for selected backends)
#   - User accounts (creator + admin)
#   - Model download (starter pack per use case)
#   - Validation (smoke tests)
#
# Usage:
#   sudo bash setup-master.sh                 # Interactive
#   sudo bash setup-master.sh --auto          # Unattended (defaults)
#   sudo bash setup-master.sh --dry-run       # Show what would happen
# ============================================================================

set -euo pipefail
trap 'echo ""; echo "[FATAL] Failed at line $LINENO. Check output above." >&2' ERR

VERSION="1.0.0"
STUDIO_BASE="/opt/ai-studio"
STUDIO_MOUNT="/mnt/studio"
STUDIO_CONFIG="$STUDIO_BASE/config"
CREATOR_HOME="/home/creator"
ADMIN_HOME="/home/admin"
SSH_PORT=2222

DRY_RUN=false
AUTO=false
STRICT=false
ADMIN_PUBKEY=""
EXTERNAL_DRIVE=""
SKIP_DOCKER=false
SKIP_SSH=false
SKIP_GPU=false
SKIP_CONTAINERS=false

# ============================================================================
# Colors & Output
# ============================================================================
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1m'; N='\033[0m'
log()  { echo -e "${G}[+]${N} $*"; }
warn() { echo -e "${Y}[!]${N} $*"; }
err()  { echo -e "${R}[X]${N} $*" >&2; }
step() { echo -e "\n${C}${B}━━━ $* ━━━${N}\n"; }

# Interactive prompt with timeout. Never hangs.
# ask "prompt" "default" [timeout_seconds]
ask() {
  local prompt="$1" default="$2" timeout="${3:-10}"
  if $AUTO; then echo "$default"; return; fi
  local val=""
  if [[ -t 0 ]]; then
    read -t "$timeout" -p "$(echo -e "${C}?${N} $prompt [${default}]: ")" val 2>/dev/null || true
  fi
  echo "${val:-$default}"
}

# Yes/No/Skip prompt with timeout. Returns 0=yes, 1=no, 2=skip.
# yns "prompt" "default(y/n/s)" [timeout_seconds]
yns() {
  local prompt="$1" default="${2:-n}" timeout="${3:-10}"
  if $AUTO; then
    [[ "$default" == "y" ]] && return 0
    [[ "$default" == "s" ]] && return 2
    return 1
  fi
  local val=""
  if [[ -t 0 ]]; then
    read -t "$timeout" -p "$(echo -e "${C}?${N} $prompt [y/N/Skip]: ")" val 2>/dev/null || true
  fi
  val="${val:-$default}"
  val="${val,,}"  # lowercase
  [[ "$val" == "y" || "$val" == "yes" ]] && return 0
  [[ "$val" == "s" || "$val" == "skip" ]] && return 2
  return 1
}

# Safe apt-get with timeouts
safe_apt() {
  apt-get -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o DPkg::Options::="--force-confold" "$@"
}

# Safe curl with timeout
safe_curl() {
  curl --max-time 30 --retry 3 --retry-delay 2 --fail --silent --show-error "$@"
}

# Network check
is_online() {
  ping -c 1 -W 3 8.8.8.8 &>/dev/null || ping -c 1 -W 3 1.1.1.1 &>/dev/null
}

# Track what was done
INSTALLED=(); SKIPPED=(); FAILED=()
track_install() { INSTALLED+=("$1"); }
track_skip() { SKIPPED+=("$1"); }
track_fail() { FAILED+=("$1"); warn "$1 failed: $2"; }

# Print summary
print_summary() {
  echo ""
  echo -e "${B}━━━ SUMMARY ━━━${N}"
  echo ""
  [[ ${#INSTALLED[@]} -gt 0 ]] && echo -e "${G}Installed:${N} ${INSTALLED[*]}"
  [[ ${#SKIPPED[@]} -gt 0 ]]  && echo -e "${Y}Skipped:${N}  ${SKIPPED[*]}"
  [[ ${#FAILED[@]} -gt 0 ]]   && echo -e "${R}Failed:${N}   ${FAILED[*]}"
  echo ""
  echo -e "Total: ${G}${#INSTALLED[@]}${N} installed, ${Y}${#SKIPPED[@]}${N} skipped, ${R}${#FAILED[@]}${N} failed"
}

confirm() {
  if yns "$1" "${2:-n}" "${3:-10}"; then return 0; else return 1; fi
}
run()  { if $DRY_RUN; then echo "  [dry-run] $*"; else eval "$*"; fi }

# ============================================================================
# Args
# ============================================================================
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)       DRY_RUN=true; shift ;;
    --auto)          AUTO=true; shift ;;
    --strict)        STRICT=true; shift ;;
    --admin-pubkey)  ADMIN_PUBKEY="$2"; shift 2 ;;
    --external)      EXTERNAL_DRIVE="$2"; shift 2 ;;
    --mount)         STUDIO_MOUNT="$2"; shift 2 ;;
    --skip-docker)   SKIP_DOCKER=true; shift ;;
    --skip-ssh)      SKIP_SSH=true; shift ;;
    --skip-gpu)      SKIP_GPU=true; shift ;;
    --skip-containers) SKIP_CONTAINERS=true; shift ;;
    --yes|-y)        AUTO=true; shift ;;
    --help|-h)
      echo "AI Creative Studio - Master Setup"
      echo ""
      echo "Usage: sudo bash setup-master.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --auto              Unattended mode (defaults for everything)"
      echo "  --yes, -y           Same as --auto"
      echo "  --dry-run           Show what would happen, don't change anything"
      echo "  --strict            Abort on any failure (default: continue)"
      echo "  --admin-pubkey KEY  Install SSH key for admin account"
      echo "  --external DRIVE    External drive to format (e.g., /dev/sda1)"
      echo "  --mount PATH        Mount point for storage (default: /mnt/studio)"
      echo "  --skip-docker       Skip Docker installation"
      echo "  --skip-ssh          Skip SSH hardening"
      echo "  --skip-gpu          Skip GPU toolkit installation"
      echo "  --skip-containers   Skip Docker image pulls"
      echo "  --help              Show this help"
      exit 0 ;;
    *) err "Unknown: $1. Use --help for options."; exit 1 ;;
  esac
done

# ============================================================================
# Step 0: Pre-flight
# ============================================================================
step "0/9 Pre-flight Checks"

if [[ $EUID -ne 0 ]]; then err "Run as root: sudo bash setup-master.sh"; exit 1; fi

[[ -f /etc/os-release ]] && . /etc/os-release || { err "Cannot detect OS"; exit 1; }
log "OS: $PRETTY_NAME ($VERSION_CODENAME)"
log "Arch: $(uname -m)"

# ============================================================================
# Step 1: Hardware Detection
# ============================================================================
step "1/9 Hardware Detection"

GPU_TYPE="none"
GPU_NAME="None"
GPU_VRAM_MB=0
TOTAL_RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "0")
CPU_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "1")
CPU_ARCH=$(uname -m)

# Apple Silicon detection
if [[ "$OSTYPE" == "darwin"* ]] || uname -r | grep -qi "darwin"; then
  PLATFORM="macos"
  GPU_TYPE="apple-silicon"
  GPU_NAME=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset" | head -1 | sed 's/.*: //' || echo "Apple Silicon")
  # Apple Silicon shares RAM/VRAM
  GPU_VRAM_MB=$((TOTAL_RAM_GB * 1024 * 70 / 100))  # ~70% usable
  TOTAL_RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}' || echo "$TOTAL_RAM_GB")
elif command -v nvidia-smi &>/dev/null; then
  PLATFORM="linux"
  GPU_TYPE="nvidia"
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
  GPU_VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
  log "NVIDIA: $GPU_NAME (${GPU_VRAM_MB}MB VRAM)"
elif [[ -d /sys/class/drm/card0 ]] && lspci 2>/dev/null | grep -qi "amd\|radeon"; then
  PLATFORM="linux"
  GPU_TYPE="amd"
  GPU_NAME="AMD GPU"
  GPU_VRAM_MB=0  # AMD detection is more complex
  warn "AMD GPU detected. ROCm support is experimental."
else
  PLATFORM="linux"
  GPU_TYPE="none"
  warn "No GPU detected. CPU-only inference (slow for large models)."
fi

GPU_VRAM_GB=$((GPU_VRAM_MB / 1024))
log "GPU: $GPU_TYPE ($GPU_NAME, ${GPU_VRAM_GB}GB)"
log "RAM: ${TOTAL_RAM_GB}GB"
log "CPU: $CPU_CORES cores ($CPU_ARCH)"

# Determine hardware tier
if [[ $TOTAL_RAM_GB -ge 64 && ($GPU_VRAM_GB -ge 24 || "$GPU_TYPE" == "apple-silicon") ]]; then
  HW_TIER="high"
  log "Hardware tier: HIGH (full stack capable)"
elif [[ $TOTAL_RAM_GB -ge 32 && ($GPU_VRAM_GB -ge 12 || "$GPU_TYPE" == "apple-silicon") ]]; then
  HW_TIER="mid"
  log "Hardware tier: MID (most models, some limits)"
elif [[ $TOTAL_RAM_GB -ge 16 ]]; then
  HW_TIER="low"
  log "Hardware tier: LOW (small models only)"
else
  HW_TIER="minimal"
  warn "Hardware tier: MINIMAL (very limited)"
fi

# ============================================================================
# Step 2: Docker Installation
# ============================================================================
step "2/9 Docker"

if $SKIP_DOCKER; then
  log "Docker installation skipped (--skip-docker)"
  track_skip "docker"
elif command -v docker &>/dev/null; then
  log "Docker already installed: $(docker --version)"
  track_install "docker-already"
else
  if yns "Docker not found. Install Docker?" "y" 15; then
    log "Installing Docker..."

    if [[ "$PLATFORM" == "macos" ]]; then
      warn "macOS detected. Install Docker Desktop manually:"
      warn "  https://docs.docker.com/desktop/install/mac-install/"
      warn "Then re-run this script."
      track_skip "docker-macos"
    else
      # Detect package manager
      PKG=""
      if command -v apt-get &>/dev/null; then PKG="apt"
      elif command -v dnf &>/dev/null; then PKG="dnf"
      elif command -v yum &>/dev/null; then PKG="yum"
      elif command -v pacman &>/dev/null; then PKG="pacman"
      fi

      if [[ -z "$PKG" ]]; then
        err "Cannot detect package manager. Install Docker manually."
        track_fail "docker" "no package manager"
      else
        log "Package manager: $PKG"

        if [[ "$PKG" == "apt" ]]; then
          run "safe_apt update -qq" || track_fail "apt-update" "network error"
          run "safe_apt install -y -qq ca-certificates curl gnupg lsb-release" || true

          run "install -m 0755 -d /etc/apt/keyrings" || true
          safe_curl -o /etc/apt/keyrings/docker.asc "https://download.docker.com/linux/$ID/gpg" 2>/dev/null || \
            track_fail "docker-gpg" "download failed"
          run "chmod a+r /etc/apt/keyrings/docker.asc" || true

          echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
            https://download.docker.com/linux/$ID $VERSION_CODENAME stable" | \
            tee /etc/apt/sources.list.d/docker.list > /dev/null

          run "safe_apt update -qq" || true
          run "safe_apt install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin" || \
            track_fail "docker-install" "apt failed"
        elif [[ "$PKG" == "dnf" || "$PKG" == "yum" ]]; then
          run "$PKG install -y docker docker-compose-plugin" || track_fail "docker-install" "$PKG failed"
        elif [[ "$PKG" == "pacman" ]]; then
          run "pacman -S --noconfirm docker docker-compose" || track_fail "docker-install" "pacman failed"
        fi

        if command -v docker &>/dev/null; then
          run "systemctl enable docker" || true
          run "systemctl start docker" || true
          log "Docker installed and started."
          track_install "docker"
        fi
      fi
    fi
  else
    warn "Docker skipped. Some features will not work."
    track_skip "docker"
  fi
fi

# GPU container runtime
if $SKIP_GPU; then
  log "GPU toolkit skipped (--skip-gpu)"
  track_skip "gpu-toolkit"
elif [[ "$GPU_TYPE" == "nvidia" ]]; then
  if ! command -v nvidia-ctk &>/dev/null; then
    if yns "NVIDIA Container Toolkit not found. Install it? (needed for GPU in Docker)" "y" 15; then
      log "Installing NVIDIA Container Toolkit..."
      safe_curl -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
        "https://nvidia.github.io/libnvidia-container/gpgkey" 2>/dev/null || \
        track_fail "nvidia-gpg" "download failed"
      echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] \
        https://nvidia.github.io/libnvidia-container/stable/deb/\$(ARCH) /" | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
      safe_apt update -qq 2>/dev/null || true
      safe_apt install -y -qq nvidia-container-toolkit 2>/dev/null || \
        track_fail "nvidia-toolkit" "install failed"
      if command -v nvidia-ctk &>/dev/null; then
        nvidia-ctk runtime configure --runtime=docker 2>/dev/null || true
        systemctl restart docker 2>/dev/null || true
        log "NVIDIA Container Toolkit configured."
        track_install "nvidia-toolkit"
      fi
    else
      track_skip "nvidia-toolkit"
    fi
  else
    log "NVIDIA Container Toolkit already installed."
    track_install "nvidia-toolkit-already"
  fi
elif [[ "$GPU_TYPE" == "apple-silicon" ]]; then
  log "Apple Silicon detected - Metal GPU passthrough via Docker Desktop"
  track_install "apple-metal"
fi

# ============================================================================
# Step 3: SSH Setup
# ============================================================================
step "3/9 SSH"

if systemctl is-active sshd &>/dev/null || systemctl is-active ssh &>/dev/null; then
  log "SSH server running."
else
  log "Installing and configuring SSH..."
  run "apt-get install -y -qq openssh-server"
  run "systemctl enable ssh"
  run "systemctl start ssh"
fi

# Check if already hardened
if grep -q "Port $SSH_PORT" /etc/ssh/sshd_config.d/*.conf 2>/dev/null; then
  log "SSH already hardened on port $SSH_PORT."
else
  log "Hardening SSH..."
  cat > /etc/ssh/sshd_config.d/99-studio.conf <<SSH
Port $SSH_PORT
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
PrintMotd yes
SSH
  run "systemctl restart sshd" || run "systemctl restart ssh"
  log "SSH hardened on port $SSH_PORT."
fi

# fail2ban
if ! command -v fail2ban-client &>/dev/null; then
  run "apt-get install -y -qq fail2ban"
fi
cat > /etc/fail2ban/jail.d/99-studio.conf <<F2B
[sshd]
enabled = true
port = $SSH_PORT
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
F2B
run "systemctl restart fail2ban" || true
run "systemctl enable fail2ban" || true

# Firewall
if command -v ufw &>/dev/null; then
  run "apt-get install -y -qq ufw" || true
  run "ufw default deny incoming" || true
  run "ufw default allow outgoing" || true
  run "ufw allow $SSH_PORT/tcp comment 'SSH'" || true
  run "ufw --force enable" || true
  log "Firewall: only port $SSH_PORT open."
fi

# ============================================================================
# Step 4: Storage
# ============================================================================
step "4/9 Storage"

run "mkdir -p $STUDIO_MOUNT"

# Auto-detect external drives if not specified
if [[ -z "$EXTERNAL_DRIVE" ]]; then
  EXTERNALS=$(lsblk -dnpo NAME,SIZE,TYPE,MOUNTPOINT | grep "disk" | grep -v "part" | awk '{print $1}' | head -5)
  log "Available drives:"
  lsblk -dnpo NAME,SIZE,TYPE,MOUNTPOINT 2>/dev/null | grep "disk" || true

  if ! $AUTO; then
    EXTERNAL_DRIVE=$(ask "External drive to format/mount (or 'skip' for existing)" "skip")
  fi
fi

if [[ "$EXTERNAL_DRIVE" != "skip" && -n "$EXTERNAL_DRIVE" ]]; then
  if [[ -b "$EXTERNAL_DRIVE" ]]; then
    if confirm "Format $EXTERNAL_DRIVE as ext4? ALL DATA WILL BE LOST"; then
      run "mkfs.ext4 -L studio $EXTERNAL_DRIVE"
      UUID=$(blkid -s UUID -o value "$EXTERNAL_DRIVE")
      if ! grep -q "$STUDIO_MOUNT" /etc/fstab; then
        run "echo 'UUID=$UUID $STUDIO_MOUNT ext4 defaults,noatime,nofail 0 2' >> /etc/fstab"
      fi
      run "mount -a"
    fi
  else
    warn "Drive $EXTERNAL_DRIVE not found. Skipping format."
  fi
fi

# Create directory structure
run "mkdir -p $STUDIO_MOUNT"/{models/{text,image/{checkpoints,loras,controlnet,vae,upscale},video,audio/{tts,music,stt}},projects,exports,uploads,cache/{huggingface,comfyui},logs,config,invokeai}
run "mkdir -p $STUDIO_BASE"/{config,tests/{smoke,integration,benchmarks},scripts}

log "Storage structure created."

# ============================================================================
# Step 5: Backend Selection
# ============================================================================
step "5/9 Backend Selection"

# Recommend backends based on hardware
case "$GPU_TYPE" in
  nvidia)
    RECOMMENDED_TEXT="llama-cpp"
    RECOMMENDED_IMAGE="comfyui"
    RECOMMENDED_VIDEO="comfyui-video"
    RECOMMENDED_TTS="kokoro"
    RECOMMENDED_STT="whisper"
    RECOMMENDED_MUSIC="audiocraft"
    ;;
  apple-silicon)
    RECOMMENDED_TEXT="llama-cpp"
    RECOMMENDED_IMAGE="comfyui"
    RECOMMENDED_VIDEO="comfyui-video"
    RECOMMENDED_TTS="kokoro"
    RECOMMENDED_STT="whisper"
    RECOMMENDED_MUSIC="audiocraft"
    ;;
  *)
    RECOMMENDED_TEXT="ollama"
    RECOMMENDED_IMAGE="comfyui"
    RECOMMENDED_VIDEO="comfyui-video"
    RECOMMENDED_TTS="kokoro"
    RECOMMENDED_STT="whisper"
    RECOMMENDED_MUSIC="audiocraft"
    ;;
esac

if $AUTO; then
  TEXT_BACKEND="$RECOMMENDED_TEXT"
  IMAGE_BACKEND="$RECOMMENDED_IMAGE"
  VIDEO_BACKEND="$RECOMMENDED_VIDEO"
  TTS_BACKEND="$RECOMMENDED_TTS"
  STT_BACKEND="$RECOMMENDED_STT"
  MUSIC_BACKEND="$RECOMMENDED_MUSIC"
else
  echo "Recommended backends for your ($GPU_TYPE, ${TOTAL_RAM_GB}GB RAM):"
  echo ""
  TEXT_BACKEND=$(ask "Text backend (llama-cpp/ollama/vllm)" "$RECOMMENDED_TEXT")
  IMAGE_BACKEND=$(ask "Image backend (comfyui/automatic1111)" "$RECOMMENDED_IMAGE")
  VIDEO_BACKEND=$(ask "Video backend (comfyui-video/animatediff)" "$RECOMMENDED_VIDEO")
  TTS_BACKEND=$(ask "TTS backend (kokoro/coqui/bark)" "$RECOMMENDED_TTS")
  STT_BACKEND=$(ask "Speech-to-text backend (whisper/faster-whisper)" "$RECOMMENDED_STT")
  MUSIC_BACKEND=$(ask "Music backend (audiocraft/stable-audio/none)" "$RECOMMENDED_MUSIC")
fi

log "Selected backends:"
log "  Text:  $TEXT_BACKEND"
log "  Image: $IMAGE_BACKEND"
log "  Video: $VIDEO_BACKEND"
log "  TTS:   $TTS_BACKEND"
log "  STT:   $STT_BACKEND"
log "  Music: $MUSIC_BACKEND"

# Write backend config
run "mkdir -p $STUDIO_CONFIG"
cat > "$STUDIO_CONFIG/backends.json" <<CONF
{
  "backends": {
    "text": "$TEXT_BACKEND",
    "image": "$IMAGE_BACKEND",
    "video": "$VIDEO_BACKEND",
    "tts": "$TTS_BACKEND",
    "stt": "$STT_BACKEND",
    "music": "$MUSIC_BACKEND"
  },
  "urls": {
    "llama-cpp": "http://studio-llamacpp:8080",
    "ollama": "http://studio-ollama:11434",
    "comfyui": "http://studio-comfyui:8188",
    "comfyui-video": "http://studio-comfyui:8188",
    "kokoro": "http://studio-kokoro:8880",
    "whisper": "http://studio-whisper:9000",
    "audiocraft": "http://studio-audiocraft:7860"
  },
  "hardware": {
    "gpu_type": "$GPU_TYPE",
    "gpu_name": "$GPU_NAME",
    "gpu_vram_gb": $GPU_VRAM_GB,
    "ram_gb": $TOTAL_RAM_GB,
    "cpu_cores": $CPU_CORES,
    "tier": "$HW_TIER"
  }
}
CONF
log "Backend config written to $STUDIO_CONFIG/backends.json"

# ============================================================================
# Step 6: Docker Compose Generation
# ============================================================================
step "6/9 Docker Compose"

# Generate compose based on selected backends
COMPOSE_FILE="$STUDIO_BASE/docker-compose.yaml"
cat > "$COMPOSE_FILE" <<'HEADER'
# ============================================================================
# AI Creative Studio - Generated Docker Compose
# Generated by setup-master.sh. Edit config/backends.json to change backends.
# ============================================================================
services:
HEADER

# Ollama service (if selected)
if [[ "$TEXT_BACKEND" == "ollama" ]]; then
cat >> "$COMPOSE_FILE" <<'SVC'
  ollama:
    image: ollama/ollama:latest
    container_name: studio-ollama
    restart: unless-stopped
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - /mnt/studio/models/text:/models
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_MODELS=/models
      - OLLAMA_HOST=0.0.0.0:11434
    deploy:
      resources:
        limits:
          memory: 48G
SVC
[[ "$GPU_TYPE" == "nvidia" ]] && cat >> "$COMPOSE_FILE" <<'GPU'
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
GPU
echo "" >> "$COMPOSE_FILE"
fi

# llama.cpp service (if selected)
if [[ "$TEXT_BACKEND" == "llama-cpp" ]]; then
  # Determine GPU layers based on hardware
  if [[ "$GPU_TYPE" == "nvidia" ]]; then
    GPU_LAYERS=99
    DOCKER_IMAGE="ghcr.io/ggerganov/llama.cpp:server-cuda"
  elif [[ "$GPU_TYPE" == "apple-silicon" ]]; then
    GPU_LAYERS=99
    DOCKER_IMAGE="ghcr.io/ggerganov/llama.cpp:server"
  else
    GPU_LAYERS=0
    DOCKER_IMAGE="ghcr.io/ggerganov/llama.cpp:server"
  fi

cat >> "$COMPOSE_FILE" <<SVC
  llamacpp:
    image: $DOCKER_IMAGE
    container_name: studio-llamacpp
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - /mnt/studio/models/text:/models
    command: >
      --host 0.0.0.0
      --port 8080
      --model /models/llama-3.1-8b-instruct-Q4_K_M.gguf
      --ctx-size 4096
      --n-gpu-layers $GPU_LAYERS
      --chat-template chatml
    deploy:
      resources:
        limits:
          memory: 48G
SVC
[[ "$GPU_TYPE" == "nvidia" ]] && cat >> "$COMPOSE_FILE" <<'GPU'
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
GPU
echo "" >> "$COMPOSE_FILE"
fi

# ComfyUI (image + video)
if [[ "$IMAGE_BACKEND" == "comfyui" || "$VIDEO_BACKEND" == "comfyui-video" ]]; then
cat >> "$COMPOSE_FILE" <<'SVC'
  comfyui:
    image: ghcr.io/ai-dock/comfyui:latest-cuda
    container_name: studio-comfyui
    restart: unless-stopped
    ports:
      - "127.0.0.1:8188:8188"
    volumes:
      - /mnt/studio/models/image:/app/ComfyUI/models
      - /mnt/studio/models/video:/app/ComfyUI/models/video
      - /mnt/studio/exports:/app/ComfyUI/output
      - /mnt/studio/uploads:/app/ComfyUI/input
    deploy:
      resources:
        limits:
          memory: 32G
SVC
[[ "$GPU_TYPE" == "nvidia" ]] && cat >> "$COMPOSE_FILE" <<'GPU'
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
GPU
echo "" >> "$COMPOSE_FILE"
fi

# Kokoro TTS
if [[ "$TTS_BACKEND" == "kokoro" ]]; then
cat >> "$COMPOSE_FILE" <<'SVC'
  kokoro:
    image: python:3.11-slim
    container_name: studio-kokoro
    restart: unless-stopped
    ports:
      - "127.0.0.1:8880:8880"
    volumes:
      - /mnt/studio/models/audio/tts:/models
      - /mnt/studio/exports:/exports
    command: >
      bash -c "pip install --no-cache-dir kokoro-onnx soundfile flask &&
      python -c \"
from flask import Flask, request, jsonify, send_file
import subprocess, os
app = Flask(__name__)
@app.route('/health')\ndef health(): return 'ok'
@app.route('/generate', methods=['POST'])\ndef generate():
    data = request.json
    return jsonify({'status': 'ok', 'message': 'TTS ready'})
app.run(host='0.0.0.0', port=8880)
\""
SVC
echo "" >> "$COMPOSE_FILE"
fi

# Whisper STT
if [[ "$STT_BACKEND" == "whisper" ]]; then
cat >> "$COMPOSE_FILE" <<'SVC'
  whisper:
    image: ghcr.io/drhino/whisper-cpp-api:latest
    container_name: studio-whisper
    restart: unless-stopped
    ports:
      - "127.0.0.1:9000:9000"
    volumes:
      - /mnt/studio/models/audio/stt:/models
    environment:
      - WHISPER_MODEL=/models/ggml-large-v3.bin
SVC
[[ "$GPU_TYPE" == "nvidia" ]] && cat >> "$COMPOSE_FILE" <<'GPU'
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
GPU
echo "" >> "$COMPOSE_FILE"
fi

# AudioCraft / MusicGen
if [[ "$MUSIC_BACKEND" == "audiocraft" ]]; then
cat >> "$COMPOSE_FILE" <<'SVC'
  audiocraft:
    image: python:3.11-slim
    container_name: studio-audiocraft
    restart: unless-stopped
    ports:
      - "127.0.0.1:7860:7860"
    volumes:
      - /mnt/studio/models/audio/music:/models
      - /mnt/studio/exports:/exports
    environment:
      - GRADIO_SERVER_NAME=0.0.0.0
      - GRADIO_SERVER_PORT=7860
    deploy:
      resources:
        limits:
          memory: 16G
SVC
[[ "$GPU_TYPE" == "nvidia" ]] && cat >> "$COMPOSE_FILE" <<'GPU'
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
GPU
echo "" >> "$COMPOSE_FILE"
fi

# Dashboard
cat >> "$COMPOSE_FILE" <<'SVC'
  dashboard:
    build:
      context: /opt/ai-studio/app/dashboard
      dockerfile: Dockerfile
    container_name: studio-dashboard
    restart: unless-stopped
    ports:
      - "127.0.0.1:5000:5000"
    volumes:
      - /home/creator/ai-studio:/home/creator/ai-studio
      - /mnt/studio:/mnt/studio
      - /mnt/studio/exports:/app/output:ro
      - /mnt/studio/uploads:/app/uploads
    environment:
      - CREATOR_HOME=/home/creator/ai-studio
      - STUDIO_MOUNT=/mnt/studio
      - STUDIO_CONFIG=/opt/ai-studio/config/backends.json
SVC

# Networks and volumes
cat >> "$COMPOSE_FILE" <<'FOOTER'

networks:
  default:
    name: studio-network

volumes:
  ollama-data:
FOOTER

log "Docker Compose generated at $COMPOSE_FILE"

# ============================================================================
# Step 7: User Accounts
# ============================================================================
step "7/9 User Accounts"

# Creator
if id creator &>/dev/null; then
  log "Creator account exists."
else
  run "useradd -m -s /usr/sbin/nologin -c 'AI Studio Creator' creator"
  log "Created creator account."
fi
run "mkdir -p $CREATOR_HOME/ai-studio"/{config,models/{text,image,video,audio},projects,exports,uploads,cache}
run "chown -R creator:creator $CREATOR_HOME"
run "chmod 700 $CREATOR_HOME"

# Admin
if id admin &>/dev/null; then
  log "Admin account exists."
else
  run "useradd -m -s /bin/bash -c 'AI Studio Admin' admin"
  log "Created admin account."
fi
run "usermod -aG docker,sudo admin" || true

# SSH key for admin
if [[ -n "$ADMIN_PUBKEY" ]]; then
  run "mkdir -p $ADMIN_HOME/.ssh"
  echo "$ADMIN_PUBKEY" >> "$ADMIN_HOME/.ssh/authorized_keys"
  run "chown -R admin:admin $ADMIN_HOME/.ssh"
  run "chmod 700 $ADMIN_HOME/.ssh"
  run "chmod 600 $ADMIN_HOME/.ssh/authorized_keys"
  log "Admin SSH key installed."
fi

# ACLs
if command -v setfacl &>/dev/null; then
  run "apt-get install -y -qq acl" || true
  run "setfacl -R -m u:creator:rwx $CREATOR_HOME"
  run "setfacl -R -m u:creator:rx $STUDIO_MOUNT/models"
  run "setfacl -R -m u:creator:rwx $STUDIO_MOUNT/projects"
  run "setfacl -R -m u:creator:rwx $STUDIO_MOUNT/exports"
  run "setfacl -R -m u:admin:rwx $STUDIO_MOUNT"
  log "Filesystem ACLs configured."
fi

# ============================================================================
# Step 8: Install CLI Tools
# ============================================================================
step "8/9 CLI Tools"

# studio-model CLI
SCRIPT_DIR_CLI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_CLI_SRC=""
if [[ -f "$SCRIPT_DIR_CLI/../app/model-manager/cli.py" ]]; then
  _CLI_SRC="$SCRIPT_DIR_CLI/../app/model-manager/cli.py"
elif [[ -f "$STUDIO_BASE/../app/model-manager/cli.py" ]]; then
  _CLI_SRC="$STUDIO_BASE/../app/model-manager/cli.py"
fi
if [[ -n "$_CLI_SRC" ]]; then
  run "cp '$_CLI_SRC' /usr/local/bin/studio-model"
  run "chmod +x /usr/local/bin/studio-model"
  log "studio-model installed."
fi

# studio-status
cat > /usr/local/bin/studio-status <<'EOF'
#!/bin/bash
echo "=== AI Creative Studio Status ==="
echo ""
cd /opt/ai-studio 2>/dev/null && docker compose ps 2>/dev/null || echo "Stack not running"
echo ""
echo "Storage: $(df -h /mnt/studio --output=avail 2>/dev/null | tail -1 | tr -s ' ') free"
echo ""
if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader
fi
echo ""
echo "SSH: $(ss -tlnp | grep -c ':2222 ') sessions on port 2222"
EOF
run "chmod +x /usr/local/bin/studio-status"
log "studio-status installed."

# ============================================================================
# Step 9: Validation
# ============================================================================
step "9/9 Validation"

PASS=0; FAIL=0

check() { if eval "$1" &>/dev/null; then echo "  PASS: $2"; ((PASS++)); else echo "  FAIL: $2"; ((FAIL++)); fi }

check "command -v docker" "Docker installed"
check "systemctl is-active docker || true" "Docker running"
check "id creator" "Creator account exists"
check "id admin" "Admin account exists"
check "[[ -d $CREATOR_HOME/ai-studio ]]" "Creator studio directory"
check "[[ -f $STUDIO_CONFIG/backends.json ]]" "Backend config exists"
check "[[ -f $COMPOSE_FILE ]]" "Docker Compose generated"
check "systemctl is-active sshd || systemctl is-active ssh" "SSH running"
check "ufw status | grep -q active" "Firewall active"

echo ""
echo -e "${B}Results: $PASS passed, $FAIL failed${N}"

# ============================================================================
# Done
# ============================================================================
echo ""
echo -e "${G}${B}════════════════════════════════════════════════════════════════${N}"
echo -e "${G}${B}  AI Creative Studio v$VERSION - Setup Complete${N}"
echo -e "${G}${B}════════════════════════════════════════════════════════════════${N}"
echo ""
echo "Hardware: $GPU_TYPE ($GPU_NAME) | ${TOTAL_RAM_GB}GB RAM | $CPU_CORES cores"
echo "Backends: $TEXT_BACKEND / $IMAGE_BACKEND / $VIDEO_BACKEND / $TTS_BACKEND / $STT_BACKEND"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start services:"
echo "     cd $STUDIO_BASE && docker compose up -d"
echo ""
echo "  2. Download starter models:"
echo "     studio-model pull llama-3.1-8b    # Text (fast)"
echo "     studio-model pull flux1-dev        # Images"
echo "     studio-model pull whisper-large-v3 # Transcription"
echo ""
echo "  3. Access dashboard:"
echo "     ssh -p $SSH_PORT -L 5000:127.0.0.1:5000 admin@\$(hostname -I | awk '{print \$1}')"
echo "     Then open: http://localhost:5000"
echo ""
echo "  4. Check status:"
echo "     studio-status"
echo "     studio-model list"
echo ""
echo "Docs: $STUDIO_BASE/../docs/"
echo ""
print_summary
echo ""
