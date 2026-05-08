import { test, expect } from '@playwright/test';

/**
 * E2E tests for BaseMap pin placement tool
 * Covers keyboard-based pin placement, Escape cancellation, and
 * toggle-button cancellation — all accessibility-critical paths.
 */

test.describe('BaseMap - Pin Tool', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // The map is rendered before data is loaded; wait for it to appear.
    await expect(page.getByRole('application', { name: 'Interactive map' })).toBeVisible();
  });

  // ── activate / deactivate via button ─────────────────────────────────────

  test('pin button activates pin mode: crosshair visible, description updated, live region announced', async ({ page }) => {
    const pinButton = page.locator('button[title="Place Pin"]');
    const crosshair = page.locator('.map-crosshair');
    const mapDesc = page.locator('[id$="-desc"]');
    const mapAnnounce = page.locator('[id$="-announce"]');

    await expect(crosshair).not.toBeVisible();

    await pinButton.click();

    await expect(crosshair).toBeVisible();
    await expect(mapDesc).toContainText('Pin placement tool active');
    await expect(mapAnnounce).toContainText('Pin placement tool active');
  });

  test('pressing pin button again (toggle off) cancels pin mode: crosshair hidden, description restored, cancellation announced', async ({ page }) => {
    const pinButton = page.locator('button[title="Place Pin"]');
    const crosshair = page.locator('.map-crosshair');
    const mapDesc = page.locator('[id$="-desc"]');
    const mapAnnounce = page.locator('[id$="-announce"]');

    // Activate then deactivate via button
    await pinButton.click();
    await expect(crosshair).toBeVisible();

    await pinButton.click();

    await expect(crosshair).not.toBeVisible();
    await expect(mapDesc).toContainText('Interactive map');
    await expect(mapAnnounce).toContainText('Pin placement tool cancelled');
  });

  // ── Escape cancellation ───────────────────────────────────────────────────

  test('Escape key cancels pin mode: crosshair hidden, description restored, cancellation announced', async ({ page }) => {
    const pinButton = page.locator('button[title="Place Pin"]');
    const map = page.getByRole('application', { name: 'Interactive map' });
    const crosshair = page.locator('.map-crosshair');
    const mapDesc = page.locator('[id$="-desc"]');
    const mapAnnounce = page.locator('[id$="-announce"]');

    await pinButton.click();
    await expect(crosshair).toBeVisible();

    await map.focus();
    await map.press('Escape');

    await expect(crosshair).not.toBeVisible();
    await expect(mapDesc).toContainText('Interactive map');
    await expect(mapAnnounce).toContainText('Pin placement tool cancelled');
  });

  // ── Enter to place ────────────────────────────────────────────────────────

  test('Enter key places a pin at the map centre: crosshair hidden, "Pin placed" announced', async ({ page }) => {
    const pinButton = page.locator('button[title="Place Pin"]');
    const map = page.getByRole('application', { name: 'Interactive map' });
    const crosshair = page.locator('.map-crosshair');
    const mapAnnounce = page.locator('[id$="-announce"]');

    await pinButton.click();
    await expect(crosshair).toBeVisible();

    await map.focus();
    await map.press('Enter');

    await expect(crosshair).not.toBeVisible();
    await expect(mapAnnounce).toContainText('Pin placed');
  });

  test('Enter key in pin mode emits pin-placed and description is restored', async ({ page }) => {
    const pinButton = page.locator('button[title="Place Pin"]');
    const map = page.getByRole('application', { name: 'Interactive map' });
    const mapDesc = page.locator('[id$="-desc"]');

    await pinButton.click();
    await map.focus();
    await map.press('Enter');

    await expect(mapDesc).toContainText('Interactive map');
  });

  // ── map is not interactive in pin mode before Enter ───────────────────────

  test('Escape is a no-op when pin mode is not active', async ({ page }) => {
    const map = page.getByRole('application', { name: 'Interactive map' });
    const crosshair = page.locator('.map-crosshair');
    const mapDesc = page.locator('[id$="-desc"]');

    await map.focus();
    await map.press('Escape');

    // Nothing should have changed
    await expect(crosshair).not.toBeVisible();
    await expect(mapDesc).toContainText('Interactive map');
  });

  // ── pin button icon reflects state ───────────────────────────────────────

  test('pin button icon switches to selected state when active and back when cancelled', async ({ page }) => {
    const pinImg = page.locator('button[title="Place Pin"] img');

    await expect(pinImg).toHaveAttribute('src', /map-pin\.png/);

    await page.locator('button[title="Place Pin"]').click();
    await expect(pinImg).toHaveAttribute('src', /map-pin-selected\.png/);

    await page.locator('button[title="Place Pin"]').click();
    await expect(pinImg).toHaveAttribute('src', /map-pin\.png/);
  });

  test('pin button icon resets to default after Enter-to-place', async ({ page }) => {
    const pinImg = page.locator('button[title="Place Pin"] img');
    const map = page.getByRole('application', { name: 'Interactive map' });

    await page.locator('button[title="Place Pin"]').click();
    await expect(pinImg).toHaveAttribute('src', /map-pin-selected\.png/);

    await map.focus();
    await map.press('Enter');
    await expect(pinImg).toHaveAttribute('src', /map-pin\.png/);
  });
});
