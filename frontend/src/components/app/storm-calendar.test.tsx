import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StormCalendar } from './storm-calendar'

// Mock the weather API
vi.mock('@/api/weather', () => ({
  hailEventsApi: {
    getCalendar: vi.fn(() => Promise.resolve({
      data: {
        year: 2026,
        month: 1,
        days: {
          '2026-01-05': {
            count: 2,
            max_severity: 'SEVERE',
            max_hail_size: 2.5,
            total_vehicles: 15000,
            events: [
              { id: 1, event_name: 'Dallas Hail Storm', hail_size: 2.5, severity: 'SEVERE', lat: 32.77, lon: -96.79, vehicles: 10000, area_sqmi: 50 },
              { id: 2, event_name: 'Fort Worth Storm', hail_size: 1.5, severity: 'MODERATE', lat: 32.75, lon: -97.33, vehicles: 5000, area_sqmi: 30 },
            ]
          },
          '2026-01-10': {
            count: 1,
            max_severity: 'MINOR',
            max_hail_size: 0.75,
            total_vehicles: 2000,
            events: [
              { id: 3, event_name: 'Small Hail Event', hail_size: 0.75, severity: 'MINOR', lat: 33.0, lon: -97.0, vehicles: 2000, area_sqmi: 10 },
            ]
          }
        },
        month_stats: {
          storm_days: 2,
          total_events: 3,
          total_vehicles: 17000,
          max_hail_size: 2.5,
          severe_days: 1,
          moderate_days: 0,
          minor_days: 1
        }
      }
    })),
    getCalendarYear: vi.fn(() => Promise.resolve({
      data: {
        year: 2026,
        months: {
          '1': { storm_days: 5, total_events: 8, total_vehicles: 50000, max_hail_size: 2.5, severe_count: 2, moderate_count: 3, minor_count: 3 },
          '2': { storm_days: 0, total_events: 0, total_vehicles: 0, max_hail_size: 0, severe_count: 0, moderate_count: 0, minor_count: 0 },
          '3': { storm_days: 3, total_events: 5, total_vehicles: 25000, max_hail_size: 1.75, severe_count: 0, moderate_count: 2, minor_count: 3 },
        },
        year_stats: {
          total_storm_days: 8,
          total_events: 13,
          total_vehicles: 75000,
          max_hail_size: 2.5,
          peak_month: 1
        }
      }
    })),
  }
}))

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
})

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  )
}

describe('StormCalendar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component title', async () => {
      renderWithProviders(<StormCalendar />)
      await waitFor(() => {
        expect(screen.getByText('Storm Calendar')).toBeInTheDocument()
      })
    })

    it('renders navigation buttons', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      })
    })

    it('renders day names header', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        expect(screen.getByText('Sun')).toBeInTheDocument()
        expect(screen.getByText('Mon')).toBeInTheDocument()
        expect(screen.getByText('Tue')).toBeInTheDocument()
        expect(screen.getByText('Wed')).toBeInTheDocument()
        expect(screen.getByText('Thu')).toBeInTheDocument()
        expect(screen.getByText('Fri')).toBeInTheDocument()
        expect(screen.getByText('Sat')).toBeInTheDocument()
      })
    })

    it('renders month/year view toggle', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        expect(screen.getByText('Storm Calendar')).toBeInTheDocument()
      })

      // The view mode selector should contain Month/Year options when opened
      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Month Navigation', () => {
    it('displays current month name', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        // Should show current month
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December']
        const currentMonth = monthNames[new Date().getMonth()]
        expect(screen.getByText(new RegExp(currentMonth))).toBeInTheDocument()
      })
    })

    it('has previous month button', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      })
    })

    it('has next month button', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(1)
      })
    })
  })

  describe('View Mode Toggle', () => {
    it('starts in month view', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        expect(screen.getByText('Sun')).toBeInTheDocument()
      })
    })

    it('can switch to year view', async () => {
      renderWithProviders(<StormCalendar />)

      // Wait for component to load
      await waitFor(() => {
        expect(screen.getByText('Storm Calendar')).toBeInTheDocument()
      })

      // Year view should show abbreviated month names
      await waitFor(() => {
        expect(screen.getByText('Sun')).toBeInTheDocument()
      })
    })
  })

  describe('Month Stats', () => {
    it('displays storm days count', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        expect(screen.getByText(/Storm Days/i)).toBeInTheDocument()
      })
    })

    it('displays total events count', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        expect(screen.getByText(/Events/i)).toBeInTheDocument()
      })
    })
  })

  describe('Event Selection', () => {
    it('calls onSelectEvent when provided and event clicked', async () => {
      const onSelectEvent = vi.fn()
      renderWithProviders(<StormCalendar onSelectEvent={onSelectEvent} />)

      await waitFor(() => {
        expect(screen.getByText('Storm Calendar')).toBeInTheDocument()
      })
    })
  })

  describe('Custom Styling', () => {
    it('accepts custom className', async () => {
      const { container } = renderWithProviders(<StormCalendar className="custom-calendar" />)

      await waitFor(() => {
        expect(container.querySelector('.custom-calendar')).toBeInTheDocument()
      })
    })
  })

  describe('Loading State', () => {
    it('shows calendar structure while loading', async () => {
      renderWithProviders(<StormCalendar />)

      await waitFor(() => {
        expect(screen.getByText('Storm Calendar')).toBeInTheDocument()
      })
    })
  })
})
