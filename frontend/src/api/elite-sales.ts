/**
 * Elite Sales API Client
 * Professional-grade field sales endpoints for HailTracker Pro
 */

import { apiGet, apiPost, apiPut, apiDelete } from './client';

// =============================================================================
// TYPES
// =============================================================================

export interface Salesperson {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  employee_id: string;
  status: 'ACTIVE' | 'INACTIVE';
  hire_date: string;
  commission_rate: number;
  created_at: string;
}

export interface FieldLead {
  id: number;
  salesperson_id: number;
  grid_cell_id?: number;
  latitude: number;
  longitude: number;
  address: string;
  customer_name: string;
  phone?: string;
  email?: string;
  vehicle_info?: {
    year?: number;
    make?: string;
    model?: string;
  };
  damage_description?: string;
  lead_quality: 'HOT' | 'WARM' | 'COLD';
  notes?: string;
  photo_urls?: string[];
  synced_to_crm: boolean;
  crm_lead_id?: number;
  created_at: string;
}

export interface RouteStop {
  stop_number: number;
  address: string;
  latitude: number;
  longitude: number;
  estimated_time: string;
  property_data?: PropertyData;
  do_not_knock: boolean;
  dnk_reason?: string;
  status?: 'pending' | 'visited' | 'skipped';
}

export interface CanvassingRoute {
  salesperson_id: number;
  grid_cell_id: number;
  start_time: string;
  estimated_completion: string;
  total_stops: number;
  estimated_drive_time: number;
  estimated_knock_time: number;
  total_distance_miles: number;
  stops: RouteStop[];
  optimization_score: number;
}

export interface PropertyData {
  owner_name?: string;
  property_value?: number;
  year_built?: number;
  bedrooms?: number;
  bathrooms?: number;
  lot_size?: number;
  vehicles_registered?: Array<{
    year: number;
    make: string;
    model: string;
  }>;
  estimated_income_bracket?: string;
  time_at_address?: string;
}

export interface GridCell {
  id: number;
  swath_id: number;
  cell_index: number;
  center_lat: number;
  center_lon: number;
  status: 'UNASSIGNED' | 'ASSIGNED' | 'COMPLETED';
  assigned_to?: number;
  homes_count: number;
  knocked_count: number;
  leads_count: number;
}

export interface CompetitorActivity {
  id: number;
  salesperson_id: number;
  competitor_name: string;
  location_lat: number;
  location_lon: number;
  activity_type: 'CANVASSING' | 'TRUCK_PARKED' | 'WORKING_JOB' | 'SIGN_PLACED';
  notes?: string;
  photo_url?: string;
  spotted_at: string;
}

export interface DNKEntry {
  id: number;
  address: string;
  latitude: number;
  longitude: number;
  reason: 'NO_SOLICITING' | 'REQUESTED' | 'AGGRESSIVE' | 'COMPETITOR';
  notes?: string;
  added_by?: number;
  added_at: string;
}

export interface Achievement {
  id: number;
  salesperson_id: number;
  achievement_type: string;
  achievement_data?: Record<string, any>;
  earned_at: string;
}

export interface LeaderboardEntry {
  id: number;
  first_name: string;
  last_name: string;
  leads_today: number;
  hot_leads_today: number;
  points?: number;
}

export interface ObjectionEntry {
  id: number;
  salesperson_id: number;
  objection_type: string;
  response_used: string;
  outcome: 'CONVERTED' | 'FOLLOW_UP' | 'LOST';
  logged_at: string;
}

export interface SalesScript {
  situation: string;
  script: {
    opening?: string;
    key_points?: string[];
    response?: string;
    tips?: string[];
  };
}

export interface InstantEstimate {
  vehicle_info: {
    year: number;
    make: string;
    model: string;
  };
  damage_assessment: {
    panel_count: number;
    severity: 'LIGHT' | 'MODERATE' | 'HEAVY';
    estimated_dents: number;
  };
  estimate_range: {
    low: number;
    high: number;
  };
  recommended_price: number;
}

// =============================================================================
// SALESPEOPLE API
// =============================================================================

export const getSalespeople = (status?: string) =>
  apiGet<{ salespeople: Salesperson[]; count: number }>(
    `/api/elite/salespeople${status ? `?status=${status}` : ''}`
  );

export const createSalesperson = (data: Partial<Salesperson>) =>
  apiPost<{ success: boolean; salesperson_id: number }>('/api/elite/salespeople', data);

export const getSalesperson = (id: number) =>
  apiGet<{
    salesperson: Salesperson;
    stats: { leads_today: number; hot_leads_today: number; total_points: number; achievements_count: number };
    achievements: Achievement[];
  }>(`/api/elite/salespeople/${id}`);

export const updateSalesperson = (id: number, data: Partial<Salesperson>) =>
  apiPut<{ success: boolean }>(`/api/elite/salespeople/${id}`, data);

// =============================================================================
// ROUTE OPTIMIZATION API
// =============================================================================

export const optimizeRoute = (data: {
  salesperson_id: number;
  grid_cell_id?: number;
  start_time?: string;
  target_homes?: number;
}) =>
  apiPost<{ success: boolean; route: CanvassingRoute }>('/api/elite/routes/optimize', data);

export const getPropertyData = (address: string) =>
  apiGet<{ address: string; property_data: PropertyData }>(
    `/api/elite/routes/property/${encodeURIComponent(address)}`
  );

// =============================================================================
// GRID CELLS API
// =============================================================================

export const getGridCells = (params?: {
  swath_id?: number;
  status?: string;
  assigned_to?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.swath_id) searchParams.append('swath_id', String(params.swath_id));
  if (params?.status) searchParams.append('status', params.status);
  if (params?.assigned_to) searchParams.append('assigned_to', String(params.assigned_to));
  const query = searchParams.toString();
  return apiGet<{ grid_cells: GridCell[]; count: number }>(
    `/api/elite/grid-cells${query ? `?${query}` : ''}`
  );
};

export const assignGridCell = (cellId: number, salespersonId: number) =>
  apiPut<{ success: boolean }>(`/api/elite/grid-cells/${cellId}/assign`, {
    salesperson_id: salespersonId,
  });

// =============================================================================
// FIELD LEADS API
// =============================================================================

export const getFieldLeads = (params?: {
  salesperson_id?: number;
  quality?: string;
  date_from?: string;
  date_to?: string;
  synced?: boolean;
  limit?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.salesperson_id) searchParams.append('salesperson_id', String(params.salesperson_id));
  if (params?.quality) searchParams.append('quality', params.quality);
  if (params?.date_from) searchParams.append('date_from', params.date_from);
  if (params?.date_to) searchParams.append('date_to', params.date_to);
  if (params?.synced !== undefined) searchParams.append('synced', String(params.synced));
  if (params?.limit) searchParams.append('limit', String(params.limit));
  const query = searchParams.toString();
  return apiGet<{ leads: FieldLead[]; count: number }>(
    `/api/elite/leads${query ? `?${query}` : ''}`
  );
};

export const createFieldLead = (data: {
  salesperson_id: number;
  latitude: number;
  longitude: number;
  address: string;
  customer_name: string;
  phone?: string;
  email?: string;
  vehicle_info?: Record<string, any>;
  damage_description?: string;
  lead_quality?: string;
  notes?: string;
  photo_urls?: string[];
  grid_cell_id?: number;
}) =>
  apiPost<{ success: boolean; lead_id: number }>('/api/elite/leads', data);

export const getFieldLead = (id: number) =>
  apiGet<FieldLead>(`/api/elite/leads/${id}`);

export const updateFieldLead = (id: number, data: Partial<FieldLead>) =>
  apiPut<{ success: boolean }>(`/api/elite/leads/${id}`, data);

export const syncLeadToCRM = (leadId: number) =>
  apiPost<{ success: boolean; crm_lead_id: number }>(`/api/elite/leads/${leadId}/sync`, {});

export const bulkSyncLeads = (leadIds: number[]) =>
  apiPost<{
    results: Array<{ field_lead_id: number; crm_lead_id: number | null; success: boolean }>;
    synced: number;
    failed: number;
  }>('/api/elite/leads/bulk-sync', { lead_ids: leadIds });

// =============================================================================
// COMPETITOR INTELLIGENCE API
// =============================================================================

export const getCompetitorActivity = (params?: {
  days?: number;
  competitor?: string;
  type?: string;
  limit?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.days) searchParams.append('days', String(params.days));
  if (params?.competitor) searchParams.append('competitor', params.competitor);
  if (params?.type) searchParams.append('type', params.type);
  if (params?.limit) searchParams.append('limit', String(params.limit));
  const query = searchParams.toString();
  return apiGet<{ activity: CompetitorActivity[]; count: number; period_days: number }>(
    `/api/elite/competitors${query ? `?${query}` : ''}`
  );
};

export const logCompetitorActivity = (data: {
  salesperson_id: number;
  competitor_name: string;
  location_lat: number;
  location_lon: number;
  activity_type: string;
  notes?: string;
  photo_url?: string;
}) =>
  apiPost<{ success: boolean; activity_id: number }>('/api/elite/competitors', data);

export const getCompetitorHeatmap = (swathId?: number, days?: number) => {
  const searchParams = new URLSearchParams();
  if (swathId) searchParams.append('swath_id', String(swathId));
  if (days) searchParams.append('days', String(days));
  const query = searchParams.toString();
  return apiGet<Record<string, any>>(`/api/elite/competitors/heatmap${query ? `?${query}` : ''}`);
};

export const getCompetitorSummary = (days?: number) =>
  apiGet<{
    competitors: Array<{
      competitor_name: string;
      total_sightings: number;
      active_days: number;
      last_seen: string;
    }>;
    period_days: number;
  }>(`/api/elite/competitors/summary${days ? `?days=${days}` : ''}`);

// =============================================================================
// DO NOT KNOCK API
// =============================================================================

export const getDNKList = (limit?: number, reason?: string) => {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.append('limit', String(limit));
  if (reason) searchParams.append('reason', reason);
  const query = searchParams.toString();
  return apiGet<{ dnk_list: DNKEntry[]; count: number }>(
    `/api/elite/dnk${query ? `?${query}` : ''}`
  );
};

export const addDNK = (data: {
  address: string;
  latitude: number;
  longitude: number;
  reason: string;
  notes?: string;
  salesperson_id?: number;
}) =>
  apiPost<{ success: boolean; dnk_id: number }>('/api/elite/dnk', data);

export const checkDNK = (lat: number, lon: number, radius?: number) => {
  const searchParams = new URLSearchParams();
  searchParams.append('lat', String(lat));
  searchParams.append('lon', String(lon));
  if (radius) searchParams.append('radius', String(radius));
  return apiGet<{ is_dnk: boolean; dnk_entry: DNKEntry | null }>(
    `/api/elite/dnk/check?${searchParams.toString()}`
  );
};

export const removeDNK = (id: number) =>
  apiDelete<{ success: boolean }>(`/api/elite/dnk/${id}`);

// =============================================================================
// SCRIPTS & OBJECTIONS API
// =============================================================================

export const getScript = (situation: string, propertyData?: Record<string, any>) => {
  const searchParams = new URLSearchParams();
  if (propertyData?.owner_name) searchParams.append('owner_name', propertyData.owner_name);
  if (propertyData?.vehicle_year) searchParams.append('vehicle_year', String(propertyData.vehicle_year));
  if (propertyData?.vehicle_make) searchParams.append('vehicle_make', propertyData.vehicle_make);
  if (propertyData?.vehicle_model) searchParams.append('vehicle_model', propertyData.vehicle_model);
  const query = searchParams.toString();
  return apiGet<SalesScript>(`/api/elite/scripts/${situation}${query ? `?${query}` : ''}`);
};

export const getAllScripts = () =>
  apiGet<{ scripts: Record<string, SalesScript>; count: number }>('/api/elite/scripts');

export const getObjections = (params?: {
  salesperson_id?: number;
  type?: string;
  outcome?: string;
  days?: number;
  limit?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params?.salesperson_id) searchParams.append('salesperson_id', String(params.salesperson_id));
  if (params?.type) searchParams.append('type', params.type);
  if (params?.outcome) searchParams.append('outcome', params.outcome);
  if (params?.days) searchParams.append('days', String(params.days));
  if (params?.limit) searchParams.append('limit', String(params.limit));
  const query = searchParams.toString();
  return apiGet<{ objections: ObjectionEntry[]; count: number; period_days: number }>(
    `/api/elite/objections${query ? `?${query}` : ''}`
  );
};

export const logObjection = (data: {
  salesperson_id: number;
  objection_type: string;
  response_used: string;
  outcome: string;
}) =>
  apiPost<{ success: boolean; objection_id: number }>('/api/elite/objections', data);

export const getObjectionAnalytics = (days?: number) =>
  apiGet<Record<string, any>>(`/api/elite/objections/analytics${days ? `?days=${days}` : ''}`);

// =============================================================================
// ESTIMATES & CONTRACTS API
// =============================================================================

export const generateInstantEstimate = (data: {
  photos?: string[];
  vehicle_info: {
    year: number;
    make: string;
    model: string;
  };
}) =>
  apiPost<{ success: boolean; estimate: InstantEstimate }>('/api/elite/estimates/instant', data);

export const createFieldContract = (data: {
  lead_id: number;
  estimate?: Record<string, any>;
  customer_email: string;
}) =>
  apiPost<{ success: boolean; contract_url: string }>('/api/elite/contracts', data);

// =============================================================================
// GAMIFICATION API
// =============================================================================

export const getAchievements = (salespersonId: number) =>
  apiGet<{ achievements: Achievement[]; total_points: number; count: number }>(
    `/api/elite/achievements/${salespersonId}`
  );

export const awardAchievement = (data: {
  salesperson_id: number;
  achievement_type: string;
  achievement_data?: Record<string, any>;
}) =>
  apiPost<{ success: boolean; achievement_id: number }>('/api/elite/achievements', data);

export const getLeaderboard = (period?: 'TODAY' | 'THIS_WEEK' | 'THIS_MONTH') =>
  apiGet<{ leaderboard: LeaderboardEntry[]; period: string; updated_at: string }>(
    `/api/elite/leaderboard${period ? `?period=${period}` : ''}`
  );

export const getLeaderboardStats = () =>
  apiGet<{
    today: { leads: number; hot_leads: number };
    this_week: { leads: number; hot_leads: number };
    this_month: { leads: number; hot_leads: number };
  }>('/api/elite/leaderboard/stats');

// =============================================================================
// MOBILE API
// =============================================================================

export const mobileCheckin = (data: {
  salesperson_id: number;
  latitude?: number;
  longitude?: number;
  battery_level?: number;
  app_version?: string;
}) =>
  apiPost<{
    success: boolean;
    checkin: Record<string, any>;
    stats: { leads_today: number; hot_leads: number };
    nearby_dnk: DNKEntry[];
    nearby_competitors: CompetitorActivity[];
    server_time: string;
  }>('/api/elite/mobile/checkin', data);

export const mobileQuickLead = (data: {
  salesperson_id: number;
  latitude?: number;
  longitude?: number;
  address?: string;
  customer_name?: string;
  phone?: string;
  lead_quality?: string;
  notes?: string;
}) =>
  apiPost<{ success: boolean; lead_id: number; message: string }>(
    '/api/elite/mobile/quick-lead',
    data
  );

export const getMobileDashboard = (salespersonId: number) =>
  apiGet<{
    salesperson_id: number;
    today: { leads: number; hot_leads: number; warm_leads: number };
    this_week: { leads: number; hot_leads: number };
    rank: number | null;
    total_salespeople: number;
    points: number;
    recent_achievements: Achievement[];
    updated_at: string;
  }>(`/api/elite/mobile/dashboard?salesperson_id=${salespersonId}`);
