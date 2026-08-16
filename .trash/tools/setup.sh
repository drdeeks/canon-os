#!/usr/bin/env bash
# ============================================================================
# AI Creative Studio - Master Setup Script
# ============================================================================
# Enterprise-grade setup for a local-only AI creative studio.
# Designed for a compute brain running Linux with Docker isolation.
#
# What this script does:
#   1. Validates system requirements
#   2. Configures external storage mount
#   3. Installs and configures Docker
#   4. Hardens SSH (key-based only, fail2ban)
#   5. Deploys the full Docker Compose stack
#   6. Downloads AI models (optional, interactive)
#   7. Creates helper scripts (tunnel, sync, status)
#   8. Configures firewall
#
# Requirements:
#   - Ubuntu 22.04+ or Debian 12+ (modify for other distros)
#   - Root/sudo access on compute brain
#   - External SSD connected or NAS reachable
#   - SSH key from your laptop already in ~/.ssh/authorized_keys
#
# Usage:
#   sudo bash setup.sh [--dry-run] [--skip-models] [--external-drive /dev/sdX1]
# ============================================================================

set -euo pipefail
trap 'echo "[FATAL] Line $LINENO failed. Aborting." >&2' ERR

# ============================================================================
# Configuration
# ============================================================================
STUDIO_BASE="/opt/ai-studio"
STUDIO_MOUNT="/mnt/studio"
STUDIO_USER="${SUDO_USER:-$USER}"
STUDIO_UID=$(id -u "$STUDIO_USER")
STUDIO_GID=$(id -g "$STUDIO_USER")
SSH_PORT=2222
DRY_RUN=false
SKIP_MODELS=false
EXTERNAL_DRIVE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[X]${NC} $*" >&2; }
step() { echo -e "\n${CYAN}${BOLD}===> $*${NC}\n"; }
run()  { if $DRY_RUN; then echo "  [dry-run] $*"; else eval "$*"; fi; }

# ============================================================================
# Argument parsing
# ============================================================================
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)      DRY_RUN=true; shift ;;
    --skip-models)  SKIP_MODELS=true; shift ;;
    --external-drive) EXTERNAL_DRIVE="$2"; shift 2 ;;
    *) err "Unknown option: $1"; exit 1 ;;
  esac
done

# ============================================================================
# Pre-flight checks
# ============================================================================
step "Pre-flight checks"

if [[ $EUID -ne 0 ]]; then
  err "This script must be run as root (use sudo)"
  exit 1
fi

if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  log "OS: $PRETTY_NAME"
else
  err "Cannot detect OS. Only Ubuntu 22.04+ / Debian 12+ supported."
  exit 1
fi

ARCH=$(uname -m)
log "Architecture: $ARCH"
if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" ]]; then
  warn "Untested architecture: $ARCH"
fi

RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
log "RAM: ${RAM_GB}GB"
if (( RAM_GB < 16 )); then
  warn "Less than 16GB RAM. Large models may not run well."
fi

if command -v nvidia-smi &>/dev/null; then
  GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)
  log "GPU: $GPU_INFO"
  GPU_TYPE="nvidia"
elif [[ "$OSTYPE" == "darwin"* ]] || (uname -r | grep -qi "apple"); then
  log "GPU: Apple Silicon (Metal)"
  GPU_TYPE="metal"
else
  warn "No GPU detected. CPU-only inference (slow for large models)."
  GPU_TYPE="none"
fi

log "Pre-flight checks passed."

# ============================================================================
# Step 1: External Storage Setup
# ============================================================================
step "1/8 External Storage Setup"

if [[ -n "$EXTERNAL_DRIVE" ]]; then
  log "Formatting external drive: $EXTERNAL_DRIVE"
  if [[ ! -b "$EXTERNAL_DRIVE" ]]; then
    err "Device $EXTERNAL_DRIVE not found. Check with: lsblk"
    exit 1
  fi

  read -p "This will DESTROY all data on $EXTERNAL_DRIVE. Continue? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    err "Aborted by user."
    exit 1
  fi

  run "mkfs.ext4 -L studio $EXTERNAL_DRIVE"

  UUID=$(blkid -s UUID -o value "$EXTERNAL_DRIVE")
  log "Drive UUID: $UUID"

  if ! grep -q "$STUDIO_MOUNT" /etc/fstab; then
    run "echo 'UUID=$UUID $STUDIO_MOUNT ext4 defaults,noatime,nofail 0 2' >> /etc/fstab"
    log "Added fstab entry."
  fi
fi

run "mkdir -p $STUDIO_MOUNT"

# Mount if not already mounted
if ! mountpoint -q "$STUDIO_MOUNT" 2>/dev/null; then
  run "mount $STUDIO_MOUNT 2>/dev/null" || warn "Mount failed - is an external drive configured?"
fi

# Create directory structure
run "mkdir -p $STUDIO_MOUNT/{models/{text,image,video,audio},projects,exports,uploads,cache,logs}"
run "chown -R $STUDIO_UID:$STUDIO_GID $STUDIO_MOUNT"

log "Storage structure created at $STUDIO_MOUNT:"
ls -la "$STUDIO_MOUNT/" 2>/dev/null || true

# ============================================================================
# Step 2: System Dependencies
# ============================================================================
step "2/8 System Dependencies"

run "apt-get update -qq"

PACKAGES=(
  curl wget git vim htop tree jq
  openssh-server
  ufw fail2ban
  nfs-common cifs-utils
  python3 python3-pip python3-venv
  rsync
  unzip
  gnupg lsb-release ca-certificates
  software-properties-common
)

run "apt-get install -y -qq ${PACKAGES[*]}"
log "System packages installed."

# ============================================================================
# Step 3: Docker Installation
# ============================================================================
step "3/8 Docker Installation"

if ! command -v docker &>/dev/null; then
  log "Installing Docker..."

  # Official Docker repo
  run "install -m 0755 -d /etc/apt/keyrings"
  run "curl --max-time 30 --retry 3 -fsSL https://download.docker.com/linux/$ID/gpg -o /etc/apt/keyrings/docker.asc"
  run "chmod a+r /etc/apt/keyrings/docker.asc"

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/$ID $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

  run "apt-get update -qq"
  run "apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin"
  log "Docker installed."
else
  log "Docker already installed: $(docker --version)"
fi

# Add user to docker group
run "usermod -aG docker $STUDIO_USER"
log "User $STUDIO_USER added to docker group."

# Docker daemon config
cat > /etc/docker/daemon.json <<'DOCKER_JSON'
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {"base": "172.28.0.0/16", "size": 24}
  ]
}
DOCKER_JSON

run "systemctl restart docker"
run "systemctl enable docker"
log "Docker configured and running."

# NVIDIA Container Toolkit (if NVIDIA GPU)
if [[ "$GPU_TYPE" == "nvidia" ]]; then
  log "Installing NVIDIA Container Toolkit..."
  run "curl --max-time 30 --retry 3 -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
  echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] \
    https://nvidia.github.io/libnvidia-container/stable/deb/\$(ARCH) /" | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null
  run "apt-get update -qq"
  run "apt-get install -y -qq nvidia-container-toolkit"
  run "nvidia-ctk runtime configure --runtime=docker"
  run "systemctl restart docker"
  log "NVIDIA Container Toolkit configured."
fi

# ============================================================================
# Step 4: SSH Hardening
# ============================================================================
step "4/8 SSH Hardening"

# Backup original config
run "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)"

cat > /etc/ssh/sshd_config.d/99-studio-hardened.conf <<SSH_CONF
# AI Creative Studio - Hardened SSH Configuration
# Only key-based auth, custom port, security restrictions

Port $SSH_PORT
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
MaxAuthTries 3
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding yes
GatewayPorts no
PermitTunnel no
AllowAgentForwarding no
PrintMotd yes
Banner /etc/ssh/banner-studio
SSH_CONF

# Create SSH banner
cat > /etc/ssh/banner-studio <<'BANNER'

  ==================================================
   AI CREATIVE STUDIO - AUTHORIZED ACCESS ONLY
   All sessions are logged. Disconnect if unauthorized.
  ==================================================

BANNER

run "systemctl restart sshd"
log "SSH hardened on port $SSH_PORT (key-based only)."

# ============================================================================
# Step 5: Firewall Configuration
# ============================================================================
step "5/8 Firewall Configuration"

run "ufw default deny incoming"
run "ufw default allow outgoing"
run "ufw allow $SSH_PORT/tcp comment 'SSH'"
run "ufw --force enable"
log "Firewall active. Only port $SSH_PORT open."

# ============================================================================
# Step 6: fail2ban Configuration
# ============================================================================
step "6/8 fail2ban Configuration"

cat > /etc/fail2ban/jail.d/99-studio.conf <<'F2B'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
banaction = ufw

[sshd-aggressive]
enabled = true
port = ssh
filter = sshd[mode=aggressive]
logpath = /var/log/auth.log
maxretry = 5
bantime = 86400
findtime = 3600
banaction = ufw
F2B

# Fix port in config for custom SSH port
sed -i "s/^port = ssh$/port = $SSH_PORT/" /etc/fail2ban/jail.d/99-studio.conf 2>/dev/null || true

run "systemctl restart fail2ban"
run "systemctl enable fail2ban"
log "fail2ban configured (3 tries = 1h ban, 5 tries = 24h ban)."

# ============================================================================
# Step 7: Docker Compose Stack Deployment
# ============================================================================
step "7/8 Docker Compose Stack"

run "mkdir -p $STUDIO_BASE"

# Copy docker-compose from the repo
if [[ -f "$SCRIPT_DIR/../docker/docker-compose.yaml" ]]; then
  run "cp $SCRIPT_DIR/../docker/docker-compose.yaml $STUDIO_BASE/docker-compose.yaml"
  log "Docker Compose file copied to $STUDIO_BASE/"
else
  warn "docker-compose.yaml not found in repo. You'll need to place it manually at $STUDIO_BASE/"
fi

# Create .env for Docker Compose
cat > "$STUDIO_BASE/.env" <<ENVFILE
# AI Creative Studio - Environment
STUDIO_MOUNT=$STUDIO_MOUNT
STUDIO_USER=$STUDIO_USER
STUDIO_UID=$STUDIO_UID
STUDIO_GID=$STUDIO_GID
GPU_TYPE=$GPU_TYPE
ENVFILE

log "Docker Compose stack ready at $STUDIO_BASE/"
log "Start with: cd $STUDIO_BASE && docker compose up -d"

# ============================================================================
# Step 8: Helper Scripts
# ============================================================================
step "8/8 Helper Scripts"

# --- studio-status: Check all services ---
cat > /usr/local/bin/studio-status <<'STATUS'
#!/bin/bash
echo "=== AI Creative Studio Status ==="
echo ""
echo "--- Docker Services ---"
cd /opt/ai-studio && docker compose ps 2>/dev/null || echo "Stack not running"
echo ""
echo "--- Storage ---"
df -h /mnt/studio 2>/dev/null || echo "External storage not mounted"
echo ""
echo "--- GPU ---"
if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader
else
  echo "No NVIDIA GPU or nvidia-smi not installed"
fi
echo ""
echo "--- SSH Connections ---"
who | grep -c "pts/" | xargs -I{} echo "Active SSH sessions: {}"
echo ""
echo "--- Top Processes ---"
ps aux --sort=-%mem | head -6
STATUS
run "chmod +x /usr/local/bin/studio-status"

# --- studio-tunnel: SSH tunnel script (runs on LAPTOP, not compute brain) ---
cat > "$STUDIO_MOUNT/scripts/studio-tunnel.sh" <<'TUNNEL'
#!/bin/bash
# Run this ON YOUR LAPTOP to tunnel into the compute brain
# Usage: ./studio-tunnel.sh [brain-hostname-or-ip]
BRAIN="${1:-studio}"

echo "Starting SSH tunnels to $BRAIN..."
echo "  Open WebUI:  http://localhost:13000"
echo "  ComfyUI:     http://localhost:18188"
echo "  Whisper:     http://localhost:19000"
echo "  Kokoro TTS:  http://localhost:18880"
echo "  Ollama API:  http://localhost:11434"
echo ""
echo "Press Ctrl+C to stop all tunnels."

ssh -N -L 13000:127.0.0.1:3000 \
       -L 18188:127.0.0.1:8188 \
       -L 19000:127.0.0.1:9000 \
       -L 18880:127.0.0.1:8880 \
       -L 11434:127.0.0.1:11434 \
       "$BRAIN"
TUNNEL
run "chmod +x $STUDIO_MOUNT/scripts/studio-tunnel.sh"

# --- studio-sync: Sync exports to laptop (runs on LAPTOP) ---
cat > "$STUDIO_MOUNT/scripts/studio-sync.sh" <<'SYNC'
#!/bin/bash
# Run this ON YOUR LAPTOP to pull exports from compute brain
# Usage: ./studio-sync.sh [brain-hostname-or-ip] [local-dir]
BRAIN="${1:-studio}"
LOCAL_DIR="${2:-$HOME/studio-exports}"

echo "Syncing exports from $BRAIN to $LOCAL_DIR ..."
mkdir -p "$LOCAL_DIR"
rsync -avh --progress "$BRAIN:/mnt/studio/exports/" "$LOCAL_DIR/"
echo "Done. Files in: $LOCAL_DIR"
SYNC
run "chmod +x $STUDIO_MOUNT/scripts/studio-sync.sh"

# --- studio-pull-models: Download models ---
cat > "$STUDIO_MOUNT/scripts/studio-pull-models.sh" <<'MODELS'
#!/bin/bash
# Download AI models to /mnt/studio/models/
# Run on the compute brain with internet access

set -euo pipefail

MODELS_DIR="/mnt/studio/models"
BASE_HF="https://huggingface.co"

echo "=== AI Creative Studio - Model Downloader ==="
echo ""
echo "Available models:"
echo "  1) Llama 3.1 70B Instruct (Q4_K_M) - ~40GB"
echo "  2) Gemma2 27B Instruct (Q4_K_M) - ~16GB"
echo "  3) Llama 3.1 8B Instruct (Q4_K_M) - ~5GB"
echo "  4) Whisper Large-v3 (GGML) - ~3GB"
echo "  5) Kokoro TTS (ONNX) - ~500MB"
echo "  6) All text models (1+2+3)"
echo "  7) All audio models (4+5)"
echo "  8) All models (everything)"
echo ""
read -p "Select [1-8]: " choice

download() {
  local url="$1"
  local dest="$2"
  echo "Downloading: $(basename "$dest")"
  mkdir -p "$(dirname "$dest")"
  if command -v wget &>/dev/null; then
    wget --timeout=30 --tries=3 -c -O "$dest" "$url"
  elif command -v curl &>/dev/null; then
    curl --max-time 60 --retry 3 -L -o "$dest" "$url" --progress-bar
  else
    echo "ERROR: Need wget or curl"
    exit 1
  fi
  echo "Saved to: $dest"
}

case "$choice" in
  1)
    download "$BASE_HF/bartowski/Llama-3.1-70B-Instruct-GGUF/resolve/main/Llama-3.1-70B-Instruct-Q4_K_M.gguf" \
      "$MODELS_DIR/text/Llama-3.1-70B-Instruct-Q4_K_M.gguf"
    ;;
  2)
    download "$BASE_HF/bartowski/gemma-2-27b-it-GGUF/resolve/main/gemma-2-27b-it-Q4_K_M.gguf" \
      "$MODELS_DIR/text/gemma-2-27b-it-Q4_K_M.gguf"
    ;;
  3)
    download "$BASE_HF/bartowski/Llama-3.1-8B-Instruct-GGUF/resolve/main/Llama-3.1-8B-Instruct-Q4_K_M.gguf" \
      "$MODELS_DIR/text/Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    ;;
  4)
    download "$BASE_HF/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin" \
      "$MODELS_DIR/audio/whisper/ggml-large-v3.bin"
    ;;
  5)
    echo "Downloading Kokoro TTS..."
    mkdir -p "$MODELS_DIR/audio/kokoro"
    download "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" \
      "$MODELS_DIR/audio/kokoro/kokoro-v1.0.onnx"
    download "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" \
      "$MODELS_DIR/audio/kokoro/voices-v1.0.bin"
    ;;
  6)
    echo "Downloading all text models..."
    $0 <<< "1" ; $0 <<< "2" ; $0 <<< "3"
    ;;
  7)
    echo "Downloading all audio models..."
    $0 <<< "4" ; $0 <<< "5"
    ;;
  8)
    echo "Downloading ALL models (this will take a while)..."
    for i in 1 2 3 4 5; do $0 <<< "$i"; done
    ;;
  *)
    echo "Invalid selection."
    exit 1
    ;;
esac

echo ""
echo "Download complete. Run 'studio-status' to verify."
MODELS
run "chmod +x $STUDIO_MOUNT/scripts/studio-pull-models.sh"

# SSH config snippet for the laptop
cat > "$STUDIO_MOUNT/scripts/ssh-config-laptop.txt" <<'SSHCONFIG'
# Add this to your LAPTOP's ~/.ssh/config
# Replace <BRAIN_IP> with your compute brain's IP address

Host studio
    HostName <BRAIN_IP>
    User <YOUR_USER>
    Port 2222
    IdentityFile ~/.ssh/id_ed25519_ai_studio
    ServerAliveInterval 60
    ServerAliveCountMax 3
    Compression yes

# Shortcuts for tunneling
Host studio-full
    HostName <BRAIN_IP>
    User <YOUR_USER>
    Port 2222
    IdentityFile ~/.ssh/id_ed25519_ai_studio
    LocalForward 13000 127.0.0.1:3000
    LocalForward 18188 127.0.0.1:8188
    LocalForward 19000 127.0.0.1:9000
    LocalForward 18880 127.0.0.1:8880
    LocalForward 11434 127.0.0.1:11434
    ServerAliveInterval 60
    ServerAliveCountMax 3
SSHCONFIG

log "Helper scripts created:"
log "  studio-status         - Check all services"
log "  studio-tunnel.sh      - SSH tunnel for laptop (in /mnt/studio/scripts/)"
log "  studio-sync.sh        - Pull exports to laptop"
log "  studio-pull-models.sh - Download AI models"
log "  ssh-config-laptop.txt - SSH config template for laptop"

# ============================================================================
# Done
# ============================================================================
echo ""
echo -e "${GREEN}${BOLD}============================================================================${NC}"
echo -e "${GREEN}${BOLD}  AI CREATIVE STUDIO - SETUP COMPLETE${NC}"
echo -e "${GREEN}${BOLD}============================================================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "  1. On your LAPTOP, add SSH key to compute brain:"
echo "     ssh-copy-id -p $SSH_PORT $STUDIO_USER@<COMPUTE_BRAIN_IP>"
echo ""
echo "  2. On your LAPTOP, add the SSH config from:"
echo "     $STUDIO_MOUNT/scripts/ssh-config-laptop.txt"
echo "     Edit <BRAIN_IP> and <YOUR_USER>, then save to ~/.ssh/config"
echo ""
echo "  3. Download models on the compute brain:"
echo "     studio-pull-models.sh"
echo ""
echo "  4. Start the Docker stack:"
echo "     cd $STUDIO_BASE && docker compose up -d"
echo ""
echo "  5. From your laptop, create SSH tunnels:"
echo "     ssh studio-full    (or use studio-tunnel.sh)"
echo ""
echo "  6. Open in browser:"
echo "     http://localhost:13000  (Open WebUI - chat with AI)"
echo "     http://localhost:18188  (ComfyUI - image/video generation)"
echo ""
echo "Documentation: $STUDIO_MOUNT/../docs/ (copy from setup repo)"
echo ""
echo "Verify setup:  studio-status"
echo ""
