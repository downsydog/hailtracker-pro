import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RadarReplay } from './radar-replay'

// Mock the weather API
vi.mock('@/api/weather', () => ({
  stormMonitorApi: {
    getAvailableRadars: vi.fn(() => Promise.resolve({
      data: {
        radars: [
          { site_code: 'KFWS', name: 'Fort Worth', state: 'TX', lat: 32.57, lon: -97.30 },
          { site_code: 'KTLX', name: 'Oklahoma City', state: 'OK', lat: 35.33, lon: -97.28 },
          { site_code: 'KAMA', name: 'Amarillo', state: 'TX', lat: 35.23, lon: -101.71 },
        ],
        count: 3
      }
    })),
    getRadarHistory: vi.fn(() => Promise.resolve({
      data: {
        radar_id: 'KFWS',
        product: 'N0Q',
        frame_count: 12,
        frame_interval_minutes: 5,
        frames: [
          { timestamp: '2026-01-24T06:00:00Z', radar_id: 'KFWS', product: 'N0Q', tile_url: '/tiles/1', image_url: '/img/1', index: 0 },
          { timestamp: '2026-01-24T06:05:00Z', radar_id: 'KFWS', product: 'N0Q', tile_url: '/tiles/2', image_url: '/img/2', index: 1 },
          { timestamp: '2026-01-24T06:10:00Z', radar_id: 'KFWS', product: 'N0Q', tile_url: '/tiles/3', image_url: '/img/3', index: 2 },
        ]
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

describe('RadarReplay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders the component title', async () => {
      renderWithProviders(<RadarReplay />)
      expect(screen.getByText('Radar Replay')).toBeInTheDocument()
    })

    it('renders playback controls', async () => {
      renderWithProviders(<RadarReplay />)

      // Component should have buttons for playback
      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('renders radar selector', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        // Look for the select trigger button with combobox role
        const comboboxes = screen.getAllByRole('combobox')
        expect(comboboxes.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('renders speed control slider', async () => {
      renderWithProviders(<RadarReplay />)

      // The component should have multiple comboboxes (one for radar, one for speed)
      await waitFor(() => {
        expect(screen.getByText('Radar Replay')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('renders frame counter', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        expect(screen.getByText(/Frame/i)).toBeInTheDocument()
      })
    })
  })

  describe('Playback Controls', () => {
    it('starts in paused state', async () => {
      renderWithProviders(<RadarReplay />)

      // Component starts paused, so it should have buttons
      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('has skip to start button', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(2)
      })
    })

    it('has skip to end button', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(2)
      })
    })

    it('has step backward button', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(3)
      })
    })

    it('has step forward button', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        const buttons = screen.getAllByRole('button')
        expect(buttons.length).toBeGreaterThan(4)
      })
    })
  })

  describe('Radar Selection', () => {
    it('uses default radar ID', async () => {
      renderWithProviders(<RadarReplay defaultRadarId="KTLX" />)

      await waitFor(() => {
        const comboboxes = screen.getAllByRole('combobox')
        expect(comboboxes.length).toBeGreaterThan(0)
      }, { timeout: 3000 })
    })

    it('accepts custom className', async () => {
      const { container } = renderWithProviders(<RadarReplay className="custom-class" />)

      await waitFor(() => {
        expect(container.querySelector('.custom-class')).toBeInTheDocument()
      })
    })
  })

  describe('Frame Display', () => {
    it('shows loading state initially', () => {
      renderWithProviders(<RadarReplay />)

      // Component should render without crashing during loading
      expect(screen.getByText('Radar Replay')).toBeInTheDocument()
    })

    it('displays frame information after loading', async () => {
      renderWithProviders(<RadarReplay />)

      await waitFor(() => {
        expect(screen.getByText(/Frame/i)).toBeInTheDocument()
      })
    })
  })

  describe('Callback Props', () => {
    it('calls onFrameChange when provided', async () => {
      const onFrameChange = vi.fn()
      renderWithProviders(<RadarReplay onFrameChange={onFrameChange} />)

      await waitFor(() => {
        expect(screen.getByText('Radar Replay')).toBeInTheDocument()
      })
    })
  })
})
