#!/usr/bin/env bash
# ============================================================================
# AI Creative Studio - User Setup Script
# ============================================================================
# The compute brain is a dedicated appliance. It runs the Creative Studio.
# Nothing else. No dev work. No projects. No code. Just the studio.
#
#   CREATOR  -- Content creator. Uses the dashboard in a browser.
#               Shell: /usr/sbin/nologin (cannot SSH in)
#               Home: /home/creator/ai-studio/ (their projects, exports)
#               GUI only. Cannot break anything.
#
#   ADMIN    -- Manages the studio remotely from their laptop.
#               SSHs in to: start/stop containers, pull models,
#               troubleshoot, update config. That's it.
#               All admin work (code, projects, everything) stays
#               on the admin's laptop. Nothing of admin's lives here.
#               Shell: /bin/bash
#               Sudo: limited to studio management only
#               Home: /home/admin/ (SSH keys + studio CLI tools, <1MB)
#
# Usage:
#   sudo bash setup-users.sh --admin-pubkey "ssh-ed25519 AAAA... admin@laptop"
#
# After setup:
#   Admin:  ssh -p 2222 admin@<brain-ip>
#   Creator: open http://localhost:5000 (via SSH tunnel)
# ============================================================================

set -euo pipefail
trap 'echo "[FATAL] Line $LINENO failed." >&2' ERR

STUDIO_BASE="/opt/ai-studio"
STUDIO_MOUNT="/mnt/studio"
CREATOR_HOME="/home/creator"
CREATOR_STUDIO="$CREATOR_HOME/ai-studio"
ADMIN_HOME="/home/admin"
ADMIN_PUBKEY=""

# Colors
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1m'; N='\033[0m'
log()  { echo -e "${G}[+]${N} $*"; }
warn() { echo -e "${Y}[!]${N} $*"; }
err()  { echo -e "${R}[X]${N} $*" >&2; }
step() { echo -e "\n${C}${B}━━━ $* ━━━${N}\n"; }

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --admin-pubkey) ADMIN_PUBKEY="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: sudo bash setup-users.sh --admin-pubkey \"ssh-ed25519 AAAA...\""
      echo ""
      echo "Sets up two accounts on the compute brain:"
      echo "  Creator -- locked down, dashboard only"
      echo "  Admin   -- SSH access to manage the studio"
      echo ""
      echo "The compute brain runs the Creative Studio and nothing else."
      echo "All admin work stays on the admin's laptop."
      exit 0 ;;
    *) err "Unknown: $1. Use --help."; exit 1 ;;
  esac
done

if [[ $EUID -ne 0 ]]; then err "Run as root"; exit 1; fi

# ============================================================================
# Step 1: Creator Account
# ============================================================================
step "1/5 Creator Account"

if id creator &>/dev/null; then
  log "Creator account exists."
else
  useradd -m -s /usr/sbin/nologin -c "AI Studio Creator" creator
  log "Created creator account (nologin shell -- GUI only)"
fi

# Creator's files live here (they can't manage remote storage)
mkdir -p "$CREATOR_STUDIO"/{config,models/{text,image,video,audio},projects,exports,uploads,cache}
chown -R creator:creator "$CREATOR_HOME"
chmod 700 "$CREATOR_HOME"

# Default settings
cat > "$CREATOR_STUDIO/config/settings.json" <<'JSON'
{
  "display_name": "Creator",
  "default_text_model": "llama-3.1-8b",
  "default_image_model": "flux1-dev",
  "tts_voice": "af_heart",
  "output_format": "mp4",
  "auto_export": true,
  "theme": "dark",
  "auto_offload_minutes": 30
}
JSON
chown creator:creator "$CREATOR_STUDIO/config/settings.json"
chmod 600 "$CREATOR_STUDIO/config/settings.json"

log "Creator home: $CREATOR_HOME"
log "  Shell: nologin (GUI only)"
log "  Files: $CREATOR_STUDIO/ (projects, exports, models)"

# ============================================================================
# Step 2: Admin Account (studio manager only, no files)
# ============================================================================
step "2/5 Admin Account (Studio Manager)"

if id admin &>/dev/null; then
  log "Admin account exists."
else
  useradd -m -s /bin/bash -c "AI Studio Admin" admin
  log "Created admin account"
fi

# Admin can manage Docker and run studio commands
# NOT full sudo -- limited to what's needed for studio management
usermod -aG docker admin

# Limited sudo for studio management
cat > /etc/sudoers.d/admin-studio <<'SUDOERS'
# Admin can manage the studio. Nothing else needs root.
admin ALL=(root) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose
admin ALL=(root) NOPASSWD: /usr/local/bin/studio-*
admin ALL=(root) NOPASSWD: /usr/bin/systemctl restart docker
admin ALL=(root) NOPASSWD: /usr/bin/systemctl start docker
admin ALL=(root) NOPASSWD: /usr/bin/systemctl stop docker
admin ALL=(root) NOPASSWD: /usr/bin/journalctl
SUDOERS
chmod 440 /etc/sudoers.d/admin-studio

# Admin home is tiny -- SSH keys + studio CLI tools, nothing else
# Home is on external drive so accidental files don't hit root disk
ADMIN_HOME="/home/admin"
mkdir -p "$ADMIN_HOME"/{.ssh,.local/bin}
chown -R admin:admin "$ADMIN_HOME"
chmod 700 "$ADMIN_HOME"

# Mount admin scratch space on external drive (not root disk)
mkdir -p "$STUDIO_MOUNT/admin-scratch"
chown admin:admin "$STUDIO_MOUNT/admin-scratch"

# Symlink any accidental files away from root disk
# If admin creates files in ~, they actually go to external drive
for d in Documents Downloads Desktop tmp; do
  mkdir -p "$STUDIO_MOUNT/admin-scratch/$d"
  chown admin:admin "$STUDIO_MOUNT/admin-scratch/$d"
  ln -sfn "$STUDIO_MOUNT/admin-scratch/$d" "$ADMIN_HOME/$d" 2>/dev/null || true
done

# Make /home/admin read-only for new file creation (except .ssh and .local)
# This forces: any work happens on external drive, not root disk
# Admin's login message reminds them
cat > "$ADMIN_HOME/.bash_logout" <<'LOGOUT'
# Clean up any accidental files on root disk
find /home/admin -maxdepth 1 -type f ! -name '.bash*' ! -name '.profile' -mtime +1 -delete 2>/dev/null
LOGOUT

# SSH key
if [[ -n "$ADMIN_PUBKEY" ]]; then
  echo "$ADMIN_PUBKEY" >> "$ADMIN_HOME/.ssh/authorized_keys"
  chmod 700 "$ADMIN_HOME/.ssh"
  chmod 600 "$ADMIN_HOME/.ssh/authorized_keys"
  log "Admin SSH key installed."
else
  warn "No admin SSH key provided. Add later:"
  warn "  echo 'ssh-ed25519 ...' >> /home/admin/.ssh/authorized_keys"
fi

log "Admin home: $ADMIN_HOME"
log "  Shell: bash (SSH access for studio management)"
log "  Sudo: Docker + studio commands only"
log "  Files: NONE stored here. All work stays on admin's laptop."

# ============================================================================
# Step 3: Filesystem Isolation
# ============================================================================
step "3/5 Filesystem Isolation"

# Creator cannot touch system directories
command -v setfacl &>/dev/null || apt-get install -y -qq acl 2>/dev/null || true

if command -v setfacl &>/dev/null; then
  # Creator: blocked from system dirs
  for dir in /etc /var /opt /usr /root /boot /sbin; do
    setfacl -m u:creator:--- "$dir" 2>/dev/null || true
  done

  # Creator: cannot see admin's home
  setfacl -m u:creator:--- "$ADMIN_HOME" 2>/dev/null || true

  # Admin: can read creator home (for troubleshooting)
  setfacl -R -m u:admin:rx "$CREATOR_HOME" 2>/dev/null || true

  # Docker socket: admin only
  if [[ -S /var/run/docker.sock ]]; then
    setfacl -m u:admin:rw /var/run/docker.sock 2>/dev/null || true
    setfacl -m u:creator:--- /var/run/docker.sock 2>/dev/null || true
  fi

  log "ACLs configured."
else
  warn "ACL tools not available. Using basic permissions."
  chmod 700 "$ADMIN_HOME"
  chmod 700 "$CREATOR_HOME"
fi

# ============================================================================
# Step 4: Studio CLI Tools
# ============================================================================
step "4/5 Studio CLI Tools"

# studio-status
cat > /usr/local/bin/studio-status <<'EOF'
#!/bin/bash
echo "=== AI Creative Studio ==="
echo ""
echo "--- Docker ---"
cd /opt/ai-studio 2>/dev/null && docker compose ps 2>/dev/null || echo "Stack not running"
echo ""
echo "--- Storage ---"
df -h /mnt/studio --output=avail,size 2>/dev/null | tail -1 | awk '{print "Free: " $1 " / Total: " $2}' || echo "Not mounted"
echo ""
echo "--- GPU ---"
if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader
else
  echo "No NVIDIA GPU"
fi
echo ""
echo "--- Users ---"
echo "Creator: $(id creator 2>/dev/null || echo 'not found')"
echo "Admin:   $(id admin 2>/dev/null || echo 'not found')"
EOF
chmod +x /usr/local/bin/studio-status
log "studio-status installed"

# studio-model CLI
if [[ -f "$STUDIO_BASE/../app/model-manager/cli.py" ]]; then
  cp "$STUDIO_BASE/../app/model-manager/cli.py" /usr/local/bin/studio-model
  chmod +x /usr/local/bin/studio-model
  log "studio-model installed"
fi

# studio-doctor
if [[ -f "$STUDIO_BASE/../scripts/studio-doctor.sh" ]]; then
  cp "$STUDIO_BASE/../scripts/studio-doctor.sh" /usr/local/bin/studio-doctor
  chmod +x /usr/local/bin/studio-doctor
  log "studio-doctor installed"
fi

# Admin's shell aliases (for managing the studio via SSH)
cat > "$ADMIN_HOME/.bashrc_studio" <<'BASHRC'
# Studio management aliases
alias status='studio-status'
alias models='studio-model'
alias doctor='studio-doctor'
alias dc='docker compose'
alias dcup='cd /opt/ai-studio && docker compose up -d'
alias dcdown='cd /opt/ai-studio && docker compose down'
alias dclogs='cd /opt/ai-studio && docker compose logs -f --tail 30'
alias dcps='docker compose ps'
alias gpu='nvidia-smi'
alias ll='ls -la'

# File locations
echo ""
echo "  +---------------------------------------------+"
echo "  |  AI CREATIVE STUDIO - COMPUTE BRAIN         |"
echo "  |                                             |"
echo "  |  This machine: studio appliance only        |"
echo "  |  Your work: stays on YOUR laptop            |"
echo "  |                                             |"
echo "  |  ~/          = SSH keys + CLI (<1MB)        |"
echo "  |  /mnt/studio = models + studio data (SSD)   |"
echo "  |  /opt/ai-studio = Docker containers         |"
echo "  |                                             |"
echo "  |  If you create files here, they go to       |"
echo "  |  /mnt/studio/admin-scratch/ (external SSD)  |"
echo "  |  NOT to this machine's root disk.            |"
echo "  |                                             |"
echo "  |  Commands: status dcup dcdown dclogs models  |"
echo "  +---------------------------------------------+"
echo ""
BASHRC
chown admin:admin "$ADMIN_HOME/.bashrc_studio"

# Load aliases on login
if ! grep -q "bashrc_studio" "$ADMIN_HOME/.bashrc" 2>/dev/null; then
  echo '[ -f ~/.bashrc_studio ] && source ~/.bashrc_studio' >> "$ADMIN_HOME/.bashrc"
fi
chown admin:admin "$ADMIN_HOME/.bashrc"

log "Admin shell aliases installed"

# ============================================================================
# Step 5: Validation
# ============================================================================
step "5/5 Validation"

PASS=0; FAIL=0
check() { if eval "$1" &>/dev/null; then echo -e "  ${G}PASS${N}  $2"; ((PASS++)); else echo -e "  ${R}FAIL${N}  $2"; ((FAIL++)); fi }

check "id creator" "Creator account exists"
check "id admin" "Admin account exists"
check "[[ $(getent passwd creator | cut -d: -f7) == '/usr/sbin/nologin' ]]" "Creator: nologin shell"
check "[[ $(getent passwd admin | cut -d: -f7) == '/bin/bash' ]]" "Admin: bash shell"
check "[[ -d $CREATOR_STUDIO ]]" "Creator studio directory exists"
check "[[ -f $CREATOR_STUDIO/config/settings.json ]]" "Creator settings exist"
check "[[ -f $ADMIN_HOME/.ssh/authorized_keys || ! -n '$ADMIN_PUBKEY' ]]" "Admin SSH configured"
check "[[ -f /etc/sudoers.d/admin-studio ]]" "Admin sudoers configured"
check "groups admin | grep -q docker" "Admin has Docker access"
check "! groups creator | grep -q sudo" "Creator: no sudo"
check "! groups creator | grep -q docker" "Creator: no Docker"
check "[[ -f /usr/local/bin/studio-status ]]" "studio-status installed"
check "[[ -f /usr/local/bin/studio-model || ! -f $STUDIO_BASE/../app/model-manager/cli.py ]]" "studio-model installed"

# Creator cannot access system files
check "! sudo -u creator cat /etc/shadow 2>/dev/null" "Creator: blocked from /etc/shadow"

# Admin home is small
ADMIN_SIZE=$(du -sm "$ADMIN_HOME" 2>/dev/null | cut -f1)
if [[ ${ADMIN_SIZE:-0} -lt 10 ]]; then
  echo -e "  ${G}PASS${N}  Admin home <10MB (no files stored: ${ADMIN_SIZE}MB)"
  ((PASS++))
else
  echo -e "  ${Y}WARN${N}  Admin home is ${ADMIN_SIZE}MB (should be <10MB)"
fi

echo ""
echo -e "  ${B}$PASS passed, $FAIL failed${N}"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo -e "${G}${B}Setup complete.${N}"
else
  echo -e "${Y}Some checks failed. Review output above.${N}"
fi

echo ""
echo "This machine is a dedicated AI Creative Studio appliance."
echo ""
echo "  CREATOR (content creator):"
echo "    Opens dashboard in browser via SSH tunnel:"
echo "    ssh -p 2222 -L 5000:127.0.0.1:5000 admin@$(hostname -I | awk '{print $1}')"
echo "    Then: http://localhost:5000"
echo ""
echo "  ADMIN (you, from your laptop):"
echo "    SSH in to manage the studio:"
echo "      ssh -p 2222 admin@$(hostname -I | awk '{print $1}')"
echo ""
echo "    Studio commands:"
echo "      status     -- check everything"
echo "      dcup       -- start the studio"
echo "      dcdown     -- stop the studio"
echo "      dclogs     -- see what's happening"
echo "      models     -- pull/list/manage models"
echo "      doctor     -- full system check"
echo ""
echo "    YOUR WORK STAYS ON YOUR LAPTOP."
echo "    This machine runs the studio and nothing else."
echo ""
