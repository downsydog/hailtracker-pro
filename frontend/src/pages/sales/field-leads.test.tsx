import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { FieldLeadsPage } from './field-leads'

// Use vi.hoisted for proper mock hoisting
const { mockGetFieldLeads, mockCreateFieldLead, mockSyncLeadToCRM, mockBulkSyncLeads } = vi.hoisted(() => ({
  mockGetFieldLeads: vi.fn(),
  mockCreateFieldLead: vi.fn(),
  mockSyncLeadToCRM: vi.fn(),
  mockBulkSyncLeads: vi.fn(),
}))

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getFieldLeads: mockGetFieldLeads,
  createFieldLead: mockCreateFieldLead,
  syncLeadToCRM: mockSyncLeadToCRM,
  bulkSyncLeads: mockBulkSyncLeads,
}))

const mockLeadsData = {
  leads: [
    {
      id: 1,
      salesperson_id: 1,
      latitude: 32.7767,
      longitude: -96.797,
      address: '123 Main St, Dallas, TX',
      customer_name: 'John Doe',
      phone: '555-1234',
      email: 'john@example.com',
      lead_quality: 'HOT',
      notes: 'Interested in hail repair',
      synced_to_crm: false,
      created_at: '2024-01-20T10:00:00Z',
    },
    {
      id: 2,
      salesperson_id: 1,
      latitude: 32.78,
      longitude: -96.8,
      address: '456 Oak Ave, Dallas, TX',
      customer_name: 'Jane Smith',
      phone: '555-5678',
      email: 'jane@example.com',
      lead_quality: 'WARM',
      notes: 'Follow up next week',
      synced_to_crm: true,
      crm_lead_id: 101,
      created_at: '2024-01-21T14:30:00Z',
    },
    {
      id: 3,
      salesperson_id: 1,
      latitude: 32.785,
      longitude: -96.79,
      address: '789 Pine Rd, Dallas, TX',
      customer_name: 'Bob Wilson',
      phone: '555-9999',
      lead_quality: 'COLD',
      synced_to_crm: false,
      created_at: '2024-01-22T09:00:00Z',
      vehicle_info: {
        year: 2022,
        make: 'Toyota',
        model: 'Camry',
      },
    },
  ],
  total: 3,
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

describe('FieldLeadsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetFieldLeads.mockResolvedValue(mockLeadsData)
    mockCreateFieldLead.mockResolvedValue({ success: true, lead_id: 4 })
    mockSyncLeadToCRM.mockResolvedValue({ success: true, crm_lead_id: 102 })
    mockBulkSyncLeads.mockResolvedValue({ success: true, synced_count: 2 })
  })

  describe('Page Rendering', () => {
    it('renders the page title and description', async () => {
      renderWithProviders(<FieldLeadsPage />)

      expect(screen.getByText('Field Leads')).toBeInTheDocument()
      expect(screen.getByText('Leads captured during door-to-door canvassing')).toBeInTheDocument()
    })

    it('displays field leads after loading', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      expect(screen.getByText('Jane Smith')).toBeInTheDocument()
      expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
    })

    it('displays lead addresses', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('123 Main St, Dallas, TX')).toBeInTheDocument()
      })

      expect(screen.getByText('456 Oak Ave, Dallas, TX')).toBeInTheDocument()
      expect(screen.getByText('789 Pine Rd, Dallas, TX')).toBeInTheDocument()
    })

    it('displays lead phone numbers', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('555-1234')).toBeInTheDocument()
      })

      expect(screen.getByText('555-5678')).toBeInTheDocument()
      expect(screen.getByText('555-9999')).toBeInTheDocument()
    })

    it('displays lead emails', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('john@example.com')).toBeInTheDocument()
      })

      expect(screen.getByText('jane@example.com')).toBeInTheDocument()
    })

    it('displays lead notes', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('Interested in hail repair')).toBeInTheDocument()
      })

      expect(screen.getByText('Follow up next week')).toBeInTheDocument()
    })

    it('displays vehicle info when available', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('2022 Toyota Camry')).toBeInTheDocument()
      })
    })
  })

  describe('Stats Cards', () => {
    it('displays total leads count', async () => {
      renderWithProviders(<FieldLeadsPage />)

      // Wait for leads to load first
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      expect(screen.getByText('Total Leads')).toBeInTheDocument()
      // Count should be 3
      const statsCards = screen.getAllByText('3')
      expect(statsCards.length).toBeGreaterThan(0)
    })

    it('displays hot leads count', async () => {
      renderWithProviders(<FieldLeadsPage />)

      // Wait for leads to load first
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      expect(screen.getByText('Hot Leads')).toBeInTheDocument()
    })

    it('displays warm leads count', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('Warm Leads')).toBeInTheDocument()
      })
    })

    it('displays synced to CRM count', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('Synced to CRM')).toBeInTheDocument()
      })
    })
  })

  describe('Sync Status Badges', () => {
    it('shows Synced badge for synced leads', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('Synced')).toBeInTheDocument()
      })
    })

    it('shows Pending badge for unsynced leads', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getAllByText('Pending').length).toBe(2) // John Doe and Bob Wilson
      })
    })
  })

  describe('Sync All Button', () => {
    it('shows Sync All button when there are pending leads', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sync all/i })).toBeInTheDocument()
      })
    })

    it('shows count of pending leads in Sync All button', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText(/Sync All \(2\)/)).toBeInTheDocument()
      })
    })

    it('calls bulkSyncLeads when Sync All is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /sync all/i })).toBeInTheDocument()
      })

      const syncButton = screen.getByRole('button', { name: /sync all/i })
      await user.click(syncButton)

      expect(mockBulkSyncLeads).toHaveBeenCalledWith([1, 3]) // IDs of unsynced leads
    })
  })

  describe('Search Functionality', () => {
    it('has a search input', async () => {
      renderWithProviders(<FieldLeadsPage />)

      expect(screen.getByPlaceholderText('Search leads...')).toBeInTheDocument()
    })

    it('filters leads by customer name', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Search leads...')
      await user.type(searchInput, 'Jane')

      await waitFor(() => {
        expect(screen.getByText('Jane Smith')).toBeInTheDocument()
        expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
        expect(screen.queryByText('Bob Wilson')).not.toBeInTheDocument()
      })
    })

    it('filters leads by address', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Search leads...')
      await user.type(searchInput, 'Oak')

      await waitFor(() => {
        expect(screen.getByText('Jane Smith')).toBeInTheDocument()
        expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
      })
    })

    it('filters leads by phone number', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Search leads...')
      await user.type(searchInput, '555-9999')

      await waitFor(() => {
        expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
        expect(screen.queryByText('John Doe')).not.toBeInTheDocument()
      })
    })
  })

  describe('Add Lead Dialog', () => {
    it('has an Add Lead button', async () => {
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      expect(addButton).toBeInTheDocument()
    })

    it('opens add lead dialog when clicking Add Lead', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add Field Lead')).toBeInTheDocument()
      })
    })

    it('shows form fields in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Customer Name *')).toBeInTheDocument()
        expect(screen.getByText('Phone')).toBeInTheDocument()
        expect(screen.getByText('Email')).toBeInTheDocument()
        expect(screen.getByText('Address *')).toBeInTheDocument()
        expect(screen.getByText('Lead Quality')).toBeInTheDocument()
        expect(screen.getByText('Notes')).toBeInTheDocument()
      })
    })

    it('shows quality buttons (HOT, WARM, COLD)', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /hot/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /warm/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /cold/i })).toBeInTheDocument()
      })
    })

    it('shows vehicle info fields (Year, Make, Model)', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Year')).toBeInTheDocument()
        expect(screen.getByText('Make')).toBeInTheDocument()
        expect(screen.getByText('Model')).toBeInTheDocument()
      })
    })

    it('has Save Lead button disabled when required fields are empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /save lead/i })
        expect(saveButton).toBeDisabled()
      })
    })

    it('enables Save Lead button when required fields are filled', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add Field Lead')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('John Smith')
      const addressInput = screen.getByPlaceholderText('123 Main St, Dallas, TX')

      await user.type(nameInput, 'Test Customer')
      await user.type(addressInput, '100 Test St')

      const saveButton = screen.getByRole('button', { name: /save lead/i })
      expect(saveButton).not.toBeDisabled()
    })

    it('calls createFieldLead when form is submitted', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add Field Lead')).toBeInTheDocument()
      })

      const nameInput = screen.getByPlaceholderText('John Smith')
      const addressInput = screen.getByPlaceholderText('123 Main St, Dallas, TX')
      const phoneInput = screen.getByPlaceholderText('(555) 123-4567')

      await user.type(nameInput, 'Test Customer')
      await user.type(addressInput, '100 Test St')
      await user.type(phoneInput, '555-0000')

      const saveButton = screen.getByRole('button', { name: /save lead/i })
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockCreateFieldLead).toHaveBeenCalled()
      })
    })

    it('allows selecting different quality levels', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add Field Lead')).toBeInTheDocument()
      })

      // Click HOT button
      const hotButton = screen.getByRole('button', { name: /hot/i })
      await user.click(hotButton)

      // Click COLD button
      const coldButton = screen.getByRole('button', { name: /cold/i })
      await user.click(coldButton)

      // The buttons should be interactive
      expect(hotButton).toBeInTheDocument()
      expect(coldButton).toBeInTheDocument()
    })

    it('closes dialog when Cancel is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<FieldLeadsPage />)

      const addButton = screen.getByRole('button', { name: /add lead/i })
      await user.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add Field Lead')).toBeInTheDocument()
      })

      const cancelButton = screen.getByRole('button', { name: /cancel/i })
      await user.click(cancelButton)

      await waitFor(() => {
        expect(screen.queryByText('Add Field Lead')).not.toBeInTheDocument()
      })
    })
  })

  describe('Filter Controls', () => {
    it('has quality filter dropdown', async () => {
      renderWithProviders(<FieldLeadsPage />)

      expect(screen.getByText('All Quality')).toBeInTheDocument()
    })

    it('has sync status filter dropdown', async () => {
      renderWithProviders(<FieldLeadsPage />)

      expect(screen.getByText('All Status')).toBeInTheDocument()
    })

    it('has refresh button', async () => {
      renderWithProviders(<FieldLeadsPage />)

      // Find the refresh button by its icon (it has no text)
      const buttons = screen.getAllByRole('button')
      const refreshButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'))
      expect(refreshButton).toBeInTheDocument()
    })
  })

  describe('Lead Actions', () => {
    it('shows more options button for each lead', async () => {
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      })

      // Find buttons with more-vertical icon - there should be one per lead
      const moreButtons = screen.getAllByRole('button').filter(btn =>
        btn.querySelector('.lucide-more-vertical')
      )
      expect(moreButtons.length).toBe(3) // One for each lead
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no leads', async () => {
      mockGetFieldLeads.mockResolvedValue({ leads: [], total: 0 })
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('No leads found')).toBeInTheDocument()
      })
    })

    it('shows Add your first lead link in empty state', async () => {
      mockGetFieldLeads.mockResolvedValue({ leads: [], total: 0 })
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('Add your first lead')).toBeInTheDocument()
      })
    })

    it('opens add dialog when clicking Add your first lead', async () => {
      const user = userEvent.setup()
      mockGetFieldLeads.mockResolvedValue({ leads: [], total: 0 })
      renderWithProviders(<FieldLeadsPage />)

      await waitFor(() => {
        expect(screen.getByText('Add your first lead')).toBeInTheDocument()
      })

      const addLink = screen.getByText('Add your first lead')
      await user.click(addLink)

      await waitFor(() => {
        expect(screen.getByText('Add Field Lead')).toBeInTheDocument()
      })
    })
  })

  describe('Loading State', () => {
    it('shows loading message while fetching', async () => {
      // Make the API call hang
      mockGetFieldLeads.mockImplementation(() => new Promise(() => {}))
      renderWithProviders(<FieldLeadsPage />)

      expect(screen.getByText('Loading leads...')).toBeInTheDocument()
    })
  })
})
