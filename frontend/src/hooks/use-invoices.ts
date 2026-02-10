/**
 * Invoice hooks for TanStack Query.
 *
 * Provides hooks for:
 * - Listing invoices
 * - Getting invoice details
 * - Creating invoice from estimate
 * - Issuing/voiding invoices
 * - Payment management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

// ============================================================================
// Types
// ============================================================================

export type InvoiceStatus = 'draft' | 'issued' | 'partial_paid' | 'paid' | 'void'
export type PayerType = 'customer' | 'insurer' | 'dealership' | 'other'
export type PaymentMethod = 'cash' | 'card' | 'check' | 'ach' | 'other'
export type LineItemCategory = 'pdr' | 'ri' | 'materials' | 'parts' | 'sublet' | 'other'
export type AllocationType = 'insurer' | 'customer_deductible' | 'customer_oop' | 'other'

export interface InvoiceLineItem {
  id: number
  invoice_id: number
  category: LineItemCategory
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface Payment {
  id: number
  invoice_id: number
  amount: number
  method: PaymentMethod
  reference: string | null
  received_at: string
  notes: string | null
  created_at: string
  created_by: number | null
}

export interface InvoiceEstimate {
  id: number
  estimate_number: string
  customer_name: string
  vehicle_year: number | null
  vehicle_make: string | null
  vehicle_model: string | null
  vehicle_display: string
  insurer_status: string
  total_price: number
  insurer_approved_total: number | null
}

export interface Invoice {
  id: number
  tenant_id: number
  invoice_number: string
  estimate_id: number
  job_id: number | null
  payer_type: PayerType
  payer_name: string | null
  allocation_type: AllocationType
  status: InvoiceStatus
  subtotal: number
  tax_rate: number
  tax_total: number
  total: number
  amount_paid: number
  balance_due: number
  is_paid: boolean
  is_overdue: boolean
  issued_at: string | null
  due_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
  created_by: number | null
  // Optional includes
  line_items?: InvoiceLineItem[]
  payments?: Payment[]
  estimate?: InvoiceEstimate
}

export interface InvoiceListParams {
  status?: InvoiceStatus
  payer_type?: PayerType
  estimate_id?: number
  job_id?: number
  overdue?: boolean
  page?: number
  per_page?: number
}

export interface CreateInvoiceFromEstimateParams {
  payer_type?: PayerType
  job_id?: number
  notes?: string
  due_days?: number
}

export interface UpdateInvoiceParams {
  payer_type?: PayerType
  payer_name?: string
  notes?: string
  due_at?: string
  tax_rate?: number
}

export interface AddLineItemParams {
  category: LineItemCategory
  description: string
  quantity?: number
  unit_price: number
}

export interface AddPaymentParams {
  amount: number
  method?: PaymentMethod
  reference?: string
  received_at?: string
  notes?: string
}

// Split billing types
export interface BillingSummary {
  requested_total: number
  approved_total: number | null
  deductible: number
  customer_oop: number
  customer_total: number
  insurer_suggested: number
  customer_suggested: number
  short_paid: number
  has_split_billing: boolean
}

export interface UpdateBillingParams {
  deductible?: number
  customer_oop?: number
}

export interface EstimateInvoicesResponse {
  invoices: Invoice[]
  billing_summary: BillingSummary
  totals: {
    total_invoiced: number
    total_paid: number
    total_balance: number
  }
  has_insurer_invoice: boolean
  has_customer_invoice: boolean
}

// ============================================================================
// Query Keys
// ============================================================================

export const invoiceKeys = {
  all: ['invoices'] as const,
  lists: () => [...invoiceKeys.all, 'list'] as const,
  list: (params: InvoiceListParams) => [...invoiceKeys.lists(), params] as const,
  details: () => [...invoiceKeys.all, 'detail'] as const,
  detail: (id: number) => [...invoiceKeys.details(), id] as const,
  payments: (id: number) => [...invoiceKeys.detail(id), 'payments'] as const,
}

// ============================================================================
// Hooks - List & Get
// ============================================================================

/**
 * List invoices with optional filters.
 */
interface InvoiceListResponse {
  invoices: Invoice[]
  total: number
  page: number
  per_page: number
  pages: number
}

export function useInvoices(params: InvoiceListParams = {}) {
  return useQuery({
    queryKey: invoiceKeys.list(params),
    queryFn: async () => {
      const searchParams = new URLSearchParams()
      if (params.status) searchParams.set('status', params.status)
      if (params.payer_type) searchParams.set('payer_type', params.payer_type)
      if (params.estimate_id) searchParams.set('estimate_id', String(params.estimate_id))
      if (params.job_id) searchParams.set('job_id', String(params.job_id))
      if (params.overdue !== undefined) searchParams.set('overdue', String(params.overdue))
      if (params.page) searchParams.set('page', String(params.page))
      if (params.per_page) searchParams.set('per_page', String(params.per_page))

      const query = searchParams.toString()
      const url = `/invoices${query ? `?${query}` : ''}`
      return apiGet<InvoiceListResponse>(url)
    },
  })
}

/**
 * Get a single invoice with full details.
 */
export function useInvoice(invoiceId: number | null) {
  return useQuery({
    queryKey: invoiceKeys.detail(invoiceId!),
    queryFn: () => apiGet<Invoice>(`/invoices/${invoiceId}?include_items=true&include_payments=true&include_estimate=true`),
    enabled: invoiceId !== null,
  })
}

/**
 * Get invoices for a specific estimate.
 */
export function useEstimateInvoices(estimateId: number | null) {
  return useInvoices(estimateId ? { estimate_id: estimateId } : {})
}

/**
 * Get invoices for a specific job.
 */
export function useJobInvoices(jobId: number | null) {
  return useInvoices(jobId ? { job_id: jobId } : {})
}

// ============================================================================
// Hooks - Create & Update
// ============================================================================

/**
 * Create an invoice from a PDR estimate.
 */
export function useCreateInvoiceFromEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, params }: { estimateId: number; params?: CreateInvoiceFromEstimateParams }) => {
      return apiPost<Invoice>(`/pdr-estimates/${estimateId}/invoice`, params || {})
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.all })
      // Also invalidate estimate queries since it now has an invoice
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', invoice.estimate_id] })
      // Instant refresh: invalidate ops dashboard and workflow
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(invoice.estimate_id) })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', invoice.estimate_id] })
    },
  })
}

/**
 * Update invoice details.
 */
export function useUpdateInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ invoiceId, params }: { invoiceId: number; params: UpdateInvoiceParams }) => {
      return apiPut<Invoice>(`/invoices/${invoiceId}`, params)
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

// ============================================================================
// Hooks - Line Items
// ============================================================================

/**
 * Add a line item to an invoice.
 */
export function useAddLineItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ invoiceId, params }: { invoiceId: number; params: AddLineItemParams }) => {
      return apiPost<Invoice>(`/invoices/${invoiceId}/line-items`, params)
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

/**
 * Remove a line item from an invoice.
 */
export function useRemoveLineItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ invoiceId, lineItemId }: { invoiceId: number; lineItemId: number }) => {
      return apiDelete<Invoice>(`/invoices/${invoiceId}/line-items/${lineItemId}`)
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}

// ============================================================================
// Hooks - Status Actions
// ============================================================================

/**
 * Issue an invoice (draft -> issued).
 */
export function useIssueInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (invoiceId: number) => {
      return apiPost<Invoice>(`/invoices/${invoiceId}/issue`)
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
      // Instant refresh: invalidate ops dashboard
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      if (invoice.estimate_id) {
        queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(invoice.estimate_id) })
        queryClient.invalidateQueries({ queryKey: ['estimate-activities', invoice.estimate_id] })
      }
    },
  })
}

/**
 * Void an invoice.
 */
export function useVoidInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (invoiceId: number) => {
      return apiPost<Invoice>(`/invoices/${invoiceId}/void`)
    },
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
      // Instant refresh: invalidate ops dashboard
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      if (invoice.estimate_id) {
        queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(invoice.estimate_id) })
      }
    },
  })
}

// ============================================================================
// Hooks - Payments
// ============================================================================

/**
 * Get payments for an invoice.
 */
interface PaymentsResponse {
  payments: Payment[]
  total_paid: number
  balance_due: number
}

export function useInvoicePayments(invoiceId: number | null) {
  return useQuery({
    queryKey: invoiceKeys.payments(invoiceId!),
    queryFn: () => apiGet<PaymentsResponse>(`/invoices/${invoiceId}/payments`),
    enabled: invoiceId !== null,
  })
}

/**
 * Add a payment to an invoice.
 */
interface AddPaymentResponse {
  payment: Payment
  invoice: Invoice
}

export function useAddPayment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ invoiceId, params }: { invoiceId: number; params: AddPaymentParams }) => {
      const result = await apiPost<AddPaymentResponse>(`/invoices/${invoiceId}/payments`, params)
      return { invoiceId, ...result }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(data.invoiceId) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.payments(data.invoiceId) })
      queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
      // Instant refresh: invalidate ops dashboard (payment affects money risk panel)
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      if (data.invoice?.estimate_id) {
        queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(data.invoice.estimate_id) })
        queryClient.invalidateQueries({ queryKey: ['estimate-activities', data.invoice.estimate_id] })
      }
    },
  })
}

// ============================================================================
// Hooks - Split Billing
// ============================================================================

/**
 * Get all invoices for an estimate with billing summary.
 */
export function useEstimateBillingSummary(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-invoices', estimateId],
    queryFn: () => apiGet<EstimateInvoicesResponse>(`/pdr-estimates/${estimateId}/invoices`),
    enabled: estimateId !== null,
  })
}

/**
 * Update billing fields on an estimate (deductible, customer_oop).
 */
export function useUpdateBilling() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, params }: { estimateId: number; params: UpdateBillingParams }) => {
      return apiPatch<{ estimate: unknown; billing_summary: BillingSummary }>(`/pdr-estimates/${estimateId}/billing`, params)
    },
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['estimate-invoices', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

/**
 * Create an insurer invoice from an approved estimate.
 */
export function useCreateInsurerInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, notes }: { estimateId: number; notes?: string }) => {
      return apiPost<{ invoice: Invoice; billing_summary: BillingSummary }>(`/pdr-estimates/${estimateId}/invoices/insurer`, { notes })
    },
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.all })
      queryClient.invalidateQueries({ queryKey: ['estimate-invoices', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
      // Instant refresh: invalidate ops dashboard and workflow
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(estimateId) })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
    },
  })
}

/**
 * Create a customer deductible invoice from an estimate.
 */
export function useCreateCustomerInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, notes, includeOop = true }: { estimateId: number; notes?: string; includeOop?: boolean }) => {
      return apiPost<{ invoice: Invoice; billing_summary: BillingSummary }>(`/pdr-estimates/${estimateId}/invoices/customer`, { notes, include_oop: includeOop })
    },
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.all })
      queryClient.invalidateQueries({ queryKey: ['estimate-invoices', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
      // Instant refresh: invalidate ops dashboard and workflow
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(estimateId) })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
    },
  })
}

// ============================================================================
// Status Helpers
// ============================================================================

export const invoiceStatusLabels: Record<InvoiceStatus, string> = {
  draft: 'Draft',
  issued: 'Issued',
  partial_paid: 'Partial',
  paid: 'Paid',
  void: 'Void',
}

export const invoiceStatusColors: Record<InvoiceStatus, string> = {
  draft: 'bg-gray-100 text-gray-800',
  issued: 'bg-blue-100 text-blue-800',
  partial_paid: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-green-100 text-green-800',
  void: 'bg-red-100 text-red-800',
}

export const payerTypeLabels: Record<PayerType, string> = {
  customer: 'Customer',
  insurer: 'Insurance',
  dealership: 'Dealership',
  other: 'Other',
}

export const paymentMethodLabels: Record<PaymentMethod, string> = {
  cash: 'Cash',
  card: 'Card',
  check: 'Check',
  ach: 'ACH',
  other: 'Other',
}

export const lineItemCategoryLabels: Record<LineItemCategory, string> = {
  pdr: 'PDR Labor',
  ri: 'R&I Labor',
  materials: 'Materials',
  parts: 'Parts',
  sublet: 'Sublet',
  other: 'Other',
}

export const allocationTypeLabels: Record<AllocationType, string> = {
  insurer: 'Insurer',
  customer_deductible: 'Deductible',
  customer_oop: 'Out-of-Pocket',
  other: 'Other',
}

export const allocationTypeColors: Record<AllocationType, string> = {
  insurer: 'bg-purple-100 text-purple-800',
  customer_deductible: 'bg-orange-100 text-orange-800',
  customer_oop: 'bg-amber-100 text-amber-800',
  other: 'bg-gray-100 text-gray-800',
}
