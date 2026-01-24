/**
 * Weather & Hail Detection API
 * =============================
 * Comprehensive API client for hail events, storm tracking, ML predictions.
 */

import api from './client'

// =============================================================================
// TYPES
// =============================================================================

// Hail Event Types
export interface HailEvent {
  id: number
  event_name: string
  event_date: string
  location?: string
  location_name?: string
  city?: string
  state?: string
  latitude?: number
  longitude?: number
  severity: 'MINOR' | 'MODERATE' | 'SEVERE' | 'CATASTROPHIC'
  status: 'ACTIVE' | 'CLOSED'
  hail_size_inches?: number
  max_hail_size?: number
  affected_zip_codes?: string[]
  affected_area_sq_miles?: number
  estimated_radius_miles?: number
  insurance_storm_code?: string
  noaa_event_id?: string
  estimated_vehicles?: number
  estimated_vehicles_affected?: number
  potential_revenue?: number
  swath_geojson?: string
  severity_info?: SeverityInfo
  stats?: StormStats
  jobs_created?: number
  created_at?: string
  updated_at?: string
}

export interface SeverityInfo {
  name: string
  hail_size: string
  hail_size_range: [number, number]
  damage_level: string
  avg_revenue_per_vehicle: number
  avg_repair_hours: number
  glass_damage_likely: boolean
  color: string
}

export interface StormStats {
  storm_id: number
  event_name: string
  estimated_vehicles: number
  market_opportunity: Record<string, { vehicles: number; revenue: number }>
  jobs_created: number
  leads_generated: number
}

export interface OverallStats {
  period_days: number
  total_storms: number
  active_storms: number
  total_estimated_vehicles: number
  by_severity: Record<string, { count: number; estimated_vehicles: number }>
  by_state: Record<string, { count: number; estimated_vehicles: number }>
}

export interface StormROI {
  storm_id: number
  event_name: string
  event_date: string
  severity: string
  estimated_vehicles: number
  jobs_created: number
  customers_acquired: number
  leads_generated: number
  lead_conversion_rate: number
  market_penetration: number
  total_revenue: number
  labor_revenue: number
  avg_revenue_per_job: number
  jobs_by_status: Record<string, number>
  jobs_by_confidence: Record<string, number>
}

export interface MarketOpportunity {
  vehicles_in_area: number
  capture_rate: number
  captured_vehicles: number
  avg_revenue_per_vehicle: number
  total_revenue_potential: number
  total_repair_hours: number
  avg_repair_hours_per_vehicle: number
  techs_needed_30_days: number
}

export interface HailEventInput {
  event_name: string
  event_date: string
  location: string
  city: string
  state: string
  severity: 'MINOR' | 'MODERATE' | 'SEVERE' | 'CATASTROPHIC'
  hail_size_inches?: number
  affected_zip_codes?: string[]
  estimated_radius_miles?: number
  insurance_storm_code?: string
  noaa_event_id?: string
  estimated_vehicles_affected?: number
  notes?: string
}

// Storm Cell Types
export interface StormCell {
  id?: number
  cell_id: number
  lat: number
  lon: number
  timestamp: string
  max_reflectivity: number
  mesh_mm: number
  mesh_inches: number
  mesh?: number
  max_hail_size?: number
  vil?: number
  echo_tops?: number
  velocity_kmh: number
  direction_deg: number
  motion_speed?: number
  motion_direction?: number
  stage: string
  lifecycle_stage?: string
  age_minutes?: number
  track_duration_minutes?: number
}

export interface CellTrack {
  cell_id: number
  start_time: string
  end_time: string
  duration_minutes: number
  max_mesh_mm: number
  max_mesh_inches: number
  max_reflectivity: number
  avg_velocity_kmh: number
  track_length_km: number
  lifecycle_stages: string[]
  position_count: number
  positions?: StormCell[]
}

export interface SwathFeature {
  type: 'Feature'
  geometry: {
    type: 'Polygon'
    coordinates: number[][][]
  }
  properties: {
    cell_id: number
    event_id?: number
    event_name?: string
    severity?: string
    max_mesh_mm: number
    max_hail_size?: number
    duration_minutes: number
    track_length_km: number
    area_sq_miles?: number
  }
}

export interface SwathCollection {
  type: 'FeatureCollection'
  features: SwathFeature[]
  count: number
}

// Storm Monitor Types
export interface MonitorStatus {
  running: boolean
  initialized: boolean
  radars?: string[]
  scans_processed?: number
  alerts_generated?: number
  last_scan?: string
  active_alerts?: number
  error?: string
}

export interface MonitorConfig {
  radar_ids: string[]
  scan_interval_seconds: number
  lookback_minutes: number
  min_reflectivity_dbz: number
  min_mesh_mm: number
  min_pdr_score: number
  coverage_region?: string
  coverage_regions?: string[]
  coverage_center_lat?: number
  coverage_center_lon?: number
  coverage_radius_miles?: number
  auto_select_radars?: boolean
  enable_sound?: boolean
  enable_console?: boolean
  sms_enabled?: boolean
  email_enabled?: boolean
  database_enabled?: boolean
}

export interface RadarSite {
  site_code: string
  name: string
  state: string
  lat?: number
  lon?: number
}

// ML Types
export interface HailClassification {
  lat: number
  lon: number
  timestamp: string
  hail_detected: boolean
  hail_probability: number
  estimated_size_mm: number
  estimated_size_inches: number
  severity: string
  pdr_score: number
  confidence: number
}

export interface StormForecast {
  forecast: {
    '15min': ForecastHorizon
    '30min': ForecastHorizon
    '60min': ForecastHorizon
    '120min': ForecastHorizon
  }
  horizons: string[]
  timestamp: string
}

export interface ForecastHorizon {
  hail_probability: number
  estimated_size: number
  confidence: number
}

export interface SizeEstimate {
  estimated_size_inches: number
  category: string
  category_id: number
  size_range: string
  confidence: number
  severity: string
}

export interface MLStatus {
  classifier: { available: boolean; type: string; model_info?: unknown }
  forecaster: { available: boolean; type: string; is_fitted: boolean }
  size_estimator: { available: boolean; type: string; is_fitted: boolean }
  ml_model: { available: boolean; type: string; is_fitted: boolean }
}

export interface StormAlert {
  id?: number
  level: string
  event_name: string
  location?: string
  pdr_score?: number
  timestamp?: string
}

// =============================================================================
// HAIL EVENTS API
// =============================================================================

export const hailEventsApi = {
  // List & Search
  list: (params?: {
    days?: number
    severity?: string
    status?: string
    limit?: number
  }) =>
    api.get<{ events: HailEvent[]; count: number; stats: OverallStats }>(
      '/api/hail-events',
      { params }
    ),

  search: (params: {
    state?: string
    city?: string
    severity?: string
    status?: string
    zip_code?: string
    start_date?: string
    end_date?: string
    limit?: number
  }) =>
    api.get<{ events: HailEvent[]; count: number }>(
      '/api/hail-events/search',
      { params }
    ),

  getActive: (days?: number) =>
    api.get<{ events: HailEvent[]; count: number }>(
      '/api/hail-events/active',
      { params: { days } }
    ),

  getByZip: (zipCode: string) =>
    api.get<{ events: HailEvent[]; count: number; zip_code: string }>(
      `/api/hail-events/by-zip/${zipCode}`
    ),

  getBySeverity: (severity: string, days?: number) =>
    api.get<{ events: HailEvent[]; count: number; severity: string }>(
      `/api/hail-events/by-severity/${severity}`,
      { params: { days } }
    ),

  getNearby: (lat: number, lon: number, radius?: number) =>
    api.get<{ events: HailEvent[]; count: number }>(
      '/api/hail-events/nearby',
      { params: { lat, lon, radius } }
    ),

  // CRUD
  get: (id: number) => api.get<HailEvent>(`/api/hail-events/${id}`),

  create: (data: HailEventInput) =>
    api.post<{ id: number; storm: HailEvent }>('/api/hail-events', data),

  update: (id: number, data: Partial<HailEventInput>) =>
    api.put<HailEvent>(`/api/hail-events/${id}`, data),

  close: (id: number, notes?: string) =>
    api.delete<{ success: boolean; status: string }>(
      `/api/hail-events/${id}`,
      { data: { notes } }
    ),

  reopen: (id: number) =>
    api.post<{ success: boolean; status: string }>(
      `/api/hail-events/${id}/reopen`
    ),

  // Statistics & ROI
  getStats: (id: number) => api.get<StormStats>(`/api/hail-events/${id}/stats`),

  getOverallStats: (days?: number) =>
    api.get<OverallStats>('/api/hail-events/stats/overall', { params: { days } }),

  getROI: (id: number) => api.get<StormROI>(`/api/hail-events/${id}/roi`),

  getPerformance: (params?: {
    start_date?: string
    end_date?: string
    min_jobs?: number
  }) =>
    api.get<{ storms: StormROI[]; count: number }>(
      '/api/hail-events/performance',
      { params }
    ),

  compare: (stormIds: number[]) =>
    api.post<{ storms: StormROI[]; totals: Record<string, number>; averages: Record<string, number> }>(
      '/api/hail-events/compare',
      { storm_ids: stormIds }
    ),

  // Market Opportunity
  estimateMarketOpportunity: (data: {
    vehicles_affected: number
    severity: string
    capture_rate?: number
  }) =>
    api.post<MarketOpportunity>('/api/hail-events/market-opportunity', data),

  // Reports
  getReport: (id: number, format?: 'json' | 'text') =>
    api.get<{ storm: HailEvent; stats: StormStats; roi: StormROI }>(
      `/api/hail-events/${id}/report`,
      { params: { format } }
    ),

  getPerformanceReport: (id: number, format?: 'json' | 'text') =>
    api.get<{ storm: HailEvent; performance: StormROI }>(
      `/api/hail-events/${id}/performance-report`,
      { params: { format } }
    ),

  getSummaryReport: (days?: number, format?: 'json' | 'text') =>
    api.get<{ period_days: number; stats: OverallStats; active_storms: HailEvent[] }>(
      '/api/hail-events/summary-report',
      { params: { days, format } }
    ),

  getMultiStormReport: (days?: number, format?: 'json' | 'text') =>
    api.get<{ period_days: number; storms: StormROI[]; stats: OverallStats }>(
      '/api/hail-events/multi-storm-report',
      { params: { days, format } }
    ),

  // Job-Storm Linking
  linkJob: (stormId: number, jobId: number, confidence?: string, notes?: string) =>
    api.post<{ success: boolean; storm_id: number; job_id: number }>(
      `/api/hail-events/${stormId}/link-job`,
      { job_id: jobId, confidence, notes }
    ),

  unlinkJob: (stormId: number, jobId: number) =>
    api.delete<{ success: boolean }>(
      `/api/hail-events/${stormId}/unlink-job/${jobId}`
    ),

  getStormJobs: (stormId: number) =>
    api.get<{ storm_id: number; jobs: unknown[]; count: number }>(
      `/api/hail-events/${stormId}/jobs`
    ),

  getJobStorm: (jobId: number) =>
    api.get<{ job_id: number; storm: HailEvent | null; link: unknown }>(
      `/api/jobs/${jobId}/storm`
    ),

  findMatchingStorm: (jobId: number, zipCode: string, damageDate: string, daysRange?: number) =>
    api.post<{ job_id: number; matching_storm: HailEvent | null }>(
      `/api/jobs/${jobId}/find-storm`,
      { zip_code: zipCode, damage_date: damageDate, days_range: daysRange }
    ),

  // Severity
  getSeverityInfo: (severity: string) =>
    api.get<{ severity: string; info: SeverityInfo }>(
      `/api/hail-events/severity-info/${severity}`
    ),

  getAllSeverityLevels: () =>
    api.get<{ levels: Record<string, SeverityInfo> }>(
      '/api/hail-events/severity-levels'
    ),

  classifySeverity: (hailSizeInches: number) =>
    api.post<{ hail_size_inches: number; severity: string; info: SeverityInfo }>(
      '/api/hail-events/classify-severity',
      { hail_size_inches: hailSizeInches }
    ),
}

// =============================================================================
// STORM CELL TRACKING API
// =============================================================================

export const stormCellsApi = {
  // Tracks
  getTracks: (minDuration?: number) =>
    api.get<{ tracks: CellTrack[]; count: number }>('/api/storm-cells', {
      params: { min_duration: minDuration },
    }),

  getTrack: (cellId: number) =>
    api.get<CellTrack>(`/api/storm-cells/${cellId}`),

  getActiveCells: () =>
    api.get<{ active_cells: StormCell[]; count: number }>(
      '/api/storm-cells/active'
    ),

  // Swaths
  getCellSwath: (cellId: number, bufferKm?: number) =>
    api.get<SwathFeature>(`/api/storm-cells/${cellId}/swath`, {
      params: { buffer_km: bufferKm },
    }),

  getAllSwaths: (minDuration?: number, bufferKm?: number) =>
    api.get<SwathCollection>('/api/storm-cells/swaths', {
      params: { min_duration: minDuration, buffer_km: bufferKm },
    }),

  // Forecasting
  getCellForecast: (cellId: number, minutes?: number) =>
    api.get<{
      cell_id: number
      forecast_minutes: number
      positions: Array<{ lat: number; lon: number; timestamp: string }>
    }>(`/api/storm-cells/${cellId}/forecast`, { params: { minutes } }),

  // Statistics
  getStats: () => api.get<Record<string, unknown>>('/api/storm-cells/stats'),

  // Processing
  processRadarScan: (detections: unknown[], scanTime?: string) =>
    api.post<{ cells: StormCell[]; count: number; scan_time: string }>(
      '/api/storm-cells/process',
      { detections, scan_time: scanTime }
    ),

  simulateStorm: (params: {
    start_lat?: number
    start_lon?: number
    direction?: number
    speed?: number
    duration?: number
    peak_reflectivity?: number
  }) =>
    api.post<{
      cells_created: number
      tracks: number
      swaths: SwathCollection
      statistics: Record<string, unknown>
    }>('/api/storm-cells/simulate', params),

  reset: () => api.post<{ success: boolean }>('/api/storm-cells/reset'),
}

// =============================================================================
// STORM MONITOR API
// =============================================================================

export const stormMonitorApi = {
  getStatus: () => api.get<MonitorStatus>('/api/storm-monitor/status'),

  start: (config?: Partial<MonitorConfig>) =>
    api.post<{ success: boolean; message: string; radars?: string[] }>(
      '/api/storm-monitor/start',
      config
    ),

  stop: () =>
    api.post<{ success: boolean; message: string }>('/api/storm-monitor/stop'),

  getConfig: () => api.get<MonitorConfig>('/api/storm-monitor/config'),

  updateConfig: (config: Partial<MonitorConfig>) =>
    api.put<{ success: boolean; message: string; config: MonitorConfig }>(
      '/api/storm-monitor/config',
      config
    ),

  getAvailableRadars: () =>
    api.get<{ radars: RadarSite[]; count: number }>('/api/storm-monitor/radars'),

  getAvailableRegions: () =>
    api.get<{ regions: string[] }>('/api/storm-monitor/regions'),

  getAlerts: () =>
    api.get<{ alerts: StormAlert[]; count: number }>('/api/storm-monitor/alerts'),

  getAlertStats: () => api.get<Record<string, unknown>>('/api/storm-monitor/alerts/stats'),
}

// =============================================================================
// ML MODELS API
// =============================================================================

export const mlApi = {
  // Classification
  classify: (data: {
    lat: number
    lon: number
    timestamp?: string
    radar_data?: Record<string, unknown>
    environmental_data?: Record<string, unknown>
    cell_data?: Record<string, unknown>
  }) => api.post<HailClassification>('/api/ml/classify', data),

  classifyBatch: (events: Array<{
    lat: number
    lon: number
    timestamp?: string
    radar_data?: Record<string, unknown>
    environmental_data?: Record<string, unknown>
    cell_data?: Record<string, unknown>
  }>) =>
    api.post<{ results: HailClassification[]; count: number; success_count: number }>(
      '/api/ml/classify-batch',
      { events }
    ),

  // Model Info
  getModelInfo: () => api.get<Record<string, unknown>>('/api/ml/model-info'),

  getFeatureImportance: () =>
    api.get<{ features: Array<{ name: string; importance: number }> }>('/api/ml/feature-importance'),

  // Forecasting
  forecast: (radarTrend: unknown[], environment: Record<string, unknown>) =>
    api.post<StormForecast>('/api/ml/forecast', {
      radar_trend: radarTrend,
      environment,
    }),

  // Size Estimation
  estimateSize: (data: {
    image_base64?: string
    features?: number[]
    image_stats?: Record<string, unknown>
  }) => api.post<SizeEstimate>('/api/ml/estimate-size', data),

  // Raw Prediction
  predict: (data: {
    radar_data?: Record<string, unknown>
    environmental_data?: Record<string, unknown>
    cell_data?: Record<string, unknown>
  }) =>
    api.post<{
      hail_detected: boolean
      probability: number
      size_mm: number
      size_inches: number
      severity: string
      confidence: number
    }>('/api/ml/predict', data),

  extractFeatures: (data: {
    radar_data?: Record<string, unknown>
    environmental_data?: Record<string, unknown>
    cell_data?: Record<string, unknown>
  }) =>
    api.post<{ features: number[]; feature_names: string[]; feature_count: number }>(
      '/api/ml/extract-features',
      data
    ),

  // Status
  getStatus: () => api.get<MLStatus>('/api/ml/status'),

  // Reference
  getSizeReference: () =>
    api.get<{
      sizes: Array<{
        name: string
        inches: number
        mm: number
        damage: string
      }>
    }>('/api/ml/size-reference'),
}

// =============================================================================
// LEGACY EXPORTS (for backward compatibility)
// =============================================================================

export const weatherApi = {
  // Hail Events (legacy names)
  getHailEvents: hailEventsApi.list,
  getHailEvent: hailEventsApi.get,
  getActiveHailEvents: hailEventsApi.getActive,
  getNearbyHailEvents: hailEventsApi.getNearby,

  // Storm Cells
  getStormCells: stormCellsApi.getActiveCells,
  getStormTracks: stormCellsApi.getTracks,
  getStormSwaths: stormCellsApi.getAllSwaths,

  // Monitor
  getMonitorStatus: stormMonitorApi.getStatus,
  startMonitor: stormMonitorApi.start,
  stopMonitor: stormMonitorApi.stop,

  // ML
  classifyHail: mlApi.classify,
  forecastStorm: mlApi.forecast,
  estimateHailSize: mlApi.estimateSize,
}

export default {
  hailEvents: hailEventsApi,
  stormCells: stormCellsApi,
  monitor: stormMonitorApi,
  ml: mlApi,
  weather: weatherApi,
}
