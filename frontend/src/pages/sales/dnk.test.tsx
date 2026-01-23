import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { DNKPage } from './dnk'

// Mock the API module with inline data
vi.mock('@/api/elite-sales', () => ({
  getDNKList: vi.fn(() => Promise.resolve({
    dnk_list: [
      {
        id: 1,
        address: '999 No Soliciting St, Dallas, TX',
        latitude: 32.775,
        longitude: -96.795,
        reason: 'NO_SOLICITING',
        notes: 'Large sign on door',
        reported_by: 1,
        added_at: '2024-01-19T10:00:00Z',
      },
      {
        id: 2,
        address: '888 Private Dr, Dallas, TX',
        latitude: 32.782,
        longitude: -96.805,
        reason: 'REQUESTED',
        notes: 'Homeowner asked not to return',
        reported_by: 1,
        added_at: '2024-01-20T14:00:00Z',
      },
    ],
    count: 2,
  })),
  addDNK: vi.fn(() => Promise.resolve({ success: true, dnk_id: 3 })),
  removeDNK: vi.fn(() => Promise.resolve({ success: true })),
}))

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

describe('DNKPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', () => {
    renderWithProviders(<DNKPage />)

    expect(screen.getByText('Do Not Knock List')).toBeInTheDocument()
  })

  it('displays DNK entries after loading', async () => {
    renderWithProviders(<DNKPage />)

    await waitFor(() => {
      expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
    })

    expect(screen.getByText('888 Private Dr, Dallas, TX')).toBeInTheDocument()
  })

  it('shows reason badges for each entry', async () => {
    renderWithProviders(<DNKPage />)

    await waitFor(() => {
      // Text appears in both stat cards and entry badges
      expect(screen.getAllByText('No Soliciting Sign').length).toBeGreaterThan(0)
    })

    expect(screen.getAllByText('Customer Requested').length).toBeGreaterThan(0)
  })

  it('has an Add DNK button', () => {
    renderWithProviders(<DNKPage />)

    const addButton = screen.getByRole('button', { name: /add.*dnk/i })
    expect(addButton).toBeInTheDocument()
  })

  it('opens add DNK dialog when clicking button', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DNKPage />)

    const addButton = screen.getByRole('button', { name: /add.*dnk/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByText('Add Do Not Knock Address')).toBeInTheDocument()
    })
  })

  it('has a search input', () => {
    renderWithProviders(<DNKPage />)

    const searchInput = screen.getByPlaceholderText(/search/i)
    expect(searchInput).toBeInTheDocument()
  })

  it('has a reason filter dropdown', () => {
    renderWithProviders(<DNKPage />)

    expect(screen.getByText(/all reasons/i)).toBeInTheDocument()
  })

  it('displays entries with action buttons', async () => {
    renderWithProviders(<DNKPage />)

    await waitFor(() => {
      // Each DNK entry has an address and action buttons
      expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
    })

    // There should be multiple buttons on the page (add button + delete buttons)
    const allButtons = screen.getAllByRole('button')
    expect(allButtons.length).toBeGreaterThan(2)
  })

  it('shows notes for entries when available', async () => {
    renderWithProviders(<DNKPage />)

    await waitFor(() => {
      expect(screen.getByText('Large sign on door')).toBeInTheDocument()
    })
  })
})
