/**
 * Export hooks for downloading receipts and CSV exports.
 *
 * Provides hooks for:
 * - Downloading payment receipts as PDF
 * - Exporting invoices as CSV
 * - Exporting payments as CSV
 */

import { useMutation } from '@tanstack/react-query'

// Base API URL
const API_BASE = import.meta.env.VITE_API_URL || '/api'

// Get auth token from localStorage
function getAuthToken(): string | null {
  return localStorage.getItem('token')
}

/**
 * Download a file from a URL with authentication.
 */
async function downloadFile(url: string, filename: string): Promise<void> {
  const token = getAuthToken()

  const response = await fetch(`${API_BASE}${url}`, {
    method: 'GET',
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Download failed' }))
    throw new Error(error.error || 'Download failed')
  }

  // Get the blob
  const blob = await response.blob()

  // Create download link
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

// ============================================================================
// Receipt Hooks
// ============================================================================

interface DownloadReceiptParams {
  invoiceId: number
  paymentId: number
  invoiceNumber?: string
}

/**
 * Download a payment receipt PDF.
 */
export function useDownloadPaymentReceipt() {
  return useMutation({
    mutationFn: async ({ invoiceId, paymentId, invoiceNumber }: DownloadReceiptParams) => {
      const url = `/invoices/${invoiceId}/payments/${paymentId}/receipt.pdf`
      const filename = `receipt_${invoiceNumber || invoiceId}_${paymentId}.pdf`
      await downloadFile(url, filename)
    },
  })
}

// ============================================================================
// CSV Export Hooks
// ============================================================================

interface ExportInvoicesParams {
  start?: string // YYYY-MM-DD
  end?: string // YYYY-MM-DD
  status?: string
  payer_type?: string
}

/**
 * Export invoices as CSV.
 */
export function useExportInvoicesCSV() {
  return useMutation({
    mutationFn: async (params: ExportInvoicesParams) => {
      const searchParams = new URLSearchParams()
      if (params.start) searchParams.set('start', params.start)
      if (params.end) searchParams.set('end', params.end)
      if (params.status) searchParams.set('status', params.status)
      if (params.payer_type) searchParams.set('payer_type', params.payer_type)

      const query = searchParams.toString()
      const url = `/exports/invoices.csv${query ? `?${query}` : ''}`

      const startDate = params.start || 'recent'
      const endDate = params.end || 'today'
      const filename = `invoices_${startDate}_to_${endDate}.csv`

      await downloadFile(url, filename)
    },
  })
}

interface ExportPaymentsParams {
  start?: string // YYYY-MM-DD
  end?: string // YYYY-MM-DD
  method?: string
  payer_type?: string
}

/**
 * Export payments as CSV.
 */
export function useExportPaymentsCSV() {
  return useMutation({
    mutationFn: async (params: ExportPaymentsParams) => {
      const searchParams = new URLSearchParams()
      if (params.start) searchParams.set('start', params.start)
      if (params.end) searchParams.set('end', params.end)
      if (params.method) searchParams.set('method', params.method)
      if (params.payer_type) searchParams.set('payer_type', params.payer_type)

      const query = searchParams.toString()
      const url = `/exports/payments.csv${query ? `?${query}` : ''}`

      const startDate = params.start || 'recent'
      const endDate = params.end || 'today'
      const filename = `payments_${startDate}_to_${endDate}.csv`

      await downloadFile(url, filename)
    },
  })
}

// ============================================================================
// Date Helpers
// ============================================================================

/**
 * Get date string for N days ago.
 */
export function getDateDaysAgo(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().split('T')[0]
}

/**
 * Get today's date string.
 */
export function getTodayDate(): string {
  return new Date().toISOString().split('T')[0]
}

/**
 * Get default date range (last 30 days).
 */
export function getDefaultDateRange(): { start: string; end: string } {
  return {
    start: getDateDaysAgo(30),
    end: getTodayDate(),
  }
}
