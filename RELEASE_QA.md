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
|File                  | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s 
|----------------------|---------|----------|---------|---------|-------------------
|All files             |     100 |    94.64 |     100 |     100 |                   
| src                  |     100 |      100 |     100 |     100 |                   
|  i18n.ts             |     100 |      100 |     100 |     100 |                   
| src/composables      |     100 |      100 |     100 |     100 |                   
|  useAstronomyData.ts |     100 |      100 |     100 |     100 |                   
|src/locales          |     100 |      100 |     100 |     100 |                   
|  en.json             |     100 |      100 |     100 |     100 |                   
|  xx-reverse.json     |     100 |      100 |     100 |     100 |                   
| src/services         |     100 |       90 |     100 |     100 |                   
|  api.ts              |     100 |       90 |     100 |     100 | 70                
| src/three/objects    |     100 |     90.9 |     100 |     100 |                   
|  Earth.ts            |     100 |      100 |     100 |     100 |                   
|  Moon.ts             |     100 |       90 |     100 |     100 | 18                
|  Sun.ts              |     100 |       90 |     100 |     100 | 19                

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

andit -r api                                                                         
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
