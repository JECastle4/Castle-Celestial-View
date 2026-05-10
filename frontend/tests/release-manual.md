# Manual Release Checklist

Covers checks that cannot be automated reliably and must be verified before every release.

---

## 1. Dependency Attributions Sync

Verify that `NOTICE` (top-level) and the About page attributions list (`frontend/src/views/AboutView.vue`) are consistent with the declared runtime dependencies.

### 1.1 Prerequisites

- `requirements.txt` — backend runtime dependencies
- `frontend/package.json` (`dependencies` section) — frontend runtime dependencies
- `NOTICE` — top-level third-party notices file
- About page running at `http://localhost:5173/en/about`

### 1.2 Steps

| # | Action | Expected |
|---|--------|----------|
| D1 | Open `requirements.txt`. Note every package listed (build/test tools in `requirements-dev.txt` are excluded from NOTICE and the About page). | — |
| D2 | Open `frontend/package.json`. Note every entry under `"dependencies"` (not `"devDependencies"`). | — |
| D3 | Open `NOTICE`. Confirm that every runtime package identified in D1 and D2 has a corresponding entry with name, copyright holder, licence, and upstream licence URL. | No runtime dependency is missing from NOTICE. No entry in NOTICE refers to a package no longer used. |
| D4 | Open the About page (`/en/about`). Confirm that every entry in the on-screen attributions list matches a corresponding entry in NOTICE (same name, same licence identifier). | The About page and NOTICE list exactly the same set of runtime dependencies. No entry is present in one but absent from the other. |
| D5 | For any new dependency added since the last release: confirm its licence is permissive and compatible with the project's MIT licence (e.g. MIT, BSD-2, BSD-3, Apache-2.0). Flag any copyleft licence (GPL, LGPL, AGPL) for legal review before release. | All new dependencies carry a permissive licence, or a legal review has been recorded in the relevant GitHub issue. |

### 1.3 Pass / Fail Criteria

- **Pass**: NOTICE and the About page contain identical runtime dependency lists, all licence identifiers are correct, and no incompatible licences are present.
- **Fail**: Any runtime dependency is missing from NOTICE or the About page, or any entry in either place refers to a package not in `requirements.txt` / `frontend/package.json` dependencies, or an incompatible licence is found without a recorded review.

Record results below and link to the release GitHub issue for any failures found.
