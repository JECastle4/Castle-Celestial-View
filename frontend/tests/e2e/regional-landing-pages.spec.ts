import { test, expect } from '@playwright/test';

test('legacy British URLs keep their page, query and fragment', async ({ page }) => {
  await page.goto('/en-UK/events?date=2026-11-03#details');
  await expect(page).toHaveURL(/\/en-GB\/events\?date=2026-11-03#details$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'en-GB');
  await expect(page.locator('link[rel="canonical"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-GB/events');
});

test('header links support keyboard navigation and opening a separate page', async ({ page }) => {
  await page.goto('/en-GB/');
  const events = page.getByRole('link', { name: 'Eclipses', exact: true });
  await events.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/en-GB\/events$/);
  await expect(page.locator('.search-btn')).toBeEnabled();
  const home = page.getByRole('link', { name: 'Solar System', exact: true });
  const opened = page.context().waitForEvent('page');
  await home.click({ modifiers: ['ControlOrMeta'] });
  const popup = await opened;
  try {
    await expect(popup).toHaveURL(/\/en-GB\/$/);
    await expect(popup.locator('.scene-introduction')).toContainText('Visualise');
    await expect(page).toHaveURL(/\/en-GB\/events$/);
  } finally {
    await popup.close();
  }
});

test('regional metadata follows mounting, locale selection, navigation and history', async ({ page }) => {
  await page.goto('/en-GB/');
  await expect(page.locator('.app-title')).toHaveText('Castle Celestial View');
  await expect(page).toHaveTitle('Interactive Solar System & Sky Viewer | Castle Celestial View');
  await expect(page.locator('.scene-introduction')).toContainText('Visualise');
  await expect(page.locator('link[hreflang="en-US"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-US/');
  await expect(page.locator('link[hreflang="en-GB"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-GB/');

  await page.locator('.footer-lang-btn').click();
  await page.getByRole('button', { name: 'English (US)', exact: true }).click();
  await expect(page).toHaveURL(/\/en-US\/$/);
  await expect(page.locator('.scene-introduction')).toContainText('Visualize');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en-US');
  await expect(page.locator('link[rel="canonical"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-US/');
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'en_US');
  await expect(page.locator('meta[property="og:url"]'))
    .toHaveAttribute('content', 'https://castlecelestialview.net/en-US/');

  await page.getByRole('link', { name: 'Eclipses', exact: true }).click();
  await expect(page).toHaveURL(/\/en-US\/events$/);
  await expect(page).toHaveTitle('New Moons, Full Moons & Eclipses | Castle Celestial View');
  await expect(page.locator('link[hreflang="en-GB"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-GB/events');
  await expect(page.locator('.search-btn')).toBeEnabled();
  await expect(page.locator('meta[property="og:url"]'))
    .toHaveAttribute('content', 'https://castlecelestialview.net/en-US/events');
  await expect(page.locator('meta[name="twitter:image"]'))
    .toHaveAttribute('content', 'https://castlecelestialview.net/social/events-v1.png');

  await page.goBack();
  await expect(page).toHaveTitle('Interactive Solar System & Sky Viewer | Castle Celestial View');
  await expect(page.locator('meta[name="twitter:image"]'))
    .toHaveAttribute('content', 'https://castlecelestialview.net/social/home-v1.png');
  await page.goBack();
  await expect(page).toHaveURL(/\/en-GB\/$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'en-GB');
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'en_GB');
  await page.goForward();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en-US');
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute('content', 'en_US');
  await page.locator('.footer-about-link').click();
  await expect(page).toHaveTitle('About | Castle Celestial View');
  await expect(page.locator('link[rel="canonical"]'))
    .toHaveAttribute('href', 'https://castlecelestialview.net/en-US/about');
  await expect(page.locator('link[rel="canonical"]')).toHaveCount(1);
  await expect(page.locator('meta[name="description"]')).toHaveCount(1);
  await expect(page.locator('link[hreflang]')).toHaveCount(3);
  for (const [path, title, image] of [
    ['/en-GB/', 'Interactive Solar System & Sky Viewer | Castle Celestial View', 'home'],
    ['/en-US/events', 'New Moons, Full Moons & Eclipses | Castle Celestial View', 'events'],
    ['/en-US/about', 'About | Castle Celestial View', 'home'],
  ]) {
    await page.goto(path);
    await expect(page.locator('.static-landing')).toHaveCount(0);
    await expect(page.locator('meta[property="og:url"]')).toHaveCount(1);
    await expect(page.locator('meta[property="og:url"]'))
      .toHaveAttribute('content', `https://castlecelestialview.net${path}`);
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content', title);
    await expect(page.locator('meta[name="twitter:title"]')).toHaveAttribute('content', title);
    await expect(page.locator('meta[property="og:image"]'))
      .toHaveAttribute('content', `https://castlecelestialview.net/social/${image}-v1.png`);
  }
});

for (const viewport of [
  { width: 1280, height: 720 },
  { width: 1024, height: 600 },
  { width: 390, height: 844 },
  { width: 320, height: 568 },
]) {
  test(`homepage explanation, map and date controls fit ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/en-GB/');
    const introduction = page.locator('.scene-introduction');
    const map = page.locator('.map-container');
    await expect(introduction).toBeVisible();
    await expect(page.locator('.ol-viewport')).toBeVisible();
    await expect(page.locator('.app-title')).toHaveText('Castle Celestial View');
    const introductionBox = await introduction.boundingBox();
    const mapBox = await map.boundingBox();
    expect(introductionBox).not.toBeNull();
    expect(mapBox).not.toBeNull();
    expect(introductionBox!.y + introductionBox!.height).toBeLessThanOrEqual(mapBox!.y + 1);
    expect(mapBox!.height).toBeGreaterThanOrEqual(220);
    expect(mapBox!.x).toBeGreaterThanOrEqual(0);
    expect(mapBox!.x + mapBox!.width).toBeLessThanOrEqual(viewport.width);
    const mapViewport = await page.locator('.ol-viewport').boundingBox();
    expect(mapViewport!.height).toBeLessThanOrEqual(mapBox!.height);
    await expect(page.getByRole('link', { name: 'Eclipses', exact: true })).toBeInViewport();

    const apply = page.getByRole('button', { name: 'Apply', exact: true });
    await apply.scrollIntoViewIfNeeded();
    await expect(apply).toBeInViewport();
    await apply.click();
    const load = page.getByRole('button', { name: 'Load Data', exact: true });
    await load.scrollIntoViewIfNeeded();
    await expect(load).toBeInViewport();
    await expect(load).toBeEnabled();
    await expect(page.locator('.footer-lang-btn')).toBeInViewport();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
  });
}
