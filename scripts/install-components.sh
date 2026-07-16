#!/usr/bin/env bash
###############################################################################
# install-components.sh - Comprehensive component installer for AI Creative Studio
#
# Detects installed versions, checks latest stable, and installs/updates
# system packages, security tools, GPU drivers, storage mounts, and AI
# container images.
#
# Usage:
#   sudo bash install-components.sh [OPTIONS]
#
# Options:
#   --check-only       Report installed/missing/outdated (no changes)
#   --install-missing  Install only missing components
#   --update-all       Update everything to latest stable
#   --dry-run          Show what would happen without making changes
#   --yes, -y          Skip interactive prompts (auto-confirm)
#   --help, -h         Show this help
#
# Can be called by setup-master.sh or run independently.
# Logs to /mnt/studio/logs/install.log
###############################################################################
set -euo pipefail

# --- Constants ---
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly LOG_DIR="/mnt/studio/logs"
readonly LOG_FILE="${LOG_DIR}/install.log"
readonly STUDIO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly BACKENDS_CONFIG="${STUDIO_DIR}/config/backends.conf"

# --- Colors (disabled when not a terminal) ---
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'
    DIM='\033[2m'; RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' DIM='' RESET=''
fi

# --- Globals ---
MODE="interactive"
DRY_RUN=false
AUTO_YES=false

INSTALLED_COUNT=0; MISSING_COUNT=0; OUTDATED_COUNT=0
UPDATED_COUNT=0; FAILED_COUNT=0; SKIPPED_COUNT=0

declare -a TABLE_ROWS=()

# =============================== LOGGING =====================================

init_logging() {
    mkdir -p "${LOG_DIR}" 2>/dev/null || true
    if ! touch "${LOG_FILE}" 2>/dev/null; then
        echo "Warning: Cannot write to ${LOG_FILE}" >&2
    fi
}

log() {
    local level="$1"; shift
    local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
    if [[ -w "${LOG_FILE}" ]]; then
        echo "[${ts}] [${level}] $*" >> "${LOG_FILE}"
    fi
}

log_info()  { log "INFO"  "$@"; }
log_warn()  { log "WARN"  "$@"; }
log_error() { log "ERROR" "$@"; }

# =============================== OUTPUT ======================================

info()  { echo -e "${BLUE}[INFO]${RESET}  $*"; log_info "$*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; log_warn "$*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*"; log_error "$*"; }
ok()    { echo -e "${GREEN}[OK]${RESET}    $*"; log_info "OK: $*"; }
step()  { echo -e "${CYAN}>>>${RESET} $*"; log_info "STEP: $*"; }
die()   { error "$@"; exit 1; }

# ============================ ARGUMENTS =====================================

usage() {
    cat <<'EOF'
Usage: install-components.sh [OPTIONS]

Options:
  --check-only       Report installed/missing/outdated (no changes)
  --install-missing  Install only missing components
  --update-all       Update everything to latest stable
  --dry-run          Show what would happen without making changes
  --yes, -y          Skip interactive prompts (auto-confirm)
  --help, -h         Show this help
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check-only)      MODE="check-only";      shift ;;
            --install-missing) MODE="install-missing";  shift ;;
            --update-all)      MODE="update-all";       shift ;;
            --dry-run)         DRY_RUN=true;            shift ;;
            --yes|-y)          AUTO_YES=true;           shift ;;
            --help|-h)         usage ;;
            *) die "Unknown option: $1 (try --help)" ;;
        esac
    done
}

# =============================== HELPERS =====================================

is_root()     { [[ "$(id -u)" -eq 0 ]]; }
ensure_root() { is_root || die "This script must be run as root (or with sudo)"; }
cmd_exists()  { command -v "$1" &>/dev/null; }

pkg_manager() {
    if command -v apt-get &>/dev/null; then echo "apt"
    elif command -v dnf &>/dev/null; then echo "dnf"
    elif command -v yum &>/dev/null; then echo "yum"
    elif command -v pacman &>/dev/null; then echo "pacman"
    else echo "unknown"; fi
}

detect_os() {
    if [[ "$(uname -s)" == "Darwin" ]]; then echo "macos"
    elif [[ -f /etc/os-release ]]; then echo "linux"
    else echo "unknown"; fi
}

detect_arch() { uname -m; }

detect_gpu() {
    local gpu="none"
    if [[ "$(uname -s)" == "Darwin" ]]; then
        [[ -n "$(sysctl -n hw.model 2>/dev/null || true)" ]] && gpu="metal"
    else
        if cmd_exists nvidia-smi && nvidia-smi &>/dev/null 2>&1; then
            gpu="nvidia"
        elif cmd_exists lspci && lspci 2>/dev/null | grep -qi "nvidia"; then
            gpu="nvidia-present"
        elif cmd_exists lspci && lspci 2>/dev/null | grep -qi "amd\|radeon"; then
            gpu="amd"
        fi
    fi
    echo "${gpu}"
}

run_cmd() {
    if ${DRY_RUN}; then
        info "[DRY-RUN] Would execute: $*"
        return 0
    fi
    "$@"
}

confirm() {
    local prompt="$1"
    ${AUTO_YES} && return 0
    echo -en "${YELLOW}${prompt} [Y/n] ${RESET}"
    local reply; read -r reply
    reply="${reply,,}"
    [[ -z "${reply}" || "${reply}" == "y" || "${reply}" == "yes" ]]
}

add_table_row() { TABLE_ROWS+=("$1|$2|$3|$4"); }

# ========================== VERSION DETECTION ===============================

get_installed_version() {
    local c="$1" v=""
    case "${c}" in
        docker)
            cmd_exists docker && v="$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        docker-compose)
            if cmd_exists docker; then
                v="$(docker compose version --short 2>/dev/null || true)"
                [[ -z "${v}" ]] && v="$(docker-compose version --short 2>/dev/null || true)"
                v="$(echo "${v}" | grep -oP '\d+\.\d+\.\d+' | head -1 || true)"
            fi ;;
        python3)
            cmd_exists python3 && v="$(python3 --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || true)" ;;
        pip3)
            cmd_exists pip3 && v="$(pip3 --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        git)
            cmd_exists git && v="$(git --version | grep -oP '\d+\.\d+\.\d+' || true)" ;;
        curl)
            cmd_exists curl && v="$(curl --version | head -1 | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        wget)
            cmd_exists wget && v="$(wget --version | head -1 | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        jq)
            cmd_exists jq && v="$(jq --version 2>&1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1 || true)" ;;
        htop)
            cmd_exists htop && v="$(htop --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        tree)
            cmd_exists tree && v="$(tree --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        unzip)
            cmd_exists unzip && v="$(unzip -v 2>&1 | head -1 | grep -oP '\d+\.\d+' | head -1 || true)" ;;
        openssh-server)
            cmd_exists sshd && v="$(sshd -V 2>&1 | grep -oP 'OpenSSH_\K[0-9p\.]+' | head -1 || true)" ;;
        fail2ban)
            cmd_exists fail2ban-client && v="$(fail2ban-client --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        ufw)
            cmd_exists ufw && v="$(ufw version 2>&1 | grep -oP '\d+\.\d+' | head -1 || true)" ;;
        gnupg)
            cmd_exists gpg && v="$(gpg --version | head -1 | grep -oP '\d+\.\d+\.\d+' || true)" ;;
        ca-certificates)
            [[ -d /etc/ssl/certs ]] && v="installed" ;;
        nvidia-container-toolkit)
            cmd_exists nvidia-ctk && v="$(nvidia-ctk --version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1 || true)" ;;
        nfs-common)
            if dpkg -l nfs-common 2>/dev/null | grep -q '^ii'; then
                v="$(dpkg -l nfs-common 2>/dev/null | awk '/^ii/{print $3}' || true)"
            elif cmd_exists mount.nfs; then v="installed"; fi ;;
        cifs-utils)
            if dpkg -l cifs-utils 2>/dev/null | grep -q '^ii'; then
                v="$(dpkg -l cifs-utils 2>/dev/null | awk '/^ii/{print $3}' || true)"
            elif cmd_exists mount.cifs; then v="installed"; fi ;;
        acl)
            cmd_exists setfacl && v="$(setfacl --version 2>&1 | grep -oP '\d+\.\d+' | head -1 || true)" ;;
        *) ;;
    esac
    echo "${v}"
}

# ========================== LATEST VERSION FETCH ============================

get_latest_version() {
    local c="$1" latest=""
    case "${c}" in
        docker)
            latest="$(curl -sfL --max-time 10 https://api.github.com/repos/moby/moby/releases/latest 2>/dev/null | jq -r .tag_name 2>/dev/null | sed 's/^v//' || true)"
            [[ -z "${latest}" || "${latest}" == "null" ]] && latest="(check online)" ;;
        docker-compose)
            latest="$(curl -sfL --max-time 10 https://api.github.com/repos/docker/compose/releases/latest 2>/dev/null | jq -r .tag_name 2>/dev/null | sed 's/^v//' || true)"
            [[ -z "${latest}" || "${latest}" == "null" ]] && latest="(check online)" ;;
        python3)
            latest="$(curl -sfL --max-time 10 https://endoflife.date/api/python.json 2>/dev/null | jq -r '.[0].latest' 2>/dev/null || true)"
            [[ -z "${latest}" || "${latest}" == "null" ]] && latest="(check online)" ;;
        git)
            latest="$(curl -sfL --max-time 10 https://api.github.com/repos/git/git/releases/latest 2>/dev/null | jq -r .tag_name 2>/dev/null | sed 's/^v//' || true)"
            [[ -z "${latest}" || "${latest}" == "null" ]] && latest="(check online)" ;;
        curl)
            latest="$(curl -sfL --max-time 10 https://curl.se/download/ 2>/dev/null | grep -oP 'curl-\K[0-9]+\.[0-9]+\.[0-9]+' | sort -V | tail -1 || true)"
            [[ -z "${latest}" ]] && latest="(check online)" ;;
        nvidia-container-toolkit)
            latest="$(curl -sfL --max-time 10 https://api.github.com/repos/NVIDIA/nvidia-container-toolkit/releases/latest 2>/dev/null | jq -r .tag_name 2>/dev/null | sed 's/^v//;s/-.*//' || true)"
            [[ -z "${latest}" || "${latest}" == "null" ]] && latest="(check online)" ;;
        fail2ban)
            latest="$(curl -sfL --max-time 10 https://api.github.com/repos/fail2ban/fail2ban/releases/latest 2>/dev/null | jq -r .tag_name 2>/dev/null | sed 's/^v//' || true)"
            [[ -z "${latest}" || "${latest}" == "null" ]] && latest="(check online)" ;;
        *) latest="(system)" ;;
    esac
    echo "${latest}"
}

# ========================= PACKAGE INSTALL ===================================

install_system_pkg() {
    local pkg="$1" mgr; mgr="$(pkg_manager)"
    case "${mgr}" in
        apt) run_cmd DEBIAN_FRONTEND=noninteractive apt-get install -y "${pkg}" ;;
        dnf) run_cmd dnf install -y "${pkg}" ;;
        *)   die "Unsupported package manager (${mgr}). Cannot install ${pkg}" ;;
    esac
}

# ==================== COMPONENT-SPECIFIC INSTALLERS ==========================

install_docker() {
    step "Installing Docker Engine..."
    local mgr; mgr="$(pkg_manager)"
    if [[ "${mgr}" == "apt" ]]; then
        run_cmd apt-get update -qq
        run_cmd apt-get install -y ca-certificates curl gnupg
        run_cmd install -m 0755 -d /etc/apt/keyrings
        run_cmd bash -c 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg'
        run_cmd chmod a+r /etc/apt/keyrings/docker.gpg
        local codename; codename="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
        run_cmd bash -c "echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${codename} stable\" > /etc/apt/sources.list.d/docker.list"
        run_cmd apt-get update -qq
        run_cmd apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin
    else
        install_system_pkg docker
    fi
    if ! ${DRY_RUN}; then
        systemctl enable docker 2>/dev/null || true
        systemctl start docker 2>/dev/null || true
    fi
}

install_docker_compose() {
    if ! cmd_exists docker; then install_docker; return; fi
    if ! docker compose version &>/dev/null 2>&1; then
        step "Installing Docker Compose plugin..."
        install_system_pkg docker-compose-plugin 2>/dev/null || true
    fi
    if ! cmd_exists docker-compose && ! docker compose version &>/dev/null 2>&1; then
        step "Installing Docker Compose standalone binary..."
        local latest
        latest="$(curl -sfL --max-time 10 https://api.github.com/repos/docker/compose/releases/latest 2>/dev/null | jq -r .tag_name 2>/dev/null || true)"
        [[ -z "${latest}" || "${latest}" == "null" ]] && latest="v2.29.0"
        run_cmd bash -c "curl -sfL https://github.com/docker/compose/releases/download/${latest}/docker-compose-\$(uname -s)-\$(uname -m) -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose"
    fi
}

install_nvidia_toolkit() {
    step "Installing NVIDIA Container Toolkit..."
    local mgr; mgr="$(pkg_manager)"
    if [[ "${mgr}" == "apt" ]]; then
        run_cmd bash -c 'curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg'
        run_cmd bash -c 'curl -sL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed "s#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g" > /etc/apt/sources.list.d/nvidia-container-toolkit.list'
        run_cmd apt-get update -qq
        run_cmd apt-get install -y nvidia-container-toolkit
    else
        warn "NVIDIA Container Toolkit auto-install only supported for apt-based systems"
    fi
}

install_fail2ban() {
    step "Installing fail2ban..."
    install_system_pkg fail2ban
    if ! ${DRY_RUN}; then
        systemctl enable fail2ban 2>/dev/null || true
        systemctl start fail2ban 2>/dev/null || true
    fi
}

install_ufw() {
    step "Installing UFW..."
    install_system_pkg ufw
}

# ======================== AI CONTAINER IMAGES ================================

declare -A AI_IMAGES=(
    [ollama]="ollama/ollama:latest"
    [comfyui]="ghcr.io/comfyanonymous/comfyui:latest"
    [whisper]="onerahmet/openai-whisper-asr-webservice:latest"
    [kokoro]="ghcr.io/remsky/kokoro-fastapi-cpu:latest"
    [audiocraft]="ghcr.io/music-generation/audiocraft:latest"
)

get_ai_container_images() {
    local images=()
    if [[ -f "${BACKENDS_CONFIG}" ]]; then
        while IFS= read -r line; do
            line="${line%%#*}"; line="${line// /}"
            [[ -z "${line}" ]] && continue
            [[ -v "AI_IMAGES[${line}]" ]] && images+=("${AI_IMAGES[${line}]}")
        done < "${BACKENDS_CONFIG}"
    else
        for key in "${!AI_IMAGES[@]}"; do images+=("${AI_IMAGES[${key}]}"); done
    fi
    printf '%s\n' "${images[@]}"
}

get_docker_image_version() {
    local image="$1"
    if docker image inspect "${image}" &>/dev/null; then
        local digest
        digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "${image}" 2>/dev/null | cut -d@ -f2 | cut -c1-12 || true)"
        [[ -n "${digest}" ]] && echo "${digest}" || echo "local"
    else
        echo ""
    fi
}

pull_ai_images() {
    if ! cmd_exists docker; then warn "Docker not installed - skipping AI container pulls"; return; fi
    if ! docker info &>/dev/null 2>&1; then warn "Docker daemon not running - skipping AI container pulls"; return; fi

    step "Managing AI container images..."
    local images; mapfile -t images < <(get_ai_container_images)

    for image in "${images[@]}"; do
        [[ -z "${image}" ]] && continue
        local installed_ver; installed_ver="$(get_docker_image_version "${image}")"
        local display_name="${image%%:*}"; display_name="${display_name##*/}"

        if [[ -z "${installed_ver}" ]]; then
            if [[ "${MODE}" == "check-only" ]]; then
                add_table_row "docker:${display_name}" "--" "--" "MISSING"
                ((MISSING_COUNT++)) || true
            elif [[ "${MODE}" == "install-missing" || "${MODE}" == "update-all" || "${MODE}" == "interactive" ]]; then
                if confirm "Pull Docker image ${image}?"; then
                    step "Pulling ${image}..."
                    if run_cmd docker pull "${image}"; then
                        ok "Pulled ${image}"; ((UPDATED_COUNT++)) || true
                    else
                        error "Failed to pull ${image}"; ((FAILED_COUNT++)) || true
                    fi
                else
                    ((SKIPPED_COUNT++)) || true
                fi
            fi
        elif [[ "${MODE}" == "update-all" ]]; then
            if confirm "Re-pull Docker image ${image}?"; then
                step "Pulling latest ${image}..."
                if run_cmd docker pull "${image}"; then
                    ok "Updated ${image}"; ((UPDATED_COUNT++)) || true
                else
                    error "Failed to pull ${image}"; ((FAILED_COUNT++)) || true
                fi
            else
                add_table_row "docker:${display_name}" "${installed_ver}" "--" "OK"
                ((INSTALLED_COUNT++)) || true
            fi
        else
            add_table_row "docker:${display_name}" "${installed_ver}" "--" "OK"
            ((INSTALLED_COUNT++)) || true
        fi
    done
}

# ========================== TABLE OUTPUT =====================================

print_table() {
    echo ""
    echo -e "${BOLD}+====================================+================+================+==========+${RESET}"
    printf "${BOLD}| %-34s | %-14s | %-14s | %-8s |${RESET}\n" "Component" "Installed" "Latest" "Status"
    echo -e "${BOLD}+====================================+================+================+==========+${RESET}"

    if [[ ${#TABLE_ROWS[@]} -eq 0 ]]; then
        printf "| %-34s | %-14s | %-14s | %-8s |\n" "(no components)" "--" "--" "--"
    fi

    for row in "${TABLE_ROWS[@]}"; do
        IFS='|' read -r comp inst latest status <<< "${row}"
        local sc=""
        case "${status}" in
            OK)       sc="${GREEN}" ;;
            MISSING)  sc="${RED}" ;;
            OUTDATED) sc="${YELLOW}" ;;
        esac
        printf "| %-34s | %-14s | %-14s | ${sc}%-8s${RESET} |\n" \
            "${comp:0:34}" "${inst:--}" "${latest:-?}" "${status}"
    done

    echo -e "${BOLD}+====================================+================+================+==========+${RESET}"
    echo ""
    echo -e "  ${GREEN}OK:${RESET} ${INSTALLED_COUNT}  ${RED}Missing:${RESET} ${MISSING_COUNT}  ${YELLOW}Outdated:${RESET} ${OUTDATED_COUNT}  Updated: ${UPDATED_COUNT}  Failed: ${FAILED_COUNT}  Skipped: ${SKIPPED_COUNT}"
    echo ""
}

# ====================== COMPONENT METADATA ===================================

declare -A COMPONENT_CATEGORIES=(
    [docker]="System" [docker-compose]="System" [python3]="System"
    [pip3]="System" [git]="System" [curl]="System" [wget]="System"
    [jq]="System" [htop]="System" [tree]="System" [unzip]="System" [acl]="System"
    [openssh-server]="Security" [fail2ban]="Security" [ufw]="Security"
    [gnupg]="Security" [ca-certificates]="Security"
    [nvidia-container-toolkit]="GPU"
    [nfs-common]="Storage" [cifs-utils]="Storage"
)

declare -A COMPONENT_PKGS=(
    [docker]="docker-ce" [docker-compose]="docker-compose-plugin"
    [python3]="python3" [pip3]="python3-pip"
    [git]="git" [curl]="curl" [wget]="wget" [jq]="jq" [htop]="htop"
    [tree]="tree" [unzip]="unzip" [acl]="acl"
    [openssh-server]="openssh-server" [fail2ban]="fail2ban" [ufw]="ufw"
    [gnupg]="gnupg" [ca-certificates]="ca-certificates"
    [nfs-common]="nfs-common" [cifs-utils]="cifs-utils"
)

# ====================== CORE PROCESSING ======================================

install_component() {
    local comp="$1"
    step "Installing/updating ${comp}..."
    case "${comp}" in
        docker)                    install_docker ;;
        docker-compose)            install_docker_compose ;;
        nvidia-container-toolkit)  install_nvidia_toolkit ;;
        fail2ban)                  install_fail2ban ;;
        ufw)                       install_ufw ;;
        *)
            local pkg="${COMPONENT_PKGS[${comp}]:-${comp}}"
            if install_system_pkg "${pkg}"; then
                ok "Installed/updated ${comp}"; ((UPDATED_COUNT++)) || true
            else
                error "Failed to install ${comp}"; ((FAILED_COUNT++)) || true
            fi
            ;;
    esac
}

process_component() {
    local comp="$1"
    local category="${COMPONENT_CATEGORIES[${comp}]:-Other}"
    local installed_ver latest_ver
    installed_ver="$(get_installed_version "${comp}")"
    latest_ver="$(get_latest_version "${comp}")"

    # Determine status
    local status
    if [[ -z "${installed_ver}" ]]; then
        status="MISSING"
    elif [[ "${latest_ver}" == "(system)" || "${latest_ver}" == "(check online)" ]]; then
        status="OK"
    elif [[ "${installed_ver}" == "${latest_ver}" ]]; then
        status="OK"
    elif printf '%s\n%s\n' "${installed_ver}" "${latest_ver}" | sort -V -C; then
        status="OUTDATED"
    else
        status="OK"
    fi

    add_table_row "${category}:${comp}" "${installed_ver}" "${latest_ver}" "${status}"

    case "${status}" in
        OK)
            ((INSTALLED_COUNT++)) || true ;;
        MISSING)
            ((MISSING_COUNT++)) || true
            if [[ "${MODE}" == "install-missing" || "${MODE}" == "interactive" ]]; then
                if confirm "Install missing component: ${comp}?"; then
                    install_component "${comp}"
                else
                    info "Skipped ${comp}"; ((SKIPPED_COUNT++)) || true
                fi
            fi ;;
        OUTDATED)
            ((OUTDATED_COUNT++)) || true
            if [[ "${MODE}" == "update-all" || "${MODE}" == "interactive" ]]; then
                if confirm "Update ${comp} (${installed_ver} -> ${latest_ver})?"; then
                    install_component "${comp}"
                else
                    info "Skipped update for ${comp}"; ((SKIPPED_COUNT++)) || true
                fi
            fi ;;
    esac
}

# =========================== MAIN ============================================

main() {
    parse_args "$@"
    init_logging

    log_info "========== install-components.sh started =========="
    log_info "Mode: ${MODE}, Dry-run: ${DRY_RUN}, Auto-yes: ${AUTO_YES}"

    echo ""
    echo -e "${BOLD}+----------------------------------------------------------+${RESET}"
    echo -e "${BOLD}|        AI Creative Studio -- Component Installer         |${RESET}"
    echo -e "${BOLD}+----------------------------------------------------------+${RESET}"
    echo ""

    # Detect environment
    local os_type gpu_type arch pkg_mgr
    os_type="$(detect_os)"
    gpu_type="$(detect_gpu)"
    arch="$(detect_arch)"
    pkg_mgr="$(pkg_manager)"

    info "OS: ${os_type} | Arch: ${arch} | Pkg Manager: ${pkg_mgr} | GPU: ${gpu_type}"
    info "Mode: ${MODE} | Dry-run: ${DRY_RUN}"
    echo ""

    [[ "${MODE}" != "check-only" ]] && ensure_root

    # Update apt cache once
    if [[ "${pkg_mgr}" == "apt" && "${MODE}" != "check-only" ]]; then
        step "Updating package index..."
        run_cmd apt-get update -qq || true
    fi

    # Build component list
    local all_components=(
        docker docker-compose python3 pip3 git curl wget jq htop tree unzip acl
        openssh-server fail2ban ufw gnupg ca-certificates
        nfs-common cifs-utils
    )
    if [[ "${gpu_type}" == "nvidia" || "${gpu_type}" == "nvidia-present" ]]; then
        all_components+=(nvidia-container-toolkit)
    fi

    # Process each component
    step "Checking ${#all_components[@]} system components..."
    echo ""
    for comp in "${all_components[@]}"; do
        process_component "${comp}"
    done

    # AI container images
    if cmd_exists docker && docker info &>/dev/null 2>&1; then
        pull_ai_images
    elif [[ "${MODE}" != "check-only" ]]; then
        warn "Docker not available - skipping AI container image management"
    fi

    # Summary
    print_table

    # Post-install notes
    if [[ "${gpu_type}" == "metal" ]]; then
        echo -e "${CYAN}Note:${RESET} Apple Metal detected - GPU acceleration available natively"
    elif [[ "${gpu_type}" == "nvidia-present" ]]; then
        echo -e "${YELLOW}Note:${RESET} NVIDIA GPU detected but nvidia-smi failed. Check driver installation."
    fi
    [[ "${MODE}" == "check-only" ]] && echo -e "${DIM}Run without --check-only to install missing components.${RESET}"

    log_info "========== install-components.sh finished =========="
    log_info "Results: OK=${INSTALLED_COUNT} Missing=${MISSING_COUNT} Outdated=${OUTDATED_COUNT} Updated=${UPDATED_COUNT} Failed=${FAILED_COUNT} Skipped=${SKIPPED_COUNT}"

    [[ ${FAILED_COUNT} -gt 0 ]] && exit 1
    exit 0
}

main "$@"
