#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Keep-Alive Daemon
# Writes heartbeat to /mnt/studio/.heartbeat and pings gateway
# Prevents external drives and network mounts from sleeping/unmounting
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/mnt/studio/logs/keep-alive"
HEARTBEAT_FILE="/mnt/studio/.heartbeat"
PID_FILE="/var/run/keep-alive.pid"
INTERVAL=60
RUNNING=true
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        INFO)  color="$GREEN" ;;
        WARN)  color="$YELLOW" ;;
        ERROR) color="$RED" ;;
        *)     color="$NC" ;;
    esac
    
    echo -e "${color}[$timestamp] [$level] $message${NC}" | tee -a "$LOG_DIR/keep-alive.log" 2>/dev/null || true
}

# Signal handler for clean shutdown
cleanup() {
    log "INFO" "Received shutdown signal, cleaning up..."
    RUNNING=false
    if [[ -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE"
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Keep-Alive Daemon - Prevents external drives and network from sleeping

OPTIONS:
    --dry-run       Show what would be done without making changes
    --interval N    Set heartbeat interval in seconds (default: 60)
    --heartbeat FILE Set heartbeat file path (default: /mnt/studio/.heartbeat)
    --log-dir DIR   Set log directory (default: /mnt/studio/logs/keep-alive)
    --pid-file FILE Set PID file (default: /var/run/keep-alive.pid)
    --help          Show this help message

EXAMPLES:
    $0                      # Start daemon
    $0 --dry-run            # Test mode
    $0 --interval 30        # Check every 30 seconds

SYSTEMD SERVICE:
    Install as systemd service:
    sudo cp keep-alive.sh /usr/local/bin/
    sudo systemctl daemon-reload
    sudo systemctl enable keep-alive.service
    sudo systemctl start keep-alive.service

EOF
}

# Initialize log directory
init_logs() {
    mkdir -p "$LOG_DIR"
    if [[ ! -w "$LOG_DIR" ]]; then
        log "ERROR" "Cannot write to log directory: $LOG_DIR"
        exit 1
    fi
}

# Rotate logs if too large
rotate_logs() {
    if [[ -f "$LOG_DIR/keep-alive.log" ]] && [[ $(stat -f%z "$LOG_DIR/keep-alive.log" 2>/dev/null || stat -c%s "$LOG_DIR/keep-alive.log" 2>/dev/null || echo "0") -gt 5242880 ]]; then
        mv "$LOG_DIR/keep-alive.log" "$LOG_DIR/keep-alive.log.old"
        log "INFO" "Rotated log file"
    fi
}

# Check if /mnt/studio is mounted
check_mount() {
    if ! mountpoint -q /mnt/studio 2>/dev/null; then
        log "WARN" "/mnt/studio is not mounted"
        
        # Try to remount from fstab
        if grep -q "/mnt/studio" /etc/fstab 2>/dev/null; then
            log "INFO" "Attempting to remount /mnt/studio from fstab..."
            if $DRY_RUN; then
                log "INFO" "[DRY RUN] Would run: mount /mnt/studio"
            else
                if mount /mnt/studio 2>/dev/null; then
                    log "INFO" "Successfully remounted /mnt/studio"
                else
                    log "ERROR" "Failed to remount /mnt/studio"
                    return 1
                fi
            fi
        else
            log "ERROR" "/mnt/studio not in fstab, cannot remount"
            return 1
        fi
    fi
    return 0
}

# Write heartbeat file
write_heartbeat() {
    if $DRY_RUN; then
        log "INFO" "[DRY RUN] Would write heartbeat to $HEARTBEAT_FILE"
        return 0
    fi
    
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local data="heartbeat:$timestamp:$$"
    
    if echo "$data" > "$HEARTBEAT_FILE" 2>/dev/null; then
        log "INFO" "Heartbeat written successfully"
        return 0
    else
        log "ERROR" "Failed to write heartbeat file"
        return 1
    fi
}

# Read and verify heartbeat
verify_heartbeat() {
    if $DRY_RUN; then
        log "INFO" "[DRY RUN] Would verify heartbeat from $HEARTBEAT_FILE"
        return 0
    fi
    
    if [[ ! -f "$HEARTBEAT_FILE" ]]; then
        log "ERROR" "Heartbeat file not found after write"
        return 1
    fi
    
    local content
    content=$(cat "$HEARTBEAT_FILE" 2>/dev/null || echo "")
    
    if [[ -z "$content" ]]; then
        log "ERROR" "Heartbeat file is empty"
        return 1
    fi
    
    if [[ "$content" == heartbeat:* ]]; then
        log "INFO" "Heartbeat verified successfully"
        return 0
    else
        log "ERROR" "Heartbeat verification failed - unexpected content: $content"
        return 1
    fi
}

# Get default gateway
get_gateway() {
    local gateway=""
    
    # Try ip route first (Linux)
    if command -v ip >/dev/null 2>&1; then
        gateway=$(ip route 2>/dev/null | grep default | awk '{print $3}' | head -1 || echo "")
    fi
    
    # Fallback to netstat (older systems, macOS)
    if [[ -z "$gateway" ]] && command -v netstat >/dev/null 2>&1; then
        gateway=$(netstat -rn 2>/dev/null | grep "^default\|^0.0.0.0" | awk '{print $2}' | head -1 || echo "")
    fi
    
    echo "$gateway"
}

# Ping gateway to keep network alive
ping_gateway() {
    local gateway
    gateway=$(get_gateway)
    
    if [[ -z "$gateway" ]]; then
        log "WARN" "Could not determine default gateway"
        return 1
    fi
    
    if $DRY_RUN; then
        log "INFO" "[DRY RUN] Would ping gateway: $gateway"
        return 0
    fi
    
    # Single ping with 2 second timeout
    if ping -c 1 -W 2 "$gateway" >/dev/null 2>&1; then
        log "INFO" "Gateway ping successful: $gateway"
        return 0
    else
        log "WARN" "Gateway ping failed: $gateway"
        
        # Try alternate ping target
        if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
            log "INFO" "Alternate ping (8.8.8.8) successful"
            return 0
        else
            log "ERROR" "Network connectivity check failed"
            return 1
        fi
    fi
}

# Perform keep-alive check
perform_check() {
    log "INFO" "Performing keep-alive check..."
    
    local success=true
    
    # Check mount
    if ! check_mount; then
        success=false
    fi
    
    # Write and verify heartbeat
    if ! write_heartbeat; then
        success=false
    fi
    
    if ! verify_heartbeat; then
        success=false
    fi
    
    # Ping gateway
    if ! ping_gateway; then
        success=false
    fi
    
    if $success; then
        log "INFO" "Keep-alive check completed successfully"
    else
        log "WARN" "Keep-alive check completed with errors"
    fi
    
    rotate_logs
}

# Main loop
main_loop() {
    log "INFO" "Starting keep-alive daemon (interval: ${INTERVAL}s)"
    
    if $DRY_RUN; then
        log "INFO" "Running in DRY RUN mode"
    fi
    
    while $RUNNING; do
        perform_check
        sleep "$INTERVAL"
    done
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --interval)
                if [[ -n "${2:-}" ]]; then
                    INTERVAL="$2"
                    shift 2
                else
                    log "ERROR" "--interval requires a number"
                    exit 1
                fi
                ;;
            --heartbeat)
                if [[ -n "${2:-}" ]]; then
                    HEARTBEAT_FILE="$2"
                    shift 2
                else
                    log "ERROR" "--heartbeat requires a path"
                    exit 1
                fi
                ;;
            --log-dir)
                if [[ -n "${2:-}" ]]; then
                    LOG_DIR="$2"
                    shift 2
                else
                    log "ERROR" "--log-dir requires a path"
                    exit 1
                fi
                ;;
            --pid-file)
                if [[ -n "${2:-}" ]]; then
                    PID_FILE="$2"
                    shift 2
                else
                    log "ERROR" "--pid-file requires a path"
                    exit 1
                fi
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Write PID file
write_pid() {
    echo $$ > "$PID_FILE"
    log "INFO" "PID $$ written to $PID_FILE"
}

# Main execution
main() {
    parse_args "$@"
    init_logs
    write_pid
    main_loop
}

# Run main
main "$@"