# Agent guidance for Castle Celestial View

Castle Celestial View visualises the Earth, Moon and Solar System from any location and date. Read [CONTRIBUTING.md](CONTRIBUTING.md) first; this file is the short version for AI coding agents.

## Layout

- `api/`: FastAPI backend (`routes/`, `services/`, `middleware/`, `locales/`). Astropy does the astronomy.
- `frontend/`: Vue 3 + TypeScript + Vite; Three.js for scenes, OpenLayers (`ol`) for maps; vue-i18n.
- `tests/`: pytest suite. `frontend/src/**/*.test.ts`: Vitest. `frontend/tests/e2e/`: Playwright.
- `docs/`: build, deploy, release and security docs. `scripts/`: ops and audit scripts.

## Commands

API (repo root, Python 3.14+, venv active):

```powershell
$env:PYTHONPATH="." ; pytest tests/ --cov=. --cov-report=term-missing
uvicorn api.main:app --reload --port 8000
```

Frontend (`frontend/`, Node 20.19+):

```powershell
npm ci
npm run dev
npm run type-check ; npm run lint:a11y ; npm run test:coverage ; npm run test:e2e
```

## Conventions

- Branch from `main` (the only long-lived branch); PRs target `main` and link an issue. Use the PR template.
- Add a `CHANGELOG.md` entry under `[Unreleased]` for user-visible changes. `pyproject.toml` and `frontend/package.json` versions must match (CI checks this).
- User-facing strings go through vue-i18n; format with `normalizeLocaleForIntl` before using `Intl`. The dev-only `xx-reverse` locale lives in `frontend/dev-locales/`.
- Maps use OpenLayers only; add alternative views as custom `ol` controls.
- Accessibility is a CI gate (`eslint-plugin-vuejs-accessibility`, jest-axe). Keep keyboard and screen reader behaviour working.
- SlowAPI-limited route handlers must name their Starlette `Request` parameter exactly `request`.
- Run security-sensitive changes past bandit and pip-audit; never commit secrets.

## Do not edit or commit

- Generated output: `frontend/dist/`, `coverage/`, `htmlcov/`, `node_modules/`, `test-results`.
- Playwright snapshots, unless the change is intentional. Linux snapshots are generated in Docker (`Update-LinuxSnapshots.ps1`), not by hand.
- Historical reports in `docs/security/` and `docs/history/` (archive only).
