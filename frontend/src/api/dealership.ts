import { apiGet, apiPost, apiPut, apiDelete } from './client'

// Dealership Portal API

export interface Dealership {
  id: number
  name: string
  code: string
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  address?: string
  city?: string
  state?: string
  zip?: string
  locations_count: number
  vehicles_count: number
  active_jobs: number
  status: 'active' | 'inactive' | 'pending'
  api_key?: string
  pricing_tier: 'standard' | 'premium' | 'enterprise'
  discount_percent: number
  created_at: string
}

export interface DealerLocation {
  id: number
  dealership_id: number
  name: string
  address: string
  city: string
  state: string
  zip: string
  phone?: string
  manager_name?: string
  manager_email?: string
  is_primary: boolean
  vehicles_count: number
  active_jobs: number
}

export interface DealerVehicle {
  id: number
  dealership_id: number
  location_id?: number
  stock_number: string
  vin: string
  year: number
  make: string
  model: string
  trim?: string
  color?: string
  mileage?: number
  status: 'available' | 'pending_repair' | 'in_repair' | 'ready' | 'sold'
  damage_type?: string
  damage_description?: string
  estimated_repair_cost?: number
  photos?: string[]
  created_at: string
  updated_at: string
}

export interface DealerJob {
  id: number
  job_number: string
  dealership_id: number
  location_id?: number
  vehicle_id: number
  vehicle: DealerVehicle
  status: string
  status_label: string
  scheduled_date?: string
  started_at?: string
  completed_at?: string
  estimate_total?: number
  invoice_total?: number
  notes?: string
}

export interface BatchUploadResult {
  success: boolean
  total_rows: number
  imported: number
  failed: number
  errors: Array<{ row: number; error: string }>
  vehicles: DealerVehicle[]
}

export interface DealerStats {
  total_vehicles: number
  pending_repair: number
  in_repair: number
  completed_this_month: number
  total_spent_this_month: number
  avg_repair_time_days: number
  locations: Array<{
    id: number
    name: string
    vehicles: number
    active_jobs: number
  }>
}

export interface FleetPricing {
  vehicle_count: number
  base_price_per_vehicle: number
  volume_discount_percent: number
  total_estimate: number
  savings: number
  breakdown: Array<{
    damage_type: string
    count: number
    avg_price: number
    subtotal: number
  }>
}

export interface ApiUsage {
  period: string
  requests_total: number
  requests_limit: number
  vehicles_synced: number
  jobs_created: number
  last_sync: string
  endpoints: Array<{
    endpoint: string
    method: string
    calls: number
    avg_response_ms: number
  }>
}

export const dealershipApi = {
  // Dealership CRUD
  getDealerships: () =>
    apiGet<{ dealerships: Dealership[] }>('/api/dealership/list'),

  getDealership: (id: number) =>
    apiGet<Dealership>(`/api/dealership/${id}`),

  createDealership: (data: Partial<Dealership>) =>
    apiPost<{ success: boolean; dealership_id: number }>('/api/dealership', data),

  updateDealership: (id: number, data: Partial<Dealership>) =>
    apiPut<{ success: boolean }>(`/api/dealership/${id}`, data),

  // Locations
  getLocations: (dealershipId: number) =>
    apiGet<{ locations: DealerLocation[] }>(`/api/dealership/${dealershipId}/locations`),

  createLocation: (dealershipId: number, data: Partial<DealerLocation>) =>
    apiPost<{ success: boolean; location_id: number }>(`/api/dealership/${dealershipId}/locations`, data),

  updateLocation: (dealershipId: number, locationId: number, data: Partial<DealerLocation>) =>
    apiPut<{ success: boolean }>(`/api/dealership/${dealershipId}/locations/${locationId}`, data),

  deleteLocation: (dealershipId: number, locationId: number) =>
    apiDelete<{ success: boolean }>(`/api/dealership/${dealershipId}/locations/${locationId}`),

  // Vehicles
  getVehicles: (dealershipId: number, params?: { status?: string; location_id?: number; page?: number }) =>
    apiGet<{ vehicles: DealerVehicle[]; total: number; page: number }>(`/api/dealership/${dealershipId}/vehicles`, { params }),

  getVehicle: (dealershipId: number, vehicleId: number) =>
    apiGet<DealerVehicle>(`/api/dealership/${dealershipId}/vehicles/${vehicleId}`),

  createVehicle: (dealershipId: number, data: Partial<DealerVehicle>) =>
    apiPost<{ success: boolean; vehicle_id: number }>(`/api/dealership/${dealershipId}/vehicles`, data),

  updateVehicle: (dealershipId: number, vehicleId: number, data: Partial<DealerVehicle>) =>
    apiPut<{ success: boolean }>(`/api/dealership/${dealershipId}/vehicles/${vehicleId}`, data),

  deleteVehicle: (dealershipId: number, vehicleId: number) =>
    apiDelete<{ success: boolean }>(`/api/dealership/${dealershipId}/vehicles/${vehicleId}`),

  // Batch Upload
  uploadVehicles: (dealershipId: number, file: File, locationId?: number) => {
    const formData = new FormData()
    formData.append('file', file)
    if (locationId) formData.append('location_id', locationId.toString())
    return apiPost<BatchUploadResult>(`/api/dealership/${dealershipId}/vehicles/batch`, formData)
  },

  downloadTemplate: () =>
    apiGet<Blob>('/api/dealership/vehicles/template', { responseType: 'blob' }),

  // Jobs
  getJobs: (dealershipId: number, params?: { status?: string; location_id?: number }) =>
    apiGet<{ jobs: DealerJob[] }>(`/api/dealership/${dealershipId}/jobs`, { params }),

  createJob: (dealershipId: number, vehicleId: number, data?: { scheduled_date?: string; notes?: string }) =>
    apiPost<{ success: boolean; job_id: number; job_number: string }>(`/api/dealership/${dealershipId}/vehicles/${vehicleId}/create-job`, data),

  // Stats & Pricing
  getStats: (dealershipId: number) =>
    apiGet<DealerStats>(`/api/dealership/${dealershipId}/stats`),

  calculateFleetPricing: (dealershipId: number, vehicleIds: number[]) =>
    apiPost<FleetPricing>(`/api/dealership/${dealershipId}/fleet-pricing`, { vehicle_ids: vehicleIds }),

  // API Management
  getApiUsage: (dealershipId: number) =>
    apiGet<ApiUsage>(`/api/dealership/${dealershipId}/api-usage`),

  regenerateApiKey: (dealershipId: number) =>
    apiPost<{ success: boolean; api_key: string }>(`/api/dealership/${dealershipId}/regenerate-api-key`),
}
