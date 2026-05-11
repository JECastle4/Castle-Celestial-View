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

[Unreleased]: https://github.com/JECastle4/Castle-Celestial-View/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JECastle4/Castle-Celestial-View/releases/tag/v1.0.0
