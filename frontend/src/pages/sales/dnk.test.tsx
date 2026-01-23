import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { DNKPage } from './dnk'

// Use vi.hoisted for proper mock hoisting
const { mockGetDNKList, mockAddDNK, mockRemoveDNK } = vi.hoisted(() => ({
  mockGetDNKList: vi.fn(),
  mockAddDNK: vi.fn(),
  mockRemoveDNK: vi.fn(),
}))

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getDNKList: mockGetDNKList,
  addDNK: mockAddDNK,
  removeDNK: mockRemoveDNK,
}))

const mockDNKData = {
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
    {
      id: 3,
      address: '777 Angry Ave, Dallas, TX',
      latitude: 32.790,
      longitude: -96.815,
      reason: 'AGGRESSIVE',
      notes: null,
      reported_by: 1,
      added_at: '2024-01-21T09:00:00Z',
    },
    {
      id: 4,
      address: '666 Competitor Ln, Dallas, TX',
      latitude: 32.795,
      longitude: -96.825,
      reason: 'COMPETITOR',
      notes: 'Working with ABC Repairs',
      reported_by: 1,
      added_at: '2024-01-22T11:00:00Z',
    },
  ],
  count: 4,
}

const mockEmptyDNKData = {
  dnk_list: [],
  count: 0,
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

describe('DNKPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetDNKList.mockResolvedValue(mockDNKData)
    mockAddDNK.mockResolvedValue({ success: true, dnk_id: 5 })
    mockRemoveDNK.mockResolvedValue({ success: true })
  })

  describe('Page Rendering', () => {
    it('renders the page title', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText('Do Not Knock List')).toBeInTheDocument()
    })

    it('renders the page description', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText('Manage addresses that should not be canvassed')).toBeInTheDocument()
    })

    it('has an Add DNK button', () => {
      renderWithProviders(<DNKPage />)

      const addButton = screen.getByRole('button', { name: /add.*dnk/i })
      expect(addButton).toBeInTheDocument()
    })
  })

  describe('Stats Cards', () => {
    it('displays stats cards for each reason type', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      // Check all reason labels appear in stats
      expect(screen.getAllByText('No Soliciting Sign').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Customer Requested').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Hostile/Aggressive').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Working with Competitor').length).toBeGreaterThan(0)
    })

    it('shows correct count for each reason', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      // Each reason should show count of 1 (from our mock data)
      const ones = screen.getAllByText('1')
      expect(ones.length).toBeGreaterThanOrEqual(4)
    })
  })

  describe('DNK List Display', () => {
    it('displays DNK entries after loading', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      expect(screen.getByText('888 Private Dr, Dallas, TX')).toBeInTheDocument()
      expect(screen.getByText('777 Angry Ave, Dallas, TX')).toBeInTheDocument()
      expect(screen.getByText('666 Competitor Ln, Dallas, TX')).toBeInTheDocument()
    })

    it('shows reason badges for each entry', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getAllByText('No Soliciting Sign').length).toBeGreaterThan(0)
      })

      expect(screen.getAllByText('Customer Requested').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Hostile/Aggressive').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Working with Competitor').length).toBeGreaterThan(0)
    })

    it('shows notes for entries when available', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('Large sign on door')).toBeInTheDocument()
      })

      expect(screen.getByText('Homeowner asked not to return')).toBeInTheDocument()
      expect(screen.getByText('Working with ABC Repairs')).toBeInTheDocument()
    })

    it('displays address count badge', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('4 addresses')).toBeInTheDocument()
      })
    })

    it('displays Address List header', async () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText('Address List')).toBeInTheDocument()
    })

    it('displays delete buttons for each entry', async () => {
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      // There should be delete buttons (icon buttons)
      const allButtons = screen.getAllByRole('button')
      expect(allButtons.length).toBeGreaterThan(4)
    })
  })

  describe('Loading State', () => {
    it('shows loading message while fetching', async () => {
      mockGetDNKList.mockImplementation(() => new Promise(() => {})) // Never resolves
      renderWithProviders(<DNKPage />)

      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('shows empty message when no DNK addresses', async () => {
      mockGetDNKList.mockResolvedValue(mockEmptyDNKData)
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('No DNK addresses found')).toBeInTheDocument()
      })
    })

    it('shows 0 addresses badge when empty', async () => {
      mockGetDNKList.mockResolvedValue(mockEmptyDNKData)
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('0 addresses')).toBeInTheDocument()
      })
    })
  })

  describe('Search Functionality', () => {
    it('has a search input', () => {
      renderWithProviders(<DNKPage />)

      const searchInput = screen.getByPlaceholderText(/search/i)
      expect(searchInput).toBeInTheDocument()
    })

    it('filters entries by address when searching', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search/i)
      await user.type(searchInput, '999')

      // Should show matching entry
      expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()

      // Should hide non-matching entries
      expect(screen.queryByText('888 Private Dr, Dallas, TX')).not.toBeInTheDocument()
    })

    it('filters entries by notes when searching', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search/i)
      await user.type(searchInput, 'ABC Repairs')

      // Should show entry with matching notes
      expect(screen.getByText('666 Competitor Ln, Dallas, TX')).toBeInTheDocument()

      // Should hide non-matching entries
      expect(screen.queryByText('999 No Soliciting St, Dallas, TX')).not.toBeInTheDocument()
    })

    it('shows empty state when search has no results', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText(/search/i)
      await user.type(searchInput, 'nonexistent address xyz')

      await waitFor(() => {
        expect(screen.getByText('No DNK addresses found')).toBeInTheDocument()
      })
    })
  })

  describe('Reason Filter', () => {
    it('has a reason filter dropdown', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText(/all reasons/i)).toBeInTheDocument()
    })

    it('has filter trigger button', () => {
      renderWithProviders(<DNKPage />)

      // Find the select trigger containing "All Reasons"
      const filterTrigger = screen.getByRole('combobox')
      expect(filterTrigger).toBeInTheDocument()
    })
  })

  describe('Add DNK Dialog', () => {
    it('opens add DNK dialog when clicking button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      const addButton = screen.getByRole('button', { name: /add.*dnk/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add Do Not Knock Address')).toBeInTheDocument()
      })
    })

    it('shows address input field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('123 Main St, Dallas, TX')).toBeInTheDocument()
      })
    })

    it('shows reason select field', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByText('Reason *')).toBeInTheDocument()
      })
    })

    it('shows notes textarea', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Additional details...')).toBeInTheDocument()
      })
    })

    it('has Cancel button in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })
    })

    it('has Add to DNK List button in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add to dnk list/i })).toBeInTheDocument()
      })
    })

    it('Add to DNK List button is disabled when address is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /add to dnk list/i })
        expect(submitButton).toBeDisabled()
      })
    })

    it('enables submit button when address is filled', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('123 Main St, Dallas, TX')).toBeInTheDocument()
      })

      const addressInput = screen.getByPlaceholderText('123 Main St, Dallas, TX')
      await user.type(addressInput, '123 Test St, Dallas, TX')

      const submitButton = screen.getByRole('button', { name: /add to dnk list/i })
      expect(submitButton).not.toBeDisabled()
    })

    it('closes dialog when Cancel is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByText('Add Do Not Knock Address')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      await waitFor(() => {
        expect(screen.queryByText('Add Do Not Knock Address')).not.toBeInTheDocument()
      })
    })

    it('calls addDNK when form is submitted', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('123 Main St, Dallas, TX')).toBeInTheDocument()
      })

      const addressInput = screen.getByPlaceholderText('123 Main St, Dallas, TX')
      await user.type(addressInput, '123 New DNK St, Dallas, TX')

      const notesInput = screen.getByPlaceholderText('Additional details...')
      await user.type(notesInput, 'Test notes')

      await user.click(screen.getByRole('button', { name: /add to dnk list/i }))

      await waitFor(() => {
        expect(mockAddDNK).toHaveBeenCalledWith(
          expect.objectContaining({
            address: '123 New DNK St, Dallas, TX',
            reason: 'NO_SOLICITING',
            notes: 'Test notes',
          })
        )
      })
    })

    it('closes dialog after successful submission', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await user.click(screen.getByRole('button', { name: /add.*dnk/i }))

      await waitFor(() => {
        expect(screen.getByPlaceholderText('123 Main St, Dallas, TX')).toBeInTheDocument()
      })

      const addressInput = screen.getByPlaceholderText('123 Main St, Dallas, TX')
      await user.type(addressInput, '123 New DNK St, Dallas, TX')

      await user.click(screen.getByRole('button', { name: /add to dnk list/i }))

      await waitFor(() => {
        expect(screen.queryByText('Add Do Not Knock Address')).not.toBeInTheDocument()
      })
    })
  })

  describe('Delete Confirmation Dialog', () => {
    it('opens delete confirmation when clicking delete button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      // Find delete buttons - they have text-red-500 class and contain a trash icon
      const allButtons = screen.getAllByRole('button')
      // Filter for ghost buttons with red styling (delete buttons)
      const deleteButtons = allButtons.filter(btn =>
        btn.classList.contains('text-red-500') ||
        btn.className.includes('text-red-500')
      )

      expect(deleteButtons.length).toBeGreaterThan(0)
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByText('Remove from DNK List?')).toBeInTheDocument()
      })
    })

    it('shows confirmation message in delete dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const allButtons = screen.getAllByRole('button')
      const deleteButtons = allButtons.filter(btn =>
        btn.classList.contains('text-red-500') ||
        btn.className.includes('text-red-500')
      )
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByText(/allow this address to appear on canvassing routes/i)).toBeInTheDocument()
      })
    })

    it('has Cancel button in delete dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const allButtons = screen.getAllByRole('button')
      const deleteButtons = allButtons.filter(btn =>
        btn.classList.contains('text-red-500') ||
        btn.className.includes('text-red-500')
      )
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })
    })

    it('has Remove button in delete dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const allButtons = screen.getAllByRole('button')
      const deleteButtons = allButtons.filter(btn =>
        btn.classList.contains('text-red-500') ||
        btn.className.includes('text-red-500')
      )
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument()
      })
    })

    it('closes delete dialog when Cancel is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const allButtons = screen.getAllByRole('button')
      const deleteButtons = allButtons.filter(btn =>
        btn.classList.contains('text-red-500') ||
        btn.className.includes('text-red-500')
      )
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByText('Remove from DNK List?')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      await waitFor(() => {
        expect(screen.queryByText('Remove from DNK List?')).not.toBeInTheDocument()
      })
    })

    it('calls removeDNK when Remove is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<DNKPage />)

      await waitFor(() => {
        expect(screen.getByText('999 No Soliciting St, Dallas, TX')).toBeInTheDocument()
      })

      const allButtons = screen.getAllByRole('button')
      const deleteButtons = allButtons.filter(btn =>
        btn.classList.contains('text-red-500') ||
        btn.className.includes('text-red-500')
      )
      await user.click(deleteButtons[0])

      await waitFor(() => {
        expect(screen.getByText('Remove from DNK List?')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /remove/i }))

      await waitFor(() => {
        expect(mockRemoveDNK).toHaveBeenCalledWith(1)
      })
    })
  })

  describe('DNK Guidelines Section', () => {
    it('displays DNK Guidelines header', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText('DNK Guidelines')).toBeInTheDocument()
    })

    it('shows guideline for No Soliciting Sign', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText(/Visible 'No Soliciting' sign posted/)).toBeInTheDocument()
    })

    it('shows guideline for Customer Requested', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText(/Homeowner explicitly asked not to be contacted/)).toBeInTheDocument()
    })

    it('shows guideline for Hostile/Aggressive', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText(/Hostile or threatening behavior/)).toBeInTheDocument()
    })

    it('shows guideline for Working with Competitor', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText(/Already working with a competitor/)).toBeInTheDocument()
    })
  })

  describe('Map Section', () => {
    it('displays DNK Map header', () => {
      renderWithProviders(<DNKPage />)

      expect(screen.getByText('DNK Map')).toBeInTheDocument()
    })
  })
})
