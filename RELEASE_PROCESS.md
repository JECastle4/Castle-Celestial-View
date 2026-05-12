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

### 7. Finalize the GitHub Release

After the workflow completes:

- Open the draft release on GitHub
- Paste the [CHANGELOG.md](CHANGELOG.md) entry into the release notes
- Link to QA evidence as documented in [RELEASE_QA.md](RELEASE_QA.md)
- Publish the release

---

## Hotfix Releases

For urgent patches on an already-released version:

1. Branch from the tag: `git checkout -b hotfix/v1.0.1 v1.0.0`
2. Apply the fix, update version to `1.0.1` in both files, update CHANGELOG.md
3. Open a PR back to `main`
4. After merge, tag `v1.0.1` on `main` and follow steps 5–7 above

---

## Related Documents

- [VERSIONING.md](VERSIONING.md) — Version numbering scheme and sync rules
- [RELEASE_QA.md](RELEASE_QA.md) — QA checklist and evidence procedures
- [CHANGELOG.md](CHANGELOG.md) — Release history
- [BUILD.md](BUILD.md) — How to build artifacts locally
