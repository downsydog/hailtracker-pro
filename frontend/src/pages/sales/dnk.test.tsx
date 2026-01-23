import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { DNKPage } from './dnk'
import { mockDNKList } from '@/test/mocks/handlers'

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getDNKList: vi.fn(() => Promise.resolve({ dnk_list: mockDNKList, total: mockDNKList.length })),
  addDNK: vi.fn(() => Promise.resolve({ success: true, dnk_id: 3 })),
  removeDNK: vi.fn(() => Promise.resolve({ success: true })),
}))

import { mockDNKList as dnkList } from '@/test/mocks/handlers'

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
      expect(screen.getByText('No Soliciting Sign')).toBeInTheDocument()
    })

    expect(screen.getByText('Customer Requested')).toBeInTheDocument()
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

  it('displays delete buttons for entries', async () => {
    renderWithProviders(<DNKPage />)

    await waitFor(() => {
      const deleteButtons = screen.getAllByRole('button', { name: '' })
      expect(deleteButtons.length).toBeGreaterThan(0)
    })
  })

  it('shows notes for entries when available', async () => {
    renderWithProviders(<DNKPage />)

    await waitFor(() => {
      expect(screen.getByText('Large sign on door')).toBeInTheDocument()
    })
  })
})
