import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { Vehicle, Job } from '@/types'

export interface VehiclesQueryParams {
  make?: string
  year_min?: number
  year_max?: number
  status?: string
  search?: string
  page?: number
  per_page?: number
}

export type CreateVehicleData = Partial<Vehicle>
export type UpdateVehicleData = Partial<Vehicle>

interface VehiclesResponse {
  vehicles: Vehicle[]
  total: number
  page: number
  per_page: number
}

export interface VINDecodeResult {
  success: boolean
  vin?: string
  year?: number
  make?: string
  model?: string
  trim?: string
  body_type?: string
  vehicle_type?: string
  error?: string
}

export const vehiclesApi = {
  list: (filters?: VehiclesQueryParams) => apiGet<VehiclesResponse>('/api/vehicles', { params: filters }),
  get: (id: number) => apiGet<Vehicle & { jobs: Job[] }>(`/api/vehicles/${id}`),
  create: (data: CreateVehicleData) => apiPost<Vehicle>('/api/vehicles', data),
  update: (id: number, data: UpdateVehicleData) => apiPut<Vehicle>(`/api/vehicles/${id}`, data),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/vehicles/${id}`),
  getMakes: () => apiGet<string[]>('/api/vehicles/makes'),

  // VIN Decoding - uses NHTSA API
  decodeVIN: (vin: string) =>
    apiGet<VINDecodeResult>(`/intake/api/decode-vin/${vin}`),
}
