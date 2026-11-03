import { test, expect } from '@playwright/test';

test('serves real discovery files and decodable sharing artwork', async ({ page, request }) => {
  const robots = await request.get('/robots.txt');
  expect(robots.status()).toBe(200);
  expect(robots.headers()['content-type']).toContain('text/plain');
  expect(await robots.text()).toContain('Sitemap: https://castlecelestialview.net/sitemap.xml');
  const sitemap = await request.get('/sitemap.xml');
  expect(sitemap.status()).toBe(200);
  expect(sitemap.headers()['content-type']).toContain('xml');
  await page.goto('/en-GB/about');
  const entries = await page.evaluate((xml) => {
    const document = new DOMParser().parseFromString(xml, 'application/xml');
    if (document.querySelector('parsererror')) throw new Error('Invalid sitemap XML');
    return Array.from(document.getElementsByTagName('url')).map(entry => ({
      url: entry.getElementsByTagName('loc')[0].textContent,
      alternates: Array.from(entry.getElementsByTagNameNS('http://www.w3.org/1999/xhtml', 'link'))
        .map(link => link.getAttribute('hreflang')),
    }));
  }, await sitemap.text());
  expect(entries.map(entry => entry.url)).toEqual([
    'https://castlecelestialview.net/en-GB/', 'https://castlecelestialview.net/en-GB/events',
    'https://castlecelestialview.net/en-US/', 'https://castlecelestialview.net/en-US/events',
  ]);
  for (const entry of entries) expect(entry.alternates).toEqual(['en-GB', 'en-US', 'x-default']);
  for (const name of ['home', 'events']) {
    const path = `/social/${name}-v1.png`;
    const response = await request.get(path);
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('image/png');
    const dimensions = await page.evaluate(async (src) => {
      const image = new Image();
      image.src = src;
      await image.decode();
      return [image.naturalWidth, image.naturalHeight];
    }, path);
    expect(dimensions).toEqual([1200, 630]);
  }
  const missing = await request.get('/social/missing.png');
  expect(missing.status()).toBe(404);
  expect(await missing.text()).not.toContain('static-landing');
});
