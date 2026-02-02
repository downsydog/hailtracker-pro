import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { Estimate, EstimateLineItem } from '@/types'

export interface EstimatesQueryParams {
  status?: string
  customer_id?: number
  start_date?: string
  end_date?: string
  search?: string
  page?: number
  per_page?: number
}

export type CreateEstimateData = Partial<Estimate>
export type UpdateEstimateData = Partial<Estimate>

interface EstimatesResponse {
  estimates: Estimate[]
  total: number
  page: number
  per_page: number
}

export const estimatesApi = {
  list: (filters?: EstimatesQueryParams) => apiGet<EstimatesResponse>('/api/estimates', { params: filters }),
  get: (id: number) => apiGet<Estimate & { items: EstimateLineItem[] }>(`/api/estimates/${id}`),
  create: (data: CreateEstimateData) => apiPost<Estimate>('/api/estimates', data),
  update: (id: number, data: UpdateEstimateData) => apiPut<Estimate>(`/api/estimates/${id}`, data),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/estimates/${id}`),
  addItem: (id: number, item: Partial<EstimateLineItem>) => apiPost<EstimateLineItem>(`/api/estimates/${id}/items`, item),
  updateItem: (id: number, itemId: number, item: Partial<EstimateLineItem>) => apiPut<EstimateLineItem>(`/api/estimates/${id}/items/${itemId}`, item),
  deleteItem: (id: number, itemId: number) => apiDelete<{ success: boolean }>(`/api/estimates/${id}/items/${itemId}`),
  send: (id: number) => apiPost<Estimate>(`/api/estimates/${id}/send`),
  approve: (id: number) => apiPost<Estimate>(`/api/estimates/${id}/approve`),
  decline: (id: number) => apiPost<Estimate>(`/api/estimates/${id}/decline`),
  convertToJob: (id: number) => apiPost<{ job_id: number }>(`/api/estimates/${id}/convert`),
  exportPdf: (id: number) => apiGet<Blob>(`/api/estimates/${id}/pdf`, { responseType: 'blob' }),
  getPhotos: (id: number) => apiGet<{ photos: EstimatePhoto[] }>(`/api/estimates/${id}/photos`),
  uploadPhoto: (id: number, file: File, description?: string) => {
    const formData = new FormData()
    formData.append('photo', file)
    if (description) formData.append('description', description)
    return apiPost<EstimatePhoto>(`/api/estimates/${id}/photos`, formData)
  },
  deletePhoto: (id: number, photoId: number) => apiDelete<{ success: boolean }>(`/api/estimates/${id}/photos/${photoId}`),
}

export interface EstimatePhoto {
  id: number
  estimate_id: number
  filename: string
  url: string
  description?: string
  created_at: string
}
