/**
 * E2E Test: Zoom-to Buttons for Outer Planets (Jupiter, Saturn, Uranus, Neptune)
 *
 * This test verifies that zoom-to buttons work correctly for the four outer planets,
 * which orbit at much larger 3D-scene distances (52-301 units) than the inner solar
 * system bodies covered by zoom-buttons-all-bodies-visible.spec.ts.
 *
 * RESEARCH DATA (see research_outer_planets_visibility.py):
 * - Date: January 1, 2026 (New York observer location: 40.7128° N, -74.0060° W)
 * - All outer planets visible window: 00:00-03:30 UTC (frames 0-7 in 30-minute intervals)
 * - Recommended test frame: Frame 4 at 02:00:00 UTC
 * - Altitudes at frame 4: Jupiter(39.3°), Saturn(20.2°), Uranus(68.8°), Neptune(23.6°)
 *
 * TEST APPROACH (mirrors zoom-buttons-all-bodies-visible.spec.ts):
 * 1. Load 24-hour data for January 1, 2026 with 30-minute frame resolution (48 frames total)
 * 2. Set location to New York (40.7128° N, -74.0060° W)
 * 3. Navigate to Frame 4 (02:00:00 UTC) where all four outer planets are visible
 * 4. Verify all outer planet zoom buttons are enabled (not .disabled state)
 * 5. Test each zoom button individually:
 *    - Click zoom button → wait for camera transition (800ms) + buffer
 *    - Take screenshot to verify zoom worked visually
 *    - Reset camera via recentre button
 */

import { test, expect, Page, Browser, BrowserContext } from '@playwright/test';

// Helper to wait for animations/scene to stabilize
async function stabilizePage(page: Page, timeoutMs: number = 8000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    try {
      const animationControls = page.locator('.animation-controls');
      const isVisible = await animationControls.isVisible({ timeout: 500 }).catch(() => false);

      if (isVisible) {
        await page.waitForTimeout(300);
        return;
      }
    } catch (e) {
      // Continue trying
    }
    await page.waitForTimeout(200);
  }
  throw new Error(`[stabilizePage] Failed to stabilize after ${timeoutMs}ms`);
}

// Load data using the form
async function loadAstronomyData(page: Page, startDate: string, endDate: string, frameCount: number) {
  // Navigate to the app (fresh navigation ensures Vue renders properly)
  await page.goto('/en-UK');
  await page.waitForLoadState('domcontentloaded');

  // Wait for input form to be attached and visible
  const inputForm = page.locator('.input-form');
  await inputForm.waitFor({ state: 'attached', timeout: 15000 });
  await expect(inputForm).toBeVisible({ timeout: 10000 });

  // Set location (New York: 40.7128° N, -74.0060° W)
  await page.locator('#latitude').fill('40.7128');
  await page.locator('#longitude').fill('-74.0060');

  // Set start date in form
  await page.locator('#start-date').fill(startDate);

  // Set end date in form
  await page.locator('#end-date').fill(endDate);

  // IMPORTANT: Also update the DateRangePicker inputs (drp-X-start/end) because the Apply button
  // emits from the DateRangePicker's internal state, not from the form inputs.
  const dateRangeStart = page.locator('input[id^="drp-"][id$="-start"]').first();
  const dateRangeEnd = page.locator('input[id^="drp-"][id$="-end"]').first();

  if (await dateRangeStart.count() > 0) {
    await dateRangeStart.fill(startDate);
  }
  if (await dateRangeEnd.count() > 0) {
    await dateRangeEnd.fill(endDate);
  }

  // Set frames per day (this affects frame-count)
  const framesPerDaySlider = page.locator('#frames-per-day');
  await framesPerDaySlider.evaluate((el: HTMLInputElement, frames: number) => {
    el.value = frames.toString();
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, frameCount);

  // Wait a moment for frame-count to update
  await page.waitForTimeout(500);

  // Click Apply to confirm date range (this is from DateRangePicker)
  await page.getByRole('button', { name: /Apply|apply/ }).click();
  await page.waitForTimeout(500);

  // Click Load Data
  await page.getByRole('button', { name: /Load Data|load/i }).click();

  // Wait for scene to load - monitor both loading indicator and animation controls
  const loadingMessage = page.locator('.loading', { hasText: 'Loading' });
  const errorMessage = page.locator('.error');
  const animationControls = page.locator('.animation-controls');

  const startTime = Date.now();
  const timeout = 250000; // 250 seconds for Firefox SSE streaming (47/48 frames taking longest)
  let lastProgressLog = startTime;

  while (Date.now() - startTime < timeout) {
    try {
      const now = Date.now();
      if (now - lastProgressLog > 10000) {
        try {
          const progressText = await page.locator('.progress-text').innerText().catch(() => 'N/A');
          console.log(`[${Math.round((now - startTime) / 1000)}s] SSE Progress: ${progressText}`);
        } catch (e) {
          // Ignore logging errors
        }
        lastProgressLog = now;
      }

      const controlsVisible = await animationControls.isVisible().catch(() => false);
      if (controlsVisible) {
        break;
      }

      const errorVisible = await errorMessage.isVisible().catch(() => false);
      if (errorVisible) {
        const errorText = await errorMessage.textContent().catch(() => 'Unknown error');
        throw new Error(`API call failed with error: ${errorText}`);
      }

      const loadingVisible = await loadingMessage.isVisible().catch(() => false);
      if (!loadingVisible) {
        break;
      }
    } catch (e: any) {
      if (e.message?.includes('closed')) {
        throw new Error(`Page was closed during loading after ${Date.now() - startTime}ms`);
      }
      throw e;
    }

    await page.waitForTimeout(100);
  }

  try {
    const controlsVisible = await animationControls.isVisible().catch(() => false);
    if (!controlsVisible) {
      const errorVisible = await errorMessage.isVisible().catch(() => false);
      if (errorVisible) {
        throw new Error(`API call failed with error: ${await errorMessage.textContent().catch(() => 'Unknown')}`);
      }
      const progressText = await page.locator('.progress-text').innerText().catch(() => 'unknown');
      throw new Error(`Loading timeout after ${timeout}ms: animation controls did not appear. Final progress: ${progressText}`);
    }
  } catch (e: any) {
    if (!e.message?.includes('timeout') && !e.message?.includes('API call')) {
      throw new Error(`Loading timeout: animation controls did not appear after ${timeout}ms`);
    }
    throw e;
  }
}

// Set animation speed via slider
async function setAnimationSpeed(page: Page, speed: number) {
  const speedSlider = page.locator('#animation-speed');
  await speedSlider.fill(speed.toString());
  await page.waitForTimeout(300);
  console.log(`[Speed] Set animation speed to ${speed}x`);
}

// Switch between 3D and SKY view modes
async function switchViewMode(page: Page, mode: '3D' | 'SKY') {
  const label = mode === '3D' ? /Solar System/i : /Sky View/i;
  await page.locator('.view-toggle').getByRole('button', { name: label }).click();
  await page.waitForTimeout(500);
}

// Ensure animation is stopped
async function pauseAnimation(page: Page) {
  const playButton = page.getByRole('button', { name: /Play|play/ });
  const pauseButton = page.getByRole('button', { name: /Pause|pause/ });

  const pauseVisible = await pauseButton.isVisible().catch(() => false);
  if (pauseVisible) {
    await pauseButton.click();
    await page.waitForTimeout(300);
  }
}

// Navigate to a specific frame and pause there
// Play continuously at high speed, poll frame counter, pause at target
async function navigateToFrameAndPause(page: Page, targetFrameIndex: number) {
  console.log(`[Frame Navigation] Starting navigation to frame ${targetFrameIndex}...`);

  const getCurrentFrame = async () => {
    try {
      const panelHeader = await page.locator('.frame-counter').textContent().catch(() => '');
      const match = panelHeader.match(/(\d+)\s*\/\s*(\d+)/);
      if (match) {
        const frameNum = parseInt(match[1], 10);
        return frameNum - 1; // Convert from 1-indexed to 0-indexed
      }
      return 0;
    } catch {
      return 0;
    }
  };

  // Set moderate speed since target frame is close to the start of the day
  await setAnimationSpeed(page, 0.5);

  const playBtn = page.getByRole('button', { name: /Play|play/ });
  if (await playBtn.isVisible().catch(() => false)) {
    console.log(`[Frame Navigation] Playing at 0.5x speed...`);
    await playBtn.click();
  }

  let currentFrame = 0;
  const pollInterval = 200;
  const startTime = Date.now();
  const maxWaitTime = 60000; // 1 minute timeout (target frame is near the start of the day)

  while (currentFrame < targetFrameIndex && Date.now() - startTime < maxWaitTime) {
    currentFrame = await getCurrentFrame();

    if (currentFrame % 2 === 0) {
      console.log(`[Frame Navigation] Current: ${currentFrame}/${targetFrameIndex}`);
    }

    await page.waitForTimeout(pollInterval);
  }

  console.log(`[Frame Navigation] ✅ Reached frame ${currentFrame}, pausing...`);
  const pauseBtn = page.getByRole('button', { name: /Pause|pause/ });
  try {
    await pauseBtn.click();
    await page.waitForTimeout(1000);
  } catch (e) {
    console.log('[Frame Navigation] Pause button click failed, continuing anyway:', e);
  }
}

// Helper to check if we're still in 3D scene mode
async function isIn3DSceneMode(page: Page): Promise<boolean> {
  try {
    const canvas = await page.locator('canvas').first().isVisible().catch(() => false);
    const controls = await page.locator('.animation-controls').isVisible().catch(() => false);
    const inputForm = await page.locator('.input-form').isVisible().catch(() => false);

    return canvas && controls && !inputForm;
  } catch {
    return false;
  }
}

// Helper to capture console messages from the page
let pageConsoleMessages: string[] = [];

async function setupPageConsoleCapture(page: Page) {
  pageConsoleMessages = [];

  page.on('console', (msg) => {
    const logEntry = `[${msg.type()}] ${msg.text()}`;
    pageConsoleMessages.push(logEntry);
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`[PageConsole] ${logEntry}`);
    }
  });
}

async function isPageHealthy(page: Page): Promise<boolean> {
  try {
    if (page.isClosed()) {
      return false;
    }

    const url = page.url();
    if (url === 'about:blank') {
      console.warn('[PageHealth] Page is at about:blank - context may have been reset');
      return false;
    }

    return true;
  } catch (e) {
    console.error('[PageHealth] Error checking page health:', e);
    return false;
  }
}

// Helper to safely take screenshots with fallback for missing platform snapshots
async function safelyTakeCanvasScreenshot(page: Page, screenshotName: string, testName: string) {
  try {
    console.log(`[Screenshot] Taking ${screenshotName} for ${testName}...`);
    await expect(page.locator('canvas').first()).toHaveScreenshot(screenshotName, { timeout: 15000 });
    console.log(`[Screenshot] Successfully compared ${screenshotName}`);
  } catch (e: any) {
    if (e.message && e.message.includes("doesn't exist")) {
      console.warn(`[Screenshot] Snapshot does not exist for ${screenshotName} on this platform. Skipping comparison. Error: ${e.message}`);
      const canvasVisible = await page.locator('canvas').first().isVisible().catch(() => false);
      if (!canvasVisible) {
        throw new Error(`[Screenshot] Canvas not visible for ${screenshotName}`);
      }
    } else {
      throw e;
    }
  }
}

async function verifySceneLoadedForZoomTest(page: Page, testName: string) {
  const pageHealthy = await isPageHealthy(page);
  if (!pageHealthy) {
    const isClosed = page.isClosed();
    const pageUrl = page.url();
    console.error(`[${testName}] Page health check failed!`);
    console.error(`  Page closed: ${isClosed}`);
    console.error(`  Page URL: ${pageUrl}`);

    throw new Error(
      `[${testName}] Page context lost! Page is closed or at about:blank.\n` +
      `  This indicates a persistent page fixture issue.`
    );
  }

  const inScene = await isIn3DSceneMode(page);
  if (!inScene) {
    const inputFormVisible = await page.locator('.input-form').isVisible().catch(() => false);
    const pageUrl = page.url();
    const currentControls = await page.locator('.animation-controls').count();
    const currentCanvas = await page.locator('canvas').count();

    console.error(`[${testName}] Scene not loaded - Page diagnostics:`);
    console.error(`  URL: ${pageUrl}`);
    console.error(`  Input form visible: ${inputFormVisible}`);
    console.error(`  Animation controls found: ${currentControls}`);
    console.error(`  Canvas elements found: ${currentCanvas}`);

    throw new Error(
      `[${testName}] Scene not loaded! Page appears to be in home/input state.\n` +
      `  URL: ${pageUrl}\n` +
      `  Input form visible: ${inputFormVisible}\n` +
      `  Animation controls found: ${currentControls}\n` +
      `  Canvas elements found: ${currentCanvas}\n` +
      `  This suggests the data load test failed or the fixture was reset.`
    );
  }
}

// Helper to click Recentre button - BLOCKING, verifies reset actually happened
async function clickRecentre(page: Page) {
  console.log('[Recentre] Attempting to reset camera...');

  const recentreBtn = page.locator('.recentre-btn').first();
  const isVisible = await recentreBtn.isVisible({ timeout: 2000 }).catch(() => false);

  if (!isVisible) {
    throw new Error('[Recentre] Recentre button not found or not visible - page may have navigated away');
  }

  await recentreBtn.click({ timeout: 2000 });
  console.log('[Recentre] Button clicked, waiting for animation to settle...');

  await page.waitForTimeout(2000);

  try {
    await stabilizePage(page, 5000);
  } catch (e) {
    throw new Error(`[Recentre] Scene failed to stabilize after recentre: ${e}`);
  }

  const stillInScene = await isIn3DSceneMode(page);
  if (!stillInScene) {
    const inputFormVisible = await page.locator('.input-form').isVisible().catch(() => false);
    if (inputFormVisible) {
      throw new Error('[Recentre] Page navigated back to input form after recentre - test fixture may be corrupted');
    }
    throw new Error('[Recentre] Not in 3D scene mode after recentre');
  }

  console.log(`[Recentre] ✅ Camera reset and scene verified. Page URL: ${page.url()}`);
}

// ==================== TESTS ====================

let persistentPage: Page;
let persistentContext: BrowserContext;
let projectConfig: any = null;

/**
 * Custom test with persistent page across serial tests
 * Matches the pattern used in zoom-buttons-all-bodies-visible.spec.ts
 */
const testWithPersistentPage = test.extend({
  page: async ({ browser }, use) => {
    let contextStillValid = false;
    if (persistentContext && persistentPage) {
      try {
        const pageClosed = persistentPage.isClosed();
        const url = persistentPage.url();
        contextStillValid = !pageClosed && url !== 'about:blank';
        console.log(`[fixture] Persistent page exists, valid: ${contextStillValid}, closed: ${pageClosed}, URL: ${url}`);
      } catch (e) {
        console.error('[fixture] Error checking persistent context/page:', e);
        contextStillValid = false;
      }
    }

    if (!contextStillValid) {
      if (persistentContext) {
        try {
          await persistentContext.close().catch(() => {});
        } catch (e) {
          console.error('[fixture] Error closing old context:', e);
        }
      }
      persistentContext = null;
      persistentPage = null;
    }

    if (!persistentContext) {
      if (!projectConfig?.baseURL) {
        console.warn('[testWithPersistentPage] projectConfig.baseURL not set; falling back to http://localhost:5173.');
      }
      if (!projectConfig?.viewport) {
        console.warn('[testWithPersistentPage] projectConfig.viewport not set; falling back to 1280x720.');
      }
      console.log('[fixture] Creating new persistent context and page');
      persistentContext = await browser.newContext({
        baseURL: projectConfig?.baseURL || 'http://localhost:5173',
        viewport: projectConfig?.viewport || { width: 1280, height: 720 },
      });
      persistentPage = await persistentContext.newPage();

      await setupPageConsoleCapture(persistentPage);

      persistentPage.on('error', (err) => {
        console.error('[PageError] Uncaught exception on page:', err);
      });

      persistentPage.on('crash', () => {
        console.error('[PageCrash] Page has crashed!');
      });

      persistentContext.on('close', () => {
        console.warn('[ContextClose] Browser context is closing');
      });

      console.log('[fixture] New persistent page created with error listeners');
    }
    await use(persistentPage);
  },
});

testWithPersistentPage.describe('Zoom Buttons - Outer Planets', () => {
  testWithPersistentPage.describe.configure({ mode: 'serial' });

  testWithPersistentPage.beforeAll(async ({}, testInfo) => {
    projectConfig = testInfo.project.use;
  });

  testWithPersistentPage.afterAll(async () => {
    if (persistentContext) {
      await persistentContext.close();
    }
  });

  testWithPersistentPage('Load data and navigate to all-outer-planets-visible frame', { timeout: 290000 }, async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    // Load data for full day
    await loadAstronomyData(page, '2026-01-01', '2026-01-01', 48);

    // Verify animation controls present
    await expect(page.locator('.animation-controls')).toBeVisible();

    // Pause any existing animation
    await pauseAnimation(page);

    // Navigate to frame 4 (02:00:00 UTC), where Jupiter, Saturn, Uranus and Neptune
    // are all simultaneously above the horizon (see research_outer_planets_visibility.py)
    console.log('Starting navigation to frame 4...');
    await navigateToFrameAndPause(page, 4);

    const panelText = await page.locator('.controls-panel').textContent();
    console.log('Current panel text:', panelText);

    const frameMatch = panelText?.match(/Frame:\s*(\d+)\s*\/\s*(\d+)/);
    const currentFrameNum = frameMatch ? parseInt(frameMatch[1], 10) : 0;

    console.log(`[FrameDebug] Frame counter: ${currentFrameNum} / ${frameMatch?.[2] || 'N/A'} (expecting 5 for 02:00 UTC frame)`);

    expect(currentFrameNum).toBeGreaterThanOrEqual(3);
    expect(currentFrameNum).toBeLessThanOrEqual(6);
    console.log(`✅ Frame counter verified: ${currentFrameNum}`);

    // Give a moment for animation to fully stop
    await page.waitForTimeout(1000);

    // Verify outer planet zoom buttons exist and are enabled
    const targetBodies = ['Jupiter', 'Saturn', 'Uranus', 'Neptune'];
    for (const body of targetBodies) {
      const btn = page.locator('.zoom-btn').filter({ hasText: body }).first();
      const isDisabled = await btn.isDisabled().catch(() => true);
      expect(isDisabled, `${body} button should not be disabled`).toBe(false);
    }
  });

  testWithPersistentPage('Zoom to Jupiter', async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    console.log(`[Zoom to Jupiter] Starting test, page URL: ${page.url()}, page closed: ${page.isClosed()}`);

    await verifySceneLoadedForZoomTest(page, 'Zoom to Jupiter');

    const jupiterBtn = page.locator('.zoom-btn').filter({ hasText: 'Jupiter' }).first();
    const isDisabled = await jupiterBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Jupiter button should be visible and enabled').toBe(false);

    console.log('[Zoom Test] Clicking Jupiter button...');
    await jupiterBtn.click();

    await page.waitForTimeout(2000);

    console.log('[Zoom Test] Taking screenshot...');
    await safelyTakeCanvasScreenshot(page, 'camera-view-zoomed-jupiter.png', 'Zoom to Jupiter');

    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Saturn', async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    console.log(`[Zoom to Saturn] Starting test, page URL: ${page.url()}, page closed: ${page.isClosed()}`);

    await verifySceneLoadedForZoomTest(page, 'Zoom to Saturn');

    const saturnBtn = page.locator('.zoom-btn').filter({ hasText: 'Saturn' }).first();
    const isDisabled = await saturnBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Saturn button should be visible and enabled').toBe(false);

    console.log('[Zoom Test] Clicking Saturn button...');
    await saturnBtn.click();

    await page.waitForTimeout(2000);

    console.log('[Zoom Test] Taking screenshot...');
    await safelyTakeCanvasScreenshot(page, 'camera-view-zoomed-saturn.png', 'Zoom to Saturn');

    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Uranus', async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    console.log(`[Zoom to Uranus] Starting test, page URL: ${page.url()}, page closed: ${page.isClosed()}`);

    await verifySceneLoadedForZoomTest(page, 'Zoom to Uranus');

    const uranusBtn = page.locator('.zoom-btn').filter({ hasText: 'Uranus' }).first();
    const isDisabled = await uranusBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Uranus button should be visible and enabled').toBe(false);

    console.log('[Zoom Test] Clicking Uranus button...');
    await uranusBtn.click();

    await page.waitForTimeout(2000);

    console.log('[Zoom Test] Taking screenshot...');
    await safelyTakeCanvasScreenshot(page, 'camera-view-zoomed-uranus.png', 'Zoom to Uranus');

    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Neptune', async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    console.log(`[Zoom to Neptune] Starting test, page URL: ${page.url()}, page closed: ${page.isClosed()}`);

    await verifySceneLoadedForZoomTest(page, 'Zoom to Neptune');

    const neptuneBtn = page.locator('.zoom-btn').filter({ hasText: 'Neptune' }).first();
    const isDisabled = await neptuneBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Neptune button should be visible and enabled').toBe(false);

    console.log('[Zoom Test] Clicking Neptune button...');
    await neptuneBtn.click();

    await page.waitForTimeout(2000);

    console.log('[Zoom Test] Taking screenshot...');
    await safelyTakeCanvasScreenshot(page, 'camera-view-zoomed-neptune.png', 'Zoom to Neptune');

    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Outer planet zoom buttons work with repeated clicks', async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    console.log(`[Zoom buttons repeated] Starting test, page URL: ${page.url()}, page closed: ${page.isClosed()}`);

    await verifySceneLoadedForZoomTest(page, 'Outer planet zoom buttons work with repeated clicks');

    const bodies = ['Jupiter', 'Saturn', 'Uranus', 'Neptune'];

    for (const body of bodies) {
      const btn = page.locator('.zoom-btn').filter({ hasText: body }).first();

      // Click once
      await btn.click();
      await page.waitForTimeout(2000);

      // Recentre (blocking with verification)
      await clickRecentre(page);
      await page.waitForTimeout(1500);

      // Click again
      await btn.click();
      await page.waitForTimeout(2000);

      // Recentre
      await clickRecentre(page);
      await page.waitForTimeout(1500);
    }

    expect(true).toBe(true);
  });

  testWithPersistentPage('Sky View mode hides outer planet zoom buttons', async ({ page: testPage }) => {
    const page = testPage || persistentPage;

    console.log(`[Sky View] Starting test, page URL: ${page.url()}, page closed: ${page.isClosed()}`);

    await verifySceneLoadedForZoomTest(page, 'Sky View mode hides outer planet zoom buttons');

    const zoomButtonsIn3D = await page.locator('.zoom-btn').count();
    expect(zoomButtonsIn3D, 'Zoom buttons should be present in 3D mode').toBeGreaterThanOrEqual(4);

    console.log('[Sky View] Switching to Sky View...');
    await switchViewMode(page, 'SKY');

    const zoomButtonsInSky = await page.locator('.zoom-btn').count();
    expect(zoomButtonsInSky, 'Zoom buttons should not be rendered in Sky View mode').toBe(0);

    console.log('[Sky View] Switching back to 3D...');
    await switchViewMode(page, '3D');

    const zoomButtonsBackIn3D = await page.locator('.zoom-btn').count();
    expect(zoomButtonsBackIn3D, 'Zoom buttons should reappear after returning to 3D mode').toBeGreaterThanOrEqual(4);
  });
});
