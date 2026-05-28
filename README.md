# Python
Castle Celestial View

## Purpose
Visualise the Solar System. Currently showing the Earth and Moon from any location on earth for pretty much any date range. Solar system view shows the orbits. Sky View is for the location on the sky as seen from the location picked.

## Languages
1. API - Python
1. FE - Vue
1. Graphics - WebGL/ThreeJ

# Public Website
https://castlecelestialview.net/

# For Check In
## Pre-commit checklist
 - Remove `node_modules` (keep `package-lock.json`).
 - Optionally clear the npm cache.
 - Confirm `npm ci` and `npm run build` succeed.
 
# To start the app:
### FE Dev PowerShell terminal 1
cd frontend; npm run dev
### FE Prod PowerShell terminal 2
cd frontend
npm run build
npm run preview
## Powershell terminal 3
may need to run:
(.\.venv\Scripts\Activate.ps1)
uvicorn api.main:app --reload --port 8000

# To run tests:
## Python
$env:PYTHONPATH="." ; pytest tests/ --cov=. --cov-report=xml --cov-report=term-missing
## FE
cd frontend
npm run build
npm run lint:a11y
npm run type-check
npm run test:coverage
npm run test:e2e
npm run test:e2e:update-snapshots

# Accessibility

## Development Phase
### axe DevTools extension (browser manual)
1. Quick spot-checks during dev
1. Catch obvious contrast/ARIA/semantic issues

## CI Gate (every PR)
### eslint-plugin-vuejs-accessibility + jest-axe
1. Automated baseline: accessibility linting plus axe-based test coverage for labels, ARIA, and semantics
1. Prevent regressions

## Release Gate (before shipping)
### Manual keyboard testing (15-20 min)
1. Tab through entire UI, both states
1. Verify focus visible, no traps

### Manual screen reader testing (15-20 min)
1. Narrator on Edge or
1. NVDA on Chrome
1. Verify announcements are clear

# Release notes
Day 1
HelloWorld
Julian Date + Day of the Week
Sun and Moon Position
Plot Sun and Moon longitude over 12 months

Day 2
Sun rise and set
Moon rise and set
Moon phase
Sun and moon animation
# Test commit to verify branch protection

## Phase 1
Building to two Open GL animations:
SunAndMoonAnimation - Earth bound
SolarSystemAnimation - Sun centered

## 1/2/2026
Initial API layer
- Dates
- Sun position
- Moon position
- Moon phase
Enough for 1 frame on the Earth bound animation.

## 4/2/2026
E2E test

## 5/2/2026
Windows size changes affects the canvas sizing.
Sizes of objects and default view settings updated.
Visibility of objects on the parameters and animation views corrected.

## 6/2/2026 - 7/2/2026
Parameter input UX
- Use a map for coordinates
- Date range picker, defaulting to today
- Slider for frames per day

## 7/2/2026
Progress bar for long running API call
-- SSE to send each frame as an event
-- Progress bar that show progress and only times out if any frame takes too long

## 8/2/2026
Consolidate CSS, remove duplication, single block per class
