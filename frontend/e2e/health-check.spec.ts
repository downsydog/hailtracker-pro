/**
 * Health Check Tests
 *
 * Stage 8G: Quick health checks that run first to verify basic connectivity
 */

import { test, expect } from '@playwright/test'
import { TEST_CONFIG } from './utils/test-config'

test.describe('Health Checks', () => {
  test('Backend API is reachable', async ({ request }) => {
    // Try common health endpoints
    const endpoints = ['/api/health', '/api/status', '/api/', '/health']

    let reachable = false
    for (const endpoint of endpoints) {
      try {
        const response = await request.get(`${TEST_CONFIG.BACKEND_URL}${endpoint}`, {
          timeout: 5000,
        })
        // Any response (even 404) means server is up
        reachable = true
        console.log(`Backend reachable at ${endpoint}: ${response.status()}`)
        break
      } catch {
        continue
      }
    }

    // If no endpoint worked, try the base URL
    if (!reachable) {
      try {
        const response = await request.get(TEST_CONFIG.BACKEND_URL, { timeout: 5000 })
        reachable = true
        console.log(`Backend reachable at base URL: ${response.status()}`)
      } catch (e) {
        console.error(`Backend not reachable at ${TEST_CONFIG.BACKEND_URL}`)
      }
    }

    expect(reachable).toBe(true)
  })

  test('Frontend is reachable', async ({ page }) => {
    const response = await page.goto(TEST_CONFIG.FRONTEND_URL)

    expect(response).not.toBeNull()
    expect(response?.status()).toBeLessThan(500)

    // Verify we got HTML
    const contentType = response?.headers()['content-type'] || ''
    expect(contentType).toContain('text/html')
  })

  test('Frontend loads React app', async ({ page }) => {
    await page.goto(TEST_CONFIG.FRONTEND_URL)
    await page.waitForLoadState('domcontentloaded')

    // Verify React root exists
    const rootElement = page.locator('#root, #app, [data-reactroot]')
    await expect(rootElement).toBeVisible({ timeout: 10000 })

    // Verify content rendered inside root
    const hasContent = await rootElement.innerHTML()
    expect(hasContent.length).toBeGreaterThan(100)
  })

  test('Login page renders', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // Look for login form elements
    const emailInput = page.locator('input[type="email"], input[name="email"]')
    const passwordInput = page.locator('input[type="password"], input[name="password"]')
    const submitBtn = page.locator('button[type="submit"]')

    // At least one should be visible
    const hasLoginForm =
      (await emailInput.isVisible().catch(() => false)) ||
      (await passwordInput.isVisible().catch(() => false)) ||
      (await submitBtn.isVisible().catch(() => false))

    expect(hasLoginForm).toBe(true)
  })

  test('API returns JSON for authenticated endpoints', async ({ request }) => {
    // Try to hit an API endpoint (should return 401 without auth)
    const response = await request.get(`${TEST_CONFIG.BACKEND_URL}/api/pdr-estimates`)

    // Should be 401 (unauthorized) or 200 if no auth required
    expect([200, 401, 403]).toContain(response.status())

    // Should return JSON
    const contentType = response.headers()['content-type'] || ''
    expect(contentType).toContain('application/json')
  })
})
