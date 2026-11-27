# Contributing to Castle Celestial View

Thanks for helping! Contributions of all sizes are welcome. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## Getting started

1. Look for an issue labelled `good first issue`, or open one to discuss your idea.
2. Fork the repository (external contributors) or branch from `main`.
3. Follow the [quick start in the README](README.md#quick-start) to run the API and frontend.

## Branches and pull requests

- `main` is the only long-lived branch. Branch from `main` and open pull requests back to `main`.
- Name branches by intent, for example `feature/moon-phase-label`, `fix/timezone-handling`, `chore/210-repo-welcome`, `docs/readme`.
- Link the issue in the PR description (`Closes #123`) and fill in the PR template.
- Keep PRs small and focused. CI must pass before merging.
- Add a `CHANGELOG.md` entry under `## [Unreleased]` for user-visible changes. Versioning rules are in [docs/VERSIONING.md](docs/VERSIONING.md).

## Checks CI runs

**API** (from the repository root, Python 3.14+):

```powershell
$env:PYTHONPATH="." ; pytest tests/ --cov=. --cov-report=term-missing
bandit -r . -x ./tests,./htmlcov,./__pycache__,./.venv,./scripts,./research,./icon-generator,./frontend
pip-audit --desc --skip-editable
pylint api
radon cc api -a
```

**Frontend** (from `frontend/`, Node 20.19+):

```powershell
npm ci
npm run build
npm run type-check
npm run lint:a11y
npm run test:coverage
npm run test:e2e
```

CI also runs CodeQL, Trivy and production-landing checks.

## Code standards

- Python: type hints preferred, docstrings for public functions, tests for new behaviour.
- Frontend: Vue 3 `<script setup>` with TypeScript. Use OpenLayers (`ol`) for maps. User-facing strings go through vue-i18n, with locale formatting via `normalizeLocaleForIntl`.
- No known security vulnerabilities. Report them privately, see [SECURITY.md](SECURITY.md).

## Accessibility

- **While developing:** spot-check with the axe DevTools browser extension.
- **Every PR (CI gate):** `eslint-plugin-vuejs-accessibility` and jest-axe must pass.
- **Before a release:** manual keyboard and screen reader testing, see [frontend/tests/accessibility-manual.md](frontend/tests/accessibility-manual.md).

## Playwright snapshots

Snapshots are per browser and platform. Update them with `npm run test:e2e:update-snapshots` (Windows). Linux snapshots are generated in Docker, via `Update-LinuxSnapshots.ps1` (or `update-linux-snapshots.sh`), using `Dockerfile.playwright`:

```bash
docker build -f Dockerfile.playwright -t playwright-linux-snapshots .
```

Only commit snapshot changes that are intended, and explain them in the PR.

## Before you commit

- Confirm `npm ci` and `npm run build` succeed in `frontend/`.
- Don't commit `node_modules`, `dist/`, `coverage/` or other generated output.

## More documentation

See [docs/README.md](docs/README.md) for build, deployment, release and security documents.
