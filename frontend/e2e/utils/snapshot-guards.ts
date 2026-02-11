/**
 * Snapshot Guards - Stage 8H
 *
 * Utilities to ensure deterministic snapshot output by:
 * - Setting fixed viewport size
 * - Disabling animations/transitions
 * - Normalizing dynamic content (timestamps, relative times)
 */

import { Page } from '@playwright/test'

// Fixed viewport for consistent snapshots
export const SNAPSHOT_VIEWPORT = {
  width: 1400,
  height: 900,
}

/**
 * Apply all snapshot guards to ensure deterministic output.
 * Call this before taking any snapshots.
 */
export async function applySnapshotGuards(page: Page): Promise<void> {
  // 1. Set fixed viewport
  await page.setViewportSize(SNAPSHOT_VIEWPORT)

  // 2. Emulate prefers-reduced-motion
  await page.emulateMedia({ reducedMotion: 'reduce' })

  // 3. Inject CSS to disable animations/transitions
  await page.addStyleTag({
    content: `
      /* Stage 8H: Disable all animations for snapshot stability */
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }

      /* Disable smooth scrolling */
      html {
        scroll-behavior: auto !important;
      }

      /* Hide cursor blinking in inputs */
      input, textarea {
        caret-color: transparent !important;
      }

      /* Stabilize loading spinners */
      .animate-spin, [class*="spinner"], [class*="loading"] {
        animation: none !important;
      }
    `,
  })

  // 4. Wait for fonts to load
  await page.evaluate(() => document.fonts.ready)

  // 5. Small settle time for layout
  await page.waitForTimeout(100)
}

/**
 * Normalize dynamic content to prevent snapshot flakiness.
 * Call after page load, before taking snapshot.
 */
export async function normalizeDynamicContent(page: Page): Promise<void> {
  await page.evaluate(() => {
    // Normalize "X minutes ago", "just now", "today", etc.
    const timePatterns = [
      /\d+ (second|minute|hour|day|week|month|year)s? ago/i,
      /just now/i,
      /today at \d+:\d+/i,
      /yesterday/i,
      /\d+:\d+\s*(am|pm)/i,
    ]

    // Find and normalize time-related text
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    const nodesToNormalize: Text[] = []

    while (walker.nextNode()) {
      const node = walker.currentNode as Text
      const text = node.textContent || ''
      if (timePatterns.some((p) => p.test(text))) {
        nodesToNormalize.push(node)
      }
    }

    // Replace with static text
    for (const node of nodesToNormalize) {
      if (node.textContent) {
        node.textContent = node.textContent
          .replace(/\d+ (second|minute|hour|day|week|month|year)s? ago/gi, 'Updated')
          .replace(/just now/gi, 'Updated')
          .replace(/today at \d+:\d+/gi, 'Today')
          .replace(/yesterday/gi, 'Yesterday')
      }
    }

    // Normalize elements with data-testid containing "time" or "date"
    document.querySelectorAll('[data-testid*="time"], [data-testid*="date"]').forEach((el) => {
      if (el.textContent && el.textContent.match(/\d/)) {
        el.textContent = 'Date/Time'
      }
    })

    // Normalize estimate numbers that include timestamps
    document.querySelectorAll('[class*="estimate-number"], [data-testid*="estimate-number"]').forEach((el) => {
      // Keep format but normalize the numeric part after dash
      const text = el.textContent || ''
      if (text.match(/EST-\d+/)) {
        el.textContent = 'EST-XXXXX'
      }
    })
  })
}

/**
 * Hide specific elements that are inherently dynamic.
 * Use sparingly - prefer normalization over hiding.
 */
export async function hideVolatileElements(page: Page, selectors: string[]): Promise<void> {
  for (const selector of selectors) {
    await page.locator(selector).evaluateAll((elements) => {
      elements.forEach((el) => {
        ;(el as HTMLElement).style.visibility = 'hidden'
      })
    }).catch(() => {
      // Element may not exist, that's ok
    })
  }
}

/**
 * Wait for page to be fully stable before snapshot.
 * Combines network idle + no pending animations.
 */
export async function waitForStableState(page: Page): Promise<void> {
  // Wait for network to be idle
  await page.waitForLoadState('networkidle').catch(() => {})

  // Wait for any remaining animations to complete
  await page.evaluate(() => {
    return new Promise<void>((resolve) => {
      // Check if any animations are running
      const animations = document.getAnimations()
      if (animations.length === 0) {
        resolve()
        return
      }
      // Wait for all animations to finish
      Promise.all(animations.map((a) => a.finished.catch(() => {}))).then(() => resolve())
    })
  })

  // Small final settle
  await page.waitForTimeout(50)
}

/**
 * Full snapshot preparation - call before any snapshot test.
 */
export async function prepareForSnapshot(page: Page): Promise<void> {
  await applySnapshotGuards(page)
  await waitForStableState(page)
  await normalizeDynamicContent(page)
}

/**
 * Mask specific regions for snapshot comparison.
 * Useful for areas with dynamic content that can't be normalized.
 */
export function getSnapshotMask(page: Page, selectors: string[]) {
  return selectors.map((selector) => page.locator(selector)).filter(Boolean)
}
