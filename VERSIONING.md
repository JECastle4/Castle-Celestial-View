# Versioning

Castle Celestial View uses [Semantic Versioning](https://semver.org/) (SemVer): `MAJOR.MINOR.PATCH`.

---

## Version Scheme

| Segment | Increment when... |
|---------|-------------------|
| **MAJOR** | Incompatible API or UI change (breaking change) |
| **MINOR** | New functionality added in a backward-compatible way |
| **PATCH** | Backward-compatible bug fixes or minor corrections |

Examples: `1.0.0`, `1.1.0`, `1.1.3`, `2.0.0`

---

## Synchronization Rule

The API (`pyproject.toml`) and Frontend (`frontend/package.json`) **must always carry the same version number**. A release tag covers both components simultaneously.

The CI workflow enforces this by failing if the two version numbers diverge (see `.github/workflows/ci.yml`).

---

## Files to Update

When bumping the version, update **both** files together in the same commit:

| File | Key |
|------|-----|
| `pyproject.toml` | `[project] version = "..."` |
| `frontend/package.json` | `"version": "..."` |

---

## Bumping the Version

1. Decide the new version number according to the scheme above.
2. Edit both files:

   ```bash
   # pyproject.toml — [project] section
   version = "1.1.0"

   # frontend/package.json
   "version": "1.1.0"
   ```

3. Commit with a conventional message:

   ```bash
   git commit -am "chore: bump version to 1.1.0"
   ```

4. Follow the steps in [RELEASE_PROCESS.md](RELEASE_PROCESS.md) to tag and publish.

---

## Tag Format

Git tags must follow the pattern `v<MAJOR>.<MINOR>.<PATCH>`, e.g.:

```
v1.0.0
v1.1.0
v2.0.0
```

The `release.yml` GitHub Actions workflow is triggered by any tag matching `v*.*.*`.

---

## API Endpoint Versioning

The REST API currently uses non-versioned routes (e.g., `/api/sun-position`). If URL versioning (e.g., `/api/v1/sun-position`) is introduced in the future, document the relationship between route version and package version here.
