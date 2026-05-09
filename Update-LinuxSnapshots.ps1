<#
.SYNOPSIS
    Updates Playwright Linux snapshots locally using Docker, so they match what
    CI (GitHub Actions / ubuntu-latest) produces – without needing four separate
    CI runs.

.DESCRIPTION
    Builds a lightweight Docker image based on the official Playwright Ubuntu
    image, then runs the two-phase snapshot update strategy that mirrors ci.yml:

        Phase 1 – Chromium / WebKit / Edge  (headless)
        Phase 2 – Firefox                   (headed + Xvfb + Mesa llvmpipe)

    The project directory is bind-mounted into the container so:
      • Your latest source changes are used immediately (no image rebuild needed).
      • Updated snapshot PNGs are written directly back to your working tree.
      • Linux node_modules are kept in a named Docker volume so they never
        conflict with the Windows node_modules on your host.

.PREREQUISITES
    Docker Desktop must be running with Linux containers enabled.

.EXAMPLE
    # From the project root:
    .\Update-LinuxSnapshots.ps1

    # Or via npm (from the frontend folder):
    npm run test:e2e:update-snapshots:linux
#>

#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$ImageName   = 'playwright-linux-snapshots'
$VolumeName  = 'playwright-linux-node-modules'

# ── 1. Verify Docker is available ────────────────────────────────────────────
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error 'Docker not found. Install Docker Desktop and ensure it is running.'
    exit 1
}

docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Docker daemon is not running. Start Docker Desktop and try again.'
    exit 1
}

# ── 2. Build the image (fast: only rebuilds when Dockerfile changes) ──────────
Write-Host "`n==> Building Docker image '$ImageName'..." -ForegroundColor Cyan
docker build `
    --tag  $ImageName `
    --file "$ProjectRoot\Dockerfile.playwright" `
    "$ProjectRoot"

if ($LASTEXITCODE -ne 0) {
    Write-Error 'Docker build failed.'
    exit 1
}

# ── 3. Run the snapshot update inside the Linux container ─────────────────────
Write-Host "`n==> Running Linux snapshot update..." -ForegroundColor Cyan
Write-Host "    Source : $ProjectRoot  →  /app  (bind mount)"
Write-Host "    Modules: $VolumeName   →  /app/frontend/node_modules  (Docker volume)"
Write-Host ''

docker run --rm `
    --volume "${ProjectRoot}:/app" `
    --volume "${VolumeName}:/app/frontend/node_modules" `
    $ImageName `
    bash /app/update-linux-snapshots.sh

if ($LASTEXITCODE -ne 0) {
    Write-Error 'Snapshot update failed. Check the output above for details.'
    exit 1
}

Write-Host "`n==> Linux snapshots updated successfully!" -ForegroundColor Green
Write-Host "    Changed files are in: frontend\tests\e2e\astronomy-scene.spec.ts-snapshots\"
