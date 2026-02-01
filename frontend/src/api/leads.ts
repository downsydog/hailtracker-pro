import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { Lead } from '@/types'

export interface LeadsQueryParams {
  status?: string
  temperature?: string
  source?: string
  search?: string
  page?: number
  per_page?: number
  limit?: number
}

export type CreateLeadData = Partial<Lead>
export type UpdateLeadData = Partial<Lead>

interface LeadsResponse {
  leads: Lead[]
  total: number
  page: number
  per_page: number
}

export const leadsApi = {
  list: (filters?: LeadsQueryParams) => apiGet<LeadsResponse>('/leads', { params: filters }),
  get: (id: number) => apiGet<Lead>(`/leads/${id}`),
  create: (data: CreateLeadData) => apiPost<Lead>('/leads', data),
  update: (id: number, data: UpdateLeadData) => apiPut<Lead>(`/leads/${id}`, data),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/leads/${id}`),
  convert: (id: number, data?: { create_job?: boolean }) => apiPost<{ customer_id: number, job_id?: number }>(`/leads/${id}/convert`, data),
}
