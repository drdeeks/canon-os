#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Resource Monitor Daemon
# Lightweight monitoring of CPU, RAM, GPU, disk, Docker, and network
# Logs to /mnt/studio/logs/resources/ in CSV + JSON format
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/mnt/studio/logs/resources"
PID_FILE="/var/run/resource-monitor.pid"
INTERVAL=30
RUNNING=true
WATCH_MODE=false
ONCE_MODE=false

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
    
    echo -e "${color}[$timestamp] [$level] $message${NC}" | tee -a "$LOG_DIR/monitor.log" 2>/dev/null || true
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

Resource Monitor Daemon - Lightweight system monitoring

OPTIONS:
    --once          Run a single check and exit
    --watch         Run continuously (default: every 30s)
    --interval N    Set check interval in seconds (default: 30)
    --log-dir DIR   Set log directory (default: /mnt/studio/logs/resources)
    --pid-file FILE Set PID file (default: /var/run/resource-monitor.pid)
    --help          Show this help message

EXAMPLES:
    $0 --once                    # Single check
    $0 --watch                   # Continuous monitoring
    $0 --watch --interval 60     # Check every 60 seconds

SYSTEMD SERVICE:
    Install as systemd service:
    sudo cp resource-monitor.sh /usr/local/bin/
    sudo systemctl daemon-reload
    sudo systemctl enable resource-monitor.service
    sudo systemctl start resource-monitor.service

EOF
}

# Check if running as root for certain operations
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log "INFO" "Running with root privileges"
    else
        log "WARN" "Running without root - some features may be limited"
    fi
}

# Initialize log directory
init_logs() {
    mkdir -p "$LOG_DIR"
    if [[ ! -w "$LOG_DIR" ]]; then
        log "ERROR" "Cannot write to log directory: $LOG_DIR"
        exit 1
    fi
}

# Rotate logs daily
rotate_logs() {
    local today
    today=$(date '+%Y-%m-%d')
    local log_file="$LOG_DIR/resources-$today.csv"
    local json_file="$LOG_DIR/latest-snapshot.json"
    
    # Create CSV with headers if new day
    if [[ ! -f "$log_file" ]]; then
        echo "timestamp,cpu_percent,ram_percent,gpu_vram_used,gpu_vram_total,disk_used_gb,disk_total_gb,docker_running,docker_stopped,docker_unhealthy,network_ok" > "$log_file"
        log "INFO" "Created new daily log: $log_file"
    fi
    
    # Clean old logs (keep 30 days)
    find "$LOG_DIR" -name "resources-*.csv" -mtime +30 -delete 2>/dev/null || true
    find "$LOG_DIR" -name "monitor.log" -size +10M -exec truncate -s 5M {} \; 2>/dev/null || true
}

# Get CPU percentage
get_cpu_percent() {
    local cpu_percent=0
    if command -v top >/dev/null 2>&1; then
        # Linux: use top
        cpu_percent=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 || echo "0")
    elif command -v ps >/dev/null 2>&1; then
        # Fallback: use ps
        cpu_percent=$(ps -A -o %cpu | awk '{sum+=$1} END {print sum}' || echo "0")
    fi
    echo "${cpu_percent:-0}"
}

# Get RAM percentage
get_ram_percent() {
    local ram_percent=0
    if command -v free >/dev/null 2>&1; then
        ram_percent=$(free | awk '/Mem:/ {printf "%.1f", $3/$2 * 100.0}' || echo "0")
    elif command -v vm_stat >/dev/null 2>&1; then
        # macOS fallback
        ram_percent=$(vm_stat | awk '/Pages active/ {active=$3} /Pages wired/ {wired=$4} /Pages free/ {free=$3} END {printf "%.1f", (active+wired)/(active+wired+free)*100}' || echo "0")
    fi
    echo "${ram_percent:-0}"
}

# Get GPU VRAM info
get_gpu_info() {
    local vram_used=0
    local vram_total=0
    
    if command -v nvidia-smi >/dev/null 2>&1; then
        # NVIDIA GPU
        local gpu_info
        gpu_info=$(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || echo "0,0")
        vram_used=$(echo "$gpu_info" | cut -d',' -f1 | xargs)
        vram_total=$(echo "$gpu_info" | cut -d',' -f2 | xargs)
    elif [[ "$(uname)" == "Darwin" ]]; then
        # macOS - Metal (approximate)
        vram_used=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "VRAM" | head -1 | awk '{print $2}' || echo "0")
        vram_total=$vram_used
    else
        # No GPU or unsupported
        vram_used=0
        vram_total=0
    fi
    
    echo "${vram_used:-0},${vram_total:-0}"
}

# Get disk space for /mnt/studio
get_disk_space() {
    local disk_used=0
    local disk_total=0
    
    if df -h /mnt/studio >/dev/null 2>&1; then
        local disk_info
        disk_info=$(df -BG /mnt/studio | tail -1 | awk '{print $3,$2}' | sed 's/G//g')
        disk_used=$(echo "$disk_info" | cut -d' ' -f1)
        disk_total=$(echo "$disk_info" | cut -d' ' -f2)
    fi
    
    echo "${disk_used:-0},${disk_total:-0}"
}

# Get Docker container status
get_docker_status() {
    local running=0
    local stopped=0
    local unhealthy=0
    
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        running=$(docker ps -q 2>/dev/null | wc -l || echo "0")
        stopped=$(docker ps -aq 2>/dev/null | wc -l || echo "0")
        stopped=$((stopped - running))
        unhealthy=$(docker ps --filter "health=unhealthy" -q 2>/dev/null | wc -l || echo "0")
    fi
    
    echo "$running,$stopped,$unhealthy"
}

# Check network connectivity
check_network() {
    local network_ok=0
    local gateway
    
    # Get default gateway
    gateway=$(ip route 2>/dev/null | grep default | awk '{print $3}' | head -1 || echo "")
    
    if [[ -n "$gateway" ]]; then
        if ping -c 1 -W 2 "$gateway" >/dev/null 2>&1; then
            network_ok=1
        fi
    elif ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        network_ok=1
    fi
    
    echo "$network_ok"
}

# Write CSV entry
write_csv() {
    local timestamp="$1"
    local cpu="$2"
    local ram="$3"
    local gpu_used="$4"
    local gpu_total="$5"
    local disk_used="$6"
    local disk_total="$7"
    local docker_run="$8"
    local docker_stop="$9"
    local docker_unhealthy="${10}"
    local network="${11}"
    
    local today
    today=$(date '+%Y-%m-%d')
    local csv_file="$LOG_DIR/resources-$today.csv"
    
    echo "$timestamp,$cpu,$ram,$gpu_used,$gpu_total,$disk_used,$disk_total,$docker_run,$docker_stop,$docker_unhealthy,$network" >> "$csv_file"
}

# Write JSON snapshot
write_json() {
    local timestamp="$1"
    local cpu="$2"
    local ram="$3"
    local gpu_used="$4"
    local gpu_total="$5"
    local disk_used="$6"
    local disk_total="$7"
    local docker_run="$8"
    local docker_stop="$9"
    local docker_unhealthy="${10}"
    local network="${11}"
    
    local json_file="$LOG_DIR/latest-snapshot.json"
    
    cat > "$json_file" << EOF
{
    "timestamp": "$timestamp",
    "cpu_percent": $cpu,
    "ram_percent": $ram,
    "gpu_vram_used_mb": $gpu_used,
    "gpu_vram_total_mb": $gpu_total,
    "disk_used_gb": $disk_used,
    "disk_total_gb": $disk_total,
    "docker_running": $docker_run,
    "docker_stopped": $docker_stop,
    "docker_unhealthy": $docker_unhealthy,
    "network_ok": $network,
    "check_interval_seconds": $INTERVAL
}
EOF
}

# Perform single check
perform_check() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log "INFO" "Performing resource check..."
    
    # Collect metrics
    local cpu
    cpu=$(get_cpu_percent)
    local ram
    ram=$(get_ram_percent)
    local gpu_info
    gpu_info=$(get_gpu_info)
    local gpu_used=$(echo "$gpu_info" | cut -d',' -f1)
    local gpu_total=$(echo "$gpu_info" | cut -d',' -f2)
    local disk_info
    disk_info=$(get_disk_space)
    local disk_used=$(echo "$disk_info" | cut -d',' -f1)
    local disk_total=$(echo "$disk_info" | cut -d',' -f2)
    local docker_info
    docker_info=$(get_docker_status)
    local docker_run=$(echo "$docker_info" | cut -d',' -f1)
    local docker_stop=$(echo "$docker_info" | cut -d',' -f2)
    local docker_unhealthy=$(echo "$docker_info" | cut -d',' -f3)
    local network
    network=$(check_network)
    
    # Write outputs
    write_csv "$timestamp" "$cpu" "$ram" "$gpu_used" "$gpu_total" "$disk_used" "$disk_total" "$docker_run" "$docker_stop" "$docker_unhealthy" "$network"
    write_json "$timestamp" "$cpu" "$ram" "$gpu_used" "$gpu_total" "$disk_used" "$disk_total" "$docker_run" "$docker_stop" "$docker_unhealthy" "$network"
    
    log "INFO" "Check complete - CPU: ${cpu}%, RAM: ${ram}%, GPU: ${gpu_used}/${gpu_total}MB, Disk: ${disk_used}/${disk_total}GB, Docker: ${docker_run}/${docker_stop}/${docker_unhealthy}, Network: ${network}"
}

# Main loop
main_loop() {
    log "INFO" "Starting resource monitor (interval: ${INTERVAL}s)"
    
    while $RUNNING; do
        perform_check
        rotate_logs
        
        if $ONCE_MODE; then
            log "INFO" "Single check completed, exiting"
            exit 0
        fi
        
        if $WATCH_MODE; then
            sleep "$INTERVAL"
        else
            break
        fi
    done
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --once)
                ONCE_MODE=true
                WATCH_MODE=false
                shift
                ;;
            --watch)
                WATCH_MODE=true
                ONCE_MODE=false
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
    
    # Default to watch mode if neither once nor watch specified
    if ! $ONCE_MODE && ! $WATCH_MODE; then
        WATCH_MODE=true
    fi
}

# Write PID file
write_pid() {
    echo $$ > "$PID_FILE"
    log "INFO" "PID $$ written to $PID_FILE"
}

# Main execution
main() {
    parse_args "$@"
    check_privileges
    init_logs
    
    if $WATCH_MODE; then
        write_pid
    fi
    
    main_loop
}

# Run main
main "$@"