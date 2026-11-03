import { test, expect } from '@playwright/test';

test.describe('landing documents without JavaScript', () => {
  test.use({ javaScriptEnabled: false });

  for (const locale of ['en-GB', 'en-US']) {
    for (const [route, title] of [
      ['/', 'Interactive Solar System & Sky Viewer | Castle Celestial View'],
      ['/events', 'New Moons, Full Moons & Eclipses | Castle Celestial View'],
      ['/about', 'About | Castle Celestial View'],
    ]) {
      test(`${locale}${route} serves its own readable document`, async ({ page }) => {
        const response = await page.goto(`/${locale}${route}?source=search`);
        expect(response?.status()).toBe(200);
        expect(response?.headers()['content-type']).toContain('text/html');
        await expect(page).toHaveTitle(title);
        await expect(page.locator('html')).toHaveAttribute('lang', locale);
        await expect(page.locator('link[rel="canonical"]'))
          .toHaveAttribute('href', `https://castlecelestialview.net/${locale}${route}`);
        await expect(page.locator('head link[hreflang="en-GB"]'))
          .toHaveAttribute('href', `https://castlecelestialview.net/en-GB${route}`);
        await expect(page.locator('head link[hreflang="en-US"]'))
          .toHaveAttribute('href', `https://castlecelestialview.net/en-US${route}`);
        await expect(page.locator('h1')).toHaveText('Castle Celestial View');
        await expect(page.locator('noscript p')).toHaveText('Enable JavaScript to use the interactive viewer and event search.');
        await expect(page.locator('noscript p')).toBeVisible();
        await expect(page.locator('main')).toContainText(route === '/events'
          ? 'an eclipse is not necessarily visible from your location'
          : route === '/about' ? 'interactive astronomy viewer' : locale === 'en-GB' ? 'Visualise' : 'Visualize');
        await expect(page.getByRole('link', { name: 'Eclipses', exact: true }))
          .toHaveAttribute('href', `/${locale}/events`);
        await expect(page.locator('script[src]')).toHaveCount(1);
        await page.getByRole('link', { name: 'Eclipses', exact: true }).click();
        await expect(page).toHaveURL(new RegExp(`/${locale}/events$`));
        await expect(page.locator('main')).toContainText('Choose a date range');
        await page.getByRole('link', { name: locale === 'en-GB' ? 'English (US)' : 'English (UK)', exact: true }).click();
        await expect(page.locator('html')).toHaveAttribute('lang', locale === 'en-GB' ? 'en-US' : 'en-GB');
      });
    }
  }
});

test('keeps content and links when the application entry script fails to download', async ({ page }) => {
  await page.route('**/assets/*.js', route => route.abort());
  await page.goto('/en-US/events');
  await expect(page.locator('.static-landing')).toBeVisible();
  await expect(page.locator('main')).toContainText('Choose a date range');
  await expect(page.locator('link[rel="canonical"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-US/events');
  await page.getByRole('link', { name: 'Solar System', exact: true }).click();
  await expect(page).toHaveURL(/\/en-US\/$/);
  await expect(page.locator('main')).toContainText('Visualize');
});

test('retains the document and shows an explicit error if the route chunk fails', async ({ page }) => {
  await page.route('**/assets/EventsView-*.js', route => route.abort());
  await page.goto('/en-GB/events');
  await expect(page.locator('.static-landing')).toBeVisible();
  await expect(page.getByRole('alert')).toHaveText('The interactive application could not start. Reload the page to try again.');
  await expect(page.locator('main')).toContainText('Choose a date range');
  await expect(page.locator('link[rel="canonical"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-GB/events');
});

test('waits for the route, then replaces rather than duplicates the static shell', async ({ page }) => {
  let release!: () => void;
  const released = new Promise<void>(resolve => { release = resolve; });
  let requested!: () => void;
  const requestStarted = new Promise<void>(resolve => { requested = resolve; });
  await page.route('**/assets/EventsView-*.js', async route => {
    requested();
    await released;
    await route.continue();
  });
  try {
    await page.goto('/en-US/events', { waitUntil: 'domcontentloaded' });
    await requestStarted;
    await expect(page.locator('.static-landing')).toBeVisible();
    await expect(page.locator('main')).toContainText('Choose a date range');
    release();
    await expect(page.locator('.search-btn')).toBeEnabled();
    await expect(page.locator('.static-landing')).toHaveCount(0);
    await expect(page.locator('main')).toHaveCount(1);
    await expect(page.locator('link[rel="canonical"]')).toHaveCount(1);
    await expect(page.locator('head link[hreflang]')).toHaveCount(3);
    await expect(page.locator('.events-description')).toContainText('an eclipse is not necessarily visible from your location');
    await expect(page.getByRole('link', { name: 'Solar System', exact: true })).toHaveAttribute('href', '/en-US/');
  } finally {
    release();
    await page.unrouteAll({ behavior: 'wait' });
  }
});
