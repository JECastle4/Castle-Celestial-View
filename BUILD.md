# Production Build Guide

This document describes how to build production artifacts for the API (Python wheel) and Frontend (static dist).

---

## Prerequisites

- Python 3.9+ with a virtual environment activated
- Node.js with `npm`
- Build tools installed: `pip install build` (for the API)

---

## API (Python Wheel)

### Build

From the repository root:

```bash
pip install build
python -m build
```

### Output

```
dist/
  astronomy_tools-<version>-py3-none-any.whl
  astronomy_tools-<version>.tar.gz
```

### Included in Distribution

- `api/` package and `api/services/` subpackage
- `api/locales/en.json` (production locale only)

### Excluded from Distribution

- `api/locales/xx-reverse.json` (dev-only pseudo-locale)
- Root-level scripts (`DayOfTheWeek.py`, `MoonPhase.py`, `generate_*.py`, etc.)
- `tests/` directory

---

## Frontend (Static Dist)

### Build

From the `frontend/` directory:

```bash
npm install
npm run build
```

### Output

```
frontend/dist/
  index.html
  assets/
    vendor-<hash>.js      # Vue and core dependencies
    three-<hash>.js       # Three.js (code-split)
    index-<hash>.js       # App entry point
    ...
```

### Production Optimizations

- TypeScript type-checking runs before bundling (`vue-tsc`)
- JavaScript is minified and chunked via Rolldown
- `import.meta.env.DEV` is replaced with `false` at build time, which tree-shakes:
  - `xx-reverse` locale from `src/locales/xx-reverse.json`
  - The `xx-reverse` route from the router
- All `console.log` calls in dev-only branches are eliminated

### Verifying Dev Locale Exclusion

After building, confirm `xx-reverse` is absent from the output:

```bash
# Should return no results
grep -r "xx-reverse" frontend/dist/
```

---

## Release Artifacts

Both artifacts are published to the GitHub Release by the `release.yml` GitHub Actions workflow when a `v*.*.*` tag is pushed. See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for the full release workflow.
