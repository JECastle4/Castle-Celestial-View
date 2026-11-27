# Castle Celestial View

[![CI](https://github.com/JECastle4/Castle-Celestial-View/actions/workflows/ci.yml/badge.svg)](https://github.com/JECastle4/Castle-Celestial-View/actions/workflows/ci.yml)
[![CodeQL](https://github.com/JECastle4/Castle-Celestial-View/actions/workflows/codeql.yml/badge.svg)](https://github.com/JECastle4/Castle-Celestial-View/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/JECastle4/Castle-Celestial-View/graph/badge.svg)](https://codecov.io/gh/JECastle4/Castle-Celestial-View)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Visualise the Solar System. See the Earth and Moon from any location on Earth, for pretty much any date range, then explore the orbits and the sky as it appears from the place you picked.

**Live site:** <https://castlecelestialview.net/en-GB/>

## Features

- **Earth and Moon view**: watch the Earth and Moon from any location and date range.
- **Solar System view**: the orbits of the planets.
- **Sky View**: where the bodies appear in the sky from the chosen location.
- **Astronomical events**: eclipses and other events, with locale-aware formatting.
- **Accessible and multilingual**: automated and manual accessibility checks, and a translated interface.

## Tech stack

| Area | Technology | Location |
| --- | --- | --- |
| API | Python 3.14, FastAPI, Astropy | [`api/`](api/) |
| Frontend | Vue 3, TypeScript, Vite | [`frontend/`](frontend/) |
| Graphics | WebGL / Three.js, OpenLayers (maps) | [`frontend/src/three/`](frontend/src/) |
| Tests | pytest, Vitest, Playwright, jest-axe | [`tests/`](tests/), [`frontend/tests/`](frontend/tests/) |

## Quick start

Prerequisites: Python 3.14+, Node.js 20.19+ and npm.

```powershell
# API (terminal 1), from the repository root
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn api.main:app --reload --port 8000
```

```powershell
# Frontend (terminal 2)
cd frontend
npm ci
npm run dev
```

Open the URL printed by Vite. The frontend expects the API on `http://localhost:8000`.

To try the production build: `npm run build` then `npm run preview` in `frontend/`.

## Running the tests

```powershell
# API (from the repository root)
$env:PYTHONPATH="." ; pytest tests/ --cov=. --cov-report=term-missing

# Frontend (from frontend/)
npm run type-check
npm run lint:a11y
npm run test:coverage
npm run test:e2e
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full checklist, accessibility gates and snapshot workflow.

## Documentation

| Document | Purpose |
| --- | --- |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute, checks and conventions |
| [AGENTS.md](AGENTS.md) | Guidance for AI coding agents |
| [docs/README.md](docs/README.md) | Index of build, deployment, release and security docs |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [SECURITY.md](SECURITY.md) | Reporting vulnerabilities |
| [SUPPORT.md](SUPPORT.md) | Getting help |

## Community

Questions and ideas are welcome in [Discussions](https://github.com/JECastle4/Castle-Celestial-View/discussions). Bugs and feature requests go in [Issues](https://github.com/JECastle4/Castle-Celestial-View/issues/new/choose). Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE). See also [NOTICE](NOTICE).
