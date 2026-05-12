#!/usr/bin/env bash
# verify-production-release.sh
#
# Downloads a Castle Celestial View GitHub Release, deploys the API wheel and
# frontend distribution locally, then runs all Playwright E2E tests against
# the production deployment to verify the release artifacts work end-to-end.
#
# Usage: ./scripts/verify-production-release.sh <tag> [--api-port <port>] [--fe-port <port>]
# See --help for full details.

set -euo pipefail

# ─── Constants ────────────────────────────────────────────────────────────────
REPO="JECastle4/Castle-Celestial-View"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── Defaults ─────────────────────────────────────────────────────────────────
TAG=""
API_PORT=8000
FE_PORT=4173          # matches vite preview port in vite.config.ts

# State (set during execution; used by cleanup trap)
WORK_DIR=""
WHL_FILENAME=""  # set in download_artifacts, used in start_api
VENV_PYTHON=""
API_PID=""
FE_PID=""

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}!${NC} $*"; }
err()   { echo -e "  ${RED}✗${NC} $*" >&2; }
step()  { echo -e "\n${BOLD}── $* ──${NC}"; }

# Returns 0 if something is already listening on the given TCP port.
# Uses the first available method: nc -z, lsof, or bash /dev/tcp.
# Does NOT use curl so that any HTTP response code (4xx, 5xx, …) is still
# treated as "port occupied" — the curl -f flag would silently ignore those.
port_in_use() {
  local port="$1"
  if command -v nc &>/dev/null; then
    nc -z localhost "$port" &>/dev/null
  elif command -v lsof &>/dev/null; then
    lsof -ti ":$port" &>/dev/null
  else
    # bash built-in /dev/tcp: succeeds when the TCP handshake completes
    (echo > "/dev/tcp/localhost/$port") &>/dev/null
  fi
}

# ─── Help ─────────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF

${BOLD}Castle Celestial View — Production Release Verification${NC}

Downloads the GitHub Release for a given tag, deploys the API wheel and
frontend dist locally (using the same proxy setup as production), then runs
all Playwright E2E tests to confirm the release artifacts work end-to-end.

${BOLD}Usage:${NC}
  $0 <tag> [options]

${BOLD}Arguments:${NC}
  <tag>               Git tag to verify, e.g. v1.0.0

${BOLD}Options:${NC}
  --api-port <port>   API server port (default: 8000)
  --fe-port <port>    Frontend server port (default: 4173)
  --help, -h          Show this help message

${BOLD}Environment variables:${NC}
  GITHUB_TOKEN        GitHub personal access token.
                      Required for private repositories.
                      Optional for public repositories (avoids rate limiting).

${BOLD}Prerequisites:${NC}
  curl, unzip        System utilities (both included in Git Bash on Windows)
  python3 >=3.11     Python interpreter (3.14 preferred — matches the wheel)
                     Used for JSON parsing (no jq required)
  node >=20          Node.js runtime
  npm                Node package manager
  frontend/node_modules must exist — run 'npm ci' in frontend/ first
  Playwright browsers must be installed — run 'npx playwright install' in frontend/

${BOLD}Examples:${NC}
  # Basic verification
  $0 v1.0.0

  # With custom ports (if defaults are already occupied)
  $0 v1.0.0 --api-port 9000 --fe-port 9100

  # With GitHub token (avoids rate limits / required for private repos)
  GITHUB_TOKEN=ghp_xxxx $0 v1.0.0

${BOLD}Docker (recommended for consistent Linux snapshots):${NC}
  docker build -f Dockerfile.playwright -t ccv-verify .
  docker run --rm \\
    -e GITHUB_TOKEN=\$GITHUB_TOKEN \\
    ccv-verify \\
    ./scripts/verify-production-release.sh v1.0.0

EOF
  exit 0
}

# ─── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)          usage ;;
    --api-port)
      if [[ $# -lt 2 || -z "${2-}" ]]; then
        err "--api-port requires a port number argument."
        echo "Run '$0 --help' for usage."
        exit 1
      fi
      API_PORT="$2"; shift ;;
    --fe-port)
      if [[ $# -lt 2 || -z "${2-}" ]]; then
        err "--fe-port requires a port number argument."
        echo "Run '$0 --help' for usage."
        exit 1
      fi
      FE_PORT="$2"; shift ;;
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
  err "A tag argument is required (e.g. v1.0.0)"
  echo "Run '$0 --help' for usage."
  exit 1
fi

# ─── Cleanup (runs on EXIT regardless of success/failure) ─────────────────────
cleanup() {
  # IMPORTANT: local var=$? must be a single combined statement.
  # Splitting into 'local var; var=$?' would reset $? to 0 after 'local' runs,
  # causing every failure to be reported as success.
  local exit_code=$?

  step "Cleaning up"

  if [[ -n "$FE_PID" ]] && kill -0 "$FE_PID" 2>/dev/null; then
    info "Stopping frontend server (PID $FE_PID)"
    kill "$FE_PID" 2>/dev/null || true
    wait "$FE_PID" 2>/dev/null || true
  fi

  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" 2>/dev/null; then
    info "Stopping API server (PID $API_PID)"
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi

  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    info "Removing temp directory $WORK_DIR"
    rm -rf "$WORK_DIR"
  fi

  echo ""
  if [[ "$exit_code" -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}✓ Production verification PASSED for $TAG${NC}"
  else
    echo -e "${RED}${BOLD}✗ Production verification FAILED for $TAG (exit code $exit_code)${NC}"
  fi
  echo ""

  exit "$exit_code"
}

trap cleanup EXIT

# ─── Prerequisites ────────────────────────────────────────────────────────────
check_prerequisites() {
  step "Checking prerequisites"

  local missing=0

  for cmd in curl unzip python3 node npm; do
    if command -v "$cmd" &>/dev/null; then
      info "$cmd  →  $(command -v "$cmd")"
    else
      err "$cmd not found — install it and try again"
      missing=1
    fi
  done

  # Python version check: 3.9 minimum (matches requires-python in pyproject.toml), 3.14 preferred
  if command -v python3 &>/dev/null; then
    local py_major py_minor
    py_major=$(python3 -c "import sys; print(sys.version_info.major)")
    py_minor=$(python3 -c "import sys; print(sys.version_info.minor)")
    local py_version="$py_major.$py_minor"

    if [[ "$py_major" -lt 3 ]] || { [[ "$py_major" -eq 3 ]] && [[ "$py_minor" -lt 9 ]]; }; then
      err "Python 3.9+ required, found $py_version"
      missing=1
    elif [[ "$py_minor" -lt 14 ]]; then
      warn "Python $py_version detected; 3.14 preferred (wheel was built with 3.14)"
    else
      info "Python $py_version  ✓"
    fi
  fi

  # Node version check: 20 minimum
  if command -v node &>/dev/null; then
    local node_major
    node_major=$(node --version | sed 's/v//' | cut -d. -f1)
    if [[ "$node_major" -lt 20 ]]; then
      err "Node 20+ required, found $(node --version)"
      missing=1
    else
      info "Node $(node --version)  ✓"
    fi
  fi

  # Frontend node_modules
  if [[ ! -d "$REPO_ROOT/frontend/node_modules" ]]; then
    err "frontend/node_modules not found — run 'npm ci' in frontend/ first"
    missing=1
  else
    info "frontend/node_modules present  ✓"
  fi

  # Playwright browsers
  if [[ ! -d "$REPO_ROOT/frontend/node_modules/@playwright" ]]; then
    err "@playwright/test not found in node_modules — run 'npm ci' in frontend/"
    missing=1
  fi

  if [[ "$missing" -ne 0 ]]; then
    err "One or more prerequisites are missing. Aborting."
    exit 1
  fi
}

# ─── Download release artifacts ───────────────────────────────────────────────
download_artifacts() {
  step "Downloading release artifacts for $TAG"

  WORK_DIR=$(mktemp -d)
  info "Working directory: $WORK_DIR"

  # Build auth header arrays
  local api_auth=()
  local asset_auth=()
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    api_auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
    asset_auth=(-H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/octet-stream")
    info "Using GITHUB_TOKEN for authenticated requests"
  else
    warn "GITHUB_TOKEN not set — unauthenticated (60 req/hr rate limit, public repos only)"
  fi

  # Fetch release metadata
  local release_api_url="https://api.github.com/repos/$REPO/releases/tags/$TAG"
  info "Fetching release metadata: $release_api_url"
  local release_json
  if ! release_json=$(curl -fsSL "${api_auth[@]}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$release_api_url" 2>&1); then
    err "GitHub API returned an error fetching release $TAG."
    err "If this is a draft release, set GITHUB_TOKEN to a token with repo read access."
    err "Alternatively, publish the draft release on GitHub before running this script."
    exit 1
  fi

  # Extract asset download URLs (python3 is already a required dependency, so
  # we use it here rather than requiring jq as an extra system dependency)
  local wheel_url fe_zip_url
  wheel_url=$(echo "$release_json" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(next((a['browser_download_url'] for a in d['assets'] if a['name'].endswith('.whl')), ''))")
  fe_zip_url=$(echo "$release_json" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print(next((a['browser_download_url'] for a in d['assets'] if '-frontend-' in a['name']), ''))")

  if [[ -z "$wheel_url" ]]; then
    err "No .whl asset found in release $TAG"
    echo "Available assets:"
    echo "$release_json" | python3 -c "import json,sys; [print(a['name']) for a in json.load(sys.stdin)['assets']]"
    exit 1
  fi
  if [[ -z "$fe_zip_url" ]]; then
    err "No frontend zip asset found in release $TAG (expected name containing '-frontend-')"
    echo "Available assets:"
    echo "$release_json" | python3 -c "import json,sys; [print(a['name']) for a in json.load(sys.stdin)['assets']]"
    exit 1
  fi

  info "Wheel:    $wheel_url"
  info "Frontend: $fe_zip_url"

  # Download the wheel
  info "Downloading wheel..."
  # Keep the real wheel filename (astronomy_tools-1.0.0-py3-none-any.whl) so pip
  # can validate the wheel name format, which it requires even for local installs.
  WHL_FILENAME=$(basename "$wheel_url")
  curl -fsSL "${asset_auth[@]}" -o "$WORK_DIR/$WHL_FILENAME" "$wheel_url"

  # Download the frontend zip
  info "Downloading frontend zip..."
  curl -fsSL "${asset_auth[@]}" -o "$WORK_DIR/frontend.zip" "$fe_zip_url"

  # Verify files are non-empty
  local whl_bytes fe_bytes
  whl_bytes=$(wc -c < "$WORK_DIR/$WHL_FILENAME" | tr -d ' ')
  fe_bytes=$(wc -c < "$WORK_DIR/frontend.zip" | tr -d ' ')

  if [[ "$whl_bytes" -eq 0 ]]; then
    err "$WHL_FILENAME downloaded as empty file — check GITHUB_TOKEN and release assets"
    exit 1
  fi
  if [[ "$fe_bytes" -eq 0 ]]; then
    err "frontend.zip downloaded as empty file — check GITHUB_TOKEN and release assets"
    exit 1
  fi

  info "api.whl:       ${whl_bytes} bytes  ($WHL_FILENAME)"
  info "frontend.zip:  ${fe_bytes} bytes"

  # Extract the frontend zip
  # The zip contains dist/ at the root: dist/index.html, dist/assets/, ...
  mkdir -p "$WORK_DIR/fe"
  unzip -q "$WORK_DIR/frontend.zip" -d "$WORK_DIR/fe"

  if [[ ! -d "$WORK_DIR/fe/dist" ]]; then
    err "Expected a dist/ directory at the root of the frontend zip"
    echo "Zip contents:"
    unzip -l "$WORK_DIR/frontend.zip" | head -20
    exit 1
  fi

  info "Frontend extracted to $WORK_DIR/fe/dist/"
}

# ─── Start API server ─────────────────────────────────────────────────────────
start_api() {
  step "Starting API server (port $API_PORT)"

  # Fail fast if the port is already in use
  if port_in_use "$API_PORT"; then
    err "Port $API_PORT is already in use."
    err "Stop any running API server (e.g. the dev uvicorn) or use --api-port to choose a different port."
    exit 1
  fi

  # Create an isolated virtual environment for the installed wheel
  info "Creating virtual environment..."
  python3 -m venv "$WORK_DIR/venv"

  # Python venvs use Scripts/ on Windows and bin/ on Unix.
  # Git Bash runs on Windows so the Windows layout applies.
  if [[ -f "$WORK_DIR/venv/Scripts/pip" ]]; then
    VENV_PYTHON="$WORK_DIR/venv/Scripts/python"
    local venv_pip="$WORK_DIR/venv/Scripts/pip"
  elif [[ -f "$WORK_DIR/venv/Scripts/pip.exe" ]]; then
    VENV_PYTHON="$WORK_DIR/venv/Scripts/python.exe"
    local venv_pip="$WORK_DIR/venv/Scripts/pip.exe"
  else
    VENV_PYTHON="$WORK_DIR/venv/bin/python"
    local venv_pip="$WORK_DIR/venv/bin/pip"
  fi
  info "Using venv python: $VENV_PYTHON"

  info "Installing wheel into venv..."
  # cd into WORK_DIR and use ./<filename> so pip sees a relative path with a
  # slash (unambiguously a local file) without any MSYS2 path translation.
  # --no-cache-dir avoids pip's cache-deserialization errors on Windows.
  ( cd "$WORK_DIR" && "$venv_pip" install --quiet --no-cache-dir "./$WHL_FILENAME" )

  # Ensure uvicorn is available (it is a declared dependency, but verify)
  if ! "$VENV_PYTHON" -c "import uvicorn" 2>/dev/null; then
    warn "uvicorn not found via wheel deps — installing separately"
    "$venv_pip" install --quiet "uvicorn[standard]"
  fi

  # Start uvicorn in the background
  info "Starting uvicorn..."
  "$VENV_PYTHON" -m uvicorn api.main:app \
    --port "$API_PORT" \
    --log-level warning \
    --no-access-log &
  API_PID=$!
  info "API server PID: $API_PID"

  # Poll /health with 2-second intervals, 30-second timeout (15 attempts)
  info "Waiting for API to become ready (http://localhost:$API_PORT/health)..."
  local attempts=0
  until curl -fsSo /dev/null "http://localhost:$API_PORT/health" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge 15 ]]; then
      err "API server did not respond within 30 seconds"
      exit 1
    fi
    sleep 2
  done
  info "API server is ready ✓"
}

# ─── Start frontend server ────────────────────────────────────────────────────
start_frontend() {
  step "Starting frontend server (port $FE_PORT)"

  # Fail fast if the port is already in use
  if port_in_use "$FE_PORT"; then
    err "Port $FE_PORT is already in use."
    err "Stop any running frontend server or use --fe-port to choose a different port."
    exit 1
  fi

  # Use 'vite preview' so the /api proxy in vite.config.ts is active.
  # The production dist uses relative API paths (/api/...) which require a
  # server-side proxy to reach the API on port 8000.
  info "Starting vite preview (dist: $WORK_DIR/fe/dist)..."

  # Run vite preview from frontend/ so vite.config.ts (and its proxy config) is
  # picked up, but override --outDir to serve the downloaded release artifacts
  # rather than a locally-built dist.
  #
  # exec replaces the subshell with the vite process itself so FE_PID is the
  # actual vite PID — without exec, kill $FE_PID would only kill the subshell
  # wrapper and leave vite running, holding the port.
  (
    cd "$REPO_ROOT/frontend"
    export API_PORT="$API_PORT"
    exec npx vite preview \
      --outDir "$WORK_DIR/fe/dist" \
      --port "$FE_PORT" \
      --strictPort
  ) &
  FE_PID=$!
  info "Frontend server PID: $FE_PID"

  # Poll root with 2-second intervals, 30-second timeout (15 attempts)
  info "Waiting for frontend to become ready (http://localhost:$FE_PORT)..."
  local attempts=0
  until curl -fsSo /dev/null "http://localhost:$FE_PORT" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [[ "$attempts" -ge 15 ]]; then
      err "Frontend server did not respond within 30 seconds"
      exit 1
    fi
    sleep 2
  done
  info "Frontend server is ready ✓"
}

# ─── Run Playwright tests ─────────────────────────────────────────────────────
run_tests() {
  step "Running Playwright E2E tests"
  info "Frontend: http://localhost:$FE_PORT"
  info "API:      http://localhost:$API_PORT"
  info "Config:   frontend/playwright.prod.config.ts"
  echo ""

  cd "$REPO_ROOT/frontend"
  PLAYWRIGHT_BASE_URL="http://localhost:$FE_PORT" \
    npx playwright test \
      --config playwright.prod.config.ts
  # Exit code from playwright propagates via set -e / trap EXIT
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BOLD}Castle Celestial View — Production Release Verification${NC}"
  echo -e "Tag: ${YELLOW}$TAG${NC}  |  API port: $API_PORT  |  Frontend port: $FE_PORT"
  echo ""

  check_prerequisites
  download_artifacts
  start_api
  start_frontend
  run_tests
}

main
