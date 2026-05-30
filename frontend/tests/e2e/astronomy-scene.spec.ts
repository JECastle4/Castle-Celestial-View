import { test, expect } from '@playwright/test';

/**
 * E2E tests for Astronomy Scene component
 * Tests full integration: Frontend UI -> API -> Three.js rendering
 */

test.describe('Astronomy Scene - Initial Load', () => {
  test('should load the page and have Load Data button enabled', { timeout: 35000 }, async ({ page }) => {
    // Navigate to the home page
    await page.goto('/en-UK');

    // Verify the main heading is present
    await expect(page.getByRole('heading', { name: 'Castle Celestial View' })).toBeVisible();

    // Verify the input form is visible (indicating we haven't loaded data yet)
    await expect(page.locator('.input-form')).toBeVisible();

    // Verify the frame count has the expected default value (48 frames)
    // This is important to ensure the API call doesn't exceed expectations
    const frameCountInput = page.locator('label:has-text("Frame Count:")').locator('..').locator('input[type="number"]');
    await expect(frameCountInput).toHaveValue('48');

    // Set the date range to 2/2/2026
    // Scope to .date-range-picker to avoid matching the duplicate date inputs
    // in the controls panel (there are 4 input[type="date"] on the page).
    // Use evaluate+dispatchEvent instead of fill() — WebKit does not fire
    // the input/change events that Vue v-model relies on for date inputs.
    const startDateInput = page.locator('.date-range-picker input[type="date"]').first();
    const endDateInput = page.locator('.date-range-picker input[type="date"]').nth(1);
    await startDateInput.evaluate((el: HTMLInputElement, val) => {
      el.value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, '2026-02-02');
    await endDateInput.evaluate((el: HTMLInputElement, val) => {
      el.value = val;
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, '2026-02-02');
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

    // Read and log the new Frame X/Y display
    const frameXYText = await currentInfo.locator('p').first().innerText();
    // Extract current and total frame numbers
    const frameXYMatch = frameXYText.match(/Frame:\s*(\d+)\s*\/\s*(\d+)/);
    const totalFrames = frameXYMatch ? parseInt(frameXYMatch[2], 10) : 0;
    expect(totalFrames).toBeGreaterThan(1);

    // After switching to Sky View and before animation checks
    const frameCountText = await page.locator('.animation-controls p').first().innerText();
    // Extract frame count number from text like 'Frames: 48'
    const frameCountMatch = frameCountText.match(/Frames:\s*(\d+)/);
    const frameCount = frameCountMatch ? parseInt(frameCountMatch[1], 10) : 0;
    expect(frameCount).toBeGreaterThan(1);

    // Wait a moment for the 3D scene to fully render
    await page.waitForTimeout(1000);

    // Capture screenshot of the full scene (including right panel)
    const scene = page.locator('.app-layout');
    await expect(scene).toHaveScreenshot('3d-view-first-frame.png');

    // Click the Sky View button
    const skyViewButton = page.getByRole('button', { name: 'Sky View' });
    await skyViewButton.click();

    // Wait for the view to transition
    await page.waitForTimeout(1000);

    // Capture screenshot of Sky View (full scene)
    await expect(scene).toHaveScreenshot('sky-view-first-frame.png');
  });
});

test.describe('Astronomy Scene - Sky View Animation Controls', () => {
  test('should play, pause, and reset animation in Sky View', async ({ page }) => {
    // Define beforePlayFrameXY at the top for this test
    let beforePlayFrameXY = '';
    // Navigate to the home page and load data as in the initial test
    await page.goto('/en');
    const startDateInput = page.locator('.date-range-picker input[type="date"]').first();
    const endDateInput = page.locator('.date-range-picker input[type="date"]').nth(1);
    await startDateInput.evaluate((el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }, '2026-02-02');
    await endDateInput.evaluate((el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }, '2026-02-02');
    const applyButton = page.getByRole('button', { name: 'Apply' });
    await applyButton.click();
    const loadButton = page.getByRole('button', { name: 'Load Data' });
    await loadButton.click();
    const loadingMessage = page.locator('.loading', { hasText: 'Loading...' });
    await expect(loadingMessage).toBeVisible();
    await expect(loadingMessage).not.toBeVisible({ timeout: 30000 });
    const errorMessage = page.locator('.error');
    if (await errorMessage.isVisible()) {
      throw new Error(`API call failed with error: ${await errorMessage.textContent()}`);
    }

    // Verify that animation controls appeared (successful load)
    const animationControls = page.locator('.animation-controls');
    await expect(animationControls).toBeVisible();
    // Wait a moment for the 3D scene to fully render
    await page.waitForTimeout(1000);

    // Switch to Sky View
    const skyViewButton = page.getByRole('button', { name: 'Sky View' });
    await skyViewButton.click();
    await page.waitForTimeout(1000);
    const scene = page.locator('.app-layout');
    // Capture initial frame info and screenshot
    const currentInfo = page.locator('.animation-controls .current-info');
    beforePlayFrameXY = await currentInfo.locator('p').first().innerText();
    await expect(scene).toHaveScreenshot('sky-view-first-frame.png');
    // Set animation speed to minimum for reliability (if present)
    const speedInput = page.locator('.animation-controls input[type="range"]#animation-speed');
    if (await speedInput.count()) {
      await speedInput.fill('0.1');
    }
    
    // Assert Recentre button is en-UK
    //const allButtons = await page.locator('.animation-controls button').allTextContents();
    //console.log('Animation control buttons:', allButtons);
    const recentreButton = page.getByRole('button', { name: 'Return the camera to the default location (centred on earth)' });
    await expect(recentreButton).toBeVisible();
    // Open language menu and select en-US
    const langBtn = page.locator('.footer-lang-btn');
    await langBtn.click();
    const enUSOption = page.locator('.footer-lang-option', { hasText: 'English (US)' });
    await enUSOption.click();
    const recenterButton = page.getByRole('button', { name: 'Return the camera to the default location (centered on earth)' });
    await expect(recenterButton).toBeVisible();
    // Open language menu and select en-UK
    await langBtn.click();
    const enUKOption = page.locator('.footer-lang-option', { hasText: 'English (UK)' });
    await enUKOption.click();
    

    // Play animation
    const playPauseButton = page.getByRole('button', { name: 'Play' });
    await playPauseButton.click();
    // Confirm Play button changed to Pause (animation started)
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
    // Wait 5 second and log again
    await page.waitForTimeout(5200);
    const afterWaitFrameXY = await currentInfo.locator('p').first().innerText();
    // Now assert that the frame has advanced
    expect(afterWaitFrameXY).not.toBe(beforePlayFrameXY);
    const resetButton = page.getByRole('button', { name: 'Restart' });
    await resetButton.click();
    await expect(scene).toHaveScreenshot('sky-view-reset-frame.png');
  });
});
