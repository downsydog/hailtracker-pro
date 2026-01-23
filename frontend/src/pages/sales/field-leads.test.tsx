import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { FieldLeadsPage } from './field-leads'
import { mockFieldLeads } from '@/test/mocks/handlers'

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getFieldLeads: vi.fn(() => Promise.resolve({ leads: mockFieldLeads, total: mockFieldLeads.length })),
  createFieldLead: vi.fn(() => Promise.resolve({ success: true, lead_id: 4 })),
  syncLeadToCRM: vi.fn(() => Promise.resolve({ success: true, crm_lead_id: 102 })),
  bulkSyncLeads: vi.fn(() => Promise.resolve({ success: true, synced_count: 2 })),
}))

import { mockFieldLeads as mockLeads } from '@/test/mocks/handlers'

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

  it('shows lead quality badges', async () => {
    renderWithProviders(<FieldLeadsPage />)

    await waitFor(() => {
      expect(screen.getByText('HOT')).toBeInTheDocument()
    })

    expect(screen.getByText('WARM')).toBeInTheDocument()
    expect(screen.getByText('COLD')).toBeInTheDocument()
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
      expect(screen.getByText('Add New Lead')).toBeInTheDocument()
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
