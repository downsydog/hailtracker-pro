import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { Customer, Vehicle, Job } from '@/types'

export interface CustomersQueryParams {
  search?: string
  has_active_job?: boolean
  page?: number
  per_page?: number
}

export type CreateCustomerData = Partial<Customer>
export type UpdateCustomerData = Partial<Customer>

interface CustomersResponse {
  customers: Customer[]
  total: number
  page: number
  per_page: number
}

export const customersApi = {
  list: (filters?: CustomersQueryParams) => apiGet<CustomersResponse>('/api/customers', { params: filters }),
  get: (id: number) => apiGet<Customer & { vehicles: Vehicle[], jobs: Job[] }>(`/api/customers/${id}`),
  create: (data: CreateCustomerData) => apiPost<Customer>('/api/customers', data),
  update: (id: number, data: UpdateCustomerData) => apiPut<Customer>(`/api/customers/${id}`, data),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/customers/${id}`),
  getVehicles: (id: number) => apiGet<Vehicle[]>(`/api/customers/${id}/vehicles`),
  addVehicle: (id: number, data: Partial<Vehicle>) => apiPost<Vehicle>(`/api/customers/${id}/vehicles`, data),
}
