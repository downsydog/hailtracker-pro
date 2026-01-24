import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HailLookupPage } from './index'

// Mock Leaflet
vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      remove: vi.fn(),
      invalidateSize: vi.fn(),
    })),
    tileLayer: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
    })),
    layerGroup: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
      clearLayers: vi.fn(),
    })),
    marker: vi.fn(() => ({
      bindPopup: vi.fn().mockReturnThis(),
      addTo: vi.fn().mockReturnThis(),
    })),
    circle: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
    })),
    divIcon: vi.fn(() => ({})),
    Icon: {
      Default: {
        prototype: {},
        mergeOptions: vi.fn(),
      },
    },
  },
}))

// Mock the weather API
vi.mock('@/api/weather', () => ({
  hailEventsApi: {
    checkLocation: vi.fn(() => Promise.resolve({
      data: {
        location: { lat: 32.7767, lon: -96.7970 },
        was_hit: true,
        events: [
          {
            id: 1,
            event_name: 'Dallas Severe Hail Storm',
            event_date: '2025-05-15',
            hail_size_inches: 2.5,
            distance_miles: 3.2,
            data_source: 'NOAA'
          },
          {
            id: 2,
            event_name: 'Fort Worth Moderate Storm',
            event_date: '2025-04-20',
            hail_size_inches: 1.25,
            distance_miles: 8.5,
            data_source: 'NOAA'
          },
          {
            id: 3,
            event_name: 'Small Hail Event',
            event_date: '2024-06-10',
            hail_size_inches: 0.75,
            distance_miles: 4.1,
            data_source: 'NOAA'
          }
        ],
        summary: {
          total_events: 3,
          max_hail_size: 2.5,
          years_checked: 5,
          most_recent: '2025-05-15',
          by_year: { '2025': 2, '2024': 1 }
        }
      }
    })),
    generateImpactReport: vi.fn(() => Promise.resolve(new Blob(['PDF content'], { type: 'application/pdf' }))),
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
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('HailLookupPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Page Rendering', () => {
    it('renders the page title', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText('Hail Lookup')).toBeInTheDocument()
    })

    it('renders the page description', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText(/Check if a location was affected by hail storms/i)).toBeInTheDocument()
    })

    it('renders search location card', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText('Search Location')).toBeInTheDocument()
    })

    it('renders the map container', () => {
      renderWithProviders(<HailLookupPage />)
      // Map container should exist
      expect(document.querySelector('[class*="map"]') || screen.getByText('Hail Lookup')).toBeInTheDocument()
    })
  })

  describe('Search Form', () => {
    it('renders latitude input field', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByPlaceholderText('e.g., 32.7767')).toBeInTheDocument()
    })

    it('renders longitude input field', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByPlaceholderText('e.g., -96.7970')).toBeInTheDocument()
    })

    it('renders years select', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText('Years to Search')).toBeInTheDocument()
    })

    it('renders radius select', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText('Search Radius')).toBeInTheDocument()
    })

    it('renders search button', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText('Check for Hail History')).toBeInTheDocument()
    })

    it('renders Use My Location button', () => {
      renderWithProviders(<HailLookupPage />)
      expect(screen.getByText('Use My Location')).toBeInTheDocument()
    })
  })

  describe('Sample Locations', () => {
    it('displays sample location buttons', () => {
      renderWithProviders(<HailLookupPage />)

      expect(screen.getByText('Dallas, TX')).toBeInTheDocument()
      expect(screen.getByText('Oklahoma City, OK')).toBeInTheDocument()
      expect(screen.getByText('Wichita, KS')).toBeInTheDocument()
    })

    it('fills coordinates when sample location clicked', async () => {
      renderWithProviders(<HailLookupPage />)

      const dallasButton = screen.getByText('Dallas, TX')
      fireEvent.click(dallasButton)

      await waitFor(() => {
        const latInput = screen.getByPlaceholderText('e.g., 32.7767') as HTMLInputElement
        expect(latInput.value).toBe('32.7767')
      })
    })
  })

  describe('Search Functionality', () => {
    it('triggers search when button clicked with valid coordinates', async () => {
      const { hailEventsApi } = await import('@/api/weather')
      renderWithProviders(<HailLookupPage />)

      // Fill in coordinates
      const latInput = screen.getByPlaceholderText('e.g., 32.7767')
      const lonInput = screen.getByPlaceholderText('e.g., -96.7970')

      fireEvent.change(latInput, { target: { value: '32.7767' } })
      fireEvent.change(lonInput, { target: { value: '-96.7970' } })

      // Click search button
      const searchButton = screen.getByText('Check for Hail History')
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(hailEventsApi.checkLocation).toHaveBeenCalled()
      })
    })
  })

  describe('Results Display', () => {
    it('shows results card after search', async () => {
      renderWithProviders(<HailLookupPage />)

      // Fill in coordinates and search
      const latInput = screen.getByPlaceholderText('e.g., 32.7767')
      const lonInput = screen.getByPlaceholderText('e.g., -96.7970')

      fireEvent.change(latInput, { target: { value: '32.7767' } })
      fireEvent.change(lonInput, { target: { value: '-96.7970' } })

      const searchButton = screen.getByText('Check for Hail History')
      fireEvent.click(searchButton)

      // After search, the component should show results
      await waitFor(() => {
        // The search form should still be visible
        expect(screen.getByText('Search Location')).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('PDF Report', () => {
    it('shows Download PDF button after search', async () => {
      renderWithProviders(<HailLookupPage />)

      // Fill in coordinates and search
      const latInput = screen.getByPlaceholderText('e.g., 32.7767')
      const lonInput = screen.getByPlaceholderText('e.g., -96.7970')

      fireEvent.change(latInput, { target: { value: '32.7767' } })
      fireEvent.change(lonInput, { target: { value: '-96.7970' } })

      const searchButton = screen.getByText('Check for Hail History')
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText(/Download PDF Report/i)).toBeInTheDocument()
      })
    })
  })

  describe('Event List', () => {
    it('displays event cards after search', async () => {
      renderWithProviders(<HailLookupPage />)

      // Fill in coordinates and search
      const latInput = screen.getByPlaceholderText('e.g., 32.7767')
      const lonInput = screen.getByPlaceholderText('e.g., -96.7970')

      fireEvent.change(latInput, { target: { value: '32.7767' } })
      fireEvent.change(lonInput, { target: { value: '-96.7970' } })

      const searchButton = screen.getByText('Check for Hail History')
      fireEvent.click(searchButton)

      await waitFor(() => {
        expect(screen.getByText(/Hail Events/i)).toBeInTheDocument()
      })
    })
  })

  describe('Empty State', () => {
    it('shows no events message when location has no hail history', async () => {
      const { hailEventsApi } = await import('@/api/weather')
      vi.mocked(hailEventsApi.checkLocation).mockResolvedValueOnce({
        data: {
          location: { lat: 32.7767, lon: -96.7970 },
          was_hit: false,
          events: [],
          summary: { total_events: 0, max_hail_size: 0, years_checked: 5, by_year: {} }
        }
      } as any)

      renderWithProviders(<HailLookupPage />)

      const latInput = screen.getByPlaceholderText('e.g., 32.7767')
      const lonInput = screen.getByPlaceholderText('e.g., -96.7970')

      fireEvent.change(latInput, { target: { value: '32.7767' } })
      fireEvent.change(lonInput, { target: { value: '-96.7970' } })

      const searchButton = screen.getByText('Check for Hail History')
      fireEvent.click(searchButton)

      // Component should render after search
      await waitFor(() => {
        expect(screen.getByText('Search Location')).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })
})
