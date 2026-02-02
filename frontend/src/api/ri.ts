import { apiClient } from './client'

// R&I = Removal and Installation
export interface RITime {
  id: number
  operation: string
  operation_name?: string
  operation_code?: string
  ri_operation_id?: number
  vehicle_type: string
  category?: string
  labor_hours: number
  difficulty: 'easy' | 'medium' | 'hard'
  source?: string
  confidence_score?: number
  notes?: string
  is_active: boolean
  [key: string]: unknown  // Allow additional properties
}

// Alias for components
export type RIOperation = RITime

export interface RICategory {
  id: number
  name: string
  description?: string
  operations_count: number
}

export interface RIEstimate {
  id: number
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  operations: Array<{
    operation_id: number
    operation_name: string
    labor_hours: number
    labor_rate: number
    total: number
  }>
  total_hours: number
  total_labor: number
}

export interface RIVehicle {
  year?: number | string
  make?: string
  model?: string
  [key: string]: unknown
}

export const riApi = {
  // Times / Operations
  getTimes: (params?: { category?: string; vehicle_type?: string; search?: string; year?: number; make?: string; model?: string }) =>
    apiClient.get<{ times: RITime[]; total: number; vehicle?: RIVehicle }>('/ri/times', params),

  getTime: (id: number) =>
    apiClient.get<RITime>(`/ri/times/${id}`),

  createTime: (data: Partial<RITime>) =>
    apiClient.post<RITime>('/ri/times', data),

  updateTime: (id: number, data: Partial<RITime>) =>
    apiClient.patch<RITime>(`/ri/times/${id}`, data),

  deleteTime: (id: number) =>
    apiClient.delete(`/ri/times/${id}`),

  // Categories
  getCategories: () =>
    apiClient.get<{ categories: RICategory[] }>('/ri/categories'),

  // Estimate Calculator
  calculateEstimate: (data: {
    vehicle_year: number
    vehicle_make: string
    vehicle_model: string
    operation_ids: number[]
  }) =>
    apiClient.post<RIEstimate>('/ri/estimate', data),

  // Import/Export
  exportTimes: () =>
    apiClient.get<Blob>('/ri/export'),

  importTimes: (file: FormData) =>
    apiClient.post<{ imported: number; errors: string[] }>('/ri/import', file),

  // Time correction
  submitTimeCorrection: (data: {
    ri_operation_id?: number
    ri_time_id: number
    suggested_hours: number
    actual_hours: number
    vehicle_year: number
    vehicle_make: string
    vehicle_model: string
    notes?: string
  }) =>
    apiClient.post('/ri/corrections', data),
}

export default riApi
