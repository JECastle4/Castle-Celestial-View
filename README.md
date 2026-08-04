# Castle Celestial View

## Purpose

Visualise the Solar System. Currently showing the Earth and Moon from any location on earth for pretty much any date range. Solar system view shows the orbits. Sky View is for the location on the sky as seen from the location picked.

## Languages

1. API - Python
1. FE - Vue
1. Graphics - WebGL/ThreeJ

## Public Website

[https://castlecelestialview.net/](https://castlecelestialview.net/)

## For Check In

### Pre-commit checklist

- Remove `node_modules` (keep `package-lock.json`).
- Optionally clear the npm cache.
- Confirm `npm ci` and `npm run build` succeed.

### To start the app

#### FE Dev PowerShell terminal 1

```powershell
cd frontend; npm run dev
```

#### FE Prod PowerShell terminal 2

```powershell
cd frontend
npm run build
npm run preview
## Powershell terminal 3
may need to run:
(.\.venv\Scripts\Activate.ps1)
uvicorn api.main:app --reload --port 8000
```

### To run tests

#### Python

```bash
$env:PYTHONPATH="." ; pytest tests/ --cov=. --cov-report=xml --cov-report=term-missing
```

#### FE

```bash
cd frontend
npm run build
npm run lint:a11y
npm run type-check
npm run test:coverage
npm run test:e2e
npm run test:e2e:update-snapshots
```

## To rebuild the docker image

```bash
docker build -f Dockerfile.playwright -t playwright-linux-snapshots .
```

## Accessibility

### Development Phase

#### axe DevTools extension (browser manual)

1. Quick spot-checks during dev
1. Catch obvious contrast/ARIA/semantic issues

### CI Gate (every PR)

#### eslint-plugin-vuejs-accessibility + jest-axe

1. Automated baseline: accessibility linting plus axe-based test coverage for labels, ARIA, and semantics
1. Prevent regressions

### Release Gate (before shipping)

#### Manual keyboard testing (15-20 min)

1. Tab through entire UI, both states
1. Verify focus visible, no traps

#### Manual screen reader testing (15-20 min)

1. Narrator on Edge or
1. NVDA on Chrome
1. Verify announcements are clear
