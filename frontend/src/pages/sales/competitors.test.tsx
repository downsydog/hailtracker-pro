import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { CompetitorsPage } from './competitors'

// Use vi.hoisted to create mock functions that are available before module loading
const { mockGetActivity, mockGetSummary, mockLogActivity } = vi.hoisted(() => ({
  mockGetActivity: vi.fn(),
  mockGetSummary: vi.fn(),
  mockLogActivity: vi.fn(),
}))

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getCompetitorActivity: mockGetActivity,
  getCompetitorSummary: mockGetSummary,
  logCompetitorActivity: mockLogActivity,
}))

const mockActivityData = {
  activity: [
    {
      id: 1,
      salesperson_id: 1,
      competitor_name: 'ABC Roofing',
      activity_type: 'CANVASSING',
      location_lat: 32.77,
      location_lon: -96.79,
      notes: 'Team of 3 canvassing',
      spotted_at: '2024-01-20T11:00:00Z',
    },
    {
      id: 2,
      salesperson_id: 1,
      competitor_name: 'XYZ Restoration',
      activity_type: 'TRUCK_PARKED',
      location_lat: 32.78,
      location_lon: -96.8,
      notes: 'Truck with signage',
      spotted_at: '2024-01-21T15:00:00Z',
    },
    {
      id: 3,
      salesperson_id: 1,
      competitor_name: 'Dent Wizard',
      activity_type: 'WORKING_JOB',
      location_lat: 32.79,
      location_lon: -96.81,
      notes: null,
      spotted_at: '2024-01-22T10:00:00Z',
    },
    {
      id: 4,
      salesperson_id: 1,
      competitor_name: 'PDR Nation',
      activity_type: 'SIGN_PLACED',
      location_lat: 32.80,
      location_lon: -96.82,
      notes: 'Yard sign in front of house',
      spotted_at: '2024-01-23T14:00:00Z',
    },
  ],
  total: 4,
}

const mockSummaryData = {
  competitors: [
    { competitor_name: 'ABC Roofing', total_sightings: 5, active_days: 3, last_seen: '2024-01-20T11:00:00Z' },
    { competitor_name: 'XYZ Restoration', total_sightings: 3, active_days: 2, last_seen: '2024-01-21T15:00:00Z' },
    { competitor_name: 'Dent Wizard', total_sightings: 2, active_days: 1, last_seen: '2024-01-22T10:00:00Z' },
  ],
}

const mockEmptyActivityData = {
  activity: [],
  total: 0,
}

const mockEmptySummaryData = {
  competitors: [],
}

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
    mockGetActivity.mockResolvedValue(mockActivityData)
    mockGetSummary.mockResolvedValue(mockSummaryData)
    mockLogActivity.mockResolvedValue({ success: true, activity_id: 5 })
  })

  describe('Page Rendering', () => {
    it('renders the page title', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Competitor Tracking')).toBeInTheDocument()
    })

    it('renders the page description', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Monitor and log competitor activity in your territory')).toBeInTheDocument()
    })

    it('has a Log Competitor button', () => {
      renderWithProviders(<CompetitorsPage />)

      const addButton = screen.getByRole('button', { name: /log competitor/i })
      expect(addButton).toBeInTheDocument()
    })

    it('has a days filter dropdown', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Last 7 days')).toBeInTheDocument()
    })
  })

  describe('Stats Cards', () => {
    it('displays Total Sightings stat card', async () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Total Sightings')).toBeInTheDocument()

      // Wait for summary data to load - Total from mock data: 5 + 3 + 2 = 10
      await waitFor(() => {
        expect(screen.getByText('10')).toBeInTheDocument()
      })
    })

    it('displays Competitors stat card', async () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Competitors')).toBeInTheDocument()

      // Wait for summary data - 3 competitors in mock data
      await waitFor(() => {
        // Find the stat card value specifically
        const competitorCards = screen.getAllByText('3')
        expect(competitorCards.length).toBeGreaterThanOrEqual(1)
      })
    })

    it('displays Period stat card', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Period')).toBeInTheDocument()
      expect(screen.getByText('7 days')).toBeInTheDocument()
    })

    it('displays Avg/Day stat card', async () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Avg/Day')).toBeInTheDocument()

      // Wait for summary data - 10 sightings / 7 days = 1.4
      await waitFor(() => {
        expect(screen.getByText('1.4')).toBeInTheDocument()
      })
    })
  })

  describe('Activity Map Section', () => {
    it('displays Activity Map header', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Activity Map')).toBeInTheDocument()
    })
  })

  describe('Competitor Summary Section', () => {
    it('displays Competitor Summary header', async () => {
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('Competitor Summary')).toBeInTheDocument()
      })
    })

    it('displays competitor names in summary', async () => {
      renderWithProviders(<CompetitorsPage />)

      // Wait for summary data to load by checking for active days text
      await waitFor(() => {
        expect(screen.getByText('3 active days')).toBeInTheDocument()
      })

      // Now competitor names should be visible - they appear in both summary and activity
      expect(screen.getAllByText('ABC Roofing').length).toBeGreaterThan(0)
      expect(screen.getAllByText('XYZ Restoration').length).toBeGreaterThan(0)
    })

    it('displays active days for each competitor', async () => {
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('3 active days')).toBeInTheDocument()
      })

      expect(screen.getByText('2 active days')).toBeInTheDocument()
      expect(screen.getByText('1 active days')).toBeInTheDocument()
    })

    it('displays total sightings count for each competitor', async () => {
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('3 active days')).toBeInTheDocument()
      })

      // The sighting count "5" should be visible
      expect(screen.getByText('5')).toBeInTheDocument()
    })

    it('displays ranking badges for competitors', async () => {
      renderWithProviders(<CompetitorsPage />)

      // Wait for summary data to load
      await waitFor(() => {
        expect(screen.getByText('3 active days')).toBeInTheDocument()
      })

      // Check that ranking numbers exist (they appear in circular badges)
      const ones = screen.getAllByText('1')
      expect(ones.length).toBeGreaterThanOrEqual(1)
    })

    it('shows empty state when no competitors', async () => {
      mockGetSummary.mockResolvedValue(mockEmptySummaryData)
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('No competitor activity logged')).toBeInTheDocument()
      })
    })
  })

  describe('Recent Activity Section', () => {
    it('displays Recent Activity header', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Recent Activity')).toBeInTheDocument()
    })

    it('displays competitor names in activity list', async () => {
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getAllByText('ABC Roofing').length).toBeGreaterThan(0)
      })

      expect(screen.getAllByText('XYZ Restoration').length).toBeGreaterThan(0)
    })

    it('displays activity types in activity list', async () => {
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('Canvassing / Door-to-Door')).toBeInTheDocument()
      })

      expect(screen.getByText('Truck Parked')).toBeInTheDocument()
      expect(screen.getByText('Working on Vehicle')).toBeInTheDocument()
      expect(screen.getByText('Yard Sign Placed')).toBeInTheDocument()
    })

    it('displays notes when available', async () => {
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('Team of 3 canvassing')).toBeInTheDocument()
      })

      expect(screen.getByText('Truck with signage')).toBeInTheDocument()
      expect(screen.getByText('Yard sign in front of house')).toBeInTheDocument()
    })

    it('shows empty state when no activity', async () => {
      mockGetActivity.mockResolvedValue(mockEmptyActivityData)
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText(/No competitor activity in the last/)).toBeInTheDocument()
      })
    })

    it('shows Log your first sighting link in empty state', async () => {
      mockGetActivity.mockResolvedValue(mockEmptyActivityData)
      renderWithProviders(<CompetitorsPage />)

      await waitFor(() => {
        expect(screen.getByText('Log your first sighting')).toBeInTheDocument()
      })
    })
  })

  describe('Loading State', () => {
    it('shows loading message while fetching activity', async () => {
      mockGetActivity.mockImplementation(() => new Promise(() => {})) // Never resolves
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })
  })

  describe('Log Competitor Dialog', () => {
    it('opens log competitor dialog when clicking button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      const addButton = screen.getByRole('button', { name: /log competitor/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Log Competitor Activity')).toBeInTheDocument()
      })
    })

    it('shows Competitor Name field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByText('Competitor Name *')).toBeInTheDocument()
      })
    })

    it('shows Activity Type field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByText('Activity Type *')).toBeInTheDocument()
      })
    })

    it('shows Notes field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByText('Notes')).toBeInTheDocument()
      })
    })

    it('shows notes textarea with placeholder', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Description of what you saw...')).toBeInTheDocument()
      })
    })

    it('has Cancel button in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })
    })

    it('has Log Activity submit button in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /log activity/i })).toBeInTheDocument()
      })
    })

    it('Log Activity button is disabled when competitor name is not selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /log activity/i })
        expect(submitButton).toBeDisabled()
      })
    })

    it('closes dialog when Cancel is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByText('Log Competitor Activity')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      await waitFor(() => {
        expect(screen.queryByText('Log Competitor Activity')).not.toBeInTheDocument()
      })
    })

    it('shows competitor name placeholder', async () => {
      const user = userEvent.setup()
      renderWithProviders(<CompetitorsPage />)

      await user.click(screen.getByRole('button', { name: /log competitor/i }))

      await waitFor(() => {
        expect(screen.getByText('Select competitor')).toBeInTheDocument()
      })
    })
  })

  describe('Days Filter', () => {
    it('shows Last 7 days as default', () => {
      renderWithProviders(<CompetitorsPage />)

      expect(screen.getByText('Last 7 days')).toBeInTheDocument()
    })

    it('has days filter trigger', () => {
      renderWithProviders(<CompetitorsPage />)

      // Find combobox for days filter
      const comboboxes = screen.getAllByRole('combobox')
      expect(comboboxes.length).toBeGreaterThan(0)
    })
  })
})
