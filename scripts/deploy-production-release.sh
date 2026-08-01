#!/usr/bin/env bash
# deploy-production-release.sh
#
# Automates production deployment of Castle Celestial View releases.
# Downloads a GitHub Release, stops the API and frontend services,
# installs the updated artifacts, then restarts the services.
#
# Usage: ./scripts/deploy-production-release.sh <tag> [options]
# See --help for full details.
#
# IMPORTANT: This script requires systemd services to be configured.
# You must customize SERVICE_API and SERVICE_FE to match your setup.

set -euo pipefail

# ─── Configuration (customize for your deployment) ──────────────────────────
# Systemd service names — UPDATE THESE to match your server setup
SERVICE_API="castle-celestial-api"      # systemd service name for gunicorn (e.g., castle-celestial-api)

# Installation directories — UPDATE THESE to match your server paths
DEPLOY_USER="deployuser"                # User who owns the API and frontend files
API_VENV_DIR="/home/$DEPLOY_USER/venv"  # Python venv with gunicorn and dependencies
FE_INSTALL_DIR="/home/$DEPLOY_USER/dist" # Frontend static files directory

# Nginx configuration (frontend is served as static files by nginx)
NGINX_RELOAD=true                       # Reload nginx after updating frontend files

# ─── Constants ────────────────────────────────────────────────────────────────
REPO="JECastle4/Castle-Celestial-View"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── Defaults ─────────────────────────────────────────────────────────────────
TAG=""
DRY_RUN=false
SKIP_BACKUP=false
VERBOSE=false

# State (set during execution; used by cleanup trap)
WORK_DIR=""
WHL_FILENAME=""
BACKUP_DIR=""

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}!${NC} $*"; }
err()   { echo -e "  ${RED}✗${NC} $*" >&2; }
step()  { echo -e "\n${BOLD}── $* ──${NC}"; }
debug() { if [[ "$VERBOSE" == "true" ]]; then echo -e "  ${BLUE}◇${NC} $*"; fi; }

# ─── Help ─────────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF

${BOLD}Castle Celestial View — Production Deployment${NC}

Downloads a GitHub Release and deploys it to the production server.
Automatically stops services, installs artifacts, and restarts services.

Designed for setup: gunicorn (API) via systemd, static frontend files, nginx proxy.

${BOLD}Usage:${NC}
  sudo $0 <tag> [options]

${BOLD}Arguments:${NC}
  <tag>               Git tag to deploy, e.g. v1.1.0.3

${BOLD}Options:${NC}
  --dry-run           Show what would be done, but don't actually do it
  --skip-backup       Skip creating a backup of the current installation
  --verbose           Enable verbose output
  --help, -h          Show this help message

${BOLD}Environment variables:${NC}
  GITHUB_TOKEN        GitHub personal access token (optional for public repos)

${BOLD}Prerequisites:${NC}
  • Must run with sudo (requires root privileges)
  • systemd (for service management)
  • curl                System utility for downloading
  • unzip               For extracting archives
  • Configured systemd service:
      - $SERVICE_API (gunicorn service)
      - nginx (for serving frontend, must be installed)

${BOLD}Configuration:${NC}
  Edit this script to customize:
    SERVICE_API       (currently: $SERVICE_API)
    DEPLOY_USER       (currently: $DEPLOY_USER)
    API_VENV_DIR      (currently: $API_VENV_DIR)
    FE_INSTALL_DIR    (currently: $FE_INSTALL_DIR)
    NGINX_RELOAD      (currently: $NGINX_RELOAD)

${BOLD}Setup required (option B):${NC}
  1. Create systemd service for gunicorn at: /etc/systemd/system/$SERVICE_API.service
     See DEPLOYMENT_GUIDE.md for template
  2. Enable the service: sudo systemctl daemon-reload && sudo systemctl enable $SERVICE_API
  3. Start the service: sudo systemctl start $SERVICE_API
  4. Verify: sudo systemctl status $SERVICE_API

${BOLD}Examples:${NC}
  # Deploy a release (dry-run first to verify)
  sudo $0 v1.1.0.3 --dry-run
  sudo $0 v1.1.0.3

  # Deploy without creating backup
  sudo $0 v1.1.0.3 --skip-backup

  # Deploy with verbose output
  sudo $0 v1.1.0.3 --verbose

${BOLD}Typical workflow:${NC}
  1. Verify release locally:                ./scripts/verify-production-release.sh v1.1.0.3
  2. Deploy to production (dry-run):        sudo ./scripts/deploy-production-release.sh v1.1.0.3 --dry-run
  3. Review the output carefully
  4. Deploy for real:                       sudo ./scripts/deploy-production-release.sh v1.1.0.3
  5. Verify the app is working:             curl https://castlecelestialview.net/api/health
  6. Apply system updates (if not done):    sudo apt update && sudo apt upgrade
  7. Reboot server (if needed):             sudo reboot

EOF
  exit 0
}

# ─── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)          usage ;;
    --dry-run)          DRY_RUN=true ;;
    --skip-backup)      SKIP_BACKUP=true ;;
    --verbose)          VERBOSE=true ;;
    v[0-9]*.[0-9]*)     TAG="$1" ;;
    *)
      err "Unknown argument: $1"
      echo "Run '$0 --help' for usage."
      exit 1
      ;;
  esac
  shift
done

if [[ -z "$TAG" ]]; then
  err "A tag argument is required (e.g. v1.1.0.3)"
  echo "Run '$0 --help' for usage."
  exit 1
fi

# ─── Privileges check ─────────────────────────────────────────────────────────
check_privileges() {
  if [[ $EUID -ne 0 ]]; then
    err "This script must be run with sudo"
    exit 1
  fi
}

# ─── Cleanup (runs on EXIT regardless of success/failure) ─────────────────────
cleanup() {
  local exit_code=$?

  step "Cleaning up"

  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    debug "Removing temp directory $WORK_DIR"
    rm -rf "$WORK_DIR"
  fi

  echo ""
  if [[ "$exit_code" -eq 0 ]]; then
    if [[ "$DRY_RUN" == "true" ]]; then
      echo -e "${BLUE}${BOLD}◇ Dry-run completed successfully for $TAG${NC}"
    else
      echo -e "${GREEN}${BOLD}✓ Deployment COMPLETED successfully for $TAG${NC}"
      if [[ -n "$BACKUP_DIR" ]]; then
        echo -e "  Backup of previous version: ${BOLD}$BACKUP_DIR${NC}"
      fi
    fi
  else
    echo -e "${RED}${BOLD}✗ Deployment FAILED for $TAG (exit code $exit_code)${NC}"
    if [[ -n "$BACKUP_DIR" ]]; then
      warn "Backup available at: $BACKUP_DIR"
    fi
  fi
  echo ""

  exit "$exit_code"
}

trap cleanup EXIT

# ─── Prerequisites ────────────────────────────────────────────────────────────
check_prerequisites() {
  step "Checking prerequisites"

  local missing=0

  for cmd in curl unzip python3 systemctl; do
    if command -v "$cmd" &>/dev/null; then
      info "$cmd  →  $(command -v "$cmd")"
    else
      err "$cmd not found — install it and try again"
      missing=1
    fi
  done

  # Verify services exist using systemctl status (more reliable)
  if ! sudo systemctl status "$SERVICE_API" &>/dev/null; then
    err "Systemd service not found or not accessible: $SERVICE_API"
    err "Try: sudo systemctl status $SERVICE_API"
    missing=1
  else
    info "Systemd service found: $SERVICE_API"
  fi

  # Verify nginx exists
  if ! sudo systemctl status nginx &>/dev/null; then
    err "Systemd service not found or not accessible: nginx"
    err "Try: sudo systemctl status nginx"
    missing=1
  else
    info "Systemd service found: nginx"
  fi

  # Verify venv and installation directories exist
  if [[ ! -d "$API_VENV_DIR" ]]; then
    err "API venv directory does not exist: $API_VENV_DIR"
    missing=1
  else
    info "API venv found: $API_VENV_DIR"
  fi

  if [[ ! -d "$FE_INSTALL_DIR" ]]; then
    err "Frontend directory does not exist: $FE_INSTALL_DIR"
    missing=1
  else
    info "Frontend directory found: $FE_INSTALL_DIR"
  fi

  if [[ "$missing" -ne 0 ]]; then
    err "One or more prerequisites are missing. Aborting."
    err ""
    err "To set up systemd services, see the deployment documentation."
    exit 1
  fi
}

# ─── Display configuration ────────────────────────────────────────────────────
display_config() {
  step "Deployment configuration"
  info "Repository:       $REPO"
  info "Release tag:      $TAG"
  info "API service:      $SERVICE_API"
  info "API venv:         $API_VENV_DIR"
  info "Frontend dir:     $FE_INSTALL_DIR"
  info "Nginx frontend:   $NGINX_RELOAD (reload after update)"
  if [[ "$DRY_RUN" == "true" ]]; then
    info "Mode:             ${YELLOW}DRY-RUN (no changes will be made)${NC}"
  fi
  if [[ "$SKIP_BACKUP" == "false" ]]; then
    info "Backup:           Enabled"
  else
    info "Backup:           ${YELLOW}Disabled${NC}"
  fi
}

# ─── Download release artifacts ───────────────────────────────────────────────
download_artifacts() {
  step "Downloading release artifacts for $TAG"

  WORK_DIR=$(mktemp -d)
  info "Working directory: $WORK_DIR"

  # Build auth header
  local api_auth=()
  local asset_auth=()
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    api_auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
    asset_auth=(-H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/octet-stream")
    info "Using GITHUB_TOKEN for authenticated requests"
  else
    warn "GITHUB_TOKEN not set — unauthenticated (60 req/hr rate limit)"
  fi

  # Fetch release metadata
  local release_api_url="https://api.github.com/repos/$REPO/releases/tags/$TAG"
  debug "Fetching: $release_api_url"
  local release_json
  if ! release_json=$(curl -fsSL "${api_auth[@]}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$release_api_url" 2>&1); then
    err "GitHub API returned an error fetching release $TAG."
    exit 1
  fi

  # Extract asset URLs
  local wheel_url fe_zip_url
  wheel_url=$(echo "$release_json" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(next((a['browser_download_url'] for a in d['assets'] if a['name'].endswith('.whl')), ''))")
  fe_zip_url=$(echo "$release_json" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(next((a['browser_download_url'] for a in d['assets'] if '-frontend-' in a['name']), ''))")

  if [[ -z "$wheel_url" ]]; then
    err "No .whl asset found in release $TAG"
    exit 1
  fi
  if [[ -z "$fe_zip_url" ]]; then
    err "No frontend zip asset found in release $TAG"
    exit 1
  fi

  info "Wheel URL:    $wheel_url"
  info "Frontend URL: $fe_zip_url"

  # Download artifacts
  info "Downloading wheel..."
  WHL_FILENAME=$(basename "$wheel_url")
  curl -fsSL "${asset_auth[@]}" -o "$WORK_DIR/$WHL_FILENAME" "$wheel_url"

  info "Downloading frontend zip..."
  curl -fsSL "${asset_auth[@]}" -o "$WORK_DIR/frontend.zip" "$fe_zip_url"

  # Verify files are non-empty
  local whl_bytes fe_bytes
  whl_bytes=$(wc -c < "$WORK_DIR/$WHL_FILENAME" | tr -d ' ')
  fe_bytes=$(wc -c < "$WORK_DIR/frontend.zip" | tr -d ' ')

  if [[ "$whl_bytes" -eq 0 ]]; then
    err "$WHL_FILENAME downloaded as empty file"
    exit 1
  fi
  if [[ "$fe_bytes" -eq 0 ]]; then
    err "frontend.zip downloaded as empty file"
    exit 1
  fi

  info "Wheel size:       ${whl_bytes} bytes ($WHL_FILENAME)"
  info "Frontend size:    ${fe_bytes} bytes"

  # Extract frontend
  mkdir -p "$WORK_DIR/fe"
  unzip -q "$WORK_DIR/frontend.zip" -d "$WORK_DIR/fe"

  if [[ ! -d "$WORK_DIR/fe/dist" ]]; then
    err "Expected a dist/ directory at the root of the frontend zip"
    exit 1
  fi

  info "Frontend extracted to $WORK_DIR/fe/dist/"
}

# ─── Execute a command (or dry-run it) ────────────────────────────────────────
run_command() {
  local description="$1"
  shift
  local cmd=("$@")

  debug "Command: ${cmd[*]}"

  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY-RUN] $description"
    echo "  would run: ${cmd[*]}"
  else
    info "$description"
    "${cmd[@]}"
  fi
}

# ─── Backup current installation ──────────────────────────────────────────────
backup_installation() {
  if [[ "$SKIP_BACKUP" == "true" ]]; then
    warn "Skipping backup (--skip-backup specified)"
    return 0
  fi

  step "Backing up current installation"

  local timestamp
  timestamp=$(date +%Y%m%d-%H%M%S)
  local deploy_home="/home/$DEPLOY_USER"
  BACKUP_DIR="$deploy_home/backups/backup-$TAG-$timestamp"

  run_command "Creating backup directory" mkdir -p "$BACKUP_DIR"
  run_command "Backing up API venv packages" \
    bash -c "pip list > '$BACKUP_DIR/pip-list.txt'" || true
  run_command "Backing up frontend dist" cp -r "$FE_INSTALL_DIR" "$BACKUP_DIR/dist" || true
  run_command "Creating backup metadata" \
    bash -c "echo 'Backed up from: $TAG at $(date)' > '$BACKUP_DIR/BACKUP_INFO.txt'"

  if [[ "$DRY_RUN" != "true" ]]; then
    info "Backup created: $BACKUP_DIR"
  fi
}

# ─── Stop services ────────────────────────────────────────────────────────────
stop_services() {
  step "Stopping services"

  run_command "Stopping $SERVICE_API" \
    systemctl stop "$SERVICE_API"

  if [[ "$DRY_RUN" != "true" ]]; then
    # Give service time to shut down gracefully
    sleep 2
    info "$SERVICE_API stopped"
  fi
}

# ─── Install API wheel ─────────────────────────────────────────────────────────
install_api() {
  step "Installing API wheel"

  local pip_cmd="$API_VENV_DIR/bin/pip"

  # Ensure pip is available
  if [[ ! -f "$pip_cmd" ]]; then
    err "pip not found at $pip_cmd"
    exit 1
  fi

  run_command "Installing/upgrading $WHL_FILENAME" \
    "$pip_cmd" install --upgrade --force-reinstall \
    "$WORK_DIR/$WHL_FILENAME"

  debug "API installation completed (or would be in dry-run)"
}

# ─── Install frontend ──────────────────────────────────────────────────────────
install_frontend() {
  step "Installing frontend distribution"

  run_command "Removing old frontend" \
    rm -rf "$FE_INSTALL_DIR"

  run_command "Creating frontend directory" \
    mkdir -p "$FE_INSTALL_DIR"

  run_command "Extracting new frontend" \
    cp -r "$WORK_DIR/fe/dist"/* "$FE_INSTALL_DIR/"

  debug "Frontend installation completed (or would be in dry-run)"
}

# ─── Start services ───────────────────────────────────────────────────────────
start_services() {
  step "Starting services"

  run_command "Starting $SERVICE_API" \
    systemctl start "$SERVICE_API"

  if [[ "$NGINX_RELOAD" == "true" ]]; then
    run_command "Reloading nginx (frontend updated)" \
      systemctl reload nginx
  fi

  if [[ "$DRY_RUN" != "true" ]]; then
    sleep 2
    info "Services started"

    # Check if API service is running
    if systemctl is-active --quiet "$SERVICE_API"; then
      info "$SERVICE_API is running"
    else
      err "$SERVICE_API failed to start (check logs with: systemctl status $SERVICE_API)"
      exit 1
    fi

    if [[ "$NGINX_RELOAD" == "true" ]]; then
      if systemctl is-active --quiet nginx; then
        info "nginx is running"
      else
        err "nginx failed to start (check logs with: systemctl status nginx)"
        exit 1
      fi
    fi
  fi
}

# ─── Main deployment flow ─────────────────────────────────────────────────────
main() {
  step "Castle Celestial View Production Deployment"
  check_privileges
  check_prerequisites
  display_config
  download_artifacts
  backup_installation
  stop_services
  install_api
  install_frontend
  start_services

  step "Post-deployment verification"
  if [[ "$DRY_RUN" != "true" ]]; then
    info "You can verify the deployment with:"
    echo "    curl http://localhost:8000/api/health"
    echo "    systemctl status $SERVICE_API"
    echo "    systemctl status nginx"
    echo ""
    info "To check service logs:"
    echo "    journalctl -u $SERVICE_API -n 50"
    echo "    journalctl -u nginx -n 50"
  fi
}

main "$@"
