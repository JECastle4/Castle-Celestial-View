import { test, expect } from '@playwright/test';

/**
 * E2E tests for Astronomy Scene component
 * Tests full integration: Frontend UI -> API -> Three.js rendering
 */

test.describe('Astronomy Scene - Initial Load', () => {
  test('should load the page and have Load Data button enabled', async ({ page }) => {
    // Navigate to the home page
    await page.goto('/');

    // Wait for the page to fully load
    await page.waitForLoadState('networkidle');

    // Verify the main heading is present
    await expect(page.getByRole('heading', { name: 'Astronomy Animation' })).toBeVisible();

    // Verify the input form is visible (indicating we haven't loaded data yet)
    await expect(page.locator('.input-form')).toBeVisible();

    // Verify the frame count has the expected default value (48 frames)
    // This is important to ensure the API call doesn't exceed expectations
    const frameCountInput = page.locator('label:has-text("Frame Count:")').locator('..').locator('input[type="number"]');
    await expect(frameCountInput).toHaveValue('48');

    // Set the date range to 2/2/2026
    const startDateInput = page.locator('input[type="date"]').first();
    const endDateInput = page.locator('input[type="date"]').nth(1);
    await startDateInput.fill('2026-02-02');
    await endDateInput.fill('2026-02-02');
    await page.waitForTimeout(100); // allow Vue to update
    // Click Apply
    const applyButton = page.getByRole('button', { name: 'Apply' });
    await expect(applyButton).toBeEnabled();
    await applyButton.click();

    // Verify the Load Data button exists and is enabled
    const loadButton = page.getByRole('button', { name: 'Load Data' });
    await expect(loadButton).toBeVisible();
    await expect(loadButton).toBeEnabled();

    // Click the Load Data button
    await loadButton.click();

    // Verify the loading message appears
    const loadingMessage = page.locator('.loading', { hasText: 'Loading...' });
    await expect(loadingMessage).toBeVisible();

    // Wait for the loading message to disappear (success or error)
    await expect(loadingMessage).not.toBeVisible({ timeout: 30000 });

    // The success toast is optional (auto-dismissed before scene transition); don't assert on it.

    // Check if there's an error message (backend not running or API error)
    const errorMessage = page.locator('.error');
    const hasError = await errorMessage.isVisible();
    
    if (hasError) {
      const errorText = await errorMessage.textContent();
      throw new Error(`API call failed with error: ${errorText}`);
    }

    // Verify that animation controls appeared (successful load)
    const animationControls = page.locator('.animation-controls');
    await expect(animationControls).toBeVisible();

    // Verify the frame count matches what we requested (48 frames)
    await expect(animationControls.locator('p', { hasText: 'Frames:' })).toHaveText('Frames: 48');

    // Verify the current frame info shows correct visibility
    const currentInfo = animationControls.locator('.current-info');
    await expect(currentInfo.getByText('Sun Visible: No')).toBeVisible();
    await expect(currentInfo.getByText('Moon Visible: Yes')).toBeVisible();

    // Wait a moment for the 3D scene to fully render
    await page.waitForTimeout(1000);

    // Capture screenshot of 3D view (first frame)
    const canvas = page.locator('canvas');
    await expect(canvas).toHaveScreenshot('3d-view-first-frame.png');

    // Click the Sky View button
    const skyViewButton = page.getByRole('button', { name: 'Sky View' });
    await skyViewButton.click();

    // Wait for the view to transition
    await page.waitForTimeout(1000);

    // Capture screenshot of Sky View (first frame)
    await expect(canvas).toHaveScreenshot('sky-view-first-frame.png');
  });
});
