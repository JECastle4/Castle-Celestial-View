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

### Frontend (Vitest)

```bash
cd frontend
npm run test
```

- [ ] All unit/component tests pass

### End-to-End (Playwright)

```bash
cd frontend
npm run test:e2e
```

- [ ] All E2E tests pass
- [ ] Visual snapshots match (no unexpected regressions)

**Evidence**: Link to the CI run on the release commit showing all checks green.

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

---

## 3. Accessibility Audit

Perform a manual accessibility review of all primary views before each release.

### Scope

Review the following views in a browser at production build (`npm run build && npm run preview`):

- [ ] Home / Landing page
- [ ] Sun position view
- [ ] Moon phase view
- [ ] Moon rise/set view
- [ ] Solar system animation
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
| Automated tests | | |
| Security scan | | |
| Accessibility audit | | |
| Licence audit | | |
| Production build verification | | |
| Manual acceptance | | |

Once all rows are complete, proceed to tagging the release as described in [RELEASE_PROCESS.md](RELEASE_PROCESS.md).
