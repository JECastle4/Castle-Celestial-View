# Release QA Checklist

Complete this checklist before tagging a release. Capture evidence for each section and link it in the GitHub Release notes.

---

## 1. Automated Tests

Run the full test suite and confirm all checks pass.

### API (Python)

```bash
pytest
```

- [ ] All unit tests pass
- [ ] Code coverage meets project threshold
- [ ] No new test failures introduced

#### 2026-05-01 218 passed, 10 warnings in 11.57s

|File                                      |Stmts |Miss  |Cover  | Missing                           |
|------------------------------------------|------|------|-------|----------------------------------|
|api\__init__.py                           |     0|      0|   100%||
|api\i18n.py                               |    68|      0|   100%||
|api\main.py                               |    64|      3|    95%|   46-48|
|api\models.py                             |    84|      0|   100%||
|api\routes.py                              |    77|    14  |  82%  | 73-79, 111-112, 155-156, 199-200, 247-248, 298-299|
|api\services\__init__.py                  |     0|      0|   100%||
|api\services\batch_earth_observations.py  |    44|      0|   100%||
|api\services\dates.py                     |    10|      0|   100%||
|api\services\moon.py                      |    21|      0|   100%||
|api\services\moon_phase.py                |    49|      0|   100%||
|api\services\sun.py                       |    20|      0|   100%||

#### 2026-05-22 218 passed, 10 warnings in 11.00s

|Name                                       |Stmts   |Miss  |Cover   |Missing|
|------------------------------------------|------|------|-------|----------------------------------|
|api\__init__.py                            |    0   |   0  | 100%||
|api\i18n.py                                |   68   |   0  | 100%||
|api\main.py                                |   64   |   3  |  95%   |48-50|
|api\models.py                              |   84   |   0  | 100%   |
|api\routes.py                              |   77   |  14  |  82%   |80-86, 118-119, 162-163, 206-207, 254-255, 305-306|
|api\services\__init__.py                   |    0   |   0  | 100%||
|api\services\batch_earth_observations.py   |   44   |   0  | 100%||
|api\services\dates.py                      |   10   |   0  | 100%||
|api\services\moon.py                       |   21   |   0  | 100%||
|api\services\moon_phase.py                 |   49   |   0  | 100%||
|api\services\sun.py                        |   20   |   0  | 100%||
|api\utils.py                               |    4   |   0  | 100%||

#### 2026-05-31 218 passed, 10 warnings in 13.91s
Identical coverage to 2026-05-22

#### 2026-07-31 552 passed. 5 deselected, 11 warnings in 50.27s

|Name                                       |Stmts   |Miss  |Cover   |Missing|
|------------------------------------------|--------|------|--------|--------|
|api\__init__.py                              |  0      |0   |100%
|api\i18n.py                                  | 64      |0   |100%
|api\main.py                                  | 64      |4    |94%   55-57, 108
|api\models.py                                |241      |0   |100%||
|api\routes.py                                |171     |28    |84%   |111-117, 149-150, 193-194, 237-238, 378-379, 503, 510-511, 563, 570-571, 623, 630-631, 683, 690-691, 741-742, 799-800|
|api\services\__init__.py                     |  0      |0   |100%||
|api\services\batch_earth_observations.py     | 97      |3    |97%   |62, 67, 69|
|api\services\common_bodies.py                | 47      |2    |96%   |45, 47|
|api\services\dates.py                        | 10      |0   |100%||
|api\services\inferior_planets.py             | 38      |1    |97%   |193|
|api\services\jupiter.py                      | 12      ||0   |100%||
|api\services\mars.py                         | 50      |2    |96%   |244, 247|
|api\services\mercury.py                      |  7      |0   |100%||
|api\services\moon.py                         | 11      |0   |100%||
|api\services\moon_phase.py                   | 44      |0   |100%||
|api\services\neptune.py                      | 12      |0   |100%||
|api\services\outer_planets.py                | 31      |3    |90%   |50, 75-77|
|api\services\saturn.py                       | 12      |0   |100%||
|api\services\sun.py                          | 11      |0   |100%||
|api\services\uranus.py                       | 12      |0   |100%||
|api\services\venus.py                        |  7      |0   |100%||
|api\utils.py                                 |  4      |0   |100%||
|research\MoonPhase.py                        | 39      |2    |95%   |66, 70|
|research\MoonRiseAndSet.py                   |144     |17    |88%   |166-168, 237-243, 247-253|
|research\SunRiseAndSet.py                    | 87     |17    |80%   |164-166, 236-242, 246-252|

### Frontend (Vitest)

```bash
cd frontend
npm run test:coverage
```

#### 2026-05-11

|Passed    |Skipped        |
|----------|---------------|
| 151      | 22 (173)      |

#### 2026-05-22

|Passed    |Skipped        |
|----------|---------------|
| 151      | 22 (173)      |

#### 2026-05-11 + 2026-05-22

|File                  | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s |
|----------------------|---------|----------|---------|---------|-------------------|
|All files             |     100 |    94.64 |     100 |     100 |                   |
| src                  |     100 |      100 |     100 |     100 |                   |
|  i18n.ts             |     100 |      100 |     100 |     100 |                   |
| src/composables      |     100 |      100 |     100 |     100 |                   |
|  useAstronomyData.ts |     100 |      100 |     100 |     100 |                   |
|src/locales          |     100 |      100 |     100 |     100 |                   |
|  en.json             |     100 |      100 |     100 |     100 |                   |
|  xx-reverse.json     |     100 |      100 |     100 |     100 |                   |
| src/services         |     100 |       90 |     100 |     100 |                   |
|  api.ts              |     100 |       90 |     100 |     100 | 70                |
| src/three/objects    |     100 |     90.9 |     100 |     100 |                   |
|  Earth.ts            |     100 |      100 |     100 |     100 |                   |
|  Moon.ts             |     100 |       90 |     100 |     100 | 18                |
|  Sun.ts              |     100 |       90 |     100 |     100 | 19                |

#### 2026-05-31

|Passed    |Skipped        |
|----------|---------------|
| 160      | 22 (182)      |

#### 2026-05-31

|File                  | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s |
|----------------------|---------|----------|---------|---------|-------------------|
|All files             |     100 |    95.08 |     100 |     100 |                   |
| src                  |     100 |      100 |     100 |     100 |                   |
|  i18n.ts             |     100 |      100 |     100 |     100 |                  |
| src/composables      |     100 |      100 |     100 |     100 |                   |
|  useAstronomyData.ts |     100 |      100 |     100 |     100 |                   |
|  useToast.ts         |     100 |      100 |     100 |     100 |                   |
| src/locales          |     100 |      100 |     100 |     100 |                   |
|  en-UK.json          |     100 |      100 |     100 |     100 |                   |
|  en-US.json          |     100 |      100 |     100 |     100 |                   |
|  xx-reverse.json     |     100 |      100 |     100 |     100 |                   |
| src/services         |     100 |       90 |     100 |     100 |                   |
|  api.ts              |     100 |       90 |     100 |     100 | 70                |
| src/three/objects    |     100 |     90.9 |     100 |     100 |                   |
|  Earth.ts            |     100 |      100 |     100 |     100 |                   |
|  Moon.ts             |     100 |       90 |     100 |     100 | 18                |
|  Sun.ts              |     100 |       90 |     100 |     100 | 19                |

- [ ] All unit/component tests pass

## 2026-07-31

|File                  | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s |
|----------------------|---------|----------|---------|---------|-------------------|
|All files             |     100 |    92.43 |     100 |     100 |                   |
| src                  |     100 |      100 |     100 |     100 |                   |
|  i18n.ts             |     100 |      100 |     100 |     100 |                   |
| src/components       |     100 |       84 |     100 |     100 |                   |
|  Header.vue          |     100 |      100 |     100 |     100 |                   |
|  PlanetCarousel.vue  |     100 |    81.81 |     100 |     100 | 52-61,79,96       |
| src/composables      |     100 |      100 |     100 |     100 |                   |
|  useAstronomyData.ts |     100 |      100 |     100 |     100 |                   |
|  useToast.ts         |     100 |      100 |     100 |     100 |                   |
| src/config           |     100 |      100 |     100 |     100 |                   |
|  cameraPresets.ts    |     100 |      100 |     100 |     100 |                   |
|  celestialBodies.ts  |     100 |      100 |     100 |     100 |                   |
| src/locales          |     100 |      100 |     100 |     100 |                   |
|  en-UK.json          |     100 |      100 |     100 |     100 |                   |
|  en-US.json          |     100 |      100 |     100 |     100 |                   |
|  xx-reverse.json     |     100 |      100 |     100 |     100 |                   |
| src/services         |     100 |       90 |     100 |     100 |                   |
|  api.ts              |     100 |       90 |     100 |     100 | 70                |
| src/three            |     100 |      100 |     100 |     100 |                   |
|  cameraAnimation.ts  |     100 |      100 |     100 |     100 |                   |
| src/three/objects    |     100 |    91.17 |     100 |     100 |                   |
|  Earth.ts            |     100 |      100 |     100 |     100 |                   |
|  Jupiter.ts          |     100 |    91.66 |     100 |     100 | 24                |
|  Mars.ts             |     100 |    91.66 |     100 |     100 | 24                |
|  Mercury.ts          |     100 |       90 |     100 |     100 | 23                |
|  Moon.ts             |     100 |       90 |     100 |     100 | 21                |
|  Neptune.ts          |     100 |    91.66 |     100 |     100 | 24                |
|  Saturn.ts           |     100 |    91.66 |     100 |     100 | 24                |
|  Sun.ts              |     100 |       90 |     100 |     100 | 23                |
|  Uranus.ts           |     100 |    91.66 |     100 |     100 | 24                |
|  Venus.ts            |     100 |       90 |     100 |     100 | 21                |
| src/utils            |     100 |      100 |     100 |     100 |                   |
|  locale.ts           |     100 |      100 |     100 |     100 | |

|Heading|Skipped|
|-------|-------|
|Test Files  23 passed | 1 skipped (24)|
|      Tests  472 passed | 22 skipped (494)|
|   Start at  20:49:09||

### End-to-End (Playwright)

```bash
cd frontend
npm run test:e2e
```

- [ ] All E2E tests pass
- [ ] Visual snapshots match (no unexpected regressions)

**Evidence**: Link to the CI run on the release commit showing all checks green.

#### 2026-05-11
Running 44 tests using 11 workers
  44 passed (38.4s)

#### 2026-05-22
Running 44 tests using 11 workers
  44 passed (41.1s)

#### 2026-05-31
Running 48 tests using 11 workers

#### 2026-07-31 (from CI)

|Heading|Time|Hash|
|-------|----|----|
|164 passed |(11.2m)| |
|CI git ||1ee3e514a697aee0df83c2fbaf560f687b08a5bf|
|Local git ||1ee3e514a697aee0df83c2fbaf560f687b08a5bf|

---

## 2. Security Scan

Security scans run automatically in CI, but confirm they are clean on the release commit.

- [ ] **Bandit** (Python static analysis) — no high or critical issues
- [ ] **pip-audit** — no known CVEs in production dependencies
- [ ] **npm audit** — no high or critical vulnerabilities in frontend dependencies

```bash
# Run locally if needed
bandit -r api/
pip-audit
cd frontend && npm audit
```

**Evidence**: CI run log showing security steps passing, or local scan output attached to the release.

#### 2026-05-11
npm audit
found 0 vulnerabilities
bandit -r api
[main]  INFO    profile include tests: None
[main]  INFO    profile exclude tests: None
[main]  INFO    cli include tests: None
[main]  INFO    cli exclude tests: None
[main]  INFO    running on Python 3.14.2
Run started:2026-05-11 21:33:33.987199+00:00

Test results:
        No issues identified.

Code scanned:
        Total lines of code: 1245
        Total lines skipped (#nosec): 0

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
Files skipped (0):

pip-audit --skip-editable
No known vulnerabilities found
---

#### 2026-05-22
npm audit
found 0 vulnerabilities

bandit -r api
[main]  INFO    profile include tests: None
[main]  INFO    profile exclude tests: None
[main]  INFO    cli include tests: None
[main]  INFO    cli exclude tests: None
[main]  INFO    running on Python 3.14.2
Run started:2026-05-22 21:11:08.146809+00:00

Test results:
        No issues identified.

Code scanned:
        Total lines of code: 1261
        Total lines skipped (#nosec): 0

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
Files skipped (0):
pip-audit --skip-editable
\ Collecting inputsWARNING: Ignoring invalid distribution ~vicorn (C:\Users\jecas\OneDrive\Documents\Programming\Python\.venv\Lib\site-packages)
No known vulnerabilities found

#### 2026-07-31

npm audit
5 high severity vulnerabilities
bandit -r api
[main]  INFO    profile include tests: None
[main]  INFO    profile exclude tests: None
[main]  INFO    cli include tests: None
[main]  INFO    cli exclude tests: None
[main]  INFO    running on Python 3.14.2
Run started:2026-07-31 20:02:25.896944+00:00

Test results:
        No issues identified.

Code scanned:
        Total lines of code: 3482
        Total lines skipped (#nosec): 0

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
Files skipped (0):

## 3. Accessibility Audit

Perform a manual accessibility review of all primary views before each release.

### Scope

Review the following views in a browser at production build (`npm run build && npm run preview`):

- [ ] Home / Landing page
- [ ] Solar System view
- [ ] Sky view
- [ ] About page


### Checks

For each view:

- [ ] All interactive elements are keyboard-navigable (Tab, Enter, Space)
- [ ] All images and icons have meaningful `alt` text or `aria-label`
- [ ] Colour contrast meets WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text)
- [ ] No content is conveyed by colour alone
- [ ] Page title and landmark regions (`<main>`, `<nav>`, `<header>`) are present
- [ ] Focus indicators are visible on all focusable elements

### Tools

Use one or more of the following to assist:

- Browser DevTools **Accessibility** panel
- [axe DevTools](https://www.deque.com/axe/) browser extension
- [WAVE](https://wave.webaim.org/) browser extension

**Evidence**: Screenshots or screen recordings of each view with the accessibility tool output. Attach to the GitHub Release or link to an external document.

#### 2026-05-11

0 Issues found on all views

#### 2026-05-22

0 Issues found on all views

#### 2026-05-31

0 Issues found on all views

#### 2026-07-31

0 Issues found on all views

---

## 4. Third-Party Licence Audit

Verify that all production dependencies carry licences that are compatible with this project before each release.

### API (Python)

```bash
pip install pip-licenses
pip-licenses --order=license --format=markdown
```

- [ ] All production dependencies listed
- [ ] No GPL, AGPL, or other copyleft licences that would conflict with this project's [LICENSE](LICENSE)
- [ ] NOTICE file updated if any new attribution is required

### Frontend (Node)

```bash
cd frontend
npx license-checker --production --summary
```

- [ ] All production dependencies listed
- [ ] No incompatible licences
- [ ] NOTICE file updated if any new attribution is required

**Evidence**: Output of the above commands saved as a text file or table, attached to the GitHub Release.

---

## 5. Production Build Verification

Confirm the release artifacts are clean and correct (see [BUILD.md](BUILD.md)).

- [ ] `python -m build` completes without errors
- [ ] Wheel filename contains the correct version: `astronomy_tools-<version>-py3-none-any.whl`
- [ ] `xx-reverse.json` is **not** present inside the wheel: `unzip -l dist/*.whl | grep xx-reverse` returns nothing
- [ ] `npm run build` completes without errors
- [ ] `xx-reverse` string is **absent** from `frontend/dist/`: `grep -r "xx-reverse" frontend/dist/` returns nothing
- [ ] Frontend dist `index.html` is present and non-empty

---

## 6. Manual Acceptance

Smoke-test the production build end-to-end in a browser.

```bash
# Serve the frontend dist against the running API
cd frontend && npm run preview
```

- [ ] App loads without console errors
- [ ] At least one astronomy calculation returns a correct result
- [ ] Language switching (if applicable) works correctly
- [ ] No broken links or missing assets

---

## Sign-Off

| Area | Passed | Evidence |
|------|--------|----------|
| Automated tests | Yes| See above|
| Security scan | Yes| See above|
| Accessibility audit | Yes| See above|
| Licence audit | Yes| No substantive change since licence and About were last generated|
| Production build verification | Fixed on branch| See changes to enable preview|
| Manual acceptance | Yes| See above|

Once all rows are complete, proceed to tagging the release as described in [RELEASE_PROCESS.md](RELEASE_PROCESS.md).
