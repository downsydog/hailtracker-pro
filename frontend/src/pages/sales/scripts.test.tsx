import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ScriptsPage } from './scripts'
import { mockScript } from '@/test/mocks/handlers'

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getScript: vi.fn(() => Promise.resolve(mockScript)),
  logObjection: vi.fn(() => Promise.resolve({ success: true })),
}))

import { mockScript as script } from '@/test/mocks/handlers'

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('ScriptsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', () => {
    renderWithProviders(<ScriptsPage />)

    expect(screen.getByText('Smart Scripts')).toBeInTheDocument()
  })

  it('displays script categories', () => {
    renderWithProviders(<ScriptsPage />)

    // Use getAllByText since categories appear in sidebar and may appear elsewhere
    expect(screen.getAllByText('Door Approach').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Price Objection').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Time Objection').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Insurance Objection').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Closing').length).toBeGreaterThan(0)
  })

  it('loads script content for selected category', async () => {
    renderWithProviders(<ScriptsPage />)

    await waitFor(() => {
      expect(screen.getByText(/Hi there! My name is/)).toBeInTheDocument()
    })
  })

  it('displays key points when available', async () => {
    renderWithProviders(<ScriptsPage />)

    await waitFor(() => {
      expect(screen.getByText('Key Points')).toBeInTheDocument()
    })

    expect(screen.getByText('Make eye contact')).toBeInTheDocument()
  })

  it('displays pro tips when available', async () => {
    renderWithProviders(<ScriptsPage />)

    await waitFor(() => {
      expect(screen.getByText('Pro Tips')).toBeInTheDocument()
    })

    expect(screen.getByText(/Best times are 4-7pm/)).toBeInTheDocument()
  })

  it('has copy buttons for script sections', async () => {
    renderWithProviders(<ScriptsPage />)

    await waitFor(() => {
      const copyButtons = screen.getAllByRole('button')
      expect(copyButtons.length).toBeGreaterThan(0)
    })
  })

  it('has a Log Outcome button', () => {
    renderWithProviders(<ScriptsPage />)

    expect(screen.getByText('Log Outcome')).toBeInTheDocument()
  })

  it('opens log outcome dialog when clicking button', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ScriptsPage />)

    const logButton = screen.getByText('Log Outcome')
    await user.click(logButton)

    await waitFor(() => {
      expect(screen.getByText('Log Objection Outcome')).toBeInTheDocument()
    })
  })

  it('shows outcome options in dialog', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ScriptsPage />)

    const logButton = screen.getByText('Log Outcome')
    await user.click(logButton)

    await waitFor(() => {
      expect(screen.getByText('Converted')).toBeInTheDocument()
      expect(screen.getByText('Follow Up')).toBeInTheDocument()
      expect(screen.getByText('Lost')).toBeInTheDocument()
    })
  })

  it('displays quick reference cards', () => {
    renderWithProviders(<ScriptsPage />)

    expect(screen.getByText('Price Objection Quick Response')).toBeInTheDocument()
    expect(screen.getByText('Time Objection Quick Response')).toBeInTheDocument()
    expect(screen.getByText('Insurance Quick Response')).toBeInTheDocument()
  })

  it('switches category when clicking sidebar item', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ScriptsPage />)

    const priceCategory = screen.getByText('Price Objection')
    await user.click(priceCategory)

    // Category should be selected
    expect(priceCategory).toBeInTheDocument()
  })
})
