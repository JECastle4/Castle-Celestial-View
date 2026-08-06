import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * E2E test for the Astronomical Events view (Issue 141).
 *
 * Exercises the full stack (Vue frontend -> FastAPI backend -> astropy
 * calculations) for a fixed date range known to contain one of each event
 * type: a total solar eclipse, a partial lunar eclipse, a plain new moon,
 * and a plain full moon. Expected values below were captured directly from
 * api.services.astronomical_events.get_astronomical_events() for
 * 2026-08-01..2026-09-30 and are asserted to minute-level (time) / 4-decimal
 * (magnitude) precision to tolerate harmless recalculation drift.
 *
 * The browser context pins locale to en-GB and timezone to UTC so the
 * Intl.DateTimeFormat-rendered times are deterministic regardless of the
 * host machine's locale/timezone (the app always stores/receives UTC).
 */

// WebKit on Windows does not fully honour Playwright's context `locale` for
// Intl.DateTimeFormat (it falls back to en-US-style formatting), so date/time
// assertions match both the en-GB (24h, "DD Mon YYYY") and the WebKit fallback
// (12h, "Mon DD, YYYY") renderings of the same UTC instant.
function timeVariants(hour24: string, minute: string, second: string): RegExp {
  const h = parseInt(hour24, 10);
  const hour12 = ((h + 11) % 12) + 1;
  const ampm = h < 12 ? 'AM' : 'PM';
  return new RegExp(`${hour24}:${minute}:${second}|${hour12}:${minute}:${second}\\s*${ampm}`, 'i');
}

function dateVariants(day: number, monthName: string, year: number): RegExp {
  return new RegExp(`${day}\\s*${monthName}[a-z]*\\.?\\s*${year}|${monthName}[a-z]*\\.?\\s*${day},?\\s*${year}`, 'i');
}

let persistentPage: Page;
let persistentContext: BrowserContext;
let projectConfig: any = null;

const testWithPersistentPage = test.extend({
  page: async ({ browser }, use) => {
    if (!persistentContext) {
      persistentContext = await browser.newContext({
        baseURL: projectConfig?.baseURL || 'http://localhost:5173',
        viewport: projectConfig?.viewport || { width: 1280, height: 720 },
        locale: 'en-GB',
        timezoneId: 'UTC',
      });
      persistentPage = await persistentContext.newPage();
    }
    await use(persistentPage);
  },
});

testWithPersistentPage.describe('Eclipse Events - August/September 2026 (Serial)', () => {
  testWithPersistentPage.describe.configure({ mode: 'serial' });

  testWithPersistentPage.beforeAll(async ({}, testInfo) => {
    projectConfig = testInfo.project.use;
  });

  testWithPersistentPage.afterAll(async () => {
    if (persistentContext) {
      await persistentContext.close();
    }
  });

  testWithPersistentPage('1. Search Aug-Sep 2026 and verify all 4 events are returned', async ({ page }) => {
    await page.goto('/en-UK/events');

    await expect(page.locator('.search-btn')).toBeVisible();

    const startDateInput = page.locator('.date-range-picker input[type="date"]').first();
    const endDateInput = page.locator('.date-range-picker input[type="date"]').nth(1);
    await startDateInput.fill('2026-08-01');
    await endDateInput.fill('2026-09-30');
    await page.getByRole('button', { name: /Apply/i }).click();

    await page.locator('.search-btn').click();

    // Generous timeout: the astropy eclipse search is CPU-bound and this suite
    // runs across 4 browser projects in parallel, so the backend can be busy
    // serving multiple identical requests concurrently.
    await expect(page.locator('.loading')).toBeHidden({ timeout: 90000 });
    await expect(page.locator('.error')).toHaveCount(0);
    await expect(page.locator('.event-item')).toHaveCount(4, { timeout: 90000 });

    // Events are returned in chronological order.
    const items = page.locator('.event-item');
    await expect(items.nth(0)).toContainText('Solar Total');
    await expect(items.nth(0)).toContainText(dateVariants(12, 'Aug', 2026));
    await expect(items.nth(1)).toContainText('Lunar Partial');
    await expect(items.nth(1)).toContainText(dateVariants(28, 'Aug', 2026));
    await expect(items.nth(2)).toContainText('New Moon');
    await expect(items.nth(3)).toContainText('Full Moon');
  });

  testWithPersistentPage('2. Expand the Solar Total panel and verify greatest eclipse time and size ratio', async ({ page }) => {
    const solarItem = page.locator('.event-item').filter({ hasText: 'Solar Total' });
    await solarItem.locator('.event-summary').click();

    const details = solarItem.locator('.event-details');
    await expect(details).toBeVisible();

    const rows = details.locator('.detail-row');
    // 2026-08-12 17:45:49.662 UTC greatest eclipse, size_ratio 1.031566
    await expect(rows.filter({ hasText: 'Greatest Eclipse' })).toContainText(timeVariants('17', '45', '49'));
    await expect(rows.filter({ hasText: 'Size Ratio' })).toContainText('1.0316');
  });

  testWithPersistentPage('3. Expand the Lunar Partial panel and verify greatest eclipse time and magnitudes', async ({ page }) => {
    const lunarItem = page.locator('.event-item').filter({ hasText: 'Lunar Partial' });
    await lunarItem.locator('.event-summary').click();

    const details = lunarItem.locator('.event-details');
    await expect(details).toBeVisible();

    const rows = details.locator('.detail-row');
    // 2026-08-28 04:13:04.257 UTC greatest eclipse, umbral 0.9045, penumbral 1.9387
    // "Umbral Magnitude" is anchored to start of the row text - "Penumbral Magnitude" would
    // otherwise also match a plain substring filter since it contains "umbral Magnitude".
    await expect(rows.filter({ hasText: 'Greatest Eclipse' })).toContainText(timeVariants('04', '13', '04'));
    await expect(rows.filter({ hasText: /^Umbral Magnitude/ })).toContainText('0.9045');
    await expect(rows.filter({ hasText: /^Penumbral Magnitude/ })).toContainText('1.9387');
  });

  testWithPersistentPage('4. Capture a snapshot with both eclipse panels expanded', async ({ page }) => {
    // Both panels remain expanded from tests 2 & 3 (serial, shared page).
    const solarDetails = page.locator('.event-item').filter({ hasText: 'Solar Total' }).locator('.event-details');
    const lunarDetails = page.locator('.event-item').filter({ hasText: 'Lunar Partial' }).locator('.event-details');
    await expect(solarDetails).toBeVisible();
    await expect(lunarDetails).toBeVisible();

    await expect(page.locator('.events-content')).toHaveScreenshot('events-aug-sep-2026-both-expanded.png');
  });

  testWithPersistentPage('5. Verify New Moon and Full Moon events are non-expandable (no eclipse)', async ({ page }) => {
    const newMoonSummary = page.locator('.event-item').filter({ hasText: 'New Moon' }).locator('.event-summary');
    const fullMoonSummary = page.locator('.event-item').filter({ hasText: 'Full Moon' }).locator('.event-summary');

    await expect(newMoonSummary).toHaveClass(/event-summary-static/);
    await expect(fullMoonSummary).toHaveClass(/event-summary-static/);

    await newMoonSummary.click();
    await fullMoonSummary.click();

    await expect(page.locator('.event-item').filter({ hasText: 'New Moon' }).locator('.event-details')).toHaveCount(0);
    await expect(page.locator('.event-item').filter({ hasText: 'Full Moon' }).locator('.event-details')).toHaveCount(0);
  });
});
