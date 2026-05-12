# Release Process

This document describes the end-to-end steps to publish a new version of Castle Celestial View. See [VERSIONING.md](VERSIONING.md) for the version numbering scheme.

---

## Overview

Releases are triggered by pushing an annotated git tag. GitHub Actions automatically builds the API wheel and frontend dist, then publishes a GitHub Release with both artifacts attached.

Not every merge to `main` produces a release — only commits that are deliberately tagged.

---

## Pre-Release Checklist

Before creating a tag, confirm all of the following:

- [ ] All CI checks pass on `main` (tests, security scans, linting)
- [ ] `pyproject.toml` version and `frontend/package.json` version match
- [ ] [RELEASE_QA.md](RELEASE_QA.md) checklist completed and evidence captured
- [ ] [CHANGELOG.md](CHANGELOG.md) entry written for this version
- [ ] No known unresolved security advisories in dependencies

---

## Step-by-Step Release

### 1. Ensure you are on `main` and up to date

```bash
git checkout main
git pull origin main
```

### 2. Bump the version

Edit both files to the new version number (see [VERSIONING.md](VERSIONING.md)):

```
pyproject.toml         →  version = "1.0.0"
frontend/package.json  →  "version": "1.0.0"
```

### 3. Update CHANGELOG.md

Add an entry for the new version under `## [Unreleased]` following the format in [CHANGELOG.md](CHANGELOG.md).

### 4. Commit the version bump

```bash
git add pyproject.toml frontend/package.json CHANGELOG.md
git commit -m "chore: Release v1.0.0"
git push origin main
```

### 5. Create an annotated tag

```bash
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin v1.0.0
```

Pushing the tag triggers the `release.yml` GitHub Actions workflow automatically.

### 6. Monitor the workflow

In the GitHub repository, go to **Actions → Release** to monitor the build. The workflow will:

1. Check out the tagged commit
2. Build the Python wheel (`python -m build`)
3. Build the frontend dist (`npm run build`)
4. Create a GitHub Release named `v1.0.0`
5. Attach both artifacts to the release

### 7. Run production verification

Before publishing, confirm the release artifacts work end-to-end:

```bash
# Stop the dev API server first (port 8000 must be free)
# Then run from the repo root — on Windows use Git Bash:
& "C:\Program Files\Git\bin\bash.exe" -c "cd '$(pwd -W)' && bash scripts/verify-production-release.sh v1.0.0"

# On macOS / Linux:
bash scripts/verify-production-release.sh v1.0.0
```

All 33 tests must pass before proceeding. On failure, investigate the
Playwright report at `frontend/playwright-report-prod/index.html`.

### 8. Publish the GitHub Release

After the workflow and verification both pass, publish the draft release:

```bash
# Option A — GitHub CLI (recommended)
gh release edit v1.0.0 --draft=false

# Option B — GitHub web UI
# Go to https://github.com/JECastle4/Castle-Celestial-View/releases
# Open the v1.0.0 draft → click "Edit" → click "Publish release"
```

> The release is intentionally created as a draft by the CI workflow so you
> have a chance to verify and update the release notes before it goes public.

---

## Hotfix Releases

For urgent patches on an already-released version:

1. Branch from the tag: `git checkout -b hotfix/v1.0.1 v1.0.0`
2. Apply the fix, update version to `1.0.1` in both files, update CHANGELOG.md
3. Open a PR back to `main`
4. After merge, tag `v1.0.1` on `main` and follow steps 5–7 above

---

## Local Production Verification

Before publishing a draft release, verify that the release artifacts work
end-to-end by downloading them and running the full Playwright E2E suite
against a local production deployment.

### What it does

The script `scripts/verify-production-release.sh`:

1. Downloads the API wheel (`.whl`) and frontend zip from the GitHub Release
2. Installs the wheel into an isolated virtual environment
3. Starts the API with `uvicorn` on port 8000
4. Serves the frontend dist with `vite preview` on port 4173 — using the same
   `/api` proxy configuration as a production reverse proxy
5. Runs all Playwright E2E tests against `http://localhost:4173`
6. Tears down both servers and removes all temp files on exit

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| `curl`, `unzip` | any | Included in Git Bash on Windows |
| Python | ≥ 3.11 (3.14 preferred) | 3.14 matches the build environment |
| Node / npm | ≥ 20 | |
| `frontend/node_modules` | — | Run `npm ci` in `frontend/` first |
| Playwright browsers | — | Run `npx playwright install` in `frontend/` |

Set `GITHUB_TOKEN` for private repositories or to avoid the 60 req/hr
unauthenticated rate limit.

### Running locally

**Windows (Git Bash):**

```bash
# Stop any running dev API server (port 8000 must be free), then:
& "C:\Program Files\Git\bin\bash.exe" -c "cd '/c/Users/<you>/path/to/repo' && bash scripts/verify-production-release.sh v1.0.0"
```

**macOS / Linux:**

```bash
# From the repo root
bash scripts/verify-production-release.sh v1.0.0
```

**Common options:**

```bash
# With custom ports if defaults (8000 / 4173) are already occupied
bash scripts/verify-production-release.sh v1.0.0 --api-port 9000 --fe-port 9100

# With a GitHub token (required for private repos; avoids rate limiting)
GITHUB_TOKEN=ghp_xxxx bash scripts/verify-production-release.sh v1.0.0
```

On success the script exits 0 and prints a summary. On failure it prints
the failing test output and exits non-zero.

### Running in Docker (recommended)

Use the existing `Dockerfile.playwright` to get a consistent Linux environment
that matches the snapshot baselines generated in CI:

```bash
# Build the verification image (from repo root)
docker build -f Dockerfile.playwright -t ccv-verify .

# Run verification (replace tag and token as needed)
docker run --rm \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  ccv-verify \
  ./scripts/verify-production-release.sh v1.0.0
```

### Report

Playwright writes results to `frontend/playwright-report-prod/`. Open
`index.html` in that directory to review test results and any failure
screenshots.

---

## Related Documents

- [VERSIONING.md](VERSIONING.md) — Version numbering scheme and sync rules
- [RELEASE_QA.md](RELEASE_QA.md) — QA checklist and evidence procedures
- [CHANGELOG.md](CHANGELOG.md) — Release history
- [BUILD.md](BUILD.md) — How to build artifacts locally
