# Production Build Guide

This document describes how to build production artifacts for the API (Python wheel) and Frontend (static dist).

---

## Prerequisites

- Python 3.14+ with a virtual environment activated
- Node.js with `npm`
- Build tools installed: `pip install build` (for the API)

---

## API (Python Wheel)

### Build

From the repository root:

```bash
pip install build
python -m build
```

### Output

```
dist/
  astronomy_tools-<version>-py3-none-any.whl
  astronomy_tools-<version>.tar.gz
```

### Included in Distribution

- `api/` package and `api/services/` subpackage
- `api/locales/en.json` (default English)
- `api/locales/en-us.json` (American English)
- `api/locales/en-gb.json` (British English)

### Excluded from Distribution

- `api/locales/xx-reverse.json` (dev-only pseudo-locale)
- Root-level scripts (`DayOfTheWeek.py`, `MoonPhase.py`, `generate_*.py`, etc.)
- `tests/` directory

---

## Frontend (Static Dist)

### Build

From the `frontend/` directory:

```bash
npm install
npm run build
```

### Output

```
frontend/dist/
  index.html             # Readable British Home fallback
  en-GB/
    index.html           # Home: /en-GB/
    events.html          # Events: /en-GB/events
    about.html           # About: /en-GB/about
  en-US/
    index.html
    events.html
    about.html
  robots.txt
  sitemap.xml            # Home/Events in both regions, not search results
  social/
    home-v1.png          # 1200 x 630 sharing artwork
    events-v1.png
  assets/
    vendor-<hash>.js      # Vue and core dependencies
    three-<hash>.js       # Three.js (code-split)
    index-<hash>.js       # App entry point
    ...
```

The Vite plugin in `frontend/plugins/landingPages.ts` generates these regional
documents using the shared route metadata and translations. Each contains
page-specific metadata, visible introductory content and real navigation links
before JavaScript runs. Generation needs neither an API server nor WebGL.
Keep the complete directory tree when packaging or deploying `dist/`.

The same build emits `robots.txt` and a four-URL sitemap from the production
page/locale definitions. Initial and runtime HTML share Open Graph and X/Twitter
large-image metadata, including regional locales, image descriptions and absolute
HTTPS URLs. About has its own metadata but reuses the Home artwork and stays
outside the search-targeted sitemap.

Original SVG artwork is maintained in `frontend/artwork/`; checked-in PNGs in
`frontend/public/social/` make normal builds independent of a browser renderer.
To regenerate them from `frontend/`, use `npm run build:social-images` with the
existing Playwright Chromium installed (`npx playwright install chromium` if
needed). The artwork is illustrative, not an eclipse prediction or a scale model.
When changing published artwork, use a new versioned filename and update
`src/metadata.ts`; production caches those image URLs for a year.

Vue waits for the initial route before replacing the static shell. If route
loading fails, the shell remains readable and displays a startup error. The
build preview serves the clean URLs; production must also resolve
`/en-GB/events` to `en-GB/events.html` (and equivalent regional routes), rather
than serving the root Home document for every request.

### Production Optimizations

- TypeScript type-checking runs before bundling (`vue-tsc`)
- JavaScript is minified and split into optimized chunks during the Vite production build
- `import.meta.env.DEV` is replaced with `false` at build time, which tree-shakes:
  - `xx-reverse` locale from `dev-locales/xx-reverse.json`
  - The `xx-reverse` route from the router
- All `console.log` calls in dev-only branches are eliminated

### Verifying Dev Locale Exclusion

After building, confirm `xx-reverse` is absent from the output:

```bash
# Should return no results
grep -r "xx-reverse" frontend/dist/
```

---

## Release Artifacts

Both artifacts are published to the GitHub Release by the `release.yml` GitHub Actions workflow when a `v*.*.*` tag is pushed. See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for the full release workflow.
