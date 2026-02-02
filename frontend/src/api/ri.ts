/**
 * R&I (Remove & Install) API Client
 * R&I operations catalog, times, auto-suggestions, estimate integration
 */

import { apiGet, apiPost, apiPut, apiDelete } from './client'

// =============================================================================
// TYPES
// =============================================================================

export interface RIOperation {
  id: number
  code: string
  name: string
  category: string
  description?: string
  default_hours: number
  default_labor_type: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface RIOperationInput {
  code: string
  name: string
  category?: string
  description?: string
  default_hours?: number
  default_labor_type?: string
}

export interface RITime {
  id: number
  ri_operation_id: number
  operation_name?: string
  operation_code?: string
  category?: string
  year_start: number
  year_end: number
  make: string
  model: string
  body_style?: string
  labor_hours: number
  source: string
  confidence_score: number
  sample_count: number
  notes?: string
  last_updated?: string
}

export interface RITimeLookup {
  hours: number
  source: string
  confidence: number
  ri_time_id: number | null
}

export interface RITimeCorrection {
  id: number
  ri_time_id?: number
  estimate_id?: number
  ri_operation_id: number
  operation_name?: string
  code?: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_body_style?: string
  suggested_hours: number
  actual_hours: number
  technician_id?: number
  notes?: string
  approved: boolean
  created_at: string
}

export interface RISuggestion {
  ri_operation_id: number
  name: string
  code: string
  hours: number
  rate: number
  labor_type: string
  total: number
  is_default: boolean
  source: string
  confidence: number
  ri_time_id?: number
  reason?: string
  panel_name?: string
}

export interface EstimateRIItem {
  id: number
  estimate_id: number
  ri_operation_id: number
  name?: string
  code?: string
  category?: string
  panel_name?: string
  labor_hours: number
  labor_rate: number
  labor_type: string
  line_total: number
  auto_suggested: boolean
  was_modified: boolean
  notes?: string
  created_at: string
}

export interface PanelAssociation {
  id: number
  panel_name: string
  ri_operation_id: number
  name?: string
  code?: string
  category?: string
  default_hours?: number
  min_dent_count: number
  is_default_selected: boolean
  vehicle_condition?: string
  condition_notes?: string
  priority: number
}

export interface LaborRates {
  body: number
  paint: number
  pdr: number
  mechanical: number
  electrical: number
  glass: number
  structural: number
  [key: string]: number
}

export interface RIStats {
  period_days: number
  top_items: Array<{
    code: string
    name: string
    category: string
    usage_count: number
    avg_hours: number
    total_revenue: number
  }>
  total_ri_items: number
  total_revenue: number
}

// =============================================================================
// R&I API
// =============================================================================

export const riApi = {
  // ==========================================================================
  // R&I OPERATIONS CATALOG
  // ==========================================================================

  // List all operations
  getOperations: (params?: { category?: string; search?: string }) =>
    apiGet<{ operations: RIOperation[]; count: number }>('/api/ri/operations', { params }),

  // Get single operation
  getOperation: (id: number) =>
    apiGet<{ operation: RIOperation }>(`/api/ri/operations/${id}`),

  // Get operation by code
  getOperationByCode: (code: string) =>
    apiGet<{ operation: RIOperation }>(`/api/ri/operations/code/${code}`),

  // Create operation
  createOperation: (data: RIOperationInput) =>
    apiPost<{ success: boolean; operation_id: number; message: string }>(
      '/api/ri/operations',
      data
    ),

  // Update operation
  updateOperation: (id: number, data: Partial<RIOperationInput & { is_active: boolean }>) =>
    apiPut<{ success: boolean; message: string }>(`/api/ri/operations/${id}`, data),

  // Delete (deactivate) operation
  deleteOperation: (id: number) =>
    apiDelete<{ success: boolean; message: string }>(`/api/ri/operations/${id}`),

  // Get operation categories
  getCategories: () =>
    apiGet<{ categories: string[] }>('/api/ri/categories'),

  // ==========================================================================
  // R&I TIMES
  // ==========================================================================

  // Get R&I times with vehicle filters
  getTimes: (params?: {
    vehicle_id?: number
    year?: number
    make?: string
    model?: string
    operation_id?: number
  }) =>
    apiGet<{
      times: RITime[]
      count: number
      vehicle: { year?: number; make?: string; model?: string }
    }>('/api/ri/times', { params }),

  // Lookup specific R&I time for vehicle
  lookupTime: (params: {
    operation_id: number
    year: number
    make: string
    model: string
    body_style?: string
  }) =>
    apiGet<RITimeLookup>('/api/ri/times/lookup', { params }),

  // Submit time correction (crowdsourced)
  submitTimeCorrection: (data: {
    ri_operation_id: number
    suggested_hours: number
    actual_hours: number
    vehicle_year: number
    vehicle_make: string
    vehicle_model: string
    vehicle_body_style?: string
    ri_time_id?: number
    estimate_id?: number
    technician_id?: number
    notes?: string
  }) =>
    apiPost<{ success: boolean; submission_id: number; message: string }>(
      '/api/ri/times/corrections',
      data
    ),

  // Get pending corrections (admin)
  getPendingCorrections: () =>
    apiGet<{ corrections: RITimeCorrection[]; count: number }>(
      '/api/ri/times/corrections/pending'
    ),

  // Approve correction (admin)
  approveCorrection: (submissionId: number) =>
    apiPost<{ success: boolean; message: string }>(
      `/api/ri/times/corrections/${submissionId}/approve`
    ),

  // ==========================================================================
  // PANELS
  // ==========================================================================

  // List panels with operation counts
  getPanels: () =>
    apiGet<{ panels: Array<{ panel_name: string; operation_count: number }> }>('/api/ri/panels'),

  // Get R&I operations for a panel
  getPanelOperations: (panel: string) =>
    apiGet<{ panel: string; operations: PanelAssociation[]; count: number }>(
      `/api/ri/panels/${panel}/operations`
    ),

  // ==========================================================================
  // AUTO-SUGGEST
  // ==========================================================================

  // Suggest R&I operations for damage
  suggestRI: (data: {
    panels: Array<string | { name: string; dent_count?: number }>
    vehicle_info?: {
      year?: number
      make?: string
      model?: string
      body_style?: string
      has_sunroof?: boolean
      has_roof_rails?: boolean
      fuel_door_side?: 'left' | 'right'
    }
    estimate_id?: number
  }) =>
    apiPost<{
      suggestions: RISuggestion[]
      total_hours: number
      total_amount: number
      count: number
    }>('/api/ri/suggest', data),

  // ==========================================================================
  // ESTIMATE R&I ITEMS
  // ==========================================================================

  // Get R&I items for estimate
  getEstimateRI: (estimateId: number) =>
    apiGet<{ items: EstimateRIItem[]; count: number; total: number }>(
      `/api/ri/estimates/${estimateId}/ri`
    ),

  // Add R&I item to estimate
  addRIToEstimate: (
    estimateId: number,
    data: {
      operation_id: number
      hours?: number
      panel_name?: string
      auto_suggested?: boolean
      notes?: string
    }
  ) =>
    apiPost<{ success: boolean; item_id: number; ri_total: number; message: string }>(
      `/api/ri/estimates/${estimateId}/ri`,
      data
    ),

  // Update R&I item on estimate
  updateEstimateRI: (
    estimateId: number,
    itemId: number,
    data: { hours?: number; notes?: string }
  ) =>
    apiPut<{ success: boolean; ri_total: number; message: string }>(
      `/api/ri/estimates/${estimateId}/ri/${itemId}`,
      data
    ),

  // Remove R&I item from estimate
  removeEstimateRI: (estimateId: number, itemId: number) =>
    apiDelete<{ success: boolean; ri_total: number; message: string }>(
      `/api/ri/estimates/${estimateId}/ri/${itemId}`
    ),

  // Bulk add R&I items from suggestions
  bulkAddRIToEstimate: (
    estimateId: number,
    items: Array<{
      ri_operation_id: number
      hours?: number
      panel_name?: string
      auto_suggested?: boolean
      notes?: string
    }>
  ) =>
    apiPost<{ success: boolean; added_count: number; item_ids: number[]; ri_total: number }>(
      `/api/ri/estimates/${estimateId}/ri/bulk`,
      { items }
    ),

  // ==========================================================================
  // LABOR RATES & STATS
  // ==========================================================================

  // Get current labor rates
  getLaborRates: () =>
    apiGet<{ rates: LaborRates }>('/api/ri/labor-rates'),

  // Get R&I usage statistics
  getStats: (days?: number) =>
    apiGet<RIStats>('/api/ri/stats', { params: { days } }),
}

export default riApi
