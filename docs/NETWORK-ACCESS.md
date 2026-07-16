# Network Access & Remote Setup Guide

This guide covers secure remote access to your AI Creative Studio compute brain from a low-end laptop (thin client). The laptop needs only SSH access and a web browser — all heavy compute runs on the brain.

## Architecture Overview

```
┌─────────────────┐         SSH (encrypted)        ┌──────────────────┐
│   Thin Client   │ ◄──────────────────────────────► │   Compute Brain  │
│  (Laptop)       │                                   │                  │
│                 │         SSH Tunnel (ports)        │   ComfyUI :8188  │
│  - SSH client   │ ◄──────────────────────────────► │   OpenWebUI :3000│
│  - Web browser  │                                   │   (all services) │
│  - No GPU       │                                   │   External SSD   │
└─────────────────┘                                   └──────────────────┘
```

---

## 1. SSH Hardening

### 1.1 Key-Based Authentication Only

Generate an Ed25519 key pair (stronger and faster than RSA):

```bash
# On the laptop (thin client)
ssh-keygen -t ed25519 -C "creative-studio-laptop" -f ~/.ssh/id_ed25519_ai_studio

# Copy public key to the compute brain
ssh-copy-id -i ~/.ssh/id_ed25519_ai_studio.pub user@brain-ip
```

### 1.2 Disable Password Authentication

Edit `/etc/ssh/sshd_config` on the compute brain:

```bash
sudo nano /etc/ssh/sshd_config
```

Set these values:

```conf
# Disable password authentication
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no

# Disable root login
PermitRootLogin no

# Only allow specific users
AllowUsers your_username

# Use SSH protocol 2 only
Protocol 2

# Limit authentication attempts
MaxAuthTries 3

# Set login grace time
LoginGraceTime 30

# Disable empty passwords
PermitEmptyPasswords no

# Enable public key authentication
PubkeyAuthentication yes
```

Restart SSH:

```bash
sudo systemctl restart sshd
```

### 1.3 Custom SSH Port

Change the default port from 22 to something non-standard (e.g., 2222):

```conf
# In /etc/ssh/sshd_config
Port 2222
```

Update firewall before restarting SSH:

```bash
sudo ufw allow 2222/tcp
sudo ufw deny 22/tcp
sudo systemctl restart sshd
```

### 1.4 Install fail2ban

Protect against brute-force attacks:

```bash
sudo apt update
sudo apt install fail2ban

# Create local config
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Configure `/etc/fail2ban/jail.local`:

```ini
[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
```

Start fail2ban:

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status sshd
```

### 1.5 SSH Client Configuration (on Laptop)

Create `~/.ssh/config`:

```conf
# AI Creative Studio Compute Brain
Host creative-brain
    HostName your-brain-ip-or-domain.com
    Port 2222
    User your_username
    IdentityFile ~/.ssh/id_ed25519_ai_studio
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    Compression yes
    
    # Keep connection alive
    TCPKeepAlive yes
    
    # Multiplexing for faster reconnection
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600

# Tunnel aliases (see section 2)
Host creative-comfy
    HostName localhost
    Port 18188
    User your_username

Host creative-webui
    HostName localhost
    Port 13000
    User your_username
```

Test the connection:

```bash
ssh creative-brain
```

---

## 2. SSH Tunneling for Web UIs

### 2.1 Local Port Forwarding

Forward remote web interfaces to your laptop's localhost:

```bash
# ComfyUI (image generation)
ssh -L 18188:localhost:8188 creative-brain

# OpenWebUI (chat interface)
ssh -L 13000:localhost:3000 creative-brain

# Both tunnels in one command
ssh -L 18188:localhost:8188 -L 13000:localhost:3000 creative-brain

# Background mode (don't open shell)
ssh -f -N -L 18188:localhost:8188 -L 13000:localhost:3000 creative-brain
```

Access in browser:
- ComfyUI: http://localhost:18188
- OpenWebUI: http://localhost:13000

### 2.2 Multi-Service Tunnel Script

Create `~/.ssh/start-tunnels.sh`:

```bash
#!/bin/bash
# Start all AI Creative Studio tunnels

BRAIN="creative-brain"

echo "Starting SSH tunnels to compute brain..."

# Kill existing tunnels
pkill -f "ssh.*$BRAIN.*-L"

# Start tunnels in background
ssh -f -N \
    -L 18188:localhost:8188 \
    -L 13000:localhost:3000 \
    -L 15000:localhost:5000 \
    -L 18080:localhost:8080 \
    -L 19000:localhost:9000 \
    -L 18880:localhost:8880 \
    -L 18890:localhost:8890 \
    $BRAIN

echo "Tunnels active:"
echo "  ComfyUI:    http://localhost:18188"
echo "  OpenWebUI:  http://localhost:13000"
echo "  Dashboard:  http://localhost:15000"
echo "  llama.cpp:  http://localhost:18080"
echo "  Whisper:    http://localhost:19000"
echo "  Kokoro:     http://localhost:18880"
echo "  AudioCraft: http://localhost:18890"
echo ""
echo "Run 'pkill -f ssh.*$BRAIN.*-L' to stop all tunnels"
```

Make executable:

```bash
chmod +x ~/.ssh/start-tunnels.sh
```

### 2.3 Auto-Reconnect with autossh

Install autossh for persistent tunnels:

```bash
sudo apt install autossh
```

Create `~/.ssh/auto-tunnels.sh`:

```bash
#!/bin/bash
# Auto-reconnecting SSH tunnels

export AUTOSSH_GATETIME=0
export AUTOSSH_POLL=60
export AUTOSSH_LOGFILE=$HOME/.ssh/autossh.log

autossh -M 0 -f -N \
    -L 18188:localhost:8188 \
    -L 13000:localhost:3000 \
    creative-brain
```

### 2.4 Systemd Service (Persistent)

Create `~/.config/systemd/user/creative-tunnels.service`:

```ini
[Unit]
Description=AI Creative Studio SSH Tunnels
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
ExecStart=/usr/bin/autossh -M 0 -f -N \
    -L 18188:localhost:8188 \
    -L 13000:localhost:3000 \
    creative-brain
ExecStop=pkill -f "autossh.*creative-brain"
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable creative-tunnels.service
systemctl --user start creative-tunnels.service
```

---

## 3. Reverse SSH for NAT Traversal

When the compute brain is behind NAT (home network), use a cheap VPS as a relay.

### 3.1 Architecture

```
┌─────────────┐    Reverse SSH     ┌─────────────┐    SSH Tunnel    ┌─────────────┐
│ Thin Client │ ◄───────────────── │  VPS Relay  │ ◄────────────── │ Compute Brain│
│  (Laptop)   │    Outbound SSH    │  (Public IP)│   Inbound SSH   │  (Behind NAT)│
└─────────────┘                    └─────────────┘                  └─────────────┘
```

### 3.2 Setup Reverse Tunnel

On the compute brain (behind NAT), create a persistent reverse tunnel to the VPS:

```bash
# One-time command (run on compute brain)
ssh -R 2222:localhost:2222 vps-user@vps-ip

# Auto-reconnecting version
autossh -M 0 -f -N -R 2222:localhost:2222 vps-user@vps-ip
```

### 3.3 VPS SSH Configuration

On the VPS, edit `/etc/ssh/sshd_config`:

```conf
GatewayPorts yes
AllowTcpForwarding yes
ClientAliveInterval 30
ClientAliveCountMax 3
```

### 3.4 Connect from Laptop

Through the VPS relay:

```bash
# Direct SSH through VPS
ssh -J vps-user@vps-ip:22 creative-brain

# Or with port forwarding
ssh -J vps-user@vps-ip -L 18188:localhost:8188 creative-brain
```

### 3.5 Persistent Reverse Tunnel Service

On the compute brain, create `/etc/systemd/system/reverse-ssh.service`:

```ini
[Unit]
Description=Reverse SSH Tunnel to VPS
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
ExecStart=/usr/bin/autossh -M 0 -N -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -R 2222:localhost:2222 vps-user@vps-ip
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable reverse-ssh.service
sudo systemctl start reverse-ssh.service
```

---

## 4. Tailscale / WireGuard Alternatives

### 4.1 Tailscale (Recommended for Simplicity)

Tailscale creates a mesh VPN without port forwarding or public IPs.

**Install on both machines:**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Benefits:**
- No port forwarding needed
- NAT traversal built-in
- MagicDNS for easy access
- Works behind CGNAT

**SSH with Tailscale:**

```bash
# Connect via Tailscale IP or hostname
ssh creative-brain

# Or use Tailscale SSH (beta)
tailscale ssh creative-brain
```

**Tailscale Funnel for web UIs (optional):**

```bash
# Expose ComfyUI publicly (if needed)
tailscale funnel --bg 8188
```

### 4.2 WireGuard (Self-Hosted)

For full control without third-party services.

**Install on both machines:**

```bash
sudo apt install wireguard
```

**Generate keys on each machine:**

```bash
wg genkey | tee privatekey | wg pubkey > publickey
```

**Compute brain config (`/etc/wireguard/wg0.conf`):**

```ini
[Interface]
PrivateKey = <brain-private-key>
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = false

# Allow SSH through WireGuard
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

[Peer]
PublicKey = <laptop-public-key>
AllowedIPs = 10.0.0.2/32
```

**Laptop config (`/etc/wireguard/wg0.conf`):**

```ini
[Interface]
PrivateKey = <laptop-private-key>
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = <brain-public-key>
Endpoint = brain-public-ip:51820
AllowedIPs = 10.0.0.1/32
PersistentKeepalive = 25
```

**Start WireGuard:**

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

**SSH through WireGuard:**

```bash
ssh user@10.0.0.1
```

---

## 5. File Transfer

### 5.1 rsync (Recommended)

Sync creative files between laptop and compute brain:

```bash
# Sync external SSD to brain (push)
rsync -avz --progress /mnt/external-ssd/ creative-brain:/mnt/external-ssd/

# Sync from brain to laptop (pull)
rsync -avz --progress creative-brain:/mnt/external-ssd/ /mnt/external-ssd/

# Exclude generated/temp files
rsync -avz --progress --exclude='*.tmp' --exclude='.cache/' \
    /mnt/external-ssd/ creative-brain:/mnt/external-ssd/

# Dry run (see what would transfer)
rsync -avzn --progress /mnt/external-ssd/ creative-brain:/mnt/external-ssd/

# Sync only changed files (incremental)
rsync -avz --progress --delete /mnt/external-ssd/ creative-brain:/mnt/external-ssd/

# Use custom SSH port
rsync -avz -e "ssh -p 2222" --progress /mnt/external-ssd/ creative-brain:/mnt/external-ssd/
```

### 5.2 scp (Simple Copy)

For individual files:

```bash
# Copy file to brain
scp -P 2222 localfile.psd creative-brain:/mnt/external-ssd/renders/

# Copy directory
scp -r -P 2222 ./project/ creative-brain:/mnt/external-ssd/projects/

# Copy from brain to laptop
scp -P 2222 creative-brain:/mnt/external-ssd/renders/output.png ./

# With bandwidth limit (KB/s)
scp -l 5000 largefile.zip creative-brain:/mnt/external-ssd/
```

### 5.3 Sync Script

Create `~/.local/bin/sync-creative-files`:

```bash
#!/bin/bash
# Sync creative files bidirectionally

BRAIN="creative-brain"
LOCAL_DIR="/mnt/external-ssd"
REMOTE_DIR="/mnt/external-ssd"

echo "Syncing creative files..."

# Pull newer files from brain
echo "Pulling from brain..."
rsync -avz --update --progress \
    --exclude='.DS_Store' \
    --exclude='*.tmp' \
    --exclude='.Trash-*' \
    "$BRAIN:$REMOTE_DIR/" "$LOCAL_DIR/"

# Push newer files to brain
echo "Pushing to brain..."
rsync -avz --update --progress \
    --exclude='.DS_Store' \
    --exclude='*.tmp' \
    --exclude='.Trash-*' \
    "$LOCAL_DIR/" "$BRAIN:$REMOTE_DIR/"

echo "Sync complete!"
```

---

## 6. Firewall Rules (ufw)

### 6.1 Basic Firewall Setup

On the compute brain:

```bash
# Reset to defaults
sudo ufw reset

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow custom SSH port
sudo ufw allow 2222/tcp comment 'SSH'

# Allow WireGuard (if using)
sudo ufw allow 51820/udp comment 'WireGuard'

# Allow Tailscale (if using)
sudo ufw allow 41641/udp comment 'Tailscale'

# Enable firewall
sudo ufw enable
```

### 6.2 Advanced Rules

```bash
# Rate limit SSH (6 connections in 30 seconds)
sudo ufw limit 2222/tcp

# Allow SSH only from specific IPs (if static)
sudo ufw allow from 192.168.1.0/24 to any port 2222

# Allow local network access to web UIs (optional, for non-tunnel access)
sudo ufw allow from 192.168.1.0/24 to any port 8188 comment 'ComfyUI LAN'
sudo ufw allow from 192.168.1.0/24 to any port 3000 comment 'OpenWebUI LAN'

# Block everything else on those ports
sudo ufw deny 8188
sudo ufw deny 3000
```

### 6.3 Check Status

```bash
sudo ufw status verbose
sudo ufw status numbered

# Check logs
sudo tail -f /var/log/ufw.log
```

---

## 7. Complete Workflow Example

### 7.1 Initial Setup (One-Time)

```bash
# 1. Generate SSH key
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_ai_studio

# 2. Copy to brain
ssh-copy-id -i ~/.ssh/id_ed25519_ai_studio.pub user@brain-ip

# 3. Configure brain SSH
ssh user@brain-ip 'sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup'
ssh user@brain-ip 'sudo sed -i "s/#Port 22/Port 2222/" /etc/ssh/sshd_config'
ssh user@brain-ip 'sudo sed -i "s/PasswordAuthentication yes/PasswordAuthentication no/" /etc/ssh/sshd_config'
ssh user@brain-ip 'sudo systemctl restart sshd'

# 4. Setup firewall
ssh user@brain-ip -p 2222 'sudo ufw default deny incoming && sudo ufw default allow outgoing && sudo ufw allow 2222/tcp && sudo ufw enable'

# 5. Install fail2ban
ssh user@brain-ip -p 2222 'sudo apt install fail2ban -y'
```

### 7.2 Daily Usage

```bash
# Start tunnels (morning)
~/.ssh/start-tunnels.sh

# Work in browser
# - ComfyUI: http://localhost:18188
# - OpenWebUI: http://localhost:3000

# Sync files
sync-creative-files

# SSH into brain when needed
ssh creative-brain

# Stop tunnels (evening)
pkill -f "ssh.*creative-brain.*-L"
```

### 7.3 Troubleshooting

```bash
# Test SSH connection
ssh -v creative-brain

# Check tunnel status
ss -tlnp | grep 18188

# Check fail2ban status
ssh creative-brain 'sudo fail2ban-client status sshd'

# Check firewall
ssh creative-brain 'sudo ufw status'

# Debug tunnel issues
ssh -v -L 18188:localhost:8188 creative-brain

# Check if brain services are running
ssh creative-brain 'systemctl status comfyui'
ssh creative-brain 'systemctl status open-webui'
```

---

## 8. Security Best Practices

1. **Never expose web UIs directly** — always use SSH tunnels or VPN
2. **Use SSH keys, never passwords**
3. **Keep systems updated** — `sudo apt update && sudo apt upgrade`
4. **Monitor logs** — `sudo tail -f /var/log/auth.log`
5. **Use fail2ban** — blocks brute-force attempts automatically
6. **Limit user access** — only necessary users should have SSH access
7. **Regular backups** — backup SSH keys and configs securely
8. **Use a VPN for public WiFi** — never SSH over untrusted networks without VPN
9. **Enable 2FA if possible** — for extra SSH security
10. **Audit SSH access** — `last` and `lastlog` commands

---

## Quick Reference

| Task | Command |
|------|---------|
| Connect to brain | `ssh creative-brain` |
| Start tunnels | `~/.ssh/start-tunnels.sh` |
| ComfyUI | http://localhost:18188 |
| OpenWebUI | http://localhost:13000 |
| Sync files | `sync-creative-files` |
| Check firewall | `ssh creative-brain 'sudo ufw status'` |
| Check fail2ban | `ssh creative-brain 'sudo fail2ban-client status sshd'` |
| Tunnel logs | `sudo tail -f /var/log/ufw.log` |