import { test, expect, type Page } from '@playwright/test';
import type { AstronomicalEvent } from '../../src/types/api.types';

const streamPath = '**/api/v1/astronomical-events-stream?*';
const solarEvent: AstronomicalEvent = {
  event_type: 'Solar Total',
  is_lunar: false,
  date: '2026-08-12 01:45:00.000',
  julian_date: 2461264.572916667,
  moon_ecl_lat_deg: 0,
  eclipse_occurs: true,
  eclipse_type: 'Total',
  greatest_eclipse_time: '2026-08-12 01:45:00.000',
  umbral_magnitude: null,
  penumbral_magnitude: null,
  size_ratio: 1.03,
  contact_times: { eclipse_begins: '2026-08-12 01:15:00.000' },
};

function streamResponse(event: AstronomicalEvent): string {
  return [
    `event: page\ndata: ${JSON.stringify({ page: 1, events: [event] })}\n\n`,
    `event: metadata\ndata: ${JSON.stringify({ total_events: 1, total_pages: 1 })}\n\n`,
  ].join('');
}

async function selectRange(page: Page) {
  const inputs = page.locator('.date-range-picker input[type="date"]');
  await inputs.nth(0).fill('2026-08-01');
  await inputs.nth(1).fill('2026-08-31');
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
}

test.describe('Events browser regressions', () => {
  test.use({ locale: 'en-GB', timezoneId: 'America/Los_Angeles' });

  test('refreshes completed results through the locale menu without changing the selected dates', async ({ page }) => {
    const requests: URL[] = [];
    await page.route(streamPath, async (route) => {
      const url = new URL(route.request().url());
      requests.push(url);
      // UK and US event names currently match in production; distinct fixture labels
      // prove that the new response replaces the old results, not just surrounding UI.
      const event = { ...solarEvent, event_type: `Result for ${url.searchParams.get('lang')}` };
      await route.fulfill({
        contentType: 'text/event-stream',
        body: streamResponse(event),
      });
    });

    await page.goto('/en-UK/events');
    await selectRange(page);
    await page.getByRole('button', { name: 'Search', exact: true }).click();
    await expect(page.locator('.event-type')).toHaveText('Result for en-UK');

    await page.getByRole('button', { name: 'Current language: English (UK)', exact: true }).click();
    await page.getByRole('button', { name: 'English (US)', exact: true }).click();

    await expect(page).toHaveURL(/\/en-US\/events$/);
    await expect(page.locator('.event-type')).toHaveText('Result for en-US');
    expect(requests.map((url) => url.searchParams.get('lang'))).toEqual(['en-UK', 'en-US']);
    for (const url of requests) {
      expect(url.searchParams.get('start_date')).toBe('2026-08-01');
      expect(url.searchParams.get('end_date')).toBe('2026-08-31');
    }
    await expect(page.locator('.date-range-picker input[type="date"]').nth(0)).toHaveValue('2026-08-01');
    await expect(page.locator('.date-range-picker input[type="date"]').nth(1)).toHaveValue('2026-08-31');
  });

  test('preserves local calendar dates and displays UTC event instants in local time', async ({ page }) => {
    await page.clock.setFixedTime(new Date('2026-10-28T01:00:00Z'));
    await page.route(streamPath, (route) => route.fulfill({
      contentType: 'text/event-stream',
      body: streamResponse(solarEvent),
    }));

    await page.goto('/en-UK/events');
    const inputs = page.locator('.date-range-picker input[type="date"]');
    await expect(inputs.nth(0)).toHaveValue('2026-10-27');
    await expect(inputs.nth(1)).toHaveValue('2027-10-27');

    await selectRange(page);
    const dates = page.locator('.parameter-value');
    await expect(dates.nth(0)).toHaveText(/1\s+Aug[a-z]*\s+2026|Aug[a-z]*\s+1,\s+2026/i);
    await expect(dates.nth(1)).toHaveText(/31\s+Aug[a-z]*\s+2026|Aug[a-z]*\s+31,\s+2026/i);

    await page.getByRole('button', { name: 'Search', exact: true }).click();
    const summary = page.locator('.event-summary');
    // 01:45 UTC on August 12 is 18:45 PDT on August 11.
    await expect(summary.locator('.event-date')).toHaveText(
      /(?:11\s+Aug[a-z]*\s+2026|Aug[a-z]*\s+11,\s+2026).*?(?:18:45|6:45\s*PM)/i,
    );
    await summary.click();
    const details = page.locator('.event-details');
    await expect(details.locator('.detail-row').filter({ hasText: 'Greatest Eclipse' }).locator('dd'))
      .toHaveText(/18:45:00|6:45:00\s*PM/i);
    await expect(details.locator('.detail-row').filter({ hasText: 'Eclipse Begins' }).locator('dd'))
      .toHaveText(/18:15:00|6:15:00\s*PM/i);
  });

  test('shares contact-time loads with export and aborts them when leaving the view', async ({ page }) => {
    await page.route(streamPath, (route) => route.fulfill({
      contentType: 'text/event-stream',
      body: streamResponse({ ...solarEvent, contact_times: null }),
    }));
    let contactRequests = 0;
    let releaseResponse!: () => void;
    const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });
    await page.route('**/api/v1/astronomical-events/contact-times?*', async (route) => {
      contactRequests++;
      await responseGate;
      await route.fulfill({ json: { contact_times: solarEvent.contact_times } });
    });

    await page.goto('/en-UK/events');
    await selectRange(page);
    await page.getByRole('button', { name: 'Search', exact: true }).click();
    await page.locator('.event-summary').click();
    await expect.poll(() => contactRequests).toBe(1);
    await page.getByRole('button', { name: 'CSV (1)', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeDisabled();
    expect(contactRequests).toBe(1);

    const aborted = page.waitForEvent('requestfailed', {
      predicate: (request) => request.url().includes('/astronomical-events/contact-times'),
    });
    try {
      await page.getByRole('button', { name: 'Solar System', exact: true }).click();
      await expect(page).toHaveURL(/\/en-UK\/$/);
      const request = await aborted;
      expect(request.failure()?.errorText).toMatch(/abort|cancel/i);
      expect(contactRequests).toBe(1);
    } finally {
      releaseResponse();
    }
  });
});
