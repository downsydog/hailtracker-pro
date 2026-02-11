/**
 * Playwright Configuration - HailTracker Pro E2E Tests
 *
 * Stage 8G: End-to-end smoke testing for estimating workflow
 * Stage 8H: Visual + structural snapshot regression tests
 *
 * Run with: npm run e2e
 * Run headed: npm run e2e:headed
 * Run specific test: npm run e2e -- --grep "estimate"
 * Run snapshots: npm run e2e:snapshots
 * Update snapshots: npm run e2e:snapshots:update
 */

import { defineConfig, devices } from '@playwright/test'

// Load env vars
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173'
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000'

export default defineConfig({
  testDir: './e2e',

  // Global setup (runs once before all tests)
  globalSetup: './e2e/global-setup.ts',

  // Run tests in files in parallel
  fullyParallel: false, // Sequential for smoke/snapshot tests (state dependencies)

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests for smoke tests (order matters)
  workers: 1,

  // Reporter to use
  reporter: [
    ['list'],
    ['html', { outputFolder: 'e2e-report', open: 'never' }],
    ['json', { outputFile: 'e2e-results.json' }],
  ],

  // Shared settings for all projects
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: FRONTEND_URL,

    // Stage 8H: Trace/screenshot/video settings for debugging
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Default timeout for actions
    actionTimeout: 10000,

    // Default navigation timeout
    navigationTimeout: 30000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment for cross-browser testing
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Global timeout
  timeout: 60000,

  // Expect timeout
  expect: {
    timeout: 10000,
    // Stage 8H: Snapshot comparison settings
    toHaveScreenshot: {
      // Allow slight pixel differences for anti-aliasing
      maxDiffPixelRatio: 0.01,
      // Threshold for color difference
      threshold: 0.2,
    },
    toMatchSnapshot: {
      // Allow slight differences
      maxDiffPixelRatio: 0.01,
    },
  },

  // Stage 8H: Snapshot output directory
  snapshotDir: './e2e/__snapshots__',
  snapshotPathTemplate: '{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}{ext}',

  // Run local dev server before starting the tests (optional)
  // webServer: {
  //   command: 'npm run dev',
  //   url: FRONTEND_URL,
  //   reuseExistingServer: !process.env.CI,
  // },
})
