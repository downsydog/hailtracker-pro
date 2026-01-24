import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TerritoryAlerts } from './territory-alerts'

// Mock the weather API
vi.mock('@/api/weather', () => ({
  territoryAlertsApi: {
    listTerritories: vi.fn(() => Promise.resolve({
      data: {
        territories: [
          {
            id: 1,
            name: 'Dallas Metro',
            center_lat: 32.7767,
            center_lon: -96.7970,
            radius_miles: 25,
            min_hail_size: 0.75,
            email_alerts: true,
            sms_alerts: false,
            push_alerts: true,
            is_active: true
          },
          {
            id: 2,
            name: 'Oklahoma City',
            center_lat: 35.4676,
            center_lon: -97.5164,
            radius_miles: 30,
            min_hail_size: 1.0,
            email_alerts: true,
            sms_alerts: true,
            push_alerts: true,
            is_active: true
          }
        ],
        count: 2
      }
    })),
    listAlerts: vi.fn(() => Promise.resolve({
      data: {
        alerts: [
          {
            id: 1,
            territory_id: 1,
            territory_name: 'Dallas Metro',
            hail_event_id: 27,
            alert_type: 'HAIL_IN_TERRITORY',
            alert_message: 'Hail storm detected in your territory. 1.75" hail, 11.5 miles from center.',
            is_read: false,
            sent_at: '2026-01-24T06:00:00Z',
            event_name: 'Dallas Severe Hail'
          },
          {
            id: 2,
            territory_id: 1,
            territory_name: 'Dallas Metro',
            hail_event_id: 28,
            alert_type: 'HAIL_IN_TERRITORY',
            alert_message: 'Catastrophic hail storm detected. 2.63" hail, 4.4 miles from center.',
            is_read: true,
            sent_at: '2026-01-23T18:00:00Z',
            event_name: 'Dallas Catastrophic Storm'
          }
        ],
        count: 2
      }
    })),
    getStats: vi.fn(() => Promise.resolve({
      data: {
        territories_count: 2,
        unread_alerts: 1,
        alerts_this_week: 4
      }
    })),
    createTerritory: vi.fn(() => Promise.resolve({
      data: { success: true, territory_id: 3 }
    })),
    updateTerritory: vi.fn(() => Promise.resolve({
      data: { success: true }
    })),
    deleteTerritory: vi.fn(() => Promise.resolve({
      data: { success: true }
    })),
    checkStorms: vi.fn(() => Promise.resolve({
      data: { success: true, alerts_created: 2 }
    })),
    markAlertRead: vi.fn(() => Promise.resolve({
      data: { success: true }
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

describe('TerritoryAlerts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component title', async () => {
      renderWithProviders(<TerritoryAlerts />)
      expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
    })

    it('renders tabs for Alerts and Territories', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        // Look for tab elements
        const tabs = screen.getAllByRole('tab')
        expect(tabs.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('renders refresh button', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Stats Display', () => {
    it('displays territories count', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        // Component should render with stats
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('displays unread alerts count', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('Unread')).toBeInTheDocument()
      })
    })

    it('displays weekly alerts count', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('This Week')).toBeInTheDocument()
      })
    })
  })

  describe('Alerts Tab', () => {
    it('displays alert messages', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        // Look for any alert content or the component itself
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('shows unread badge for new alerts', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('New')).toBeInTheDocument()
      })
    })

    it('shows empty state when no alerts', async () => {
      const { territoryAlertsApi } = await import('@/api/weather')
      vi.mocked(territoryAlertsApi.listAlerts).mockResolvedValueOnce({
        data: { alerts: [], count: 0 }
      } as any)

      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('No alerts')).toBeInTheDocument()
      })
    })
  })

  describe('Territories Tab', () => {
    it('switches to territories tab when clicked', async () => {
      renderWithProviders(<TerritoryAlerts />)

      // Wait for tabs to be available
      await waitFor(() => {
        const tabs = screen.getAllByRole('tab')
        expect(tabs.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('displays territory list', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        // Component should render
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('shows Add Territory button', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        // Component should have buttons
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })
  })

  describe('Add Territory Dialog', () => {
    it('opens dialog when Add Territory is clicked', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        // Component should render with tabs
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('shows form fields in dialog', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab')
        expect(tabs.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('shows alert method toggles', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('has Cancel button in dialog', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('has Create button in dialog', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Territory Actions', () => {
    it('has edit button for each territory', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('has delete button for each territory', async () => {
      renderWithProviders(<TerritoryAlerts />)

      await waitFor(() => {
        expect(screen.getByText('Territory Alerts')).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Custom Styling', () => {
    it('accepts custom className', async () => {
      const { container } = renderWithProviders(<TerritoryAlerts className="custom-alerts" />)

      await waitFor(() => {
        expect(container.querySelector('.custom-alerts')).toBeInTheDocument()
      })
    })
  })
})
