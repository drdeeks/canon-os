# AI Creative Studio Scripts

Lightweight monitoring and keep-alive scripts for the AI Creative Studio environment.

## Scripts

### resource-monitor.sh

Lightweight resource monitor daemon that runs every 30 seconds and logs to `/mnt/studio/logs/resources/`.

**Features:**
- CPU % monitoring
- RAM % monitoring
- GPU VRAM used/total (nvidia-smi or Metal on macOS)
- Disk space on /mnt/studio
- Docker container status (running/stopped/unhealthy)
- Network connectivity check
- CSV + JSON output for dashboard consumption
- Daily log rotation
- Minimal overhead (<1% CPU)

**Usage:**
```bash
# Single check
./resource-monitor.sh --once

# Continuous monitoring (every 30 seconds)
./resource-monitor.sh --watch

# Custom interval
./resource-monitor.sh --watch --interval 60

# Show help
./resource-monitor.sh --help
```

### keep-alive.sh

External drive keep-alive daemon that prevents drives from sleeping/unmounting.

**Features:**
- Writes heartbeat to `/mnt/studio/.heartbeat` every 60 seconds
- Reads back to verify write success
- Attempts remount via fstab if drive unmounts
- Pings gateway to keep network alive
- Dry-run mode for testing
- Minimal overhead

**Usage:**
```bash
# Start daemon
./keep-alive.sh

# Test mode (no actual writes)
./keep-alive.sh --dry-run

# Custom interval
./keep-alive.sh --interval 30

# Show help
./keep-alive.sh --help
```

### studio-doctor.sh
Swiss army knife diagnostic tool for browsing models, checking health, validating system, optimizing settings, generating reports.

Usage:
```
studio-doctor                   # Full diagnostic
studio-doctor health            # Quick health check
studio-doctor models            # Browse available models
studio-doctor backends          # Show backend status
studio-doctor optimize          # Optimize settings
studio-doctor report            # Generate report
```

### setup.sh
Master setup script for enterprise-grade local-only AI creative studio. Validates system requirements, configures external storage mount, installs Docker, sets up users, deploys containers.

### setup-master.sh
Single entry point for fresh machine setup. Handles hardware detection, Docker installation, SSH hardening, storage setup, backend selection, and full stack deployment.

### install-services.sh
Installs resource-monitor and keep-alive as systemd services.

Usage:
```
sudo ./install-services.sh --all        # Install both services
sudo ./install-services.sh --resource   # Install only resource-monitor
sudo ./install-services.sh --keep-alive # Install only keep-alive
sudo ./install-services.sh --status     # Check status
sudo ./install-services.sh --uninstall  # Uninstall
```

### install-components.sh
Comprehensive component installer. Detects installed versions, checks latest stable, and installs/updates system packages, security tools, GPU drivers, storage mounts, and AI container images.

Usage:
```
sudo bash install-components.sh --check-only       # Report installed/missing/outdated
sudo bash install-components.sh --install-missing  # Install only missing components
sudo bash install-components.sh --update-all       # Update everything to latest stable
sudo bash install-components.sh --dry-run          # Show what would happen
sudo bash install-components.sh --yes              # Skip interactive prompts
```

### studio-update.sh
Update/upgrade manager for AI Creative Studio.

Usage:
```
studio-update check          # Check what can be updated
studio-update pull           # Pull latest Docker images
studio-update scripts        # Update scripts from repo
studio-update dashboard      # Rebuild dashboard container
studio-update all            # Update everything
studio-update rollback       # Rollback to previous versions

studio-update --dry-run      # Show what would be updated
studio-update --offline      # Skip network-dependent checks
studio-update --timeout 30   # Override default timeouts (seconds)
```

### setup-users.sh
User setup script for creator and admin accounts. Configures home directories, SSH keys, permissions, and storage isolation.

### resource-monitor.service
Systemd service file for resource-monitor.sh daemon.

### keep-alive.service
Systemd service file for keep-alive.sh daemon.

## Installation as Systemd Services

### Quick Install

```bash
# Install both services
sudo ./install-services.sh --all

# Install only resource-monitor
sudo ./install-services.sh --resource

# Install only keep-alive
sudo ./install-services.sh --keep-alive

# Check status
sudo ./install-services.sh --status

# Uninstall
sudo ./install-services.sh --uninstall
```

### Manual Installation

1. Copy service files to systemd directory:
```bash
sudo cp resource-monitor.service /etc/systemd/system/
sudo cp keep-alive.service /etc/systemd/system/
```

2. Reload systemd:
```bash
sudo systemctl daemon-reload
```

3. Enable and start services:
```bash
sudo systemctl enable --now resource-monitor.service
sudo systemctl enable --now keep-alive.service
```

4. Check status:
```bash
systemctl status resource-monitor.service
systemctl status keep-alive.service
```

5. View logs:
```bash
journalctl -u resource-monitor.service -f
journalctl -u keep-alive.service -f
```

## Log Locations

- Resource Monitor: `/mnt/studio/logs/resources/`
  - `resources-YYYY-MM-DD.csv` - Daily CSV logs
  - `latest-snapshot.json` - Latest check (for dashboard)
  - `monitor.log` - Application log

- Keep-Alive: `/mnt/studio/logs/keep-alive/`
  - `keep-alive.log` - Application log
  - `/mnt/studio/.heartbeat` - Heartbeat file

## Requirements

- Bash 4.0+
- Linux or macOS
- Optional: nvidia-smi (for GPU monitoring)
- Optional: Docker (for container monitoring)
- Root access for systemd installation

## Signal Handling

Both scripts handle SIGTERM and SIGINT for clean shutdown:
- PID files are cleaned up
- Logs are flushed
- Process exits gracefully

## Configuration

### Resource Monitor
- `--interval N` - Check interval in seconds (default: 30)
- `--log-dir DIR` - Log directory (default: /mnt/studio/logs/resources)
- `--pid-file FILE` - PID file location

### Keep-Alive
- `--interval N` - Heartbeat interval in seconds (default: 60)
- `--heartbeat FILE` - Heartbeat file location
- `--log-dir DIR` - Log directory (default: /mnt/studio/logs/keep-alive)
- `--dry-run` - Test mode without actual writes

## Dashboard Integration

The `latest-snapshot.json` file is updated every check interval and can be consumed by any dashboard:

```json
{
    "timestamp": "2026-04-18 12:00:00",
    "cpu_percent": 15.2,
    "ram_percent": 45.8,
    "gpu_vram_used_mb": 2048,
    "gpu_vram_total_mb": 8192,
    "disk_used_gb": 150,
    "disk_total_gb": 500,
    "docker_running": 3,
    "docker_stopped": 1,
    "docker_unhealthy": 0,
    "network_ok": 1,
    "check_interval_seconds": 30
}
```