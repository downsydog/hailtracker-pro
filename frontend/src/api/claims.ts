import { apiGet, apiPost, apiPut, apiDelete } from './client'

export interface InsuranceClaim {
  id: number
  claim_number: string
  job_id: number
  customer_id: number
  customer_name: string
  vehicle_info?: string
  insurance_company: string
  policy_number?: string
  deductible: number
  status: 'pending' | 'submitted' | 'in_review' | 'approved' | 'denied' | 'paid' | 'closed'
  submitted_date?: string
  approved_date?: string
  approved_amount?: number
  paid_date?: string
  paid_amount?: number
  adjuster_name?: string
  adjuster_phone?: string
  adjuster_email?: string
  notes?: string
  documents: ClaimDocument[]
  created_at: string
  updated_at: string
}

export interface ClaimDocument {
  id: number
  claim_id: number
  document_type: 'estimate' | 'photos' | 'supplement' | 'invoice' | 'adjuster_report' | 'authorization' | 'other'
  filename: string
  file_url: string
  uploaded_at: string
  uploaded_by?: number
}

export interface ClaimTimelineEvent {
  id: number
  claim_id: number
  event_type: string
  description: string
  created_at: string
  created_by?: number
}

export interface ClaimCreateData {
  job_id: number
  insurance_company: string
  policy_number?: string
  deductible: number
  adjuster_name?: string
  adjuster_phone?: string
  adjuster_email?: string
  notes?: string
}

export interface ClaimFilters {
  status?: string
  insurance_company?: string
  customer_id?: number
  job_id?: number
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}

export const claimsApi = {
  // List claims with filters
  getClaims: (filters?: ClaimFilters) =>
    apiGet<{ claims: InsuranceClaim[]; total: number; page: number }>('/api/claims', { params: filters }),

  // Get single claim with timeline
  getClaim: (id: number) =>
    apiGet<{ claim: InsuranceClaim; timeline: ClaimTimelineEvent[] }>(`/api/claims/${id}`),

  // Create new claim
  createClaim: (data: ClaimCreateData) =>
    apiPost<{ success: boolean; claim_id: number; claim_number: string }>('/api/claims', data),

  // Update claim
  updateClaim: (id: number, data: Partial<ClaimCreateData>) =>
    apiPut<{ success: boolean }>(`/api/claims/${id}`, data),

  // Delete claim
  deleteClaim: (id: number) =>
    apiDelete<{ success: boolean }>(`/api/claims/${id}`),

  // Update claim status
  updateStatus: (id: number, status: InsuranceClaim['status'], notes?: string) =>
    apiPost<{ success: boolean }>(`/api/claims/${id}/status`, { status, notes }),

  // Submit to insurance
  submitClaim: (id: number) =>
    apiPost<{ success: boolean }>(`/api/claims/${id}/submit`),

  // Record approval
  recordApproval: (id: number, data: { approved_amount: number; notes?: string }) =>
    apiPost<{ success: boolean }>(`/api/claims/${id}/approve`, data),

  // Record denial
  recordDenial: (id: number, reason: string) =>
    apiPost<{ success: boolean }>(`/api/claims/${id}/deny`, { reason }),

  // Record payment received
  recordPayment: (id: number, data: { paid_amount: number; paid_date: string; notes?: string }) =>
    apiPost<{ success: boolean }>(`/api/claims/${id}/payment`, data),

  // Upload document
  uploadDocument: (id: number, file: File, documentType: ClaimDocument['document_type']) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', documentType)
    return apiPost<{ success: boolean; document_id: number }>(`/api/claims/${id}/documents`, formData)
  },

  // Delete document
  deleteDocument: (claimId: number, documentId: number) =>
    apiDelete<{ success: boolean }>(`/api/claims/${claimId}/documents/${documentId}`),

  // Add timeline note
  addNote: (id: number, note: string) =>
    apiPost<{ success: boolean }>(`/api/claims/${id}/notes`, { note }),

  // Get claim stats
  getStats: () =>
    apiGet<{
      total_pending: number
      total_in_review: number
      total_approved: number
      total_value_pending: number
      avg_processing_days: number
      count_by_company: Record<string, number>
    }>('/api/claims/stats'),

  // Get insurance companies list
  getInsuranceCompanies: () =>
    apiGet<{ companies: string[] }>('/api/claims/insurance-companies'),
}
