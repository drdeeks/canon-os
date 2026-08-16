#!/usr/bin/env bash
###############################################################################
# studio-update.sh - AI Creative Studio Update/Upgrade Manager
#
# Commands:
#   studio-update check          Check what can be updated
#   studio-update pull           Pull latest Docker images
#   studio-update scripts        Update scripts from repo
#   studio-update dashboard      Rebuild dashboard container
#   studio-update all            Update everything
#   studio-update rollback       Rollback to previous versions
#   studio-update --dry-run      Show what would be updated
#   studio-update --offline      Skip network-dependent checks
#   studio-update --timeout 30   Override default timeouts (seconds)
#
# Features:
#   - Version tracking via /opt/ai-studio/config/versions.json
#   - Docker image digest comparison (local vs remote)
#   - Safe update: pull before stopping containers
#   - Rollback with previous image tags
#   - Health check after update
#   - Auto-backup configs before update
#   - Rolling restart for minimal downtime
#   - Update summary notifications
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly STUDIO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly CONFIG_DIR="/opt/ai-studio/config"
readonly VERSIONS_FILE="${CONFIG_DIR}/versions.json"
readonly ROLLBACK_DIR="/opt/ai-studio/rollback"
readonly BACKUP_DIR="/opt/ai-studio/backups"
readonly COMPOSE_FILE="${STUDIO_ROOT}/docker-compose.yml"
readonly LOG_FILE="/opt/ai-studio/logs/studio-update.log"
readonly REPO_URL="https://github.com/ai-creative/studio.git"

# Default timeouts (seconds)
TIMEOUT_CHECK=5
TIMEOUT_PULL=60
TIMEOUT_DOCKER_COMPOSE=10
TIMEOUT_PYTHON=5
TIMEOUT_HEALTH=3
TIMEOUT_GIT=30

# ---------------------------------------------------------------------------
# Colors & logging
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

log()      { local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"; echo -e "${DIM}[${ts}]${NC} $*" | tee -a "${LOG_FILE}" 2>/dev/null || true; }
info()     { log "${BLUE}[INFO]${NC}  $*"; }
success()  { log "${GREEN}[OK]${NC}    $*"; }
warn()     { log "${YELLOW}[WARN]${NC}  $*"; }
error()    { log "${RED}[ERROR]${NC} $*" >&2; }
header()   { echo -e "\n${BOLD}${CYAN}═══ $* ═══${NC}\n" | tee -a "${LOG_FILE}" 2>/dev/null || true; }

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
DRY_RUN=false
OFFLINE=false
UPDATED_ITEMS=()
FAILED_ITEMS=()
ROLLBACK_IMAGES=()

# ---------------------------------------------------------------------------
# Timeout wrapper
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Network check
# ---------------------------------------------------------------------------
is_online() {
    if $OFFLINE; then
        return 1
    fi
    _timeout "$TIMEOUT_CHECK" ping -c 1 -W 2 8.8.8.8 &>/dev/null 2>&1
}

# ---------------------------------------------------------------------------
# JSON helpers: python3 with jq fallback
# ---------------------------------------------------------------------------
_json_get() {
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
        local jq_key=".${key//./.}"
        jq -r "${jq_key} // empty" "$file" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ensure_dirs() {
    mkdir -p "${CONFIG_DIR}" "${ROLLBACK_DIR}" "${BACKUP_DIR}" "$(dirname "${LOG_FILE}")"
}

require_cmd() {
    for cmd in "$@"; do
        if ! command -v "${cmd}" &>/dev/null; then
            error "Required command not found: ${cmd}"
            error "Fix: install ${cmd} (e.g., apt install ${cmd})"
            exit 1
        fi
    done
}

# Run a command or print it in dry-run mode
run() {
    if ${DRY_RUN}; then
        echo -e "  ${DIM}[dry-run]${NC} $*"
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# Version management
# ---------------------------------------------------------------------------
init_versions() {
    if [[ ! -f "${VERSIONS_FILE}" ]]; then
        info "Creating initial versions file..."
        mkdir -p "$(dirname "${VERSIONS_FILE}")"
        cat > "${VERSIONS_FILE}" <<'JSON'
{
  "scripts": {
    "version": "0.0.0",
    "updated_at": ""
  },
  "dashboard": {
    "image": "",
    "tag": "latest",
    "digest": "",
    "updated_at": ""
  },
  "backends": {}
}
JSON
    fi
}

get_version() {
    local key="$1"
    if [[ -f "${VERSIONS_FILE}" ]]; then
        _json_get "${VERSIONS_FILE}" "$key"
    else
        echo ""
    fi
}

set_version() {
    local key="$1" value="$2"
    if command -v python3 &>/dev/null; then
        _timeout "$TIMEOUT_PYTHON" python3 -c "
import json
with open('${VERSIONS_FILE}', 'r') as f:
    d = json.load(f)
keys = '${key}'.split('.')
ref = d
for k in keys[:-1]:
    if k not in ref or not isinstance(ref[k], dict):
        ref[k] = {}
    ref = ref[k]
ref[keys[-1]] = '${value}'
with open('${VERSIONS_FILE}', 'w') as f:
    json.dump(d, f, indent=2)
" 2>/dev/null || warn "Failed to update version key: ${key}"
    elif command -v jq &>/dev/null; then
        local jq_key=".${key//./.}"
        local tmp
        tmp=$(mktemp)
        jq "${jq_key} = \"${value}\"" "${VERSIONS_FILE}" > "$tmp" 2>/dev/null && mv "$tmp" "${VERSIONS_FILE}" || {
            rm -f "$tmp"
            warn "Failed to update version key: ${key}"
        }
    else
        warn "Neither python3 nor jq available to update versions"
    fi
}

# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------
get_local_digest() {
    local image="$1"
    _timeout "$TIMEOUT_CHECK" docker inspect --format='{{index .RepoDigests 0}}' "${image}" 2>/dev/null \
        | sed 's/.*@//' || echo ""
}

get_remote_digest() {
    local image="$1"
    if $OFFLINE || ! is_online; then
        echo ""
        return
    fi
    local manifest
    manifest=$(_timeout "$TIMEOUT_CHECK" docker manifest inspect "${image}" 2>/dev/null || echo "")
    if [[ -z "$manifest" ]]; then
        echo ""
        return
    fi
    if command -v python3 &>/dev/null; then
        echo "$manifest" | _timeout "$TIMEOUT_PYTHON" python3 -c "
import json, sys
m = json.load(sys.stdin)
if 'config' in m:
    print(m['config'].get('digest', ''))
elif 'manifests' in m and m['manifests']:
    print(m['manifests'][0].get('digest', ''))
else:
    print('')
" 2>/dev/null || echo ""
    elif command -v jq &>/dev/null; then
        echo "$manifest" | jq -r '.config.digest // (if .manifests and (.manifests | length > 0) then .manifests[0].digest else empty end) // empty' 2>/dev/null || echo ""
    else
        echo ""
    fi
}

get_local_tag() {
    local image="$1"
    _timeout "$TIMEOUT_CHECK" docker inspect --format='{{index .RepoDigests 0}}' "${image}" 2>/dev/null \
        | grep -oP ':\K[0-9a-f]{64}' || echo ""
}

# ---------------------------------------------------------------------------
# Compose helpers
# ---------------------------------------------------------------------------
compose() {
    if [[ -f "${COMPOSE_FILE}" ]]; then
        _timeout "$TIMEOUT_DOCKER_COMPOSE" docker compose -f "${COMPOSE_FILE}" "$@"
    elif [[ -f "${STUDIO_ROOT}/docker-compose.yaml" ]]; then
        _timeout "$TIMEOUT_DOCKER_COMPOSE" docker compose -f "${STUDIO_ROOT}/docker-compose.yaml" "$@"
    else
        error "docker-compose.yml not found at ${COMPOSE_FILE}"
        error "Fix: ensure docker-compose.yml exists in ${STUDIO_ROOT}"
        return 1
    fi
}

get_compose_services() {
    local compose_file="${COMPOSE_FILE}"
    [[ -f "${compose_file}" ]] || compose_file="${STUDIO_ROOT}/docker-compose.yaml"
    if [[ -f "${compose_file}" ]]; then
        if command -v python3 &>/dev/null; then
            _timeout "$TIMEOUT_PYTHON" python3 -c "
import yaml, sys
with open('${compose_file}') as f:
    d = yaml.safe_load(f)
for svc in d.get('services', {}):
    img = d['services'][svc].get('image', '')
    if img:
        print(f'{svc}|{img}')
" 2>/dev/null
        elif command -v jq &>/dev/null; then
            # Convert YAML to JSON first if yq available, else use docker compose
            if command -v yq &>/dev/null; then
                yq -r '.services | to_entries[] | select(.value.image) | "\(.key)|\(.value.image)"' "${compose_file}" 2>/dev/null
            else
                _timeout "$TIMEOUT_DOCKER_COMPOSE" docker compose -f "${compose_file}" config --services 2>/dev/null | while read -r svc; do
                    echo "${svc}|"
                done
            fi
        fi
    fi
}

get_compose_images() {
    local compose_file="${COMPOSE_FILE}"
    [[ -f "${compose_file}" ]] || compose_file="${STUDIO_ROOT}/docker-compose.yaml"
    if [[ -f "${compose_file}" ]]; then
        if command -v python3 &>/dev/null; then
            _timeout "$TIMEOUT_PYTHON" python3 -c "
import yaml, sys
with open('${compose_file}') as f:
    d = yaml.safe_load(f)
imgs = set()
for svc in d.get('services', {}).values():
    img = svc.get('image', '')
    if img:
        imgs.add(img)
for i in sorted(imgs):
    print(i)
" 2>/dev/null
        elif command -v yq &>/dev/null; then
            yq -r '.services[].image // empty' "${compose_file}" 2>/dev/null | sort -u
        fi
    fi
}

# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
backup_configs() {
    header "Backing up configurations"
    local ts; ts="$(date '+%Y%m%d_%H%M%S')"
    local backup_path="${BACKUP_DIR}/backup_${ts}"
    run mkdir -p "${backup_path}"

    if [[ -d "${CONFIG_DIR}" ]]; then
        run cp -a "${CONFIG_DIR}/." "${backup_path}/config/"
        success "Config directory backed up"
    fi

    if [[ -f "${COMPOSE_FILE}" ]]; then
        run cp "${COMPOSE_FILE}" "${backup_path}/docker-compose.yml"
        success "docker-compose.yml backed up"
    elif [[ -f "${STUDIO_ROOT}/docker-compose.yaml" ]]; then
        run cp "${STUDIO_ROOT}/docker-compose.yaml" "${backup_path}/docker-compose.yml"
        success "docker-compose.yaml backed up"
    fi

    if [[ -d "${SCRIPT_DIR}" ]]; then
        run cp -a "${SCRIPT_DIR}/." "${backup_path}/scripts/"
        success "Scripts backed up"
    fi

    echo "${backup_path}" > "${ROLLBACK_DIR}/last_backup"
    success "Backup saved to ${backup_path}"
}

# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------
save_rollback_state() {
    local ts; ts="$(date '+%Y%m%d_%H%M%S')"
    local state_file="${ROLLBACK_DIR}/state_${ts}.json"

    if command -v python3 &>/dev/null; then
        local images_json
        images_json=$(printf '%s\n' "${ROLLBACK_IMAGES[@]}" | _timeout "$TIMEOUT_PYTHON" python3 -c "
import sys, json
imgs = []
for line in sys.stdin:
    line = line.strip()
    if line:
        imgs.append(line)
print(json.dumps(imgs))
" 2>/dev/null || echo '[]')

        _timeout "$TIMEOUT_PYTHON" python3 -c "
import json
images = ${images_json}
state = {'timestamp': '${ts}', 'images': images}
with open('${state_file}', 'w') as f:
    json.dump(state, f, indent=2)
" 2>/dev/null || true
    elif command -v jq &>/dev/null; then
        local images_json="[]"
        for img in "${ROLLBACK_IMAGES[@]}"; do
            if [[ -n "$img" ]]; then
                images_json=$(echo "$images_json" | jq --arg i "$img" '. + [$i]' 2>/dev/null || echo "$images_json")
            fi
        done
        jq -n --arg ts "$ts" --argjson imgs "$images_json" '{timestamp: $ts, images: $imgs}' > "$state_file" 2>/dev/null || true
    fi

    echo "${state_file}" > "${ROLLBACK_DIR}/last_state"
}

cmd_rollback() {
    header "Rollback"
    local state_file="${ROLLBACK_DIR}/last_state"

    if [[ ! -f "${state_file}" ]]; then
        error "No rollback state found"
        error "Fix: run 'studio-update all' first to create a rollback point"
        exit 1
    fi

    local last_state
    last_state="$(cat "${state_file}")"

    if [[ ! -f "${last_state}" ]]; then
        error "Rollback state file missing: ${last_state}"
        error "Fix: the rollback state was deleted. Manual recovery may be needed."
        exit 1
    fi

    info "Rolling back from ${last_state}..."

    # Restore backup
    local backup_path
    backup_path="$(cat "${ROLLBACK_DIR}/last_backup" 2>/dev/null || echo "")"
    if [[ -n "${backup_path}" && -d "${backup_path}" ]]; then
        if [[ -d "${backup_path}/config" ]]; then
            run cp -a "${backup_path}/config/." "${CONFIG_DIR}/"
            success "Config restored"
        fi
        if [[ -f "${backup_path}/docker-compose.yml" ]]; then
            run cp "${backup_path}/docker-compose.yml" "${COMPOSE_FILE}"
            success "docker-compose.yml restored"
        fi
        if [[ -d "${backup_path}/scripts" ]]; then
            run cp -a "${backup_path}/scripts/." "${SCRIPT_DIR}/"
            success "Scripts restored"
        fi
    fi

    # Pull and restart with previous images
    local images=""
    if command -v python3 &>/dev/null; then
        images="$(_timeout "$TIMEOUT_PYTHON" python3 -c "
import json
with open('${last_state}') as f:
    state = json.load(f)
for img in state.get('images', []):
    print(img)
" 2>/dev/null)"
    elif command -v jq &>/dev/null; then
        images="$(jq -r '.images[]? // empty' "${last_state}" 2>/dev/null || echo "")"
    fi

    if [[ -n "${images}" ]]; then
        while IFS= read -r img; do
            if [[ -n "${img}" ]]; then
                info "Restoring image: ${img}"
                run _timeout "$TIMEOUT_PULL" docker pull "${img}" || warn "Failed to pull ${img}"
            fi
        done <<< "${images}"
    fi

    run compose down --timeout 30 || true
    run compose up -d
    sleep 5

    if health_check; then
        success "Rollback completed successfully"
    else
        error "Rollback health check failed - manual intervention required"
        error "Fix: check 'docker compose logs' for errors"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
health_check() {
    header "Health check"
    local all_healthy=true
    local max_attempts=30
    local attempt=0

    local services
    services="$(get_compose_services 2>/dev/null || echo "")"

    if [[ -z "${services}" ]]; then
        warn "No services found in compose file"
        return 0
    fi

    while IFS='|' read -r svc image; do
        [[ -z "${svc}" ]] && continue
        attempt=0
        local healthy=false

        info "Checking ${svc}..."
        while (( attempt < max_attempts )); do
            local status
            local container_id
            container_id="$(compose ps -q "${svc}" 2>/dev/null || echo "")"
            if [[ -n "${container_id}" ]]; then
                status="$(_timeout "$TIMEOUT_CHECK" docker inspect --format='{{.State.Health.Status}}' "${container_id}" 2>/dev/null || echo "none")"
            else
                status="none"
            fi

            if [[ "${status}" == "healthy" ]]; then
                success "${svc} is healthy"
                healthy=true
                break
            elif [[ "${status}" == "none" ]]; then
                # No healthcheck defined, check if running
                local running
                if [[ -n "${container_id}" ]]; then
                    running="$(_timeout "$TIMEOUT_CHECK" docker inspect --format='{{.State.Running}}' "${container_id}" 2>/dev/null || echo "false")"
                else
                    running="false"
                fi
                if [[ "${running}" == "true" ]]; then
                    success "${svc} is running"
                    healthy=true
                    break
                fi
            fi

            (( attempt++ )) || true
            sleep 2
        done

        if ! ${healthy}; then
            error "${svc} failed health check after ${max_attempts} attempts"
            error "Fix: check 'docker compose logs ${svc}' for errors"
            all_healthy=false
        fi
    done <<< "${services}"

    ${all_healthy}
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
cmd_check() {
    header "Checking for updates"
    ensure_dirs
    init_versions

    local updates_available=0

    # Check network first
    if ! is_online; then
        if $OFFLINE; then
            info "Offline mode: skipping remote checks"
        else
            warn "No network connectivity - skipping remote update checks"
            warn "Fix: check network config or use --offline to suppress this warning"
        fi
    fi

    # Check Docker images
    info "Checking Docker images..."
    local images
    images="$(get_compose_images 2>/dev/null || echo "")"

    if [[ -n "${images}" ]]; then
        while IFS= read -r image; do
            [[ -z "${image}" ]] && continue
            local local_dig remote_dig
            local_dig="$(get_local_digest "${image}")"
            remote_dig="$(get_remote_digest "${image}")"

            if [[ -z "${local_dig}" ]]; then
                echo -e "  ${YELLOW}NEW${NC}    ${image} (not pulled yet)"
                (( updates_available++ )) || true
            elif [[ -n "${remote_dig}" && "${local_dig}" != "${remote_dig}" ]]; then
                echo -e "  ${GREEN}UPDATE${NC} ${image}"
                echo -e "         local:  ${DIM}${local_dig:0:24}...${NC}"
                echo -e "         remote: ${DIM}${remote_dig:0:24}...${NC}"
                (( updates_available++ )) || true
            elif $OFFLINE || ! is_online; then
                echo -e "  ${DIM}OK${NC}     ${image} (local only, remote not checked)"
            else
                echo -e "  ${DIM}OK${NC}     ${image}"
            fi
        done <<< "${images}"
    fi

    # Check scripts (if in a git repo) - skip if offline
    if [[ -d "${STUDIO_ROOT}/.git" ]]; then
        if $OFFLINE || ! is_online; then
            info "Skipping git remote check (offline)"
        else
            info "Checking script repository..."
            local local_head remote_head
            local_head="$(cd "${STUDIO_ROOT}" && git rev-parse HEAD 2>/dev/null || echo "")"
            remote_head="$(cd "${STUDIO_ROOT}" && _timeout "$TIMEOUT_GIT" git ls-remote origin HEAD 2>/dev/null | awk '{print $1}' || echo "")"

            if [[ -n "${local_head}" && -n "${remote_head}" && "${local_head}" != "${remote_head}" ]]; then
                echo -e "  ${GREEN}UPDATE${NC} scripts (${local_head:0:8} -> ${remote_head:0:8})"
                (( updates_available++ )) || true
            else
                echo -e "  ${DIM}OK${NC}     scripts (up to date)"
            fi
        fi
    fi

    # Show current versions
    echo ""
    info "Current versions:"
    if [[ -f "${VERSIONS_FILE}" ]]; then
        if command -v python3 &>/dev/null; then
            _timeout "$TIMEOUT_PYTHON" python3 -c "
import json
with open('${VERSIONS_FILE}') as f:
    d = json.load(f)
def show(prefix, obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            show(f'{prefix}.{k}' if prefix else k, v)
    else:
        print(f'  {prefix}: {obj}')
show('', d)
" 2>/dev/null || warn "Could not parse versions file"
        elif command -v jq &>/dev/null; then
            jq -r 'paths(scalars) as $p | getpath($p) | "\( $p | map(tostring) | join(".")): \(.)"' "${VERSIONS_FILE}" 2>/dev/null || warn "Could not parse versions file"
        else
            warn "Neither python3 nor jq available to parse versions"
        fi
    fi

    echo ""
    if (( updates_available > 0 )); then
        echo -e "${BOLD}${GREEN}${updates_available} update(s) available${NC}"
    else
        success "Everything is up to date"
    fi
}

cmd_pull() {
    header "Pulling Docker images"
    ensure_dirs
    init_versions

    if ! is_online && ! $OFFLINE; then
        error "No network connectivity - cannot pull images"
        error "Fix: check network config or use --offline to skip"
        return 1
    fi

    local images
    images="$(get_compose_images 2>/dev/null || echo "")"

    if [[ -z "${images}" ]]; then
        warn "No images found in docker-compose.yml"
        return 0
    fi

    ROLLBACK_IMAGES=()

    while IFS= read -r image; do
        [[ -z "${image}" ]] && continue

        local current_tag
        current_tag="$(_timeout "$TIMEOUT_CHECK" docker inspect --format='{{index .RepoDigests 0}}' "${image}" 2>/dev/null || echo "")"

        if [[ -n "${current_tag}" ]]; then
            ROLLBACK_IMAGES+=("${current_tag}")
        fi

        info "Pulling ${image}..."
        if run _timeout "$TIMEOUT_PULL" docker pull "${image}"; then
            success "Pulled ${image}"
            UPDATED_ITEMS+=("docker:${image}")
        else
            error "Failed to pull ${image}"
            error "Fix: check image name, network, or Docker Hub status"
            FAILED_ITEMS+=("docker:${image}")
        fi
    done <<< "${images}"

    if ! ${DRY_RUN} && (( ${#ROLLBACK_IMAGES[@]} > 0 )); then
        save_rollback_state
    fi
}

cmd_scripts() {
    header "Updating scripts"
    ensure_dirs
    init_versions

    if ! is_online && ! $OFFLINE; then
        error "No network connectivity - cannot update scripts"
        error "Fix: check network config or use --offline to skip"
        return 1
    fi

    if [[ -d "${STUDIO_ROOT}/.git" ]]; then
        local current_rev new_rev
        current_rev="$(cd "${STUDIO_ROOT}" && git rev-parse HEAD 2>/dev/null || echo "unknown")"

        info "Fetching latest changes..."
        if run _timeout "$TIMEOUT_GIT" git -C "${STUDIO_ROOT}" fetch origin; then
            success "Fetched from origin"
        else
            error "Failed to fetch from origin"
            error "Fix: check git remote config and network connectivity"
            FAILED_ITEMS+=("scripts:fetch")
            return 1
        fi

        new_rev="$(cd "${STUDIO_ROOT}" && _timeout "$TIMEOUT_GIT" git rev-parse origin/main 2>/dev/null || \
                   cd "${STUDIO_ROOT}" && _timeout "$TIMEOUT_GIT" git rev-parse origin/master 2>/dev/null || echo "")"

        if [[ -n "${new_rev}" && "${current_rev}" != "${new_rev}" ]]; then
            info "Updating ${current_rev:0:8} -> ${new_rev:0:8}..."
            if run _timeout "$TIMEOUT_GIT" git -C "${STUDIO_ROOT}" merge --ff-only "origin/main" 2>/dev/null || \
               run _timeout "$TIMEOUT_GIT" git -C "${STUDIO_ROOT}" merge --ff-only "origin/master" 2>/dev/null; then
                success "Scripts updated"
                UPDATED_ITEMS+=("scripts:${new_rev:0:8}")
                set_version "scripts.version" "${new_rev:0:8}"
                set_version "scripts.updated_at" "$(date -Iseconds)"
            else
                warn "Could not fast-forward, trying rebase..."
                if run _timeout "$TIMEOUT_GIT" git -C "${STUDIO_ROOT}" pull --rebase; then
                    success "Scripts updated via rebase"
                    UPDATED_ITEMS+=("scripts:rebased")
                else
                    error "Failed to update scripts"
                    error "Fix: resolve git conflicts manually in ${STUDIO_ROOT}"
                    FAILED_ITEMS+=("scripts:update")
                fi
            fi
        else
            success "Scripts already up to date"
        fi
    else
        # Not a git repo - download scripts
        info "Not a git repo - checking for script updates via download..."
        local tmpdir
        tmpdir="$(mktemp -d)"
        trap "rm -rf '${tmpdir}'" RETURN

        if run _timeout "$TIMEOUT_GIT" git clone --depth 1 "${REPO_URL}" "${tmpdir}/studio"; then
            local scripts_updated=false
            for script in "${tmpdir}/studio/scripts/"*.sh; do
                [[ -f "${script}" ]] || continue
                local basename
                basename="$(basename "${script}")"
                if [[ ! -f "${SCRIPT_DIR}/${basename}" ]] || \
                   ! diff -q "${script}" "${SCRIPT_DIR}/${basename}" &>/dev/null; then
                    run cp "${script}" "${SCRIPT_DIR}/${basename}"
                    run chmod +x "${SCRIPT_DIR}/${basename}"
                    scripts_updated=true
                    info "Updated ${basename}"
                fi
            done

            if ${scripts_updated}; then
                success "Scripts updated from repository"
                UPDATED_ITEMS+=("scripts:downloaded")
            else
                success "Scripts already up to date"
            fi
        else
            error "Failed to clone repository"
            error "Fix: check network and REPO_URL (${REPO_URL})"
            FAILED_ITEMS+=("scripts:clone")
        fi
    fi
}

cmd_dashboard() {
    header "Rebuilding dashboard"
    ensure_dirs
    init_versions

    # Save current image for rollback
    local dashboard_image
    dashboard_image="$(get_compose_services 2>/dev/null | grep -i 'dashboard' | cut -d'|' -f2 || echo "")"

    if [[ -n "${dashboard_image}" ]]; then
        local current_digest
        current_digest="$(get_local_digest "${dashboard_image}")"
        if [[ -n "${current_digest}" ]]; then
            ROLLBACK_IMAGES+=("${dashboard_image}@${current_digest}")
        fi
    fi

    info "Building dashboard container..."
    if run compose build --no-cache dashboard 2>/dev/null || \
       run compose build --no-cache frontend 2>/dev/null || \
       run compose build dashboard 2>/dev/null; then
        success "Dashboard image built"
    else
        warn "No dashboard service found or build failed, trying generic rebuild..."
        # Try to find any UI/frontend service
        local ui_service
        ui_service="$(get_compose_services 2>/dev/null | grep -iE 'dashboard|frontend|ui|web' | head -1 | cut -d'|' -f1 || echo "")"
        if [[ -n "${ui_service}" ]]; then
            run compose build "${ui_service}" || {
                error "Failed to build ${ui_service}"
                error "Fix: check Dockerfile and build context for ${ui_service}"
                FAILED_ITEMS+=("dashboard:build")
                return 1
            }
        else
            error "No dashboard/frontend service found"
            error "Fix: add a dashboard or frontend service to docker-compose.yml"
            FAILED_ITEMS+=("dashboard:service")
            return 1
        fi
    fi

    info "Restarting dashboard service..."
    local dash_svc
    dash_svc="$(get_compose_services 2>/dev/null | grep -iE 'dashboard|frontend|ui|web' | head -1 | cut -d'|' -f1 || echo "")"
    if [[ -n "${dash_svc}" ]]; then
        run compose up -d --no-deps "${dash_svc}"
        UPDATED_ITEMS+=("dashboard:${dash_svc}")
        set_version "dashboard.updated_at" "$(date -Iseconds)"
    fi

    if ! ${DRY_RUN}; then
        save_rollback_state
    fi
}

cmd_restart_rolling() {
    local services
    services="$(get_compose_services 2>/dev/null || echo "")"

    if [[ -z "${services}" ]]; then
        warn "No services found"
        return 0
    fi

    while IFS='|' read -r svc image; do
        [[ -z "${svc}" ]] && continue
        info "Restarting ${svc}..."
        run compose up -d --no-deps "${svc}"
        sleep 3

        # Wait for this service to be healthy before continuing
        local attempts=0
        while (( attempts < 20 )); do
            local running
            local container_id
            container_id="$(compose ps -q "${svc}" 2>/dev/null || echo "")"
            if [[ -n "${container_id}" ]]; then
                running="$(_timeout "$TIMEOUT_CHECK" docker inspect --format='{{.State.Running}}' "${container_id}" 2>/dev/null || echo "false")"
            else
                running="false"
            fi
            if [[ "${running}" == "true" ]]; then
                success "${svc} is running"
                break
            fi
            (( attempts++ )) || true
            sleep 2
        done
    done <<< "${services}"
}

cmd_all() {
    header "Full update"
    ensure_dirs
    init_versions

    if ! is_online && ! $OFFLINE; then
        error "No network connectivity detected"
        error "Fix: check network or use --offline for local-only operations"
        exit 1
    fi

    backup_configs

    # 1. Pull images first (safe: doesn't affect running containers)
    info "Phase 1: Pulling images..."
    cmd_pull

    # 2. Update scripts
    info "Phase 2: Updating scripts..."
    cmd_scripts

    # 3. Rolling restart
    info "Phase 3: Rolling restart..."
    if ! ${DRY_RUN}; then
        cmd_restart_rolling
    else
        echo -e "  ${DIM}[dry-run]${NC} Would perform rolling restart"
    fi

    # 4. Health check
    if ! ${DRY_RUN}; then
        if health_check; then
            success "All services healthy after update"
        else
            error "Some services unhealthy after update!"
            error "Fix: run 'studio-update rollback' to revert changes"
            exit 1
        fi
    fi

    print_summary
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print_summary() {
    header "Update Summary"

    if (( ${#UPDATED_ITEMS[@]} > 0 )); then
        echo -e "${GREEN}Updated items:${NC}"
        for item in "${UPDATED_ITEMS[@]}"; do
            echo -e "  ${GREEN}✓${NC} ${item}"
        done
    else
        echo -e "${DIM}No items were updated${NC}"
    fi

    if (( ${#FAILED_ITEMS[@]} > 0 )); then
        echo -e "\n${RED}Failed items:${NC}"
        for item in "${FAILED_ITEMS[@]}"; do
            echo -e "  ${RED}✗${NC} ${item}"
        done
    fi

    echo ""
    info "Update completed at $(date '+%Y-%m-%d %H:%M:%S')"
    info "Log file: ${LOG_FILE}"

    if (( ${#ROLLBACK_IMAGES[@]} > 0 )); then
        info "Rollback available: studio-update rollback"
    fi
}

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
${BOLD}AI Creative Studio Update Manager${NC}

${CYAN}Usage:${NC}
  studio-update <command> [options]

${CYAN}Commands:${NC}
  check           Check what can be updated (Docker images, scripts, configs)
  pull            Pull latest Docker images for configured backends
  scripts         Update scripts from repository
  dashboard       Rebuild dashboard container
  all             Update everything (images, scripts, rolling restart)
  rollback        Rollback to previous versions
  status          Show current versions

${CYAN}Options:${NC}
  --dry-run       Show what would be updated without making changes
  --offline       Skip network-dependent checks (remote digest, git fetch)
  --timeout N     Override default timeouts in seconds (default: check=5, pull=60, compose=10)
  --help, -h      Show this help message

${CYAN}Examples:${NC}
  studio-update check                  # See what needs updating
  studio-update --dry-run all          # Preview full update
  studio-update pull                   # Pull latest Docker images
  studio-update all                    # Full update with health checks
  studio-update rollback              # Revert to previous state
  studio-update --offline check       # Check local state without network

EOF
}

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
cmd_status() {
    header "Current Status"
    ensure_dirs
    init_versions

    info "Versions file: ${VERSIONS_FILE}"
    if [[ -f "${VERSIONS_FILE}" ]]; then
        if command -v python3 &>/dev/null; then
            _timeout "$TIMEOUT_PYTHON" python3 -c "
import json
with open('${VERSIONS_FILE}') as f:
    d = json.load(f)
def show(prefix, obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            show(f'{prefix}.{k}' if prefix else k, v)
    else:
        print(f'  {prefix}: {obj}')
show('', d)
" 2>/dev/null || warn "Could not parse versions"
        elif command -v jq &>/dev/null; then
            jq -r 'paths(scalars) as $p | getpath($p) | "\( $p | map(tostring) | join(".")): \(.)"' "${VERSIONS_FILE}" 2>/dev/null || warn "Could not parse versions"
        else
            warn "Neither python3 nor jq available to parse versions"
            warn "Fix: install python3 or jq"
        fi
    fi

    echo ""
    info "Running containers:"
    compose ps 2>/dev/null || warn "Could not list containers (Docker may not be running)"

    echo ""
    info "Rollback state:"
    if [[ -f "${ROLLBACK_DIR}/last_state" ]]; then
        echo "  Last state: $(cat "${ROLLBACK_DIR}/last_state")"
    else
        echo "  No rollback state available"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    require_cmd docker

    local command=""
    while (( $# > 0 )); do
        case "$1" in
            --dry-run|-n)
                DRY_RUN=true
                shift
                ;;
            --offline)
                OFFLINE=true
                shift
                ;;
            --timeout)
                if [[ -n "${2:-}" ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
                    TIMEOUT_CHECK="$2"
                    TIMEOUT_PULL="$2"
                    TIMEOUT_DOCKER_COMPOSE="$2"
                    TIMEOUT_PYTHON="$2"
                    TIMEOUT_HEALTH="$2"
                    TIMEOUT_GIT="$2"
                    shift 2
                else
                    error "--timeout requires a numeric argument (seconds)"
                    exit 1
                fi
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            -*)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                command="$1"
                shift
                ;;
        esac
    done

    if ${DRY_RUN}; then
        echo -e "${YELLOW}${BOLD}DRY RUN MODE - No changes will be made${NC}\n"
    fi

    if $OFFLINE; then
        echo -e "${DIM}Offline mode: network checks skipped${NC}\n"
    fi

    case "${command}" in
        check)
            cmd_check
            ;;
        pull)
            cmd_pull
            ;;
        scripts)
            cmd_scripts
            ;;
        dashboard)
            cmd_dashboard
            ;;
        all)
            cmd_all
            ;;
        rollback)
            cmd_rollback
            ;;
        status)
            cmd_status
            ;;
        "")
            error "No command specified"
            usage
            exit 1
            ;;
        *)
            error "Unknown command: ${command}"
            usage
            exit 1
            ;;
    esac

    # Print summary for update operations
    if [[ "${command}" != "check" && "${command}" != "status" ]]; then
        print_summary
    fi
}

main "$@"
