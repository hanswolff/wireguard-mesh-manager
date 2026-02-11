#!/usr/bin/env bash
set -euo pipefail

# This script is destructive. It will stop all containers, delete the SQLite database,
# optionally restore from a provided backup, restart containers, and rotate the master password.

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly DATA_FILE="$PROJECT_ROOT/backend/data/wireguard.db"
readonly LEGACY_DATA_FILE="$PROJECT_ROOT/backend/data/database.sqlite"
readonly DEFAULT_API_URL="http://localhost:8000"
readonly DEFAULT_BOOTSTRAP_TOKEN="change-me-secure-bootstrap-token"
readonly DOCKER_COMPOSE_BIN="${DOCKER_COMPOSE:-docker compose}"

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat <<'USAGE'
Usage: scripts/new-database-with-master-password.sh [--new-password <password>] [--bootstrap-token <token>] [--backup-path <path>] [--api-url <url>] [--yes]

Options:
  --new-password, -p   New master password to set after recreation (optional, will prompt if not provided)
  --bootstrap-token    Bootstrap token for initial unlock (optional, must match backend BOOTSTRAP_TOKEN env var)
                       Required if bootstrap_token is configured in backend
  --backup-path, -b    Path to an existing backup file to restore before rotation (optional)
  --api-url            Base URL for the backend API (default: http://localhost:8000)
  --yes, -y            Skip confirmation prompt (DANGEROUS)
  --help, -h           Show this help message

This script WILL stop containers, delete the SQLite database at backend/data/wireguard.db,
optionally restore a backup, restart services, and rotate the master password directly inside the backend container.
It exits non-zero on any failure.
USAGE
}

require_command() {
    local cmd="$1"
    # Handle multi-word commands like "docker compose"
    local first_word="${cmd%% *}"

    if ! command -v "$first_word" >/dev/null 2>&1; then
        log_error "Required command '$first_word' not found in PATH"
        exit 1
    fi

    # For docker compose, verify the subcommand works
    if [[ "$cmd" == *"docker compose"* ]]; then
        if ! $cmd version >/dev/null 2>&1; then
            log_error "Required command '$cmd' failed to execute (docker compose plugin not available)"
            exit 1
        fi
    fi
}

wait_for_backend() {
    local api_url="$1"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for backend to become available at ${api_url}/api/health"
    until curl -sSf "${api_url}/api/health" >/dev/null 2>&1; do
        if [[ $attempt -ge $max_attempts ]]; then
            log_error "Backend did not become ready after ${max_attempts} attempts"
            exit 1
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
}

confirm_destruction() {
    if [[ "$SKIP_CONFIRM" == "true" ]]; then
        return
    fi

    echo
    log_warn "This operation is DESTRUCTIVE and will delete the existing SQLite database."
    read -r -p "Type 'delete' to proceed: " response
    if [[ "$response" != "delete" ]]; then
        log_error "Confirmation failed; aborting."
        exit 1
    fi
}

NEW_MASTER_PASSWORD=""
BOOTSTRAP_TOKEN=""
BACKUP_PATH=""
API_URL="$DEFAULT_API_URL"
SKIP_CONFIRM="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --new-password|-p)
            NEW_MASTER_PASSWORD="$2"
            shift 2
            ;;
        --bootstrap-token)
            BOOTSTRAP_TOKEN="$2"
            shift 2
            ;;
        --backup-path|-b)
            BACKUP_PATH="$2"
            shift 2
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --yes|-y)
            SKIP_CONFIRM="true"
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$NEW_MASTER_PASSWORD" ]]; then
    # Prompt for password if not provided
    while true; do
        read -s -r -p "Enter new master password: " NEW_MASTER_PASSWORD
        echo
        if [[ -z "$NEW_MASTER_PASSWORD" ]]; then
            log_error "Password cannot be empty"
            continue
        fi
        if [[ ${#NEW_MASTER_PASSWORD} -lt 8 ]]; then
            log_error "Password must be at least 8 characters long"
            continue
        fi
        read -s -r -p "Confirm new master password: " PASSWORD_CONFIRM
        echo
        if [[ "$NEW_MASTER_PASSWORD" != "$PASSWORD_CONFIRM" ]]; then
            log_error "Passwords do not match"
            continue
        fi
        break
    done
    unset PASSWORD_CONFIRM
fi

if [[ -n "$BACKUP_PATH" && ! -f "$BACKUP_PATH" ]]; then
    log_error "Backup file not found at: $BACKUP_PATH"
    exit 1
fi

require_command "$DOCKER_COMPOSE_BIN"
require_command curl
require_command python3

confirm_destruction

cd "$PROJECT_ROOT"

log_info "Stopping containers via $DOCKER_COMPOSE_BIN down"
$DOCKER_COMPOSE_BIN down

log_warn "Deleting SQLite database at $DATA_FILE"
rm -f "$DATA_FILE"
if [[ -f "$LEGACY_DATA_FILE" ]]; then
    log_warn "Deleting legacy SQLite database at $LEGACY_DATA_FILE"
    rm -f "$LEGACY_DATA_FILE"
fi

log_info "Starting containers for master password bootstrap"
$DOCKER_COMPOSE_BIN up -d

wait_for_backend "$API_URL"

log_info "Step 1: Fetching CSRF token"
CSRF_COOKIE_JAR="$(mktemp)"
trap 'rm -f "$CSRF_COOKIE_JAR"' EXIT
curl -sSf -c "$CSRF_COOKIE_JAR" "${API_URL}/api/csrf/token" >/dev/null
CSRF_TOKEN="$(awk '$6 == "csrf_token" {print $7}' "$CSRF_COOKIE_JAR" | tail -n 1)"
if [[ -z "$CSRF_TOKEN" ]]; then
    log_error "Failed to retrieve CSRF token"
    exit 1
fi

log_info "Step 2: Running database migrations"
$DOCKER_COMPOSE_BIN exec -T backend alembic upgrade head

log_info "Step 3: Unlocking master password (bootstrap session)"
MASTER_UNLOCK_PAYLOAD=$(NEW_MASTER_PASSWORD="$NEW_MASTER_PASSWORD" BOOTSTRAP_TOKEN="$BOOTSTRAP_TOKEN" python3 - <<'PY'
import json
import os

payload = {"master_password": os.environ["NEW_MASTER_PASSWORD"]}
if os.environ.get("BOOTSTRAP_TOKEN"):
    payload["bootstrap_token"] = os.environ["BOOTSTRAP_TOKEN"]
print(json.dumps(payload))
PY
)
UNLOCK_RESPONSE=$(curl -sSf -X POST \
    -H "Content-Type: application/json" \
    -H "X-CSRF-Token: $CSRF_TOKEN" \
    -H "Origin: http://localhost:3000" \
    -b "$CSRF_COOKIE_JAR" \
    -d "$MASTER_UNLOCK_PAYLOAD" \
    "${API_URL}/api/master-password/unlock")

SESSION_TOKEN=$(echo "$UNLOCK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_token', ''))")
if [[ -z "$SESSION_TOKEN" ]]; then
    log_error "Failed to extract master session token from unlock response"
    log_error "Response: $UNLOCK_RESPONSE"
    exit 1
fi

if [[ -n "$BACKUP_PATH" ]]; then
    log_info "Step 4: Restoring backup from $BACKUP_PATH"
    curl -sSf -X POST \
        -H "Content-Type: multipart/form-data" \
        -H "Authorization: Master $SESSION_TOKEN" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -H "Origin: http://localhost:3000" \
        -b "$CSRF_COOKIE_JAR" \
        -F "file=@${BACKUP_PATH}" \
        "${API_URL}/backup/upload" >/dev/null

    log_info "Step 5: Re-unlocking master password after restore"
    UNLOCK_RESPONSE=$(curl -sSf -X POST \
        -H "Content-Type: application/json" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -H "Origin: http://localhost:3000" \
        -b "$CSRF_COOKIE_JAR" \
        -d "$MASTER_UNLOCK_PAYLOAD" \
        "${API_URL}/api/master-password/unlock")
    SESSION_TOKEN=$(echo "$UNLOCK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_token', ''))")
    if [[ -z "$SESSION_TOKEN" ]]; then
        log_error "Failed to extract master session token after restore"
        log_error "Response: $UNLOCK_RESPONSE"
        exit 1
    fi
fi

log_info "Initial setup completed successfully!"
log_info "Master password set (cached in memory)"
