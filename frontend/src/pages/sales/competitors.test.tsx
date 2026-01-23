import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { CompetitorsPage } from './competitors'
import { mockCompetitorActivity } from '@/test/mocks/handlers'

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getCompetitorActivity: vi.fn(() => Promise.resolve({ activities: mockCompetitorActivity, total: mockCompetitorActivity.length })),
  getCompetitorSummary: vi.fn(() => Promise.resolve({
    competitors: [
      { company_name: 'ABC Roofing', total_sightings: 5, last_seen: '2024-01-20T11:00:00Z' },
      { company_name: 'XYZ Restoration', total_sightings: 3, last_seen: '2024-01-21T15:00:00Z' },
    ],
  })),
  logCompetitorActivity: vi.fn(() => Promise.resolve({ success: true, activity_id: 3 })),
}))

import { mockCompetitorActivity as activities } from '@/test/mocks/handlers'

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

describe('CompetitorsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', () => {
    renderWithProviders(<CompetitorsPage />)

    expect(screen.getByText('Competitor Tracking')).toBeInTheDocument()
  })

  it('displays competitor activities after loading', async () => {
    renderWithProviders(<CompetitorsPage />)

    await waitFor(() => {
      expect(screen.getByText('ABC Roofing')).toBeInTheDocument()
    })

    expect(screen.getByText('XYZ Restoration')).toBeInTheDocument()
  })

  it('shows activity type for each entry', async () => {
    renderWithProviders(<CompetitorsPage />)

    await waitFor(() => {
      expect(screen.getByText(/canvassing/i)).toBeInTheDocument()
    })
  })

  it('has a Log Competitor button', () => {
    renderWithProviders(<CompetitorsPage />)

    const addButton = screen.getByRole('button', { name: /log competitor/i })
    expect(addButton).toBeInTheDocument()
  })

  it('opens log competitor dialog when clicking button', async () => {
    const user = userEvent.setup()
    renderWithProviders(<CompetitorsPage />)

    const addButton = screen.getByRole('button', { name: /log competitor/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByText('Log Competitor Activity')).toBeInTheDocument()
    })
  })

  it('displays competitor summary section', async () => {
    renderWithProviders(<CompetitorsPage />)

    await waitFor(() => {
      expect(screen.getByText('Competitor Summary')).toBeInTheDocument()
    })
  })

  it('shows total sightings in summary', async () => {
    renderWithProviders(<CompetitorsPage />)

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument() // ABC Roofing sightings
    })
  })

  it('has activity type options in log form', async () => {
    const user = userEvent.setup()
    renderWithProviders(<CompetitorsPage />)

    const addButton = screen.getByRole('button', { name: /log competitor/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByText('Activity Type')).toBeInTheDocument()
    })
  })
})
