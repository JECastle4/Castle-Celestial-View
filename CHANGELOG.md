# Changelog

All notable changes to Castle Celestial View are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/) — see [VERSIONING.md](VERSIONING.md).

---

## [Unreleased]

---

## [1.0.0] - 2026-05-11

### Added

- Sun position calculation from observer location and date/time
- Moon phase, position, rise and set time calculations
- Solar system animation
- Sun and moon animation and plot views
- Day of the week calculator
- FastAPI REST API with i18n support (`en` locale)
- Vue 3 frontend with Three.js 3D animations
- Responsive base map view
- Production build pipeline (API wheel + frontend static dist)
- GitHub Actions CI workflow with Python tests, security scans, and code quality checks
- Accessibility audit completed for all primary views
- Third-party licence audit completed; attributions in [NOTICE](NOTICE)

### QA Attestation

- **Automated tests**: CI run — _[link to passing CI run]_
- **Security scan**: Bandit + pip-audit + npm audit — _[link to CI run or scan output]_
- **Accessibility audit**: _[link to screenshots/recordings]_
- **Licence audit**: _[link to licence report]_
- **Production build verification**: Wheel and dist confirmed clean of dev-only files

---

## [1.0.1] - 2026-05-22
### Changed
- Refactored: Moved jd_to_weekday from root-level script to utils.py for proper API packaging and reuse.
- Updated: All imports and tests now reference api.utils.jd_to_weekday.
### Fixed
- E2E: Playwright tests now robust against Firefox/WebKit quirks (removed networkidle waits, fixed date input handling, increased timeout for slowest test).
- E2E: Date range test now reliably targets the correct input fields, preventing accidental long-range API calls.
### Security
- Added: Explicit pins for idna>=3.15 and starlette>=1.0.1 in requirements.txt to address CVE-2026-45409 and PYSEC-2026-161.
- Upgraded: All Python dependencies to latest secure versions.

### QA Attestation
- **Automated tests**: All unit, integration, and E2E tests pass.
- **Security scan**: Bandit + pip-audit + npm audit — no known vulnerabilities.
- **Accessibility audit**: Manual and automated checks pass.
- **Licence audit**: No incompatible changes.
- **Production build verification**: Artifacts verified clean.
