# E2E Tests - Stage 8G + 8H

End-to-end testing for the HailTracker Pro estimating workflow.

## Purpose

- **Stage 8G**: Smoke tests - "does the estimating system actually work"
- **Stage 8H**: Snapshot regression tests - detect UI regressions visually

This is NOT unit testing or performance testing.

## Test Coverage

### A. Auth + Boot
- Backend health check
- Frontend loads without console errors
- Login succeeds and persists session

### B. Estimate Core Flow
- Navigate to /estimates
- Create new estimate
- Enter minimum required data
- Save and verify redirect

### C. Panel + Damage Entry
- Select panels in diagram
- Enter dent damage data
- Verify data persistence

### D. Inline Access / R&I Flow (CRITICAL)
- Panel-specific R&I suggestions
- R&I pill states (AVAILABLE, ADDING, ADDED)
- Operation add without 404s

### E. Bulk Access Bundle
- "Apply Suggested Access" bulk add
- Activity logging verification
- Duplicate prevention

### F. R&I Tab
- Operations render
- Step breakdown
- Justification text

### G. PDF + Supplement
- Estimate PDF generation
- Supplement creation

### H. Dispute / Evidence Pack
- Adjuster pack generation

### I. Route Integrity
- All routes accessible
- No redirect loops
- No blank screens

## Stage 8H: Snapshot Regression Tests

Visual + structural snapshot testing to detect UI regressions:

### Snapshots Captured

| Page/State | Snapshot File |
|------------|---------------|
| Login page | `estimating-login.png` |
| Estimates list | `estimating-list.png` |
| New estimate | `estimating-new.png` |
| New estimate + Roof selected | `estimating-new-roof.png` |
| Saved estimate | `estimating-saved.png` |
| Saved + R&I added | `estimating-saved-roof-ri-added.png` |
| R&I tab | `estimating-ri-tab.png` |
| Review page | `estimating-review.png` |

### Region Snapshots

- `region-totals.png` - Totals sidebar
- `region-access-ri-roof.png` - R&I section (roof panel)
- `region-access-ri-added.png` - R&I section with ADDED pill
- `region-denial-pack.png` - Denial pack card
- `region-actions.png` - Actions panel

### Snapshot Stability

The test suite uses guards to ensure deterministic output:
- Fixed viewport: 1400x900
- Disabled animations/transitions
- Normalized timestamps ("Updated", "Today")
- Reduced motion preference

## Setup

```bash
# Install dependencies (including Playwright)
npm install

# Install browser (Chromium)
npm run e2e:install
```

## Running Tests

```bash
# Run all e2e tests (headless)
npm run e2e

# Run with browser visible
npm run e2e:headed

# Run with Playwright UI
npm run e2e:ui

# Debug mode (step through)
npm run e2e:debug

# Run specific test suites
npm run e2e:health   # Health checks only
npm run e2e:smoke    # Full smoke test
npm run e2e:routes   # Route integrity only
npm run e2e:snapshots        # Snapshot regression tests
npm run e2e:snapshots:update # Update baseline snapshots

# View HTML report
npm run e2e:report
```

## Configuration

Set environment variables to customize:

```bash
# Frontend URL (default: http://localhost:5173)
FRONTEND_URL=http://localhost:5173

# Backend URL (default: http://localhost:5000)
BACKEND_URL=http://localhost:5000

# Test credentials
TEST_USER_EMAIL=test@hailtracker.com
TEST_USER_PASSWORD=testpassword123
```

## File Structure

```
e2e/
├── README.md                       # This file
├── tsconfig.json                   # TypeScript config for e2e
├── global-setup.ts                 # Pre-test setup
├── utils/
│   ├── test-config.ts              # Configuration & selectors
│   ├── fixtures.ts                 # Custom test fixtures
│   └── snapshot-guards.ts          # Stage 8H: Snapshot stability helpers
├── health-check.spec.ts            # Basic connectivity tests
├── route-integrity.spec.ts         # Route scanning tests
├── estimating-smoke.spec.ts        # Stage 8G: Full workflow smoke test
├── estimating-snapshots.spec.ts    # Stage 8H: Visual regression tests
└── __snapshots__/                  # Baseline snapshots (auto-generated)
```

## Test Output

- **Console**: Real-time test progress
- **HTML Report**: `e2e-report/index.html`
- **JSON Results**: `e2e-results.json`
- **Screenshots**: `e2e-screenshots/` (on failure)
- **Snapshots**: `e2e/__snapshots__/` (baseline images)
- **Traces**: `test-results/` (on failure, for debugging)

## CI Integration

```yaml
# Example GitHub Actions
- name: Run E2E Tests
  run: |
    npm ci
    npm run e2e:install
    npm run e2e
  env:
    FRONTEND_URL: http://localhost:5173
    BACKEND_URL: http://localhost:5000
```

## Adding New Tests

1. Add test to appropriate spec file or create new one
2. Use `test` from `./utils/fixtures` for auth/error tracking
3. Use selectors from `TEST_CONFIG.SELECTORS`
4. Add data-testid attributes to components for stability

## Troubleshooting

### Tests fail on login
- Verify TEST_USER credentials are valid
- Check backend is running
- Check CORS configuration

### Tests timeout
- Increase timeouts in playwright.config.ts
- Check network connectivity
- Verify selectors match current UI

### Console errors in tests
- Check testContext.consoleErrors for details
- Some warnings are filtered (React dev, DevTools)

### Snapshot tests failing
- Run `npm run e2e:snapshots:update` to update baselines after intentional UI changes
- Check if dynamic content (timestamps, IDs) is causing flakiness
- Verify viewport is consistent (1400x900)
- Check `e2e/__snapshots__` for visual diff comparison

### Snapshot not deterministic
- Add element to `normalizeDynamicContent()` in `snapshot-guards.ts`
- Use `hideVolatileElements()` for elements that can't be normalized
- Check for CSS animations that aren't being disabled
