import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendRoot = path.resolve(__dirname, '..');
const pythonExe = process.env.CI
  ? 'python'
  : process.platform === 'win32'
    ? path.join(backendRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(backendRoot, '.venv', 'bin', 'python');

/**
 * Playwright configuration for E2E tests
 * Testing astronomy animation scene rendering and API integration
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  // Maximum time one test can run
  timeout: 30 * 1000,
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI for more stability
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter to use
  reporter: 'html',
  
  // Shared settings for all projects
  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:5173',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'retain-on-failure',
  },

  // Configure projects for different browsers (Chromium, Firefox, WebKit, and Edge)
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Wait for network to be idle before considering navigation done
        // Important for API calls to complete before taking screenshots
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          // These prefs force WebGL on even when Firefox's internal heuristics
          // would normally block it (e.g. when Mesa advertises a software renderer).
          // Combined with LIBGL_ALWAYS_SOFTWARE=1 + MESA_GL_VERSION_OVERRIDE=4.5 and
          // an Xvfb virtual display (see ci.yml), Firefox runs in headed mode against
          // a real X11/GLX path so Mesa llvmpipe handles WebGL correctly.
          firefoxUserPrefs: {
            'dom.webgl.force-enabled': true,
            'webgl.force-enabled': true,
          },
        },
      },
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'edge',
      use: {
        ...devices['Desktop Edge'],
        channel: 'msedge',
        viewport: { width: 1280, height: 720 },
      },
    },
  ],

  // Run Vite dev server and FastAPI backend before starting tests
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000, // 2 minutes to start
      stdout: 'ignore',
      stderr: 'pipe',
    },
    {
      command: `"${pythonExe}" -m uvicorn api.main:app --port 8000`,
      cwd: backendRoot,
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60 * 1000, // 1 minute to start
      stdout: 'ignore',
      stderr: 'pipe',
    },
  ],

  // Screenshot comparison settings
  expect: {
    toHaveScreenshot: {
      // Allow 0.2% pixel difference to account for minor rendering variations
      maxDiffPixelRatio: 0.002,
      
      // Threshold for pixel color difference (0-1)
      threshold: 0.2,
      
      // Animations can cause timing issues, so we use a small animation setting
      animations: 'disabled',
    },
  },
});
