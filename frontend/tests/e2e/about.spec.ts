import { test, expect } from '@playwright/test';

test.describe('About Page', () => {
  test('should open about page from footer link and display copyright with year and author name', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click the About link in the footer
    const aboutLink = page.getByRole('link', { name: 'About' });
    await expect(aboutLink).toBeVisible();
    await aboutLink.click();

    await page.waitForLoadState('networkidle');

    // Assert the about page heading is visible
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Assert copyright text contains a 4-digit year and the author's name
    const copyrightEl = page.locator('.copyright');
    await expect(copyrightEl).toBeVisible();
    const copyrightText = await copyrightEl.innerText();
    expect(copyrightText).toMatch(/\d{4}/);         // any 4-digit year
    expect(copyrightText).toMatch(/Castle/);        // author surname

    // Assert the close/back link returns to the main page
    const closeLink = page.getByRole('link', { name: /←|Close/i });
    await expect(closeLink).toBeVisible();
  });

  test('should navigate back to main page from about page', async ({ page }) => {
    await page.goto('/en/about');
    await page.waitForLoadState('networkidle');

    const closeLink = page.getByRole('link', { name: /←|Close/i });
    await expect(closeLink).toBeVisible();
    await closeLink.click();

    await page.waitForLoadState('networkidle');
    await expect(page.locator('.input-form')).toBeVisible();
  });
});
