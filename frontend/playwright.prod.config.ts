import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for production release verification.
 *
 * Used by scripts/verify-production-release.sh to run all E2E tests against a
 * live deployment of the release artifacts (API wheel + frontend dist).
 *
 * Key differences from the default playwright.config.ts:
 *   - No webServer block — servers are started externally by the verify script.
 *   - baseURL reads from PLAYWRIGHT_BASE_URL (set by the script) or defaults to
 *     http://localhost:4173 (vite preview port, matching vite.config.ts).
 *   - Edge excluded — msedge is not present in Docker / Linux CI.
 *   - Retries disabled — flaky production servers should fail, not be retried.
 *   - HTML report written to playwright-report-prod/ to avoid overwriting the
 *     dev report in playwright-report/.
 */
export default defineConfig({
  testDir: './tests/e2e',

  timeout: 30 * 1000,

  fullyParallel: true,

  forbidOnly: !!process.env.CI,

  // No retries: a failure against production artifacts should be investigated,
  // not automatically retried.
  retries: 0,

  workers: process.env.CI ? 1 : undefined,

  reporter: [['html', { outputFolder: 'playwright-report-prod', open: 'never' }]],

  use: {
    // The verify script sets PLAYWRIGHT_BASE_URL; default matches vite preview port.
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:4173',

    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // No webServer — the verify script starts both servers before running this config.

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          firefoxUserPrefs: {
            'dom.webgl.force-enabled': true,
            'webgl.force-enabled': true,
          },
        },
      },
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1280, height: 720 },
      },
    },
    // Edge excluded: requires the msedge channel which is not available in Docker
    // or standard Linux environments. Run the default playwright.config.ts on
    // Windows to cover Edge.
  ],

  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.002,
      threshold: 0.2,
      animations: 'disabled',
    },
  },
});
