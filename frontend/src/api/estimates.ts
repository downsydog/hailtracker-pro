import { apiClient } from './client'

export interface Estimate {
  id: number
  estimate_number: string
  customer_id: number
  customer_name: string
  vehicle_id: number
  vehicle_info: string
  status: 'draft' | 'sent' | 'approved' | 'declined' | 'expired'
  subtotal: number
  tax: number
  total: number
  valid_until?: string
  notes?: string
  created_at: string
  sent_at?: string
  approved_at?: string
}

export interface EstimateLineItem {
  id: number
  estimate_id: number
  description: string
  service_type: string
  quantity: number
  unit_price: number
  total: number
}

export interface EstimateTemplate {
  id: number
  name: string
  description?: string
  items: Array<{
    description: string
    service_type: string
    unit_price: number
  }>
}

export interface EstimatePhoto {
  id: number
  estimate_id: number
  url: string
  thumbnail_url: string
  caption?: string
  type: 'damage' | 'vehicle' | 'other'
  created_at: string
}

export const estimatesApi = {
  // Estimates
  getEstimates: (params?: { status?: string; customer_id?: number; page?: number }) =>
    apiClient.get<{ estimates: Estimate[]; total: number }>('/estimates', params),

  getEstimate: (id: number) =>
    apiClient.get<{ estimate: Estimate; items: EstimateLineItem[] }>(`/estimates/${id}`),

  createEstimate: (data: {
    customer_id: number
    vehicle_id: number
    items: Array<{ description: string; service_type: string; quantity: number; unit_price: number }>
    notes?: string
    valid_days?: number
  }) =>
    apiClient.post<{ estimate_id: number; estimate_number: string }>('/estimates', data),

  updateEstimate: (id: number, data: Partial<Estimate>) =>
    apiClient.patch<Estimate>(`/estimates/${id}`, data),

  deleteEstimate: (id: number) =>
    apiClient.delete(`/estimates/${id}`),

  // Actions
  sendEstimate: (id: number, method?: 'email' | 'sms') =>
    apiClient.post(`/estimates/${id}/send`, { method }),

  approveEstimate: (id: number, signature?: string) =>
    apiClient.post(`/estimates/${id}/approve`, { signature }),

  declineEstimate: (id: number, reason?: string) =>
    apiClient.post(`/estimates/${id}/decline`, { reason }),

  convertToJob: (id: number) =>
    apiClient.post<{ job_id: number; job_number: string }>(`/estimates/${id}/convert-to-job`),

  // PDF
  generatePdf: (id: number) =>
    apiClient.get<Blob>(`/estimates/${id}/pdf`),

  // Templates
  getTemplates: () =>
    apiClient.get<{ templates: EstimateTemplate[] }>('/estimates/templates'),

  createTemplate: (data: Partial<EstimateTemplate>) =>
    apiClient.post<EstimateTemplate>('/estimates/templates', data),

  applyTemplate: (estimateId: number, templateId: number) =>
    apiClient.post(`/estimates/${estimateId}/apply-template`, { template_id: templateId }),

  // Stats
  getStats: () =>
    apiClient.get<{
      total_estimates: number
      pending: number
      approved: number
      declined: number
      total_value: number
      conversion_rate: number
    }>('/estimates/stats'),
}

export default estimatesApi
