import { apiGet, apiPost, apiPut, apiDelete } from './client'

export interface Invoice {
  id: number
  invoice_number: string
  job_id: number
  customer_id: number
  customer_name: string
  vehicle_info?: string
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled' | 'refunded'
  issue_date: string
  due_date: string
  subtotal: number
  tax_rate: number
  tax_amount: number
  discount_amount: number
  total: number
  amount_paid: number
  balance_due: number
  notes?: string
  payment_terms?: string
  created_at: string
  updated_at: string
}

export interface InvoiceLineItem {
  id: number
  invoice_id: number
  description: string
  quantity: number
  unit_price: number
  total: number
  service_type?: string
}

export interface InvoicePayment {
  id: number
  invoice_id: number
  amount: number
  payment_method: 'cash' | 'check' | 'credit_card' | 'debit_card' | 'ach' | 'insurance' | 'other'
  reference_number?: string
  payment_date: string
  notes?: string
  created_by?: number
  created_at: string
}

export interface InvoiceCreateData {
  job_id: number
  customer_id: number
  issue_date?: string
  due_date?: string
  notes?: string
  payment_terms?: string
  items: Array<{
    description: string
    quantity: number
    unit_price: number
    service_type?: string
  }>
  tax_rate?: number
  discount_amount?: number
}

export interface InvoiceFilters {
  status?: string
  customer_id?: number
  job_id?: number
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}

export const invoicesApi = {
  // List invoices with filters
  getInvoices: (filters?: InvoiceFilters) =>
    apiGet<{ invoices: Invoice[]; total: number; page: number }>('/api/invoices', { params: filters }),

  // Get single invoice with details
  getInvoice: (id: number) =>
    apiGet<{ invoice: Invoice; items: InvoiceLineItem[]; payments: InvoicePayment[] }>(`/api/invoices/${id}`),

  // Create new invoice
  createInvoice: (data: InvoiceCreateData) =>
    apiPost<{ success: boolean; invoice_id: number; invoice_number: string }>('/api/invoices', data),

  // Update invoice
  updateInvoice: (id: number, data: Partial<InvoiceCreateData>) =>
    apiPut<{ success: boolean }>(`/api/invoices/${id}`, data),

  // Delete invoice (only drafts)
  deleteInvoice: (id: number) =>
    apiDelete<{ success: boolean }>(`/api/invoices/${id}`),

  // Send invoice to customer
  sendInvoice: (id: number, method?: 'email' | 'sms') =>
    apiPost<{ success: boolean }>(`/api/invoices/${id}/send`, { method }),

  // Mark invoice as paid
  markPaid: (id: number) =>
    apiPost<{ success: boolean }>(`/api/invoices/${id}/mark-paid`),

  // Record payment
  addPayment: (id: number, payment: Omit<InvoicePayment, 'id' | 'invoice_id' | 'created_at'>) =>
    apiPost<{ success: boolean; payment_id: number }>(`/api/invoices/${id}/payments`, payment),

  // Delete payment
  deletePayment: (invoiceId: number, paymentId: number) =>
    apiDelete<{ success: boolean }>(`/api/invoices/${invoiceId}/payments/${paymentId}`),

  // Generate PDF
  generatePdf: (id: number) =>
    apiGet<Blob>(`/api/invoices/${id}/pdf`, { responseType: 'blob' }),

  // Create from estimate
  createFromEstimate: (estimateId: number) =>
    apiPost<{ success: boolean; invoice_id: number }>(`/api/estimates/${estimateId}/create-invoice`),

  // Create from job
  createFromJob: (jobId: number) =>
    apiPost<{ success: boolean; invoice_id: number }>(`/api/jobs/${jobId}/create-invoice`),

  // Get invoice summary stats
  getStats: () =>
    apiGet<{
      total_outstanding: number
      total_overdue: number
      total_this_month: number
      count_by_status: Record<string, number>
    }>('/api/invoices/stats'),
}
