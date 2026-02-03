import { apiGet, apiPost, apiPut, apiDelete } from './client'

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
    apiGet<{ vehicles: FleetVehicle[] }>('/fleet/vehicles'),

  // Get single vehicle details
  getVehicle: (id: number) =>
    apiGet<FleetVehicle>(`/fleet/vehicles/${id}`),

  // Update vehicle status
  updateVehicleStatus: (id: number, status: FleetVehicle['status'], notes?: string) =>
    apiPost<{ success: boolean }>(`/fleet/vehicles/${id}/status`, { status, notes }),

  // Update vehicle location (from mobile app)
  updateVehicleLocation: (id: number, lat: number, lng: number) =>
    apiPost<{ success: boolean }>(`/fleet/vehicles/${id}/location`, { lat, lng }),

  // Assign vehicle to driver
  assignVehicle: (vehicleId: number, driverId: number) =>
    apiPost<{ success: boolean }>(`/fleet/vehicles/${vehicleId}/assign`, { driver_id: driverId }),

  // Unassign vehicle
  unassignVehicle: (vehicleId: number) =>
    apiPost<{ success: boolean }>(`/fleet/vehicles/${vehicleId}/unassign`),

  // Get all drivers with status
  getDrivers: () =>
    apiGet<{ drivers: FleetDriver[] }>('/fleet/drivers'),

  // Get driver details
  getDriver: (id: number) =>
    apiGet<FleetDriver>(`/fleet/drivers/${id}`),

  // Update driver status
  updateDriverStatus: (id: number, status: FleetDriver['status']) =>
    apiPost<{ success: boolean }>(`/fleet/drivers/${id}/status`, { status }),

  // Update driver location (from mobile app)
  updateDriverLocation: (id: number, lat: number, lng: number) =>
    apiPost<{ success: boolean }>(`/fleet/drivers/${id}/location`, { lat, lng }),

  // Routes
  getRoutes: (date?: string) =>
    apiGet<{ routes: FleetRoute[] }>('/fleet/routes', { params: { date } }),

  getRoute: (id: number) =>
    apiGet<FleetRoute>(`/fleet/routes/${id}`),

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
    apiPost<{ success: boolean; route_id: number }>('/fleet/routes', data),

  updateRoute: (id: number, data: Partial<FleetRoute>) =>
    apiPut<{ success: boolean }>(`/fleet/routes/${id}`, data),

  // Start route
  startRoute: (id: number) =>
    apiPost<{ success: boolean }>(`/fleet/routes/${id}/start`),

  // Complete route stop
  completeStop: (routeId: number, stopId: number, notes?: string) =>
    apiPost<{ success: boolean }>(`/fleet/routes/${routeId}/stops/${stopId}/complete`, { notes }),

  // Skip route stop
  skipStop: (routeId: number, stopId: number, reason: string) =>
    apiPost<{ success: boolean }>(`/fleet/routes/${routeId}/stops/${stopId}/skip`, { reason }),

  // Optimize route order
  optimizeRoute: (id: number) =>
    apiPost<{ success: boolean; optimized_stops: FleetRouteStop[] }>(`/fleet/routes/${id}/optimize`),

  // Get fleet stats
  getStats: () =>
    apiGet<FleetStats>('/fleet/stats'),

  // Get real-time positions (for map refresh)
  getRealTimePositions: () =>
    apiGet<{
      vehicles: Array<{ id: number; lat: number; lng: number; status: string }>
      drivers: Array<{ id: number; lat: number; lng: number; status: string }>
    }>('/fleet/positions'),

  // Get directions between points
  getDirections: (origin: { lat: number; lng: number }, destination: { lat: number; lng: number }) =>
    apiGet<{
      distance_miles: number
      duration_minutes: number
      polyline: string
    }>('/fleet/directions', {
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
    }>('/fleet-locations', { params }),

  // Search locations
  search: (query: string, limit?: number) =>
    apiGet<{ locations: FleetLocation[] }>('/fleet-locations/search', {
      params: { q: query, limit }
    }),

  // Get locations within bounding box
  getInBbox: (bbox: { south: number; west: number; north: number; east: number }, categories?: string[]) =>
    apiGet<{ locations: FleetLocation[] }>('/fleet-locations/bbox', {
      params: { ...bbox, category: categories }
    }),

  // Get locations near a point
  getNearby: (lat: number, lon: number, options?: {
    radius?: number
    min_vehicles?: number
    categories?: string[]
  }) =>
    apiGet<{ locations: FleetLocation[] }>('/fleet-locations/nearby', {
      params: { lat, lon, ...options, category: options?.categories }
    }),

  // Get category summary
  getCategories: () =>
    apiGet<{ categories: FleetLocationCategory[] }>('/fleet-locations/categories'),

  // Get overall stats
  getStats: () =>
    apiGet<FleetLocationStats>('/fleet-locations/stats'),

  // Get unique cities in database
  getCities: () =>
    apiGet<{
      cities: Array<{
        city: string
        state: string
        location_count: number
        total_vehicles: number
      }>
    }>('/fleet-locations/cities'),

  // Discover fleet locations for a city using multi-source discovery
  discoverCity: (city: string, state: string, bbox?: [number, number, number, number], sources?: string[]) =>
    apiPost<{
      success: boolean
      city: string
      state: string
      existing_locations: number
      new_locations: number
      total_locations: number
      sources_searched: Record<string, number>
      stats?: {
        total_locations: number
        total_estimated_vehicles: number
        by_category: Record<string, number>
        by_source: Record<string, number>
        by_tier: Record<string, number>
        verified_fleets: number
      }
      errors?: string[]
    }>('/fleet-locations/discover', { city, state, bbox, sources }),

  // Get data sources status (OSM, FMCSA, Yelp)
  getDataSources: () =>
    apiGet<{
      sources: Array<{
        name: string
        status: 'active' | 'needs_import' | 'needs_api_key' | 'not_configured'
        description: string
        cost: string
        rate_limit?: string
        carriers?: number
        signup_url?: string
      }>
    }>('/fleet-locations/sources'),

  // Get all category definitions
  getCategoryInfo: () =>
    apiGet<{
      categories: Array<{
        key: string
        name: string
        tier: number
        icon: string
        color: string
        est_vehicles: number
        keywords: string[]
        yelp_category?: string
        fmcsa?: boolean
      }>
      tier_descriptions: Record<number, string>
    }>('/fleet-locations/category-info'),

  // ===== SCRAPED BUSINESSES (BBB, Manta, etc.) =====

  // Get scraped businesses from database
  getScrapedBusinesses: (params?: {
    city?: string
    state?: string
    category?: string
    min_vehicles?: number
    source?: string
    tier?: number
    limit?: number
    offset?: number
  }) =>
    apiGet<{
      businesses: Array<{
        id: number
        name: string
        address: string
        city: string
        state: string
        zip: string
        phone: string
        website: string
        category: string
        subcategory: string
        source: string
        tier: number
        estimated_vehicles: number
        latitude: number | null
        longitude: number | null
        bbb_rating: string | null
        years_in_business: number | null
        scraped_at: string
      }>
      count: number
    }>('/fleet-locations/businesses', { params }),

  // Get scraped business stats
  getScrapedStats: (city?: string, state?: string) =>
    apiGet<{
      total_businesses: number
      total_estimated_vehicles: number
      by_source: Record<string, number>
      by_category: Array<{ category: string; count: number; vehicles: number }>
      by_tier: Record<number, number>
    }>('/fleet-locations/businesses/stats', { params: { city, state } }),

  // Scrape businesses for a city
  scrapeCity: (city: string, state: string, sources?: string[]) =>
    apiPost<{
      success: boolean
      city: string
      new_businesses: number
      by_source: Record<string, number>
      total_in_database: number
    }>('/fleet-locations/scrape', { city, state, sources }),

  // Scrape multiple cities
  scrapeMultiple: (cities: Array<{ city: string; state: string }>, sources?: string[]) =>
    apiPost<{
      success: boolean
      results: Array<{
        city: string
        state: string
        new_businesses: number
        by_source: Record<string, number>
      }>
      total_new: number
    }>('/fleet-locations/scrape-multiple', { cities, sources }),

  // Geocode all businesses in database
  geocodeAll: (limit?: number) =>
    apiPost<{
      success: boolean
      geocoded: number
      failed: number
      total_with_coords: number
    }>('/fleet-locations/geocode-all', { limit }),

  // ===== ROUTE OPTIMIZATION =====

  // Optimize route for visiting multiple locations
  optimizeRoute: (locations: Array<{
    id?: number
    name?: string
    latitude: number
    longitude: number
  }>, startLocation?: { latitude: number; longitude: number }) =>
    apiPost<{
      success: boolean
      locations: Array<{
        id?: number
        name?: string
        latitude: number
        longitude: number
        visit_order: number
      }>
      order: number[]
      total_distance_miles: number
      total_time_minutes: number
      route_geometry?: any
      legs: Array<{
        from_index: number
        to_index: number
        distance_miles: number
        duration_minutes: number
      }>
    }>('/fleet-locations/optimize-route', { locations, start_location: startLocation }),

  // Get turn-by-turn directions
  getDirections: (origin: { latitude: number; longitude: number }, destination: { latitude: number; longitude: number }) =>
    apiPost<{
      success: boolean
      distance_miles: number
      duration_minutes: number
      geometry?: any
      steps: Array<{
        instruction: string
        distance_miles: number
        duration_minutes: number
        name: string
      }>
    }>('/fleet-locations/directions', { origin, destination }),

  // Generate Google Maps URL for route
  getGoogleMapsUrl: (locations: Array<{ latitude: number; longitude: number }>) =>
    apiPost<{ url: string }>('/fleet-locations/google-maps-url', { locations }),

  // ===== HAIL OVERLAY =====

  // Get businesses affected by hail events
  getHailAffectedBusinesses: (params?: {
    days?: number
    min_size?: string
    min_vehicles?: number
  }) =>
    apiGet<{
      businesses: Array<{
        id: number
        name: string
        category: string
        city: string
        state: string
        latitude: number
        longitude: number
        estimated_vehicles: number
        hail_events: Array<{
          event_id: number
          date: string
          max_size: string
          max_size_inches: number
          distance_miles: number
        }>
      }>
      total: number
      by_hail_size: Record<string, number>
    }>('/fleet-locations/businesses/hail-affected', { params }),

  // Smart swath-based discovery - finds businesses INSIDE hail swath polygons
  // Uses multiple data sources: OSM, Foursquare, Yelp, HERE, TomTom, Google, Yellow Pages, BBB
  // Deduplicates, geocodes, and filters to swath polygons
  smartScrapeSwaths: (params: {
    event_ids: number[]
    buffer_miles?: number
    force_refresh?: boolean
    // New sources parameter - recommended: ['osm', 'foursquare', 'yelp']
    sources?: ('osm' | 'foursquare' | 'yelp' | 'here' | 'tomtom' | 'google' | 'yellowpages' | 'bbb')[]
    // Legacy parameters (still supported)
    include_osm?: boolean
    include_yellowpages?: boolean
    include_bbb?: boolean
  }) =>
    apiPost<{
      success: boolean
      businesses: AffectedBusiness[]
      stats: {
        total_found: number
        cached: boolean
        from_cache: number
        newly_scraped: number
        osm_found: number
        foursquare_found: number
        yelp_found: number
        here_found: number
        tomtom_found: number
        google_found: number
        yellowpages_found: number
        bbb_found: number
        geocoded: number
        duplicates_removed: number
        final_in_swath: number
        by_category: Record<string, number>
        by_source: Record<string, number>
        total_vehicles: number
        events_processed: number
      }
      api_status: {
        foursquare: { configured: boolean; free_tier: string }
        yelp: { configured: boolean; free_tier: string }
        here: { configured: boolean; free_tier: string }
        tomtom: { configured: boolean; free_tier: string }
        google: { configured: boolean; free_tier: string }
        osm: { configured: boolean; free_tier: string }
      }
    }>('/fleet-locations/smart-scrape-swaths', params),

  // Get API configuration status for all discovery sources
  getApiStatus: () =>
    apiGet<{
      apis: {
        foursquare: { configured: boolean; free_tier: string }
        yelp: { configured: boolean; free_tier: string }
        here: { configured: boolean; free_tier: string }
        tomtom: { configured: boolean; free_tier: string }
        google: { configured: boolean; free_tier: string }
        osm: { configured: boolean; free_tier: string }
      }
      recommended: string[]
      setup_instructions: Record<string, string>
    }>('/fleet-locations/api-status'),

  // Mark a swath-discovered business as added to CRM
  markBusinessAddedToCRM: (businessId: number) =>
    apiPost<{ success: boolean; message: string }>(
      `/fleet-locations/swath-businesses/${businessId}/add-to-crm`,
      {}
    ),

  // Clear cached swath discoveries
  clearSwathCache: (eventIds?: number[]) =>
    apiPost<{ success: boolean; message: string }>(
      '/fleet-locations/swath-businesses/clear-cache',
      { event_ids: eventIds }
    ),

  // Tile-based discovery - complete coverage of irregular swath shapes
  // Uses 0.25 sq mile tiles to ensure maximum business coverage
  // Smart default: 200 tiles prioritizing dense urban areas
  tileDiscover: (params: {
    event_ids: number[]
    tile_size_miles?: number  // 0.25 (default), 0.5, or 1.0
    sources?: ('osm' | 'yelp' | 'foursquare' | 'here' | 'tomtom' | 'google' | 'bbb' | 'yellowpages')[]
    force_refresh?: boolean
    max_tiles?: number  // Limit tiles searched (default 200, 0 = unlimited)
  }) =>
    apiPost<{
      success: boolean
      businesses: AffectedBusiness[]
      stats: {
        tiles_total: number
        tiles_searched: number
        tiles_from_cache: number
        by_source: Record<string, number>
        total_found: number
        duplicates_removed: number
        geocoded: number
        total_vehicles: number
        by_category: Record<string, number>
      }
      tile_stats: {
        count: number
        tile_size_miles: number
        estimated_area_sq_miles: number
        bounds?: {
          min_lat: number
          max_lat: number
          min_lon: number
          max_lon: number
        }
      }
    }>('/fleet-locations/tile-discover', params),

  // HYBRID discovery - OSM + YellowPages + BBB + Manta
  // 1 OSM query for all swaths + city-based queries = ~60 seconds
  fastDiscover: (params: {
    event_ids: number[]
    force_refresh?: boolean
    include_osm?: boolean      // default: true - OpenStreetMap (returns coords)
    include_yp?: boolean       // default: true - Yellow Pages (by city)
    include_bbb?: boolean      // default: true - BBB (by city)
    include_manta?: boolean    // default: true - Manta (by city)
  }) =>
    apiPost<{
      success: boolean
      businesses: AffectedBusiness[]
      stats: {
        swaths_total: number
        swaths_from_cache: number
        osm_queries: number
        osm_found: number
        yp_found: number
        bbb_found: number
        manta_found: number
        total_elements: number
        total_found: number
        duplicates_removed: number
        total_vehicles: number
        by_category: Record<string, number>
        by_source: Record<string, number>
      }
      timing: {
        total_seconds: number
        osm_seconds: number
        city_seconds: number
      }
    }>('/fleet-locations/fast-discover', params),
}

// ===== HAIL EVENTS DATE-BASED OVERLAY =====

export interface HailEvent {
  id: number
  event_date: string
  event_name: string
  city?: string
  max_hail_size: number
  center_lat: number
  center_lon: number
  area_sq_miles?: number
  estimated_vehicles?: number
  data_source?: string
  confidence?: number
  swath_polygon?: any
  swath_raw?: string
}

export interface HailEventDate {
  date: string
  event_count: number
  max_size: number
  severity: 'MINOR' | 'MODERATE' | 'SEVERE'
  total_vehicles: number
  has_swath: boolean
}

export interface AffectedBusiness {
  id: number
  name: string
  address: string
  city: string
  state: string
  zip: string
  phone: string
  website: string
  email?: string
  category: string
  subcategory?: string
  estimated_vehicles: number
  tier: number
  latitude: number
  longitude: number
  source: string
  osm_id?: string
  bbb_rating?: string
  added_to_crm?: boolean
  event_id?: number
  hail_date?: string
  hail_size?: number
}

export const hailEventsApi = {
  // Get hail events for a specific date with swath polygons
  getEventsByDate: (params: {
    date?: string
    start_date?: string
    end_date?: string
    state?: string
    min_size?: number
  }) =>
    apiGet<{
      count: number
      events: HailEvent[]
      query: typeof params
    }>('/hail-events/by-date', { params }),

  // Get list of dates that have hail events
  getEventDates: (params?: {
    year?: number
    month?: number
    state?: string
    limit?: number
  }) =>
    apiGet<{
      count: number
      year: number
      month?: number
      dates: HailEventDate[]
    }>('/hail-events/dates', { params }),

  // Get businesses within a specific hail event's swath
  getAffectedBusinesses: (eventId: number) =>
    apiGet<{
      event: {
        id: number
        date: string
        name: string
        city?: string
        max_hail_size: number
        area_sq_miles?: number
        center_lat: number
        center_lon: number
      }
      affected_count: number
      total_estimated_vehicles: number
      estimated_value: number
      businesses: AffectedBusiness[]
    }>(`/hail-events/${eventId}/affected-businesses`),

  // Get all businesses affected by hail on a specific date
  // If eventIds provided, only search those specific events (viewport filtering)
  getAffectedBusinessesByDate: (date: string, minSize?: number, eventIds?: number[]) =>
    apiGet<{
      date: string
      event_count: number
      events: Array<{
        id: number
        name: string
        city?: string
        max_hail_size: number
        area_sq_miles?: number
        center_lat: number
        center_lon: number
      }>
      affected_count: number
      total_estimated_vehicles: number
      estimated_value: number
      businesses: AffectedBusiness[]
      viewport_filtered?: boolean
    }>('/hail-events/affected-businesses-by-date', {
      params: {
        date,
        min_size: minSize,
        event_ids: eventIds?.join(',') // Send as comma-separated string
      }
    }),
}

// ===== FLEET LEADS CRM =====

export interface FleetLead {
  id: number
  business_id?: number
  company_name: string
  contact_name?: string
  contact_phone?: string
  contact_email?: string
  address?: string
  city: string
  state: string
  category?: string
  estimated_vehicles: number
  tier?: number
  status: 'NEW' | 'CONTACTED' | 'CALLBACK' | 'QUOTED' | 'NEGOTIATING' | 'WON' | 'LOST'
  priority: 'LOW' | 'MEDIUM' | 'HIGH'
  source?: string
  hail_affected?: boolean
  hail_date?: string
  hail_size?: number
  hail_distance?: number
  notes?: string
  quote_amount?: number
  won_amount?: number
  next_followup_date?: string
  last_contact_date?: string
  call_count?: number
  created_at: string
  updated_at: string
  latitude?: number
  longitude?: number
}

export interface FleetLeadActivity {
  id: number
  lead_id: number
  activity_type: string
  description: string
  created_at: string
  created_by?: string
}

export const fleetLeadsApi = {
  // Get all leads with filters
  getLeads: (params?: {
    status?: string
    priority?: string
    city?: string
    state?: string
    hail_affected?: boolean
    search?: string
    limit?: number
    offset?: number
  }) =>
    apiGet<{
      leads: FleetLead[]
      count: number
    }>('/fleet-leads', { params }),

  // Get single lead
  getLead: (id: number) =>
    apiGet<FleetLead>(`/fleet-leads/${id}`),

  // Create new lead from scraped business
  createLead: (data: {
    business_id?: number
    company_name?: string  // or business_name - backend accepts both
    name?: string  // alias for company_name
    address?: string
    city?: string
    state?: string
    phone?: string
    website?: string
    category?: string
    estimated_vehicles?: number
    tier?: number
    source?: string
    latitude?: number
    longitude?: number
    hail_affected?: boolean
    hail_date?: string
    hail_size?: number
    hail_distance?: number
  }) =>
    apiPost<{ success: boolean; lead_id: number; message: string }>('/fleet-leads', data),

  // Update lead
  updateLead: (id: number, data: Partial<FleetLead>) =>
    apiPut<{ success: boolean; lead: FleetLead }>(`/fleet-leads/${id}`, data),

  // Delete lead
  deleteLead: (id: number) =>
    apiDelete<{ success: boolean }>(`/fleet-leads/${id}`),

  // Log activity/note
  logNote: (id: number, note: string) =>
    apiPost<{ success: boolean }>(`/fleet-leads/${id}/note`, { note }),

  // Get leads stats
  getStats: () =>
    apiGet<{
      by_status: Array<{ status: string; count: number; vehicles: number; value: number }>
      pipeline: { count: number; vehicles: number; value: number }
      won: { count: number; value: number }
      hail_affected: { count: number; vehicles: number }
      followups_due: number
      recent_activity: number
      by_city: Array<{ city: string; state: string; count: number; vehicles: number }>
    }>('/fleet-leads/stats'),

  // Get leads due for follow-up
  getFollowups: (days?: number) =>
    apiGet<{ leads: FleetLead[] }>('/fleet-leads/followups', { params: { days } }),

  // Bulk import from scraped businesses
  bulkImport: (businesses: Array<{
    id?: number
    name: string
    address?: string
    city: string
    state: string
    phone?: string
    category?: string
    estimated_vehicles?: number
    tier?: number
    source?: string
    latitude?: number
    longitude?: number
  }>) =>
    apiPost<{
      success: boolean
      created: number
      duplicates: number
      errors?: string[]
    }>('/fleet-leads/bulk', { businesses }),

  // Get leads for map display
  getLeadsMap: (params?: {
    status?: string
    city?: string
    state?: string
  }) =>
    apiGet<{
      leads: FleetLead[]
      count: number
    }>('/fleet-leads', { params: { ...params, limit: 500 } }),
}

// =============================================================================
// MAIN CRM LEADS INTEGRATION
// =============================================================================
// These functions connect Fleet Intelligence to the MAIN CRM leads system

export interface MainCrmLeadResult {
  success: boolean
  lead_id?: number
  temperature?: string
  message: string
  duplicate?: boolean
  error?: string
}

export interface BulkLeadResult {
  success: boolean
  created: number
  skipped: number
  created_ids: number[]
  errors: string[]
  message: string
}

// =============================================================================
// BATCH SCRAPING WITH PRESETS
// =============================================================================

export interface ScrapePreset {
  name: string
  description: string
  cities: Array<{ city: string; state: string }>
}

export interface BatchScrapeResult {
  success: boolean
  total_new_businesses: number
  total_new_vehicles: number
  results: Array<{
    city: string
    state: string
    new_businesses: number
    new_vehicles: number
    by_source: Record<string, number>
  }>
  errors?: string[]
}

export const batchScrapeApi = {
  // Get available scrape presets (Hail Alley, Texas, etc.)
  getPresets: () =>
    apiGet<{ presets: Record<string, ScrapePreset> }>('/fleet-locations/scrape-presets'),

  // Batch scrape cities
  batchScrape: (params: {
    cities: Array<{ city: string; state: string }>
    sources?: string[]
  }) =>
    apiPost<BatchScrapeResult>('/fleet-locations/batch-scrape', params),

  // Scrape using a preset
  scrapePreset: (presetKey: string, sources?: string[]) =>
    apiPost<BatchScrapeResult>('/fleet-locations/batch-scrape', {
      preset: presetKey,
      sources
    }),
}

// =============================================================================
// EMAIL TEMPLATES
// =============================================================================

export interface EmailTemplate {
  key: string
  name: string
  subject: string
  body: string
  follow_up_days: number
}

export interface GeneratedEmail {
  subject: string
  body: string
  template_name: string
  follow_up_days: number
}

export const emailTemplatesApi = {
  // List all templates
  listTemplates: () =>
    apiGet<{
      templates: Array<{
        key: string
        name: string
        subject_preview: string
        follow_up_days: number
      }>
    }>('/fleet-locations/email-templates'),

  // Get a specific template with variables filled
  getTemplate: (templateKey: string, variables?: Record<string, string>) =>
    apiGet<{ template: GeneratedEmail }>(`/fleet-locations/email-templates/${templateKey}`, {
      params: variables
    }),

  // Get best template for a business (auto-selects based on category)
  getTemplateForBusiness: (businessId: number, senderInfo?: {
    sender_name?: string
    sender_company?: string
    sender_phone?: string
    sender_email?: string
  }) =>
    apiGet<{
      template: GeneratedEmail
      template_key: string
    }>(`/fleet-locations/email-templates/for-business/${businessId}`, {
      params: senderInfo
    }),
}

// =============================================================================
// CALL SCRIPTS
// =============================================================================

export interface CallScript {
  key: string
  name: string
  category: string
  script: string
}

export const callScriptsApi = {
  // List all call scripts
  listScripts: () =>
    apiGet<{
      scripts: Array<{
        key: string
        name: string
        category: string
      }>
    }>('/fleet-locations/call-scripts'),

  // Get a specific script with variables filled
  getScript: (scriptKey: string, variables?: Record<string, string>) =>
    apiGet<{ script: CallScript }>(`/fleet-locations/call-scripts/${scriptKey}`, {
      params: variables
    }),

  // Get best script for a business (auto-selects based on category)
  getScriptForBusiness: (businessId: number, callerInfo?: {
    caller_name?: string
    caller_company?: string
  }) =>
    apiGet<{
      script: CallScript
      script_key: string
    }>(`/fleet-locations/call-scripts/for-business/${businessId}`, {
      params: callerInfo
    }),
}

// =============================================================================
// RECENT SIGNIFICANT STORMS
// =============================================================================

export interface SignificantStorm {
  date: string
  total_events: number
  max_hail_size: number
  states_affected: string[]
  major_cities: string[]
  total_area_sq_miles: number
  display_name: string
}

export interface StormSummary {
  date: string
  events: Array<{
    id: number
    event_name: string
    city?: string
    state?: string
    max_hail_size: number
    area_sq_miles?: number
    center_lat: number
    center_lon: number
    has_swath: boolean
  }>
  stats: {
    total_events: number
    max_size: number
    total_area: number
    states: string[]
    cities: string[]
  }
}

export const recentStormsApi = {
  // Get recent significant storms (1"+ hail from last 90 days)
  getRecentStorms: (params?: {
    days?: number
    min_size?: number
    limit?: number
  }) =>
    apiGet<{
      storms: SignificantStorm[]
      count: number
      days_back: number
      min_size: number
    }>('/hail-events/recent-significant', { params }),

  // Get detailed summary for a specific storm date
  getStormSummary: (stormDate: string) =>
    apiGet<StormSummary>(`/hail-events/storm-summary/${stormDate}`),
}

// =============================================================================
// FLEET LEAD CONVERSION REPORTS
// =============================================================================

export interface FleetLeadReports {
  funnel: Array<{
    status: string
    count: number
    percentage: number
  }>
  conversion_stats: {
    total_leads: number
    converted: number
    lost: number
    active: number
    conversion_rate: number
    loss_rate: number
  }
  hail_comparison: Array<{
    category: string
    total: number
    converted: number
    lost: number
    conversion_rate: number
    avg_follow_ups: number
  }>
  by_temperature: Array<{
    temperature: string
    total: number
    converted: number
    conversion_rate: number
  }>
  by_city: Array<{
    city: string
    state: string
    total_leads: number
    converted: number
    conversion_rate: number
  }>
  weekly_trends: Array<{
    week: string
    new_leads: number
    converted: number
    in_progress: number
  }>
  top_deals: Array<{
    id: number
    company_name: string
    city: string
    state: string
    temperature: string
    created_at: string
    converted_at: string
    notes?: string
  }>
  lost_reasons: Array<{
    reason: string
    count: number
  }>
  response_time: {
    avg_days: number
    min_days: number
    max_days: number
  }
}

export const fleetReportsApi = {
  // Get comprehensive fleet lead reports
  getReports: (params?: {
    start_date?: string
    end_date?: string
  }) =>
    apiGet<{
      success: boolean
      reports: FleetLeadReports
      filters: {
        start_date?: string
        end_date?: string
      }
    }>('/leads/reports/fleet', { params }),
}

// =============================================================================
// MAIN CRM LEADS INTEGRATION
// =============================================================================
// These functions connect Fleet Intelligence to the MAIN CRM leads system

export const mainCrmLeadsApi = {
  /**
   * Add a single business to the main CRM as a lead.
   * Used when clicking "Add to CRM" on a business marker.
   */
  addBusinessToLeads: (business: {
    name: string
    address?: string
    city: string
    state: string
    zip?: string
    phone?: string
    category?: string
    estimated_vehicles?: number
    tier?: number
    latitude?: number
    longitude?: number
    hail_affected?: boolean
    hail_date?: string
    hail_size?: number
    hail_distance?: number
  }) =>
    apiPost<MainCrmLeadResult>('/leads/from-fleet-discovery', {
      company_name: business.name,
      address: business.address,
      city: business.city,
      state: business.state,
      zip: business.zip,
      phone: business.phone,
      category: business.category,
      estimated_vehicles: business.estimated_vehicles,
      tier: business.tier,
      latitude: business.latitude,
      longitude: business.longitude,
      hail_affected: business.hail_affected,
      hail_date: business.hail_date,
      hail_size: business.hail_size,
      hail_distance: business.hail_distance || 0,
    }),

  /**
   * Bulk add businesses from hail swath to main CRM as HOT leads.
   * Used for "Add All Affected Businesses" button.
   */
  bulkAddFromHailSwath: (params: {
    businesses: Array<{
      name: string
      address?: string
      city: string
      state: string
      phone?: string
      category?: string
      estimated_vehicles?: number
      tier?: number
      latitude?: number
      longitude?: number
    }>
    hail_date: string
    hail_size: number
  }) =>
    apiPost<BulkLeadResult>('/leads/from-fleet-discovery/bulk', {
      businesses: params.businesses.map(b => ({
        company_name: b.name,
        name: b.name,
        address: b.address,
        city: b.city,
        state: b.state,
        phone: b.phone,
        category: b.category,
        estimated_vehicles: b.estimated_vehicles,
        tier: b.tier,
        latitude: b.latitude,
        longitude: b.longitude,
      })),
      hail_date: params.hail_date,
      hail_size: params.hail_size,
    }),
}
