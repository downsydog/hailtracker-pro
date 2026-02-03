import { apiClient } from './client'

export interface DealershipLocation {
  id: number
  dealership_id?: number
  name: string
  address: string
  city: string
  state: string
  zip: string
  phone?: string
  email?: string
  manager_name?: string
  manager_email?: string
  is_active?: boolean
  is_primary?: boolean
  vehicles_count: number
  vehicles?: number
  active_jobs?: number
}

export interface DealershipVehicle {
  id: number
  location_id: number
  dealership_id?: number
  vin: string
  year: number
  make: string
  model: string
  trim?: string
  color: string
  mileage?: number
  stock_number?: string
  status: 'available' | 'pending' | 'sold' | 'service' | 'pending_repair' | 'in_repair' | 'ready' | string
  damage_status?: 'none' | 'minor' | 'moderate' | 'severe'
  damage_type?: string
  damage_description?: string
  estimated_repair_cost?: number
  notes?: string
  created_at: string
  updated_at?: string
}

export interface DealershipUpload {
  id: number
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  records_total: number
  records_processed: number
  records_failed: number
  error_message?: string
  created_at: string
}

export interface DealershipApiKey {
  id: number
  name: string
  key_prefix: string
  permissions: string[]
  last_used?: string
  created_at: string
  is_active: boolean
}

export interface DealershipStats {
  total_vehicles: number
  vehicles_with_damage?: number
  pending_uploads?: number
  pending_repair?: number
  in_repair?: number
  completed_this_month?: number
  total_spent_this_month?: number
  avg_repair_time_days?: number
  locations_count?: number
  locations?: Array<{ id: number; name: string; vehicle_count?: number; vehicles?: number; active_jobs?: number }>
}

// Aliases for components using different names
export type DealerLocation = DealershipLocation
export type DealerVehicle = DealershipVehicle
export type DealerStats = DealershipStats

export interface Dealership {
  id: number
  name: string
  code?: string
  contact_name?: string
  email?: string
  phone?: string
  address?: string
  city?: string
  state?: string
  zip?: string
  is_active?: boolean
  status?: string
  api_key?: string
  pricing_tier?: string
  discount_percent?: number
  locations_count?: number
  vehicles_count?: number
  active_jobs?: number
  created_at: string
}

export interface ApiUsage {
  total_calls?: number
  calls_today?: number
  calls_this_month?: number
  limit?: number
  period?: string
  requests_total?: number
  requests_limit?: number
  vehicles_synced?: number
  jobs_created?: number
  last_sync?: string
  endpoints?: Array<{ name?: string; endpoint?: string; count?: number; method?: string; calls?: number; avg_response_ms?: number }>
  by_endpoint?: Record<string, number>
}

export interface DealerJob {
  id: number
  dealership_id?: number
  job_number: string
  vehicle_id: number
  vehicle_info?: string
  vehicle?: {
    id?: number
    dealership_id?: number
    year: number
    make: string
    model: string
    vin?: string
    stock_number?: string
    status?: string
    created_at?: string
    updated_at?: string
  }
  status: string
  status_label?: string
  damage_type?: string
  estimated_cost?: number
  estimate_total?: number
  invoice_total?: number
  scheduled_date?: string
  completed_at?: string
  created_at?: string
}

export interface BatchUploadResult {
  id: number
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  success?: boolean
  total_records?: number
  total_rows?: number
  processed?: number
  imported?: number
  failed?: number
  errors?: Array<string | { row: number; error: string }>
  vehicles?: Array<{ id?: number; vin: string; year: number; make: string; model: string; status: string; stock_number?: string }>
  created_at: string
  completed_at?: string
}

export const dealershipApi = {
  // Dashboard
  getDashboard: () =>
    apiClient.get<{ stats: DealershipStats; recent_uploads: DealershipUpload[] }>('/dealership/dashboard'),

  getStats: (_dealershipId?: number) =>
    apiClient.get<DealershipStats>('/dealership/stats'),

  getJobs: (params?: { status?: string; location_id?: number } | number) =>
    apiClient.get<{ jobs: DealerJob[]; total: number }>('/dealership/jobs', typeof params === 'number' ? {} : params),

  getDealership: (_dealershipId?: number) =>
    apiClient.get<Dealership>('/dealership'),

  getApiUsage: (_dealershipId?: number) =>
    apiClient.get<ApiUsage>('/dealership/api/usage'),

  regenerateApiKey: (_dealershipId?: number) =>
    apiClient.post<{ key: string }>('/dealership/api-key/regenerate'),

  // Locations
  getLocations: (_dealershipId?: number) =>
    apiClient.get<{ locations: DealershipLocation[] }>('/dealership/locations'),

  getLocation: (id: number, _dealershipId?: number) =>
    apiClient.get<DealershipLocation>(`/dealership/locations/${id}`),

  createLocation: (_dealershipIdOrData: number | Partial<DealershipLocation>, data?: Partial<DealershipLocation>) =>
    apiClient.post<DealershipLocation>('/dealership/locations', typeof _dealershipIdOrData === 'number' ? data : _dealershipIdOrData),

  updateLocation: (idOrDealershipId: number, dataOrId?: Partial<DealershipLocation> | number, maybeData?: Partial<DealershipLocation>) =>
    apiClient.patch<DealershipLocation>(`/dealership/locations/${typeof dataOrId === 'number' ? dataOrId : idOrDealershipId}`, typeof dataOrId === 'number' ? maybeData : dataOrId),

  deleteLocation: (id: number, _dealershipId?: number) =>
    apiClient.delete(`/dealership/locations/${id}`),

  // Vehicles
  getVehicles: (_dealershipIdOrParams?: number | { location_id?: number; status?: string; page?: number }, params?: { location_id?: number; status?: string; page?: number }) =>
    apiClient.get<{ vehicles: DealershipVehicle[]; total: number; page?: number }>('/dealership/vehicles', typeof _dealershipIdOrParams === 'number' ? params : _dealershipIdOrParams),

  getVehicle: (id: number) =>
    apiClient.get<DealershipVehicle>(`/dealership/vehicles/${id}`),

  createVehicle: (data: Partial<DealershipVehicle>) =>
    apiClient.post<DealershipVehicle>('/dealership/vehicles', data),

  updateVehicle: (id: number, data: Partial<DealershipVehicle>) =>
    apiClient.patch<DealershipVehicle>(`/dealership/vehicles/${id}`, data),

  deleteVehicle: (id: number) =>
    apiClient.delete(`/dealership/vehicles/${id}`),

  // Uploads
  getUploads: () =>
    apiClient.get<{ uploads: DealershipUpload[] }>('/dealership/uploads'),

  uploadVehicles: (_dealershipIdOrFile: number | FormData, file?: File | FormData, _locationId?: number) => {
    // Support both old signature (file: FormData) and new signature (dealershipId, file, locationId)
    const formData = typeof _dealershipIdOrFile === 'number' ? file : _dealershipIdOrFile
    return apiClient.post<DealershipUpload>('/dealership/uploads', formData as FormData)
  },

  getUploadStatus: (id: number) =>
    apiClient.get<DealershipUpload>(`/dealership/uploads/${id}`),

  // API Keys
  getApiKeys: () =>
    apiClient.get<{ keys: DealershipApiKey[] }>('/dealership/api-keys'),

  createApiKey: (data: { name: string; permissions: string[] }) =>
    apiClient.post<{ key: DealershipApiKey; secret: string }>('/dealership/api-keys', data),

  revokeApiKey: (id: number) =>
    apiClient.delete(`/dealership/api-keys/${id}`),

  // Download template
  downloadTemplate: () =>
    apiClient.get<Blob>('/dealership/uploads/template'),

  // Upload with location
  uploadVehiclesWithOptions: (_dealershipId: number, file: FormData, _locationId?: number) =>
    apiClient.post<DealershipUpload>('/dealership/uploads', file),

  // Create job from vehicle
  createJob: (vehicleIdOrDealershipId: number, dataOrVehicleId?: { damage_type?: string; notes?: string } | number, maybeData?: { damage_type?: string; notes?: string }) => {
    // Support both old signature (vehicleId, data) and new signature (dealershipId, vehicleId, data)
    const vehicleId = typeof dataOrVehicleId === 'number' ? dataOrVehicleId : vehicleIdOrDealershipId
    const data = typeof dataOrVehicleId === 'number' ? maybeData : dataOrVehicleId
    return apiClient.post<DealerJob>(`/dealership/vehicles/${vehicleId}/create-job`, data)
  },
}

export default dealershipApi
