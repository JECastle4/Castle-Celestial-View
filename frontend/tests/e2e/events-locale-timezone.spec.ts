import { test, expect, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { withRuntimeServer } from './helpers/runtime-server';
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
  const browserErrors = new WeakMap<Page, string[]>();
  const expectedHttpErrors = new WeakMap<Page, Set<number>>();

  test.beforeEach(async ({ page }) => {
    // Navigation reaches the map view; keep unrelated network failures out of console evidence.
    await page.route('https://tile.openstreetmap.org/**', (route) => route.fulfill({
      contentType: 'image/png',
      body: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII=',
        'base64',
      ),
    }));
    const errors: string[] = [];
    browserErrors.set(page, errors);
    expectedHttpErrors.set(page, new Set());
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('console', (message) => {
      if (message.type() !== 'error') return;
      const expectedStatus = [...(expectedHttpErrors.get(page) ?? [])].some((status) =>
        message.text().startsWith('Failed to load resource:') &&
        message.text().includes(`status of ${status}`) &&
        message.location().url.includes('/api/v1/astronomical-events/contact-times'));
      if (!expectedStatus) errors.push(message.text());
    });
  });

  test.afterEach(({ page }) => {
    expect(browserErrors.get(page)).toEqual([]);
  });

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

  for (const transition of ['new search', 'locale change'] as const) {
    test(`keeps contact loads alive across a ${transition} without applying stale results`, async ({ page }) => {
      let searches = 0;
      await page.route(streamPath, (route) => {
        searches++;
        return route.fulfill({
          contentType: 'text/event-stream',
          body: streamResponse({
            ...solarEvent, event_type: `Search ${searches}`, contact_times: null,
          }),
        });
      });
      let contactRequests = 0;
      const failedRequests: string[] = [];
      page.on('requestfailed', (request) => {
        if (request.url().includes('/astronomical-events/contact-times')) {
          failedRequests.push(request.failure()?.errorText ?? 'unknown failure');
        }
      });
      let releaseFirst!: () => void;
      let releaseSecond!: () => void;
      const firstGate = new Promise<void>((resolve) => { releaseFirst = resolve; });
      const secondGate = new Promise<void>((resolve) => { releaseSecond = resolve; });
      await page.route('**/api/v1/astronomical-events/contact-times?*', async (route) => {
        const index = ++contactRequests;
        await (index === 1 ? firstGate : secondGate);
        await route.fulfill({ json: { contact_times: solarEvent.contact_times } });
      });

      try {
        await page.goto('/en-UK/events');
        await selectRange(page);
        await page.getByRole('button', { name: 'Search', exact: true }).click();
        await expect(page.locator('.event-type')).toHaveText('Search 1');
        await page.locator('.event-summary').click();
        await expect.poll(() => contactRequests).toBe(1);

        if (transition === 'new search') {
          await page.getByRole('button', { name: 'Search', exact: true }).click();
        } else {
          await page.getByRole('button', { name: 'Current language: English (UK)', exact: true }).click();
          await page.getByRole('button', { name: 'English (US)', exact: true }).click();
        }
        await expect(page.locator('.event-type')).toHaveText('Search 2');
        const completed = page.waitForResponse((response) =>
          response.url().includes('/astronomical-events/contact-times'));
        releaseFirst();
        const response = await completed;
        expect(await response.finished()).toBeNull();
        expect(response.status()).toBe(200);
        // A fresh load proves the old response did not populate the replacement event.
        await page.locator('.event-summary').click();
        await expect.poll(() => contactRequests).toBe(2);
        releaseSecond();
        await expect(page.locator('.event-details .detail-row').filter({ hasText: 'Eclipse Begins' }))
          .toBeVisible();
        expect(failedRequests).toEqual([]);
      } finally {
        releaseFirst();
        releaseSecond();
      }
    });
  }

  test('browser cancellation reaches the API and records a disconnected calculation', async ({ page, request }, testInfo) => {
    await withRuntimeServer(request, testInfo, {
      TEST_RUNTIME_BLOCK_CONTACT: 'true',
    }, async (origin) => {
      await page.route(streamPath, (route) => route.fulfill({
        contentType: 'text/event-stream',
        body: streamResponse({ ...solarEvent, contact_times: null }),
      }));
      await page.route('**/api/v1/astronomical-events/contact-times?*', (route) => {
        const url = new URL(route.request().url());
        return route.continue({ url: `${origin}${url.pathname}${url.search}` });
      });
      await page.goto('/en-UK/events');
      await selectRange(page);
      await page.getByRole('button', { name: 'Search', exact: true }).click();
      await page.locator('.event-summary').click();
      await expect.poll(async () =>
        (await (await request.get(`${origin}/__test/state`)).json()).contact_started,
      ).toBe(1);
      const aborted = page.waitForEvent('requestfailed', {
        predicate: (active) => active.url().includes('/astronomical-events/contact-times'),
      });
      await page.getByRole('button', { name: 'Solar System', exact: true }).click();
      expect((await aborted).failure()?.errorText).toMatch(/abort|cancel/i);
      const released = await request.post(`${origin}/__test/release`);
      expect(released.ok()).toBe(true);
      await expect.poll(async () =>
        (await request.get(`${origin}/api/metrics`)).text(),
      ).toContain(
        'abandoned_work_total{endpoint="/api/v1/astronomical-events/contact-times",reason="client_disconnect"} 1.0',
      );
      const metrics = await (await request.get(`${origin}/api/metrics`)).text();
      expect(metrics).not.toContain('error_type="');
      expect(metrics).not.toContain('reason="timeout"');
    });
  });

  test('completes one shared details/export request and downloads populated CSV', async ({ page }) => {
    await page.route(streamPath, (route) => route.fulfill({
      contentType: 'text/event-stream',
      body: streamResponse({ ...solarEvent, contact_times: null }),
    }));
    let requests = 0;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    await page.route('**/api/v1/astronomical-events/contact-times?*', async (route) => {
      requests++;
      await gate;
      await route.fulfill({ json: { contact_times: solarEvent.contact_times } });
    });
    try {
      await page.goto('/en-UK/events');
      await selectRange(page);
      await page.getByRole('button', { name: 'Search', exact: true }).click();
      await page.locator('.event-summary').click();
      await expect.poll(() => requests).toBe(1);
      await page.getByRole('button', { name: 'CSV (1)', exact: true }).click();
      await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeDisabled();
      const downloaded = page.waitForEvent('download');
      release();
      const download = await downloaded;
      const path = await download.path();
      if (!path) throw new Error('CSV download has no local artifact');
      const csv = await readFile(path, 'utf8');
      expect(download.suggestedFilename()).toMatch(/\.csv$/);
      expect(csv.split('\n')).toEqual([
        'Date,Event Type,Is Lunar,Occurs,Contact Type,Time (UTC)',
        `${solarEvent.date},${solarEvent.event_type},No,Yes,eclipse_begins,2026-08-12 01:15:00.000`,
      ]);
      await expect(page.locator('.event-details .detail-row').filter({ hasText: 'Eclipse Begins' }))
        .toContainText(/18:15:00|6:15:00\s*PM/i);
      await expect(page.locator('.loading-spinner')).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeEnabled();
      await expect(page.getByRole('button', { name: 'CSV (1)', exact: true })).toBeEnabled();
      await expect(page.locator('.export-success')).toBeVisible();
      expect(requests).toBe(1);
    } finally {
      release();
    }
  });

  test('downloads the original JSON snapshot before applying a deferred locale refresh', async ({ page }) => {
    const searches: string[] = [];
    await page.route(streamPath, (route) => {
      const locale = new URL(route.request().url()).searchParams.get('lang')!;
      searches.push(locale);
      return route.fulfill({
        contentType: 'text/event-stream',
        body: streamResponse({
          ...solarEvent, event_type: `Result for ${locale}`, contact_times: null,
        }),
      });
    });
    let contactRequests = 0;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    await page.route('**/api/v1/astronomical-events/contact-times?*', async (route) => {
      contactRequests++;
      expect(new URL(route.request().url()).searchParams.get('lang')).toBe('en-UK');
      await gate;
      await route.fulfill({ json: { contact_times: solarEvent.contact_times } });
    });
    try {
      await page.goto('/en-UK/events');
      await selectRange(page);
      await page.getByRole('button', { name: 'Search', exact: true }).click();
      await expect(page.locator('.event-type')).toHaveText('Result for en-UK');
      await page.getByRole('button', { name: 'JSON (1)', exact: true }).click();
      await expect.poll(() => contactRequests).toBe(1);
      await page.getByRole('button', { name: 'Current language: English (UK)', exact: true }).click();
      await page.getByRole('button', { name: 'English (US)', exact: true }).click();
      await expect(page).toHaveURL(/\/en-US\/events$/);
      await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeDisabled();
      await expect(page.locator('.event-type')).toHaveText('Result for en-UK');
      expect(searches).toEqual(['en-UK']);
      const downloaded = page.waitForEvent('download');
      release();
      const download = await downloaded;
      const path = await download.path();
      if (!path) throw new Error('JSON download has no local artifact');
      const data = JSON.parse(await readFile(path, 'utf8'));
      expect(data.count).toBe(1);
      expect(data.events).toEqual([{
        date: solarEvent.date, eventType: 'Result for en-UK',
        isLunar: false, eclipseOccurs: true, contactTimes: solarEvent.contact_times,
      }]);
      await expect(page.locator('.event-type')).toHaveText('Result for en-US');
      await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeEnabled();
      expect(searches).toEqual(['en-UK', 'en-US']);
      expect(contactRequests).toBe(1);
    } finally {
      release();
    }
  });

  test('ends a timed-out real SSE search without reconnecting and allows a fresh search', async ({ page, request }, testInfo) => {
    await withRuntimeServer(request, testInfo, {
      TEST_RUNTIME_BLOCK_STREAM: 'true', TEST_RUNTIME_BUDGET: '1',
    }, async (origin) => {
      let searches = 0;
      // Observe actual EventSource.close(), not just absence of immediate reconnects.
      await page.addInitScript(() => {
        const NativeEventSource = window.EventSource;
        const streams: EventSource[] = [];
        Object.defineProperty(window, '__testEventSources', { value: streams });
        window.EventSource = class extends NativeEventSource {
          constructor(url: string | URL, options?: EventSourceInit) {
            super(url, options);
            streams.push(this);
          }
        };
      });
      await page.route(streamPath, (route) => {
        searches++;
        const url = new URL(route.request().url());
        return route.continue({ url: `${origin}${url.pathname}${url.search}` });
      });
      await page.goto('/en-UK/events');
      await selectRange(page);
      const search = page.getByRole('button', { name: 'Search', exact: true });
      await search.click();
      await expect(page.locator('.loading')).toBeVisible();
      await expect(page.locator('.error')).toHaveText(/connection/i, { timeout: 10000 });
      await expect(page.locator('.loading')).toHaveCount(0);
      await expect(search).toBeEnabled();
      await expect.poll(() => page.evaluate(() => {
        const streams: EventSource[] = Reflect.get(window, '__testEventSources');
        return streams.map((stream) => stream.readyState);
      })).toEqual([2]);
      const metrics = await (await request.get(`${origin}/api/metrics`)).text();
      expect(metrics).toContain(
        'errors_total{endpoint="/api/v1/astronomical-events-stream",error_type="timeout",status="200"} 1.0',
      );
      expect(searches).toBe(1);
      expect((await request.post(`${origin}/__test/release`)).ok()).toBe(true);
      await search.click();
      await expect(page.locator('.empty-state')).toBeVisible();
      await expect(page.locator('.error')).toHaveCount(0);
      await expect(search).toBeEnabled();
      expect(searches).toBe(2);
    });
  });

  for (const outcome of ['429 recovery', '503 partial export'] as const) {
    test(`downloads contact times with ${outcome}`, async ({ page }) => {
      const second = {
        ...solarEvent, date: '2026-08-28 04:13:00.000', event_type: 'Second eclipse',
        contact_times: null,
      };
      const events = outcome === '429 recovery'
        ? [{ ...solarEvent, contact_times: null }]
        : [{ ...solarEvent, contact_times: null }, second];
      await page.route(streamPath, (route) => route.fulfill({
        contentType: 'text/event-stream',
        body: [
          `event: page\ndata: ${JSON.stringify({ page: 1, events })}\n\n`,
          `event: metadata\ndata: ${JSON.stringify({ total_events: events.length, total_pages: 1 })}\n\n`,
        ].join(''),
      }));
      const attempts: string[] = [];
      expectedHttpErrors.get(page)!.add(outcome === '429 recovery' ? 429 : 503);
      await page.route('**/api/v1/astronomical-events/contact-times?*', (route) => {
        const date = route.request().postDataJSON().event_date;
        attempts.push(date);
        if (outcome === '429 recovery' && attempts.length === 1) {
          return route.fulfill({
            status: 429, headers: { 'Retry-After': '1' },
            json: { error: 'rate_limit_exceeded', retry_after: 1 },
          });
        }
        if (date === second.date) {
          return route.fulfill({ status: 503, json: { error: 'Request timeout' } });
        }
        return route.fulfill({ json: { contact_times: solarEvent.contact_times } });
      });
      await page.goto('/en-UK/events');
      await selectRange(page);
      const search = page.getByRole('button', { name: 'Search', exact: true });
      await search.click();
      const exportButton = page.getByRole('button', { name: `JSON (${events.length})`, exact: true });
      const downloaded = page.waitForEvent('download');
      await exportButton.click();
      const download = await downloaded;
      const path = await download.path();
      if (!path) throw new Error('Export download has no local artifact');
      const data = JSON.parse(await readFile(path, 'utf8'));
      expect(data.count).toBe(events.length);
      expect(data.events[0].contactTimes).toEqual(solarEvent.contact_times);
      await expect(search).toBeEnabled();
      await expect(exportButton).toBeEnabled();
      if (outcome === '429 recovery') {
        expect(attempts).toEqual([solarEvent.date, solarEvent.date]);
        await expect(page.locator('.export-success')).toBeVisible();
        await expect(page.locator('.export-warning')).toHaveCount(0);
      } else {
        expect(attempts).toEqual([solarEvent.date, second.date]);
        expect(data.events[1]).toMatchObject({ date: second.date, contactTimes: null });
        await expect(page.locator('.export-warning')).toBeVisible();
        await expect(page.locator('.export-warning')).toContainText(/1.*2/);
      }
    });
  }
});
