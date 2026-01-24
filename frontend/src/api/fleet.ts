import { apiGet, apiPost, apiPut } from './client'

// Fleet Location (business prospects)
export interface FleetLocation {
  id: number
  name: string
  category: string
  subcategory?: string
  brand?: string
  address?: string
  city: string
  state: string
  zip_code?: string
  lat: number
  lon: number
  phone?: string
  email?: string
  website?: string
  estimated_vehicles: number
  vehicle_confidence?: string
  parking_type?: string
  luxury_vehicles?: boolean
  average_vehicle_value?: number
  accessibility?: string
  operating_hours?: string
  worked_before?: boolean
  avg_revenue_per_vehicle?: number
  market_saturation?: string
  icon?: string
  color?: string
  tier?: number
  category_name?: string
  distance_km?: number
}

export interface FleetLocationCategory {
  category: string
  display_name?: string
  icon?: string
  color?: string
  tier?: number
  location_count: number
  total_vehicles: number
  avg_vehicles: number
  potential_revenue: number
}

export interface FleetLocationStats {
  total_locations: number
  total_vehicles: number
  categories: number
  potential_revenue: number
  top_categories: Array<{
    category: string
    count: number
    vehicles: number
  }>
}

export interface FleetVehicle {
  id: number
  vehicle_id: number
  vehicle_info: string
  license_plate?: string
  vin?: string
  assigned_to?: number
  assigned_to_name?: string
  current_location?: {
    lat: number
    lng: number
    address?: string
    updated_at: string
  }
  status: 'available' | 'in_use' | 'en_route' | 'at_job' | 'maintenance' | 'out_of_service'
  current_job_id?: number
  current_job_number?: string
  fuel_level?: number
  odometer?: number
  last_inspection_date?: string
  next_service_due?: string
}

export interface FleetDriver {
  id: number
  user_id: number
  name: string
  phone?: string
  assigned_vehicle_id?: number
  assigned_vehicle_info?: string
  current_location?: {
    lat: number
    lng: number
    updated_at: string
  }
  status: 'available' | 'on_job' | 'en_route' | 'off_duty'
  current_job_id?: number
}

export interface FleetRoute {
  id: number
  driver_id: number
  driver_name: string
  vehicle_id?: number
  date: string
  stops: FleetRouteStop[]
  total_distance_miles: number
  estimated_duration_minutes: number
  status: 'planned' | 'in_progress' | 'completed'
  started_at?: string
  completed_at?: string
}

export interface FleetRouteStop {
  id: number
  sequence: number
  job_id?: number
  job_number?: string
  customer_name?: string
  location: {
    lat: number
    lng: number
    address: string
  }
  scheduled_arrival?: string
  actual_arrival?: string
  estimated_duration_minutes: number
  status: 'pending' | 'arrived' | 'completed' | 'skipped'
  notes?: string
}

export interface FleetStats {
  total_vehicles: number
  vehicles_in_use: number
  vehicles_available: number
  vehicles_in_maintenance: number
  total_drivers: number
  drivers_on_duty: number
  active_routes: number
  total_miles_today: number
}

export const fleetApi = {
  // Get all fleet vehicles with current locations
  getVehicles: () =>
    apiGet<{ vehicles: FleetVehicle[] }>('/api/fleet/vehicles'),

  // Get single vehicle details
  getVehicle: (id: number) =>
    apiGet<FleetVehicle>(`/api/fleet/vehicles/${id}`),

  // Update vehicle status
  updateVehicleStatus: (id: number, status: FleetVehicle['status'], notes?: string) =>
    apiPost<{ success: boolean }>(`/api/fleet/vehicles/${id}/status`, { status, notes }),

  // Update vehicle location (from mobile app)
  updateVehicleLocation: (id: number, lat: number, lng: number) =>
    apiPost<{ success: boolean }>(`/api/fleet/vehicles/${id}/location`, { lat, lng }),

  // Assign vehicle to driver
  assignVehicle: (vehicleId: number, driverId: number) =>
    apiPost<{ success: boolean }>(`/api/fleet/vehicles/${vehicleId}/assign`, { driver_id: driverId }),

  // Unassign vehicle
  unassignVehicle: (vehicleId: number) =>
    apiPost<{ success: boolean }>(`/api/fleet/vehicles/${vehicleId}/unassign`),

  // Get all drivers with status
  getDrivers: () =>
    apiGet<{ drivers: FleetDriver[] }>('/api/fleet/drivers'),

  // Get driver details
  getDriver: (id: number) =>
    apiGet<FleetDriver>(`/api/fleet/drivers/${id}`),

  // Update driver status
  updateDriverStatus: (id: number, status: FleetDriver['status']) =>
    apiPost<{ success: boolean }>(`/api/fleet/drivers/${id}/status`, { status }),

  // Update driver location (from mobile app)
  updateDriverLocation: (id: number, lat: number, lng: number) =>
    apiPost<{ success: boolean }>(`/api/fleet/drivers/${id}/location`, { lat, lng }),

  // Routes
  getRoutes: (date?: string) =>
    apiGet<{ routes: FleetRoute[] }>('/api/fleet/routes', { params: { date } }),

  getRoute: (id: number) =>
    apiGet<FleetRoute>(`/api/fleet/routes/${id}`),

  createRoute: (data: {
    driver_id: number
    vehicle_id?: number
    date: string
    stops: Array<{
      job_id?: number
      location: { lat: number; lng: number; address: string }
      scheduled_arrival?: string
      estimated_duration_minutes?: number
    }>
  }) =>
    apiPost<{ success: boolean; route_id: number }>('/api/fleet/routes', data),

  updateRoute: (id: number, data: Partial<FleetRoute>) =>
    apiPut<{ success: boolean }>(`/api/fleet/routes/${id}`, data),

  // Start route
  startRoute: (id: number) =>
    apiPost<{ success: boolean }>(`/api/fleet/routes/${id}/start`),

  // Complete route stop
  completeStop: (routeId: number, stopId: number, notes?: string) =>
    apiPost<{ success: boolean }>(`/api/fleet/routes/${routeId}/stops/${stopId}/complete`, { notes }),

  // Skip route stop
  skipStop: (routeId: number, stopId: number, reason: string) =>
    apiPost<{ success: boolean }>(`/api/fleet/routes/${routeId}/stops/${stopId}/skip`, { reason }),

  // Optimize route order
  optimizeRoute: (id: number) =>
    apiPost<{ success: boolean; optimized_stops: FleetRouteStop[] }>(`/api/fleet/routes/${id}/optimize`),

  // Get fleet stats
  getStats: () =>
    apiGet<FleetStats>('/api/fleet/stats'),

  // Get real-time positions (for map refresh)
  getRealTimePositions: () =>
    apiGet<{
      vehicles: Array<{ id: number; lat: number; lng: number; status: string }>
      drivers: Array<{ id: number; lat: number; lng: number; status: string }>
    }>('/api/fleet/positions'),

  // Get directions between points
  getDirections: (origin: { lat: number; lng: number }, destination: { lat: number; lng: number }) =>
    apiGet<{
      distance_miles: number
      duration_minutes: number
      polyline: string
    }>('/api/fleet/directions', {
      params: {
        origin_lat: origin.lat,
        origin_lng: origin.lng,
        dest_lat: destination.lat,
        dest_lng: destination.lng
      }
    }),
}

// Fleet Locations API (business prospects)
export const fleetLocationsApi = {
  // List locations with filters
  getLocations: (params?: {
    page?: number
    per_page?: number
    category?: string
    min_vehicles?: number
    search?: string
  }) =>
    apiGet<{
      locations: FleetLocation[]
      total: number
      page: number
      per_page: number
      pages: number
    }>('/api/fleet-locations', { params }),

  // Search locations
  search: (query: string, limit?: number) =>
    apiGet<{ locations: FleetLocation[] }>('/api/fleet-locations/search', {
      params: { q: query, limit }
    }),

  // Get locations within bounding box
  getInBbox: (bbox: { south: number; west: number; north: number; east: number }, categories?: string[]) =>
    apiGet<{ locations: FleetLocation[] }>('/api/fleet-locations/bbox', {
      params: { ...bbox, category: categories }
    }),

  // Get locations near a point
  getNearby: (lat: number, lon: number, options?: {
    radius?: number
    min_vehicles?: number
    categories?: string[]
  }) =>
    apiGet<{ locations: FleetLocation[] }>('/api/fleet-locations/nearby', {
      params: { lat, lon, ...options, category: options?.categories }
    }),

  // Get category summary
  getCategories: () =>
    apiGet<{ categories: FleetLocationCategory[] }>('/api/fleet-locations/categories'),

  // Get overall stats
  getStats: () =>
    apiGet<FleetLocationStats>('/api/fleet-locations/stats'),
}
