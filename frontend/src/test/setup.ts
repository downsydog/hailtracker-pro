// Minimal test setup - mock browser APIs not in jsdom
import '@testing-library/jest-dom'

// Mock ResizeObserver (not in jsdom)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
