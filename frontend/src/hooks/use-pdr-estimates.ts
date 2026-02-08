/**
 * PDR Estimates API Hooks
 * TanStack Query hooks for PDR estimating module
 * Matrix-based pricing: per-panel pricing with count ranges and size multipliers
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiPut, apiDelete } from '@/api/client'

// ============ Types ============

export interface MatrixProfile {
  id: number
  name: string
  is_default: boolean
  is_system: boolean
  oversized_charge: number
  aluminum_multiplier: number
  hss_multiplier: number
  glue_pull_multiplier: number
  tall_roof_multiplier: number
  labor_rate: number
  notes?: string
}

export interface MatrixRow {
  count_range: string
  count_min: number
  count_max: number
  dime: { price: number | null; is_cr: boolean }
  nickel: { price: number | null; is_cr: boolean }
  quarter: { price: number | null; is_cr: boolean }
  half: { price: number | null; is_cr: boolean }
}

export interface MatrixPricing {
  panel: string
  panel_display: string
  dent_count: number
  majority_size: 'dime' | 'nickel' | 'quarter' | 'half'
  size_display: string
  count_range: string
  matrix_base_price: number
  multiplier_total: number
  multiplied_price: number
  oversized_count: number
  oversized_charge_each: number
  oversized_total: number
  upcharges: Array<{
    type: string
    label: string
    multiplier?: number
    percentage?: string
    charge_each?: number
    count?: number
    total?: number
  }>
  upcharge_total: number
  panel_total: number
  is_cr: boolean
  matrix_profile_id: number
  matrix_profile_name: string
}

export interface Panel {
  id: number
  panel_name: string
  total_dent_count: number
  majority_size: 'dime' | 'nickel' | 'quarter' | 'half'
  oversized_count: number
  is_aluminum: boolean
  is_hss: boolean
  requires_glue_pull: boolean
  is_tall_roof: boolean
  is_conventional_repair: boolean
  matrix_base_price: number
  upcharge_total: number
  panel_total: number
  ri_items: RIItem[]
}

export interface RIItem {
  id: number
  item_name: string
  operation_name?: string  // Display name for UI
  operation_code?: string
  category?: string
  time_hours: number
  calculated_time_hours?: number  // Calculated based on scope
  price: number
  scope_level?: 'min' | 'typical' | 'max'
  scope_bullets?: string[]
  scope_typical?: string  // Description of typical scope
}

export interface Discovery {
  id: number
  type: string
  discovery_type: string  // Same as type, for compatibility
  description: string
  additional_time_hours: number
  additional_cost: number
  photo_url?: string
  panel_name?: string
  narrative?: string
  created_at: string
}

export interface PDREstimate {
  id: number
  estimate_number: string
  status: 'draft' | 'in_progress' | 'approved' | 'completed'
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vin?: string
  vehicle_vin?: string  // Alias for vin
  vehicle_tier?: string
  is_tall_roof_vehicle: boolean
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  lead_id?: number
  contact_id?: number
  job_id?: number
  matrix_profile_id?: number
  matrix_profile_name?: string
  matrix_profile?: string  // Alias for matrix_profile_name
  insurance_profile?: {
    carrier_name: string
    claim_number?: string
  }
  claim_number?: string
  panels: Panel[]
  labor_total: number
  ri_total: number
  total_price: number
  has_cr_panels: boolean
  created_at: string
  updated_at: string
}

export interface WorkOrder {
  id: number
  estimate_id: number
  work_order_number?: string
  status: 'assigned' | 'in_progress' | 'completed'
  technician_id?: number
  technician_name?: string
  customer_name?: string
  vehicle?: string  // Vehicle display string
  matrix_profile?: string  // Matrix profile name
  panels: Panel[]
  discoveries: Discovery[]
  start_time?: string
  end_time?: string
  total_time_minutes?: number
  created_at: string
}

export interface VINDecodeResult {
  valid: boolean
  year: number
  make: string
  model: string
  vehicle_tier: string
  tier_multiplier: number
  aluminum_panels: string[]
  is_ev: boolean
  adas_features: string[]
  vehicle_string: string
}

export interface AluminumCheck {
  make: string
  model?: string
  year?: number
  aluminum_panels: string[]
  has_aluminum: boolean
}

// Standard panel names
export const PANEL_NAMES: Record<string, string> = {
  hood: 'Hood',
  roof: 'Roof',
  deck_lid: 'Deck Lid / Trunk',
  lf_door: 'Left Front Door',
  rf_door: 'Right Front Door',
  lr_door: 'Left Rear Door',
  rr_door: 'Right Rear Door',
  l_fender: 'Left Fender',
  r_fender: 'Right Fender',
  l_quarter: 'Left Quarter Panel',
  r_quarter: 'Right Quarter Panel',
  l_roof_rail: 'Left Roof Rail',
  r_roof_rail: 'Right Roof Rail',
  metal_sunroof: 'Metal Sunroof',
  cowl_other: 'Cowl / Other',
  bedside_l: 'Left Bedside',
  bedside_r: 'Right Bedside',
  cab_corner_l: 'Left Cab Corner',
  cab_corner_r: 'Right Cab Corner',
  tailgate: 'Tailgate'
}

export const SIZE_LABELS: Record<string, string> = {
  dime: 'Dime',
  nickel: 'Nickel',
  quarter: 'Quarter',
  half: 'Half Dollar'
}

// ============ API Functions ============

const pdrApi = {
  // Estimates
  listEstimates: (filters?: Record<string, string | number>) =>
    apiGet<{ estimates: PDREstimate[]; total: number }>('/pdr-estimates', { params: filters }),

  getEstimate: (id: number) =>
    apiGet<PDREstimate>(`/pdr-estimates/${id}`),

  createEstimate: (data: Partial<PDREstimate>) =>
    apiPost<{ success: boolean; estimate: PDREstimate }>('/pdr-estimates', data),

  updateEstimate: (id: number, data: Partial<PDREstimate>) =>
    apiPut<{ success: boolean; estimate: PDREstimate }>(`/pdr-estimates/${id}`, data),

  deleteEstimate: (id: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${id}`),

  approveEstimate: (id: number, signature?: string) =>
    apiPost<{ success: boolean; estimate: PDREstimate }>(`/pdr-estimates/${id}/approve`, { signature }),

  setMatrixProfile: (id: number, data: { matrix_profile_id?: number; is_tall_roof_vehicle?: boolean }) =>
    apiPut<{ success: boolean; estimate: PDREstimate }>(`/pdr-estimates/${id}/set-matrix-profile`, data),

  linkToCRM: (id: number, data: { lead_id?: number; contact_id?: number; job_id?: number }) =>
    apiPut<{ success: boolean; estimate: PDREstimate }>(`/pdr-estimates/${id}/link`, data),

  // Matrix Profiles
  listMatrixProfiles: () =>
    apiGet<{ profiles: MatrixProfile[]; count: number }>('/pdr-estimates/matrix-profiles'),

  getMatrixProfile: (id: number, panel?: string) =>
    apiGet<{ profile: MatrixProfile; matrix_data: Record<string, MatrixRow[]> }>(
      `/pdr-estimates/matrix-profiles/${id}`,
      { params: panel ? { panel } : undefined }
    ),

  createMatrixProfile: (data: { name: string; copy_from_id?: number; [key: string]: unknown }) =>
    apiPost<{ success: boolean; profile: MatrixProfile }>('/pdr-estimates/matrix-profiles', data),

  updateMatrixProfile: (id: number, data: Partial<MatrixProfile>) =>
    apiPut<{ success: boolean; profile: MatrixProfile }>(`/pdr-estimates/matrix-profiles/${id}`, data),

  // Matrix Lookup (calculate panel price)
  matrixLookup: (data: {
    matrix_profile_id?: number
    panel: string
    dent_count: number
    majority_size: 'dime' | 'nickel' | 'quarter' | 'half'
    oversized_count?: number
    is_aluminum?: boolean
    is_hss?: boolean
    requires_glue_pull?: boolean
    is_tall_roof?: boolean
  }) => apiPost<MatrixPricing>('/pdr-estimates/matrix-lookup', data),

  // Panels (Matrix-based)
  addPanel: (estimateId: number, data: {
    panel_name: string
    total_dent_count: number
    majority_size: 'dime' | 'nickel' | 'quarter' | 'half'
    oversized_count?: number
    is_aluminum?: boolean
    is_hss?: boolean
    requires_glue_pull?: boolean
    is_tall_roof?: boolean
  }) => apiPost<{ success: boolean; panel: Panel; pricing: MatrixPricing }>(
    `/pdr-estimates/${estimateId}/panels`, data
  ),

  updatePanel: (estimateId: number, panelId: number, data: Partial<Panel>) =>
    apiPut<{ success: boolean; panel: Panel; pricing: MatrixPricing }>(
      `/pdr-estimates/${estimateId}/panels/${panelId}`, data
    ),

  deletePanel: (estimateId: number, panelId: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${estimateId}/panels/${panelId}`),

  // Calculate Totals (Matrix-based)
  calculateTotals: (id: number) =>
    apiPost<{
      estimate_id: number
      panels: MatrixPricing[]
      panel_count: number
      labor_total: number
      ri_total: number
      grand_total: number
      has_cr_panels: boolean
      warning?: string
    }>(`/pdr-estimates/${id}/calculate-matrix`),

  // R&I
  getRILibrary: (category?: string) =>
    apiGet<{ items: RIItem[]; by_category: Record<string, RIItem[]> }>(
      '/pdr-estimates/ri-library',
      { params: category ? { category } : undefined }
    ),

  getRISuggestions: (estimateId: number, panelId: number) =>
    apiGet<{ suggestions: RIItem[]; panel_name: string; vehicle_tier: string }>(
      `/pdr-estimates/${estimateId}/panels/${panelId}/rin-suggestions`
    ),

  addRIFromLibrary: (estimateId: number, panelId: number, data: {
    operation_code: string
    scope_level?: 'min' | 'typical' | 'max'
  }) => apiPost<{ success: boolean; rin_item: RIItem }>(
    `/pdr-estimates/${estimateId}/panels/${panelId}/rin-from-library`, data
  ),

  deleteRI: (estimateId: number, riId: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${estimateId}/ri/${riId}`),

  // VIN Decode
  decodeVIN: (vin: string) =>
    apiGet<VINDecodeResult>(`/pdr-estimates/vin/decode/${vin}`),

  // Aluminum Check
  checkAluminum: (make: string, model?: string, year?: number) =>
    apiGet<AluminumCheck>('/pdr-estimates/check-aluminum', {
      params: { make, model, year }
    }),

  // Reference Data
  getPanels: () =>
    apiGet<{ panels: Record<string, string>; sizes: Record<string, string> }>('/pdr-estimates/panels'),

  // Work Orders
  createWorkOrder: (estimateId: number, techId?: number) =>
    apiPost<{ success: boolean; work_order: WorkOrder }>(
      `/pdr-estimates/${estimateId}/work-order`,
      { technician_id: techId }
    ),

  getWorkOrder: (workOrderId: number) =>
    apiGet<WorkOrder>(`/work-orders/${workOrderId}`),

  updateWorkOrder: (workOrderId: number, data: Partial<WorkOrder>) =>
    apiPut<WorkOrder>(`/work-orders/${workOrderId}`, data),

  addDiscovery: (workOrderId: number, data: {
    type?: string
    discovery_type?: string
    description?: string
    additional_time_hours?: number
    additional_cost?: number
    photo_url?: string
    photo_base64?: string
    panel_name?: string
  }) => apiPost<Discovery>(`/work-orders/${workOrderId}/discoveries`, {
    ...data,
    type: data.type || data.discovery_type  // Normalize to type for API
  }),

  // Supplements
  getSupplement: (workOrderId: number) =>
    apiGet<{
      work_order_id: number
      estimate_id: number
      original_total: number
      additional_time_hours: number
      additional_cost: number
      new_total: number
      supplement_total: number  // Total of discoveries
      grand_total: number  // original_total + supplement_total
      discoveries: Discovery[]
      narrative: string
    }>(`/work-orders/${workOrderId}/supplement`),

  // Matrix format (for insurance)
  getMatrix: (estimateId: number) =>
    apiGet<{
      format: string
      estimate_number: string
      vehicle: string
      vin?: string
      panels: Array<{
        panel_name: string
        total_dents: number
        dime: number
        nickel: number
        quarter: number
        half_dollar: number
        panel_labor: number
      }>
      ri_items: RIItem[]
      labor_total: number
      ri_total: number
      grand_total: number
    }>(`/pdr-estimates/${estimateId}/matrix`),

  // Photos
  uploadPhoto: (estimateId: number, data: FormData) =>
    fetch(`/api/pdr-estimates/${estimateId}/photos`, {
      method: 'POST',
      body: data,
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    }).then(r => r.json()),

  getPhotos: (estimateId: number) =>
    apiGet<{ photos: Array<{ id: number; file_path: string; photo_type: string }> }>(
      `/pdr-estimates/${estimateId}/photos`
    ),

  // Leads (for linking)
  searchLeads: (query: string) =>
    apiGet<{ leads: Array<{ id: number; business_name: string; contact_name: string; phone: string }> }>(
      '/leads', { params: { search: query } }
    ),
}

// ============ Hooks ============

// Estimates
export function usePDREstimates(filters?: Record<string, string | number>) {
  return useQuery({
    queryKey: ['pdr-estimates', filters],
    queryFn: () => pdrApi.listEstimates(filters),
  })
}

export function usePDREstimate(id: number | null) {
  return useQuery({
    queryKey: ['pdr-estimates', id],
    queryFn: () => pdrApi.getEstimate(id!),
    enabled: !!id,
  })
}

export function useCreatePDREstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: Partial<PDREstimate>) => pdrApi.createEstimate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
    },
  })
}

export function useUpdatePDREstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<PDREstimate> }) =>
      pdrApi.updateEstimate(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
    },
  })
}

export function useSetMatrixProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { matrix_profile_id?: number; is_tall_roof_vehicle?: boolean } }) =>
      pdrApi.setMatrixProfile(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
    },
  })
}

export function useApprovePDREstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, signature }: { id: number; signature?: string }) =>
      pdrApi.approveEstimate(id, signature),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
    },
  })
}

export function useCalculateTotals() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => pdrApi.calculateTotals(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
    },
  })
}

export function useLinkToCRM() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { lead_id?: number; contact_id?: number; job_id?: number } }) =>
      pdrApi.linkToCRM(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
    },
  })
}

// Matrix Profiles
export function useMatrixProfiles() {
  return useQuery({
    queryKey: ['matrix-profiles'],
    queryFn: () => pdrApi.listMatrixProfiles(),
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
  })
}

export function useMatrixProfile(id: number | null, panel?: string) {
  return useQuery({
    queryKey: ['matrix-profiles', id, panel],
    queryFn: () => pdrApi.getMatrixProfile(id!, panel),
    enabled: !!id,
  })
}

export function useMatrixLookup() {
  return useMutation({
    mutationFn: (data: Parameters<typeof pdrApi.matrixLookup>[0]) =>
      pdrApi.matrixLookup(data),
  })
}

// Panels
export function useAddPanel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, data }: {
      estimateId: number
      data: Parameters<typeof pdrApi.addPanel>[1]
    }) => pdrApi.addPanel(estimateId, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

export function useUpdatePanel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId, data }: {
      estimateId: number
      panelId: number
      data: Partial<Panel>
    }) => pdrApi.updatePanel(estimateId, panelId, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

export function useDeletePanel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId }: { estimateId: number; panelId: number }) =>
      pdrApi.deletePanel(estimateId, panelId),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

// R&I
export function useRILibrary(category?: string) {
  return useQuery({
    queryKey: ['ri-library', category],
    queryFn: () => pdrApi.getRILibrary(category),
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
  })
}

export function useRISuggestions(estimateId: number | null, panelId: number | null) {
  return useQuery({
    queryKey: ['ri-suggestions', estimateId, panelId],
    queryFn: () => pdrApi.getRISuggestions(estimateId!, panelId!),
    enabled: !!estimateId && !!panelId,
  })
}

export function useAddRIFromLibrary() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId, data }: {
      estimateId: number
      panelId: number
      data: { operation_code: string; scope_level?: 'min' | 'typical' | 'max' }
    }) => pdrApi.addRIFromLibrary(estimateId, panelId, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

// VIN Decode
export function useDecodeVIN() {
  return useMutation({
    mutationFn: (vin: string) => pdrApi.decodeVIN(vin),
  })
}

// Aluminum Check
export function useCheckAluminum() {
  return useMutation({
    mutationFn: ({ make, model, year }: { make: string; model?: string; year?: number }) =>
      pdrApi.checkAluminum(make, model, year),
  })
}

// Work Orders
export function useCreateWorkOrder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, techId }: { estimateId: number; techId?: number }) =>
      pdrApi.createWorkOrder(estimateId, techId),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['work-orders'] })
    },
  })
}

export function useWorkOrder(id: number | null) {
  return useQuery({
    queryKey: ['work-orders', id],
    queryFn: () => pdrApi.getWorkOrder(id!),
    enabled: !!id,
  })
}

export function useUpdateWorkOrder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<WorkOrder> }) =>
      pdrApi.updateWorkOrder(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['work-orders', id] })
    },
  })
}

export function useAddDiscovery() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ workOrderId, data }: {
      workOrderId: number
      data: Parameters<typeof pdrApi.addDiscovery>[1]
    }) => pdrApi.addDiscovery(workOrderId, data),
    onSuccess: (_, { workOrderId }) => {
      queryClient.invalidateQueries({ queryKey: ['work-orders', workOrderId] })
    },
  })
}

// Supplement
export function useSupplement(workOrderId: number | null) {
  return useQuery({
    queryKey: ['supplement', workOrderId],
    queryFn: () => pdrApi.getSupplement(workOrderId!),
    enabled: !!workOrderId,
  })
}

// Matrix Format
export function useMatrixFormat(estimateId: number | null) {
  return useQuery({
    queryKey: ['matrix-format', estimateId],
    queryFn: () => pdrApi.getMatrix(estimateId!),
    enabled: !!estimateId,
  })
}

// Lead Search
export function useSearchLeads(query: string) {
  return useQuery({
    queryKey: ['leads-search', query],
    queryFn: () => pdrApi.searchLeads(query),
    enabled: query.length >= 2,
  })
}

// Export API for direct use if needed
export { pdrApi }
