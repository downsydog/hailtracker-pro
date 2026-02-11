/**
 * Playwright Test Fixtures
 *
 * Stage 8G: Custom fixtures for auth, error tracking, and helpers
 */

import { test as base, expect, Page, BrowserContext } from '@playwright/test'
import { TEST_CONFIG } from './test-config'

// Types for error tracking
interface ConsoleError {
  type: string
  text: string
  location?: string
  timestamp: number
}

interface NetworkError {
  url: string
  status: number
  statusText: string
  method: string
  timestamp: number
}

// Extended test context
interface TestContext {
  consoleErrors: ConsoleError[]
  networkErrors: NetworkError[]
  authToken: string | null
  createdEstimateId: string | null
}

// Custom fixture type
type TestFixtures = {
  testContext: TestContext
  authenticatedPage: Page
}

// Create custom test with fixtures
export const test = base.extend<TestFixtures>({
  // Test context for tracking errors and state
  testContext: async ({}, use) => {
    const context: TestContext = {
      consoleErrors: [],
      networkErrors: [],
      authToken: null,
      createdEstimateId: null,
    }
    await use(context)
  },

  // Pre-authenticated page
  authenticatedPage: async ({ page, testContext }, use) => {
    // Set up console error tracking
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        testContext.consoleErrors.push({
          type: msg.type(),
          text: msg.text(),
          location: msg.location()?.url,
          timestamp: Date.now(),
        })
      }
    })

    // Set up network error tracking (4xx, 5xx)
    page.on('response', (response) => {
      const status = response.status()
      if (status >= 400) {
        testContext.networkErrors.push({
          url: response.url(),
          status,
          statusText: response.statusText(),
          method: response.request().method(),
          timestamp: Date.now(),
        })
      }
    })

    // Perform login
    await performLogin(page, testContext)

    await use(page)
  },
})

// Re-export expect
export { expect }

/**
 * Perform login and store auth token
 * In DEV_MODE (default), the app auto-logs in when no token is present.
 * We just need to navigate to the app and wait for DEV_MODE auto-login to complete.
 */
async function performLogin(page: Page, context: TestContext): Promise<void> {
  // Clear any existing tokens to trigger DEV_MODE auto-login
  await page.goto('/')
  await page.evaluate(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  })

  // Navigate to the app - DEV_MODE will auto-login if VITE_DEV_MODE !== 'false'
  // The app should redirect through login or auto-authenticate
  await page.goto('/estimates')

  // Wait for the page to settle - either we're authenticated or we need to wait for DEV_MODE
  // First, give the app time to initialize and potentially auto-login
  await page.waitForLoadState('networkidle')

  // Check if we're still on login page - if so, try the Demo Login button
  const currentUrl = page.url()
  if (currentUrl.includes('/login')) {
    const demoLoginBtn = page.getByRole('button', { name: /Demo Login/i })
    if (await demoLoginBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await demoLoginBtn.click()
      // Wait for the page reload and then navigate
      await page.waitForLoadState('load')
      await page.waitForTimeout(1000)
      await page.goto('/estimates')
      await page.waitForLoadState('networkidle')
    }
  }

  // Extract and store auth token from localStorage
  const token = await page.evaluate(() => localStorage.getItem('token'))
  context.authToken = token
}

/**
 * Helper: Wait for network idle
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout })
}

/**
 * Helper: Assert no console errors
 */
export function assertNoConsoleErrors(context: TestContext, allowedPatterns: RegExp[] = []): void {
  const unexpectedErrors = context.consoleErrors.filter((error) => {
    return !allowedPatterns.some((pattern) => pattern.test(error.text))
  })

  if (unexpectedErrors.length > 0) {
    const errorMessages = unexpectedErrors.map((e) => `[${e.type}] ${e.text}`).join('\n')
    throw new Error(`Unexpected console errors:\n${errorMessages}`)
  }
}

/**
 * Helper: Assert no network errors (excluding expected ones)
 */
export function assertNoNetworkErrors(
  context: TestContext,
  allowedStatuses: number[] = [],
  allowedUrlPatterns: RegExp[] = []
): void {
  const unexpectedErrors = context.networkErrors.filter((error) => {
    if (allowedStatuses.includes(error.status)) return false
    if (allowedUrlPatterns.some((pattern) => pattern.test(error.url))) return false
    return true
  })

  if (unexpectedErrors.length > 0) {
    const errorMessages = unexpectedErrors
      .map((e) => `[${e.status}] ${e.method} ${e.url}`)
      .join('\n')
    throw new Error(`Unexpected network errors:\n${errorMessages}`)
  }
}

/**
 * Helper: Take screenshot with context
 */
export async function takeScreenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({
    path: `e2e-screenshots/${name}-${Date.now()}.png`,
    fullPage: true,
  })
}

/**
 * Helper: Wait for element and click
 */
export async function safeClick(page: Page, selector: string, timeout = 10000): Promise<void> {
  await page.waitForSelector(selector, { state: 'visible', timeout })
  await page.click(selector)
}

/**
 * Helper: Wait for element and fill
 */
export async function safeFill(
  page: Page,
  selector: string,
  value: string,
  timeout = 10000
): Promise<void> {
  await page.waitForSelector(selector, { state: 'visible', timeout })
  await page.fill(selector, value)
}

/**
 * Helper: Extract estimate ID from URL
 */
export function extractEstimateIdFromUrl(url: string): string | null {
  const match = url.match(/\/estimates\/(\d+)/)
  return match ? match[1] : null
}

/**
 * Helper: Wait for autosave
 */
export async function waitForAutosave(page: Page, timeout = 5000): Promise<void> {
  // Look for save indicator or network request
  await Promise.race([
    page.waitForSelector('[data-testid="save-indicator"]', { timeout }).catch(() => {}),
    page.waitForResponse(
      (resp) => resp.url().includes('/pdr-estimates') && resp.request().method() !== 'GET',
      { timeout }
    ).catch(() => {}),
    page.waitForTimeout(2000), // Fallback
  ])
}
