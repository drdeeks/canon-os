#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Install Script for Resource Monitor and Keep-Alive Services
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local message="$*"
    
    case "$level" in
        INFO)  color="$GREEN" ;;
        WARN)  color="$YELLOW" ;;
        ERROR) color="$RED" ;;
        *)     color="$NC" ;;
    esac
    
    echo -e "${color}[$level] $message${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "This script must be run as root"
        exit 1
    fi
}

install_service() {
    local service_name="$1"
    local script_name="$2"
    
    log "INFO" "Installing $service_name..."
    
    # Copy service file
    if [[ -f "$SCRIPT_DIR/$service_name.service" ]]; then
        cp "$SCRIPT_DIR/$service_name.service" "$SYSTEMD_DIR/"
        log "INFO" "Service file copied to $SYSTEMD_DIR"
    else
        log "ERROR" "Service file not found: $SCRIPT_DIR/$service_name.service"
        return 1
    fi
    
    # Make script executable
    chmod +x "$SCRIPT_DIR/$script_name"
    log "INFO" "Made $script_name executable"
    
    # Create necessary directories
    mkdir -p /mnt/studio/logs/resources
    mkdir -p /mnt/studio/logs/keep-alive
    log "INFO" "Created log directories"
    
    # Reload systemd
    systemctl daemon-reload
    log "INFO" "Systemd daemon reloaded"
}

enable_service() {
    local service_name="$1"
    
    log "INFO" "Enabling $service_name..."
    systemctl enable "$service_name.service"
    log "INFO" "$service_name enabled"
}

start_service() {
    local service_name="$1"
    
    log "INFO" "Starting $service_name..."
    systemctl start "$service_name.service"
    log "INFO" "$service_name started"
}

show_status() {
    local service_name="$1"
    
    echo
    log "INFO" "Status of $service_name:"
    systemctl status "$service_name.service" --no-pager -l || true
    echo
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Install and configure monitoring services"
    echo
    echo "OPTIONS:"
    echo "    --all           Install both services"
    echo "    --resource      Install resource-monitor only"
    echo "    --keep-alive    Install keep-alive only"
    echo "    --no-start      Install but don't start services"
    echo "    --status        Show status of installed services"
    echo "    --uninstall     Remove services"
    echo "    --help          Show this help"
    echo
    echo "EXAMPLES:"
    echo "    $0 --all              # Install and start both services"
    echo "    $0 --resource --no-start  # Install resource-monitor, don't start"
    echo "    $0 --status           # Check service status"
    echo "    $0 --uninstall        # Remove all services"
}

uninstall_service() {
    local service_name="$1"
    
    log "INFO" "Uninstalling $service_name..."
    
    # Stop and disable if running
    if systemctl is-active --quiet "$service_name.service" 2>/dev/null; then
        systemctl stop "$service_name.service"
    fi
    if systemctl is-enabled --quiet "$service_name.service" 2>/dev/null; then
        systemctl disable "$service_name.service"
    fi
    
    # Remove service file
    if [[ -f "$SYSTEMD_DIR/$service_name.service" ]]; then
        rm "$SYSTEMD_DIR/$service_name.service"
    fi
    
    systemctl daemon-reload
    log "INFO" "$service_name uninstalled"
}

main() {
    local install_resource=false
    local install_keep_alive=false
    local start_services=true
    local show_status_only=false
    local uninstall=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --all)
                install_resource=true
                install_keep_alive=true
                shift
                ;;
            --resource)
                install_resource=true
                shift
                ;;
            --keep-alive)
                install_keep_alive=true
                shift
                ;;
            --no-start)
                start_services=false
                shift
                ;;
            --status)
                show_status_only=true
                shift
                ;;
            --uninstall)
                uninstall=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Show status and exit
    if $show_status_only; then
        show_status "resource-monitor"
        show_status "keep-alive"
        exit 0
    fi
    
    # Uninstall
    if $uninstall; then
        check_root
        uninstall_service "resource-monitor"
        uninstall_service "keep-alive"
        log "INFO" "All services uninstalled"
        exit 0
    fi
    
    # Check if we have something to install
    if ! $install_resource && ! $install_keep_alive; then
        log "WARN" "No services specified for installation"
        show_usage
        exit 1
    fi
    
    check_root
    
    # Install services
    if $install_resource; then
        install_service "resource-monitor" "resource-monitor.sh"
        if $start_services; then
            enable_service "resource-monitor"
            start_service "resource-monitor"
            show_status "resource-monitor"
        fi
    fi
    
    if $install_keep_alive; then
        install_service "keep-alive" "keep-alive.sh"
        if $start_services; then
            enable_service "keep-alive"
            start_service "keep-alive"
            show_status "keep-alive"
        fi
    fi
    
    log "INFO" "Installation complete!"
    echo
    echo "Useful commands:"
    echo "  systemctl status resource-monitor.service"
    echo "  systemctl status keep-alive.service"
    echo "  journalctl -u resource-monitor.service -f"
    echo "  journalctl -u keep-alive.service -f"
}

main "$@"