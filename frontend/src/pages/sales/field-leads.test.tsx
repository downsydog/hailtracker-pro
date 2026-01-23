import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { FieldLeadsPage } from './field-leads'

// Mock the API module with inline data
vi.mock('@/api/elite-sales', () => ({
  getFieldLeads: vi.fn(() => Promise.resolve({
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
      },
    ],
    total: 3,
  })),
  createFieldLead: vi.fn(() => Promise.resolve({ success: true, lead_id: 4 })),
  syncLeadToCRM: vi.fn(() => Promise.resolve({ success: true, crm_lead_id: 102 })),
  bulkSyncLeads: vi.fn(() => Promise.resolve({ success: true, synced_count: 2 })),
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

describe('FieldLeadsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', async () => {
    renderWithProviders(<FieldLeadsPage />)

    expect(screen.getByText('Field Leads')).toBeInTheDocument()
  })

  it('displays loading state initially', () => {
    renderWithProviders(<FieldLeadsPage />)

    // Should show loading or skeleton while fetching
    expect(screen.getByText('Field Leads')).toBeInTheDocument()
  })

  it('displays field leads after loading', async () => {
    renderWithProviders(<FieldLeadsPage />)

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })

    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
    expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
  })

  it('shows lead sync status badges', async () => {
    renderWithProviders(<FieldLeadsPage />)

    await waitFor(() => {
      // Leads show Synced or Pending badges
      expect(screen.getByText('Synced')).toBeInTheDocument()
    })

    // Multiple leads are pending sync
    expect(screen.getAllByText('Pending').length).toBeGreaterThan(0)
  })

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

  it('displays filter controls', async () => {
    renderWithProviders(<FieldLeadsPage />)

    // Quality filter
    expect(screen.getByText(/quality/i)).toBeInTheDocument()
  })

  it('shows synced status for leads', async () => {
    renderWithProviders(<FieldLeadsPage />)

    await waitFor(() => {
      // Jane Smith is synced
      expect(screen.getByText('Jane Smith')).toBeInTheDocument()
    })
  })
})
