/**
 * Playwright Global Setup
 *
 * Stage 8G: Runs before all tests to verify prerequisites
 */

import { FullConfig } from '@playwright/test'

async function globalSetup(config: FullConfig) {
  const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:5173'
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000'

  console.log('\n========================================')
  console.log('E2E SMOKE TEST SUITE - Stage 8G')
  console.log('========================================')
  console.log(`Frontend URL: ${frontendUrl}`)
  console.log(`Backend URL: ${backendUrl}`)
  console.log('========================================\n')

  // Optional: Verify services are running
  try {
    const frontendCheck = await fetch(frontendUrl, { method: 'HEAD' }).catch(() => null)
    if (!frontendCheck) {
      console.warn('⚠️  Warning: Frontend may not be running at', frontendUrl)
    } else {
      console.log('✓ Frontend is reachable')
    }
  } catch {
    console.warn('⚠️  Warning: Could not reach frontend')
  }

  try {
    const backendCheck = await fetch(`${backendUrl}/api/health`, { method: 'GET' }).catch(() =>
      fetch(backendUrl, { method: 'HEAD' }).catch(() => null)
    )
    if (!backendCheck) {
      console.warn('⚠️  Warning: Backend may not be running at', backendUrl)
    } else {
      console.log('✓ Backend is reachable')
    }
  } catch {
    console.warn('⚠️  Warning: Could not reach backend')
  }

  console.log('\nStarting tests...\n')
}

export default globalSetup
