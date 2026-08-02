# Changelog

All notable changes to Castle Celestial View are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/) — see [VERSIONING.md](VERSIONING.md).

---

## [Unreleased]

## [1.1.1] - 2026-08-01

### Added
- **Validation Layer**: Date/time format validators in Pydantic models (YYYY-MM-DD, HH:MM:SS with bounds checking)
- **Business Logic Validation**: TimeRange model ensures start_dt < end_dt (rejects equal or inverted times)
- **Error Handling**: ValidationError caught at route layer, returns 422 status code instead of crashes
- **Stability Audit Toolkit**: 5 comprehensive test modules (68 tests total, 100% pass rate)
  - test-boundaries.py: Coordinate/date/frame count edge cases (17 tests)
  - test-error-handling.py: Malformed requests, graceful degradation (12 tests)
  - test-resource-safety.py: Memory/connection leaks, cleanup verification (5 tests)
  - test-concurrency.py: Parallel requests, race conditions, idempotency (4 tests)
  - test-astropy-limits.py: IERS date coverage, precision, performance scaling (5 tests)
  - test-validation-fixes.py: Unit tests for all validators (25 tests)

### Fixed
- **Critical**: Connection crashes (WinError 10054) eliminated — invalid dates/times now return 422 instead of crashing
- **Critical**: Same start/end timestamp validation — rejected with 422 instead of accepted
- **Critical**: Inverted time range validation — caught early, returns 422 instead of passing to astropy
- **Important**: Frame count out-of-range — validated against 2-10000 bounds
- **Important**: Latitude/longitude out-of-range — validated against ±90/±180 bounds
- All validation issues fixed with zero API crashes

### Testing
- 25 unit tests for date/time/range validation (all passing)
- 68 total tests across 5 stability audit modules (all passing)
- Frame counts: 2-500 tested successfully; 10000+ identified as timeout limit
- Date ranges: 1900-2100 covered; IERS data accessible
- Concurrency: 10 parallel requests, 30 mixed load requests validated
- Resource safety: 100 sequential requests show <100MB memory growth, proper connection cleanup

### QA Attestation
- **Unit tests**: 25/25 PASS ✓
- **Boundary tests**: 17/17 PASS ✓
- **Error handling tests**: 12/12 PASS ✓
- **Resource safety tests**: 5/5 PASS ✓
- **Concurrency tests**: 4/4 PASS ✓
- **Astropy limits tests**: 5/5 PASS ✓
- **Overall pass rate**: 68/68 (100%) ✓
- **API crashes**: 0 ✓
- **Validation coverage**: Date format, time format, time range, coordinates, frame count ✓

### Performance Notes
- Frame count scaling: 10-500 frames complete within acceptable time; 1000+ may timeout
- Memory usage: Stable across 100 sequential requests
- Connection pool: Properly recovers after stress testing
- Date precision: Maintained for all dates 1900-2100

## [1.1.0] - 2026-07-31

### Added
- Mercury: API endpoint and frontend animation with live position data
- Venus: API endpoint and frontend animation with live position and glare magnitude data
- Mars: API endpoint and frontend animation with live position and orbital phase data
- Outer planets: Full support for Jupiter, Saturn, Uranus, and Neptune with API endpoints and frontend animations
- Camera control system: Named camera positions for each celestial object with zoom and pan capabilities
- Enhanced test coverage: E2E tests for all camera view positions and transitions

### Changed
- Refactored: Eliminated duplicate code blocks across planet/sun/moon astronomy services for improved maintainability
- Reorganized: Research and development scripts moved to dedicated `research/` folder, excluded from coverage calculations
- Improved: Test robustness against browser quirks (Firefox/WebKit) and timing-dependent snapshot tests
- Updated: Python requirement from 3.11 to 3.14
- Updated: Starlette requirement from >=1.0.1 to >=1.3.1
- Updated: Numerous frontend dependencies and GitHub Actions versions

### Fixed
- E2E tests: Fixed reset animation state issues and improved frame synchronization for reliable screenshot captures
- CI workflow: Corrected YAML encoding issues (em-dash, comparison operator symbols)
- TypeScript: Resolved @typescript-eslint/parser peer dependency conflicts
- Frontend: Fixed button ordering in header and A11y translation issues
- Pylint: Moved `sys` import to module toplevel and corrected line length violations

### Chores
- Established pytest coverage threshold at 90% (`fail_under`) as hard minimum for code quality
- Added comprehensive type hints and improved API documentation
- Dependency management: Regular updates via Dependabot for npm, pip, and GitHub Actions

### QA Attestation
- **Automated tests**: All unit, integration, and E2E tests pass
- **Security scan**: Bandit + pip-audit + npm audit — no known vulnerabilities
- **Accessibility audit**: Manual and automated checks pass
- **Licence audit**: No incompatible changes
- **Production build verification**: Artifacts verified clean

## [1.0.2] - 2026-05-31

### Added
- Language selection in the footer; support for en-UK and en-US
- Recentre button: returns to the default camera position with toast message
- Date range is centered at the bottom; map fits the view; animation canvas adjusted to fit view
- HTTPS configuration and hosting information

### Changed
- Solar System objects are now proportioned closer to real life; Sun, Moon, and Earth sizes improved
- Button style in footer is consistent; text is white; favicon added to About button
- Language support moved to resource files

### Fixed
- Fixed API proxy and gunicorn config

### Security
- Updated idna requirement from >=3.15 to >=3.16

### QA Attestation
- **Automated tests**: All unit, integration, and E2E tests pass
- **Security scan**: Bandit + pip-audit + npm audit — no known vulnerabilities
- **Accessibility audit**: Manual and automated checks pass
- **Licence audit**: No incompatible changes
- **Production build verification**: Artifacts verified clean

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
