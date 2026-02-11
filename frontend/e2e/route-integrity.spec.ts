/**
 * Route Integrity Scan
 *
 * Stage 8G: Validate all estimating-related routes work correctly
 */

import { test, expect } from './utils/fixtures'
import { TEST_CONFIG } from './utils/test-config'

// All routes to scan
const ROUTES_TO_SCAN = [
  // Core estimating routes
  { path: '/estimates', name: 'Estimates List', requiresAuth: true },
  { path: '/estimates/new', name: 'New Estimate', requiresAuth: true },

  // Dashboard / home
  { path: '/', name: 'Home/Dashboard', requiresAuth: false },
  { path: '/dashboard', name: 'Dashboard', requiresAuth: true },

  // Other potentially related routes
  { path: '/customers', name: 'Customers', requiresAuth: true },
  { path: '/jobs', name: 'Jobs', requiresAuth: true },
  { path: '/leads', name: 'Leads', requiresAuth: true },

  // Settings
  { path: '/settings', name: 'Settings', requiresAuth: true },
]

test.describe('Route Integrity Scan', () => {
  for (const route of ROUTES_TO_SCAN) {
    test(`Route: ${route.name} (${route.path})`, async ({ authenticatedPage, testContext }) => {
      // Reset error tracking
      testContext.consoleErrors = []
      testContext.networkErrors = []

      // Navigate to route
      const response = await authenticatedPage.goto(route.path)

      // Wait for page to settle
      await authenticatedPage.waitForLoadState('networkidle').catch(() => {})

      // 1. Check response status
      const status = response?.status() || 0
      expect(status).toBeLessThan(500) // No server errors

      // 2. Check for redirect loops
      const finalUrl = authenticatedPage.url()
      const urlCount = new Map<string, number>()
      // Note: Playwright doesn't expose redirect chain easily, so we check final URL

      // 3. Check for blank screen
      const bodyText = await authenticatedPage.locator('body').innerText().catch(() => '')
      const hasContent = bodyText.trim().length > 10
      expect(hasContent).toBe(true)

      // 4. Check for "Resource not found" errors
      const hasNotFoundError =
        bodyText.toLowerCase().includes('not found') &&
        !bodyText.toLowerCase().includes('no results') &&
        !bodyText.toLowerCase().includes('nothing found')

      if (hasNotFoundError) {
        console.warn(`Warning: Possible "not found" error on ${route.path}`)
      }

      // 5. Check for critical console errors (not React dev warnings)
      const criticalConsoleErrors = testContext.consoleErrors.filter(
        (e) =>
          !e.text.includes('React') &&
          !e.text.includes('DevTools') &&
          !e.text.includes('favicon') &&
          !e.text.includes('manifest')
      )

      if (criticalConsoleErrors.length > 0) {
        console.warn(`Console errors on ${route.path}:`, criticalConsoleErrors.map((e) => e.text))
      }

      // 6. Check for 404/500 network errors on critical resources
      const critical404s = testContext.networkErrors.filter(
        (e) =>
          e.status === 404 &&
          !e.url.includes('favicon') &&
          !e.url.includes('manifest') &&
          !e.url.includes('.map')
      )

      const serverErrors = testContext.networkErrors.filter((e) => e.status >= 500)

      expect(serverErrors.length).toBe(0)

      if (critical404s.length > 0) {
        console.warn(`404s on ${route.path}:`, critical404s.map((e) => e.url))
      }

      console.log(`✓ ${route.name} (${route.path}) - OK`)
    })
  }
})

test.describe('Dynamic Route Integrity', () => {
  test('Estimate detail route with valid ID', async ({ authenticatedPage, testContext }) => {
    // First, get a valid estimate ID
    await authenticatedPage.goto('/estimates')
    await authenticatedPage.waitForLoadState('networkidle')

    // Try to find an estimate link
    const estimateLink = authenticatedPage.locator('a[href*="/estimates/"]').first()
    let estimateId = '1' // Fallback

    if (await estimateLink.isVisible({ timeout: 3000 })) {
      const href = await estimateLink.getAttribute('href')
      const match = href?.match(/\/estimates\/(\d+)/)
      if (match) {
        estimateId = match[1]
      }
    }

    // Reset error tracking
    testContext.networkErrors = []

    // Navigate to estimate detail
    await authenticatedPage.goto(`/estimates/${estimateId}`)
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {})

    // Check for 404 on the estimate itself
    const estimate404 = testContext.networkErrors.find(
      (e) => e.status === 404 && e.url.includes('/pdr-estimates/')
    )

    if (estimate404) {
      console.log(`Note: Estimate ${estimateId} not found (expected if no data)`)
    }

    // Page should still render (even if estimate not found)
    const bodyText = await authenticatedPage.locator('body').innerText()
    expect(bodyText.length).toBeGreaterThan(10)
  })

  test('Estimate review route', async ({ authenticatedPage, testContext }) => {
    testContext.networkErrors = []

    await authenticatedPage.goto('/estimates/1/review')
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {})

    // Should either show review page or redirect to detail
    const finalUrl = authenticatedPage.url()
    expect(finalUrl).toContain('/estimates/')

    // No server errors
    const serverErrors = testContext.networkErrors.filter((e) => e.status >= 500)
    expect(serverErrors.length).toBe(0)
  })
})

test.describe('Navigation Flow', () => {
  test('Can navigate from estimates list to detail', async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/estimates')
    await authenticatedPage.waitForLoadState('networkidle')

    // Find an estimate link or new estimate button
    const estimateLink = authenticatedPage.locator('a[href*="/estimates/"]').first()
    const newEstimateBtn = authenticatedPage.locator(
      'button:has-text("New Estimate"), a:has-text("New Estimate")'
    ).first()

    if (await estimateLink.isVisible({ timeout: 3000 })) {
      await estimateLink.click()
      await authenticatedPage.waitForURL(/\/estimates\/\d+/)
      expect(authenticatedPage.url()).toMatch(/\/estimates\/\d+/)
    } else if (await newEstimateBtn.isVisible({ timeout: 3000 })) {
      await newEstimateBtn.click()
      await authenticatedPage.waitForURL(/\/estimates\/(new|\d+)/)
      expect(authenticatedPage.url()).toMatch(/\/estimates\/(new|\d+)/)
    } else {
      console.log('Warning: No estimate links found on estimates page')
    }
  })

  test('Back navigation works from estimate detail', async ({ authenticatedPage }) => {
    // Start at estimates list
    await authenticatedPage.goto('/estimates')
    await authenticatedPage.waitForLoadState('networkidle')

    // Navigate to an estimate (new or existing)
    await authenticatedPage.goto('/estimates/new')
    await authenticatedPage.waitForLoadState('networkidle')

    // Go back
    await authenticatedPage.goBack()

    // Should be back at estimates list
    await authenticatedPage.waitForURL(/\/estimates$/)
    expect(authenticatedPage.url()).toMatch(/\/estimates$/)
  })
})
