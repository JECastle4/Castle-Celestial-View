# Web Frontend Setup Guide

## Step 1: Install Node.js

Download and install Node.js from: https://nodejs.org/

Choose the **LTS version** (Long Term Support) - currently 20.x or newer.

Verify installation:
```powershell
node --version
npm --version
```

## Step 2: Install Dependencies

Navigate to the frontend directory and install packages:

```powershell
cd frontend
npm install
```

This will install:
- Vue 3
- TypeScript
- Vite (build tool)
- Three.js
- OrbitControls

## Step 3: Start the Backend API

In a separate terminal, start the FastAPI server:

```powershell
# From the Python project root
uvicorn api.main:app --reload
```

API should be running on: http://localhost:8000

## Step 4: Start the Frontend Dev Server

In the frontend directory:

```powershell
npm run dev
```

Frontend will be available at: http://localhost:5173

## Step 5: Test the Application

1. Open http://localhost:5173 in your browser
2. Enter location details (default: London - 51.5°N, 0.1°W)
3. Set date range (default: 24 hours)
4. Click "Load Data" - this will fetch from your local API
5. Use "Play" to animate
6. Use mouse to orbit the camera

## Regional landing pages

British English uses `/en-GB/` (Home), `/en-GB/events` and `/en-GB/about`;
American English uses the equivalent `/en-US/` routes. Both language resources
are retained, including regional spelling such as Recentre/Recenter. The bare
root defaults to British English, without overriding an explicitly chosen region.

Old `/en-UK/...` links redirect to `/en-GB/...`, preserving the page, query and
fragment. The production nginx configuration supplies permanent HTTP redirects;
Vue Router also handles legacy links on static/development servers. The API
loads `en-gb.json`, accepts case-insensitive tags and retains `en-UK` as an alias
for older clients, in query parameters and Accept-Language headers.

`src/metadata.ts` is the shared source of production route/locale metadata.
Each Home, Events and About page has its own title, description and self-canonical
URL. Reciprocal `en-GB`/`en-US` hreflang links identify regional alternatives;
`x-default` points to the British version of the same page. These are selection
signals for search engines, not guaranteed regional search placement. Canonical
URLs omit search-state query parameters and fragments.

The visible application heading and header mode controls are unchanged.
Localized introductory copy appears above the homepage map before loading data.
On narrow screens the explanation, map, date picker and query controls scroll
together; the language selector remains in the footer.

**Delivery boundary:** this first slice updates metadata on client navigation.
Page-specific initial HTML, crawler-visible navigation, social cards, robots and
the four-URL Home/Events sitemap are subsequent work. Do not treat this slice
alone as complete search-engine or sharing-crawler support.

### Focused verification

From `frontend/`:

```bash
npx vitest run src/metadata.test.ts src/router.test.ts src/i18n.test.ts src/utils/locale.test.ts src/components/Footer.test.ts src/components/Header.test.ts src/views/EventsView.test.ts src/composables/contactTimesCancellation.test.ts
npm run build
npm run lint:a11y
```

With the built frontend served by `npm run preview`, the production-artifact
configuration can verify navigation and responsive layout without an API:

```bash
npx playwright test tests/e2e/regional-landing-pages.spec.ts --config=playwright.prod.config.ts --project=chromium
```

From the repository root, verify API locale loading and negotiation:

```bash
python -m pytest tests/test_api_i18n.py tests/test_main_integration.py::TestLocaleResolution tests/test_api_routes.py::TestAcceptLanguage -o addopts=''
```

When using Node versions exposing experimental global Web Storage, run Vitest
with `NODE_OPTIONS=--no-experimental-webstorage` so happy-dom provides browser
storage. The browser checks cover both spellings, legacy URLs, reciprocal
alternates, direct entry, back/forward navigation and 320/390/1024/1280px layouts.

## CORS Configuration

The FastAPI backend needs CORS enabled for local development. This should already be configured in `api/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

**Problem:** API requests fail with CORS error
**Solution:** Check CORS middleware in FastAPI and that backend is running

**Problem:** "Module not found" errors
**Solution:** Run `npm install` again

**Problem:** TypeScript errors
**Solution:** Run `npm run type-check` to see detailed errors

**Problem:** Black screen
**Solution:** Check browser console for WebGL errors (F12)

## Next Steps

- Add textures to celestial bodies
- Implement proper time interpolation between data points
- Add star background
- Add trajectory trails
- Add time controls (play/pause/speed)
- Add date picker UI
