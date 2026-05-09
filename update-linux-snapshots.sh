#!/usr/bin/env bash
# update-linux-snapshots.sh
#
# Runs inside the playwright-linux-snapshots Docker container.
# Mirrors the two-phase strategy used in ci.yml:
#   Phase 1 – Chromium / WebKit / Edge  (headless, no Xvfb needed)
#   Phase 2 – Firefox                   (headed + Xvfb + Mesa llvmpipe)
#
# The entire project is bind-mounted at /app so any source changes on the
# Windows host are immediately visible here. node_modules lives in a named
# Docker volume so the Linux build never conflicts with the Windows one.

set -euo pipefail

echo "==> Installing Python dependencies..."
pip3 install -r /app/requirements.txt -e /app \
    --break-system-packages \
    --quiet

echo "==> Installing Node dependencies..."
cd /app/frontend
npm ci --silent

echo "==> Installing Playwright browsers (matching installed package version)..."
npx playwright install --with-deps chromium firefox webkit msedge 2>/dev/null || \
npx playwright install --with-deps chromium firefox webkit

echo ""
echo "==> Phase 1: Updating snapshots – Chromium / WebKit / Edge (headless)..."
CI=true npx playwright test \
    --project=chromium \
    --project=webkit \
    --project=edge \
    --update-snapshots

echo ""
echo "==> Phase 2: Updating snapshots – Firefox (headed via Xvfb + Mesa llvmpipe)..."
CI=true \
LIBGL_ALWAYS_SOFTWARE=1 \
MESA_GL_VERSION_OVERRIDE=4.5 \
xvfb-run --server-args="-screen 0 1280x720x24" \
    npx playwright test \
        --project=firefox \
        --headed \
        --update-snapshots

echo ""
echo "==> Done! Linux snapshots have been updated."
