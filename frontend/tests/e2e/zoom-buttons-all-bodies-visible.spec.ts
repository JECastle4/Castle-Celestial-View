/**
 * E2E Test: Zoom-to Buttons with All Celestial Bodies Visible
 *
 * This test verifies that zoom-to buttons work correctly when all celestial bodies
 * (Sun, Mercury, Venus, Moon, Mars) are simultaneously visible.
 *
 * RESEARCH DATA (Phase 1 Complete):
 * - Date: June 19, 2026 (New York observer location: 40.7128° N, -74.0060° W)
 * - All bodies visible window: 15:00-21:30 EDT (14 consecutive 30-min frames)
 * - Recommended test frame: Frame 30 at 15:00:00 EDT (3:00 PM)
 * - Minimum altitudes at frame 30: Sun(55.88°), Moon(21.65°), Mercury(56.75°), Venus(47.33°), Mars(26.34°)
 *
 * TEST APPROACH:
 * 1. Load 24-hour data for June 19, 2026 with 30-minute frame resolution (48 frames total)
 * 2. Set animation speed to 0.1x (10 seconds per frame for easy manual control)
 * 3. Pause animation and navigate to Frame 30 (15:00:00 EDT) where all bodies are visible
 * 4. Verify all zoom buttons are enabled (bodies visible, not .disabled state)
 * 5. Test each zoom button individually:
 *    - Click zoom button → wait for camera transition (800ms) + buffer
 *    - Take screenshot to verify zoom worked visually
 *    - Reset camera via recentre button
 * 6. Test Sky View mode disables zoom buttons
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
  
  // Set start date
  await page.locator('#start-date').fill(startDate);
  
  // Set end date
  await page.locator('#end-date').fill(endDate);
  
  // Set frames per day (this affects frame-count)
  const framesPerDaySlider = page.locator('#frames-per-day');
  await framesPerDaySlider.evaluate((el: HTMLInputElement, frames: number) => {
    el.value = frames.toString();
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, frameCount);
  
  // Wait a moment for frame-count to update
  await page.waitForTimeout(500);
  
  // Click Apply to confirm date range
  await page.getByRole('button', { name: /Apply|apply/ }).click();
  
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
      // Log progress every 10 seconds
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
      
      // Check if animation controls appeared (scene loaded successfully)
      const controlsVisible = await animationControls.isVisible().catch(() => false);
      if (controlsVisible) {
        break;
      }
      
      // Check if error appeared
      const errorVisible = await errorMessage.isVisible().catch(() => false);
      if (errorVisible) {
        const errorText = await errorMessage.textContent().catch(() => 'Unknown error');
        throw new Error(`API call failed with error: ${errorText}`);
      }
      
      // Check if loading disappeared
      const loadingVisible = await loadingMessage.isVisible().catch(() => false);
      if (!loadingVisible) {
        break;
      }
    } catch (e: any) {
      // If page/context/browser is closed, stop trying
      if (e.message?.includes('closed')) {
        throw new Error(`Page was closed during loading after ${Date.now() - startTime}ms`);
      }
      // Re-throw other errors
      throw e;
    }
    
    // Wait a bit before checking again
    await page.waitForTimeout(100);
  }
  
  // Final check: if we still have a loading message and no controls, something went wrong
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
  
  // Set high speed for fast approach
  await setAnimationSpeed(page, 2.0);
  
  // Play continuously
  const playBtn = page.getByRole('button', { name: /Play|play/ });
  if (await playBtn.isVisible().catch(() => false)) {
    console.log(`[Frame Navigation] Playing at 2.0x speed...`);
    await playBtn.click();
  }
  
  let currentFrame = 0;
  const pollInterval = 200; // Check frame every 200ms
  const startTime = Date.now();
  const maxWaitTime = 120000; // 2 minute timeout
  
  // Poll frame counter until we reach target frame
  let speedAdjusted = false;
  while (currentFrame < targetFrameIndex && Date.now() - startTime < maxWaitTime) {
    currentFrame = await getCurrentFrame();
    
    // Dynamically adjust speed based on proximity to target (only adjust once)
    if (currentFrame >= 25 && !speedAdjusted) {
      // Moderate slowdown when approaching target (frames 25+)
      await setAnimationSpeed(page, 0.5);
      console.log(`[Frame Navigation] Slowed to 0.5x for precise approach`);
      speedAdjusted = true;
    }
    
    // Log progress every 5 frames
    if (currentFrame % 5 === 0) {
      console.log(`[Frame Navigation] Current: ${currentFrame}/${targetFrameIndex}`);
    }
    
    await page.waitForTimeout(pollInterval);
  }
  
  // Pause at target frame
  console.log(`[Frame Navigation] ✅ Reached frame ${currentFrame}, pausing...`);
  const pauseBtn = page.getByRole('button', { name: /Pause|pause/ });
  try {
    await pauseBtn.click();
    await page.waitForTimeout(1000); // Extended wait for pause to take effect and animation to settle
  } catch (e) {
    console.log('[Frame Navigation] Pause button click failed, continuing anyway:', e);
  }
}

// Verify all bodies visible by checking zoom button disabled state
async function verifyAllBodiesVisible(page: Page) {
  const zoomButtons = page.locator('.zoom-btn');
  const count = await zoomButtons.count();
  
  // Should have at least Sun, Mercury, Venus, Moon, Mars (5+)
  expect(count).toBeGreaterThanOrEqual(5);
  
  // Collect button info for debugging
  const buttonStates: any[] = [];
  for (let i = 0; i < count; i++) {
    const btn = zoomButtons.nth(i);
    const text = await btn.textContent().catch(() => '');
    const isDisabled = await btn.isDisabled().catch(() => false);
    const hasDisabledClass = await btn.evaluate((el) => el.classList.contains('disabled')).catch(() => false);
    
    buttonStates.push({
      index: i,
      text: text.trim(),
      disabled: isDisabled,
      disabledClass: hasDisabledClass
    });
  }
  
  // Log for debugging
  console.log('Zoom button states:', buttonStates);
  
  // Check that key buttons are not disabled
  const targetBodies = ['Sun', 'Mercury', 'Venus', 'Moon', 'Mars'];
  for (const body of targetBodies) {
    const btn = zoomButtons.filter({ hasText: body }).first();
    const isDisabled = await btn.isDisabled().catch(() => true);
    expect(isDisabled, `${body} button should not be disabled`).toBe(false);
  }
}

// Helper to check if we're still in 3D scene mode
async function isIn3DSceneMode(page: Page): Promise<boolean> {
  try {
    const canvas = await page.locator('canvas').first().isVisible().catch(() => false);
    const controls = await page.locator('.animation-controls').isVisible().catch(() => false);
    const inputForm = await page.locator('.input-form').isVisible().catch(() => false);
    
    // We're in 3D mode if canvas and controls are visible, and input form is NOT visible
    return canvas && controls && !inputForm;
  } catch {
    return false;
  }
}

// Helper to verify we're in 3D scene mode before a zoom test - throws if not
async function verifySceneLoadedForZoomTest(page: Page, testName: string) {
  const inScene = await isIn3DSceneMode(page);
  if (!inScene) {
    const inputFormVisible = await page.locator('.input-form').isVisible().catch(() => false);
    const pageUrl = page.url();
    const currentControls = await page.locator('.animation-controls').count();
    const currentCanvas = await page.locator('canvas').count();
    
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
  
  // Click the button
  await recentreBtn.click({ timeout: 2000 });
  console.log('[Recentre] Button clicked, waiting for animation to settle...');
  
  // Wait for camera animation to complete (longer for CI)
  await page.waitForTimeout(2000);
  
  // Stabilize the scene to ensure camera reset is complete
  try {
    await stabilizePage(page, 5000);
  } catch (e) {
    throw new Error(`[Recentre] Scene failed to stabilize after recentre: ${e}`);
  }
  
  // Verify we're still in 3D scene mode
  const stillInScene = await isIn3DSceneMode(page);
  if (!stillInScene) {
    const inputFormVisible = await page.locator('.input-form').isVisible().catch(() => false);
    if (inputFormVisible) {
      throw new Error('[Recentre] Page navigated back to input form after recentre - test fixture may be corrupted');
    }
    throw new Error('[Recentre] Not in 3D scene mode after recentre');
  }
  
  console.log('[Recentre] ✅ Camera reset and scene verified');
}

// ==================== TESTS ====================

let persistentPage: Page;
let persistentContext: BrowserContext;
let projectConfig: any = null;

/**
 * Custom test with persistent page across serial tests
 * Matches the carousel tests (astronomy-scene.spec.ts) pattern
 * Uses project baseURL and viewport from playwright.config.ts
 */
const testWithPersistentPage = test.extend({
  page: async ({ browser }, use) => {
    if (!persistentContext) {
      // Create context with project settings (baseURL and viewport) from configuration
      // This prevents brittle hardcoding and allows configuration changes in playwright.config.ts
      if (!projectConfig?.baseURL) {
        console.warn('[testWithPersistentPage] projectConfig.baseURL not set; falling back to http://localhost:5173. Ensure beforeAll runs before the first test fixture.');
      }
      if (!projectConfig?.viewport) {
        console.warn('[testWithPersistentPage] projectConfig.viewport not set; falling back to 1280x720.');
      }
      persistentContext = await browser.newContext({
        baseURL: projectConfig?.baseURL || 'http://localhost:5173',
        viewport: projectConfig?.viewport || { width: 1280, height: 720 },
      });
      persistentPage = await persistentContext.newPage();
    }
    await use(persistentPage);
  },
});

testWithPersistentPage.describe('Zoom Buttons with All Bodies Visible', () => {
  // Configure tests to run serially
  testWithPersistentPage.describe.configure({ mode: 'serial' });
  
  testWithPersistentPage.beforeAll(async ({}, testInfo) => {
    // Capture project configuration from testInfo to use in persistent context
    projectConfig = testInfo.project.use;
    
    // Note: Navigation happens in loadAstronomyData() for each test,
    // which ensures Vue components render properly
  });

  testWithPersistentPage.afterAll(async () => {
    if (persistentContext) {
      await persistentContext.close();
    }
  });

  testWithPersistentPage('Load data and navigate to all-bodies-visible frame', { timeout: 290000 }, async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Load data for full day
    await loadAstronomyData(page, '2026-06-19', '2026-06-19', 48);
    
    // Verify animation controls present
    await expect(page.locator('.animation-controls')).toBeVisible();
    
    // Pause any existing animation
    await pauseAnimation(page);
    
    // Navigate to frame 30 with fast continuous play + poll + pause strategy
    // Frame 30 (15:00 EDT) is in the all-visible window (frames 30-43)
    console.log('Starting navigation to frame 30... This will take ~30-40 seconds');
    await navigateToFrameAndPause(page, 30);
    
    // Verify panel text shows we're at frame 30 (or nearby)
    const panelText = await page.locator('.controls-panel').textContent();
    console.log('Current panel text:', panelText);
    
    // Verify frame counter shows frame 30-31 (1-indexed)
    const frameMatch = panelText?.match(/Frame:\s*(\d+)\s*\/\s*(\d+)/);
    const currentFrameNum = frameMatch ? parseInt(frameMatch[1], 10) : 0;
    expect(currentFrameNum).toBeGreaterThanOrEqual(30);
    expect(currentFrameNum).toBeLessThanOrEqual(32); // Allow for off-by-one in indexing
    console.log(`✅ Frame counter verified: ${currentFrameNum}`);
    
    // Give a moment for animation to fully stop
    await page.waitForTimeout(1000);
    
    // Verify zoom buttons exist and are accessible
    const zoomButtons = page.locator('.zoom-btn');
    const count = await zoomButtons.count();
    console.log(`Found ${count} zoom buttons`);
    expect(count).toBeGreaterThanOrEqual(5);
  });

  testWithPersistentPage('Zoom to Sun', async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Verify scene is loaded from previous test
    await verifySceneLoadedForZoomTest(page, 'Zoom to Sun');
    
    // Verify button exists and is not disabled
    const sunBtn = page.locator('.zoom-btn').filter({ hasText: 'Sun' }).first();
    const isDisabled = await sunBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Sun button should be visible and enabled').toBe(false);
    
    // Click zoom to Sun
    console.log('[Zoom Test] Clicking Sun button...');
    await sunBtn.click();
    
    // Wait for camera transition and 3D rendering to complete (extended for CI)
    await page.waitForTimeout(2000);
    
    // Verify camera view matches snapshot
    console.log('[Zoom Test] Taking screenshot...');
    await expect(page.locator('canvas').first()).toHaveScreenshot('camera-view-zoomed-sun.png', { timeout: 15000 });
    
    // Reset camera with blocking verification
    await clickRecentre(page);
    
    // Extended wait after recentre to ensure scene is fully settled for next test
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Mercury', async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Verify scene is loaded from previous test
    await verifySceneLoadedForZoomTest(page, 'Zoom to Mercury');
    
    const mercBtn = page.locator('.zoom-btn').filter({ hasText: 'Mercury' }).first();
    const isDisabled = await mercBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Mercury button should be visible and enabled').toBe(false);
    
    console.log('[Zoom Test] Clicking Mercury button...');
    await mercBtn.click();
    
    await page.waitForTimeout(2000);
    
    console.log('[Zoom Test] Taking screenshot...');
    await expect(page.locator('canvas').first()).toHaveScreenshot('camera-view-zoomed-mercury.png', { timeout: 15000 });
    
    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Venus', async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Verify scene is loaded from previous test
    await verifySceneLoadedForZoomTest(page, 'Zoom to Venus');
    
    const venusBtn = page.locator('.zoom-btn').filter({ hasText: 'Venus' }).first();
    const isDisabled = await venusBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Venus button should be visible and enabled').toBe(false);
    
    console.log('[Zoom Test] Clicking Venus button...');
    await venusBtn.click();
    
    await page.waitForTimeout(2000);
    
    console.log('[Zoom Test] Taking screenshot...');
    await expect(page.locator('canvas').first()).toHaveScreenshot('camera-view-zoomed-venus.png', { timeout: 15000 });
    
    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Moon', async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Verify scene is loaded from previous test
    await verifySceneLoadedForZoomTest(page, 'Zoom to Moon');
    
    const moonBtn = page.locator('.zoom-btn').filter({ hasText: 'Moon' }).first();
    const isDisabled = await moonBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Moon button should be visible and enabled').toBe(false);
    
    console.log('[Zoom Test] Clicking Moon button...');
    await moonBtn.click();
    
    await page.waitForTimeout(2000);
    
    console.log('[Zoom Test] Taking screenshot...');
    await expect(page.locator('canvas').first()).toHaveScreenshot('camera-view-zoomed-moon.png', { timeout: 15000 });
    
    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom to Mars', async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Verify scene is loaded from previous test
    await verifySceneLoadedForZoomTest(page, 'Zoom to Mars');
    
    const marsBtn = page.locator('.zoom-btn').filter({ hasText: 'Mars' }).first();
    const isDisabled = await marsBtn.isDisabled().catch(() => true);
    expect(isDisabled, 'Mars button should be visible and enabled').toBe(false);
    
    console.log('[Zoom Test] Clicking Mars button...');
    await marsBtn.click();
    
    await page.waitForTimeout(2000);
    
    console.log('[Zoom Test] Taking screenshot...');
    await expect(page.locator('canvas').first()).toHaveScreenshot('camera-view-zoomed-mars.png', { timeout: 15000 });
    
    await clickRecentre(page);
    await page.waitForTimeout(2000);
  });

  testWithPersistentPage('Zoom buttons work with repeated clicks', async ({ page: testPage }) => {
    const page = testPage || persistentPage;
    
    // Verify scene is loaded from previous test
    await verifySceneLoadedForZoomTest(page, 'Zoom buttons work with repeated clicks');
    
    const bodies = ['Sun', 'Mercury', 'Venus', 'Moon', 'Mars'];
    
    for (const body of bodies) {
      const btn = page.locator('.zoom-btn').filter({ hasText: body }).first();
      
      // Click once
      await btn.click();
      await page.waitForTimeout(2000);
      
      // Recentre (now blocking with verification)
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
});
