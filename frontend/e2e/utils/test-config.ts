/**
 * E2E Test Configuration & Constants
 *
 * Stage 8G: Centralized config for smoke tests
 */

export const TEST_CONFIG = {
  // URLs (from env or defaults)
  FRONTEND_URL: process.env.FRONTEND_URL || 'http://localhost:5173',
  BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:5000',

  // Test credentials
  TEST_USER: {
    email: process.env.TEST_USER_EMAIL || 'test@hailtracker.com',
    password: process.env.TEST_USER_PASSWORD || 'testpassword123',
  },

  // Timeouts
  TIMEOUTS: {
    SHORT: 3000,
    MEDIUM: 10000,
    LONG: 30000,
    DOWNLOAD: 60000,
  },

  // Selectors (data-testid based for stability)
  SELECTORS: {
    // Auth
    LOGIN_EMAIL: '[data-testid="login-email"], input[name="email"], input[type="email"]',
    LOGIN_PASSWORD: '[data-testid="login-password"], input[name="password"], input[type="password"]',
    LOGIN_SUBMIT: '[data-testid="login-submit"], button[type="submit"]',

    // Navigation
    NAV_ESTIMATES: '[data-testid="nav-estimates"], a[href*="/estimates"]',
    NEW_ESTIMATE_BTN: '[data-testid="new-estimate"], button:has-text("New Estimate")',

    // Estimate Form
    VEHICLE_YEAR: '[data-testid="vehicle-year"], input[name="vehicleYear"]',
    VEHICLE_MAKE: '[data-testid="vehicle-make"], input[name="vehicleMake"]',
    VEHICLE_MODEL: '[data-testid="vehicle-model"], input[name="vehicleModel"]',
    CUSTOMER_NAME: '[data-testid="customer-name"], input[name="customerName"]',
    SAVE_ESTIMATE: '[data-testid="save-estimate"], button:has-text("Save")',

    // Vehicle Diagram
    PANEL_ROOF: '[data-testid="panel-roof"], [data-panel="roof"], .panel-roof',
    PANEL_HOOD: '[data-testid="panel-hood"], [data-panel="hood"], .panel-hood',

    // Panel Entry
    DENT_COUNT_SELECT: '[data-testid="dent-count"], select[name="countRange"]',
    DENT_SIZE_SELECT: '[data-testid="dent-size"], select[name="dentSize"]',
    PANEL_SAVE: '[data-testid="panel-save"], button:has-text("Save Panel")',

    // R&I Section
    RI_SECTION: '[data-testid="ri-section"], .ri-section, [class*="access"]',
    RI_PILL: '[data-testid="ri-pill"], button[class*="pill"]',
    RI_PILL_ADDED: '[data-testid="ri-pill-added"], button[class*="green"]',
    BULK_ADD_BTN: 'button:has-text("Apply Suggested"), button:has-text("Add All")',

    // Tabs
    TAB_RI: '[data-testid="tab-ri"], button:has-text("R&I"), [role="tab"]:has-text("R&I")',
    TAB_REVIEW: '[data-testid="tab-review"], button:has-text("Review")',

    // PDF/Downloads
    DOWNLOAD_PDF: 'button:has-text("Download PDF"), button:has-text("PDF")',
    DISPUTE_PACK: 'button:has-text("Dispute"), button:has-text("Adjuster Pack")',

    // Supplement
    NEW_SUPPLEMENT: 'button:has-text("New Supplement"), button:has-text("Create Supplement")',
    SUPPLEMENT_SAVE: 'button:has-text("Save Supplement")',
  },

  // Routes to test
  ROUTES: {
    HOME: '/',
    LOGIN: '/login',
    ESTIMATES: '/estimates',
    ESTIMATES_NEW: '/estimates/new',
    ESTIMATE_DETAIL: (id: string | number) => `/estimates/${id}`,
    ESTIMATE_REVIEW: (id: string | number) => `/estimates/${id}/review`,
  },
}

// Test data generators
export const generateTestEstimate = () => ({
  vehicleYear: String(2020 + Math.floor(Math.random() * 5)),
  vehicleMake: ['Toyota', 'Honda', 'Ford', 'Chevrolet'][Math.floor(Math.random() * 4)],
  vehicleModel: ['Camry', 'Accord', 'F-150', 'Silverado'][Math.floor(Math.random() * 4)],
  customerName: `Test Customer ${Date.now()}`,
  customerPhone: '555-' + String(Math.floor(Math.random() * 10000)).padStart(4, '0'),
})

export const generateTestPanel = () => ({
  countRange: ['1-5', '6-15', '16-30'][Math.floor(Math.random() * 3)],
  dentSize: ['dime', 'nickel', 'quarter'][Math.floor(Math.random() * 3)],
})
