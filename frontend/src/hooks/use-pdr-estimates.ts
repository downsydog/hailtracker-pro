/**
 * PDR Estimates API Hooks
 * TanStack Query hooks for PDR estimating module
 * Matrix-based pricing: per-panel pricing with count ranges and size multipliers
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiPut, apiDelete } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

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

// Customer status for authorization workflow
export type CustomerStatus = 'draft' | 'pending_signature' | 'authorized' | 'declined'

// Insurer status for approval workflow
export type InsurerStatus = 'not_submitted' | 'submitted' | 'approved' | 'declined' | 'needs_revision'

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

  // =========================================================================
  // SPLIT WORKFLOW: Customer Authorization vs Insurer Approval
  // =========================================================================

  // Customer authorization (signature-based)
  customer_status?: CustomerStatus
  is_customer_authorized?: boolean
  signed_at?: string
  signed_by_name?: string
  signed_by_email?: string
  customer_declined_at?: string
  customer_declined_reason?: string

  // Insurer approval workflow
  insurer_status?: InsurerStatus
  is_insurer_approved?: boolean
  submitted_to_insurer_at?: string
  submitted_to_insurer_by?: number
  insurer_approved_at?: string
  insurer_approved_by?: number
  insurer_declined_at?: string
  insurer_declined_reason?: string

  // Insurer financial tracking (partial approvals)
  requested_total?: number
  insurer_approved_total?: number | null
  insurer_approved_labor?: number | null
  insurer_approved_ri?: number | null
  insurer_approved_materials?: number | null
  insurer_approved_tax?: number | null
  insurer_approval_notes?: string | null
  insurer_approval_reference?: string | null
  short_paid_amount?: number | null
  approval_delta?: number | null
  has_partial_approval?: boolean

  // Locking (estimate locked when insurer_status='approved')
  is_locked?: boolean
  combined_status_display?: string

  // Legacy fields (for backward compatibility)
  approval_status?: 'draft' | 'pending_signature' | 'signed' | 'approved' | 'declined'
  signature_image?: string  // Base64 encoded
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

  approveEstimate: (id: number) =>
    apiPost<{ success: boolean; estimate: PDREstimate }>(`/pdr-estimates/${id}/approve`, {}),

  declineEstimate: (id: number, reason?: string) =>
    apiPost<{ success: boolean; insurer_status: string }>(`/pdr-estimates/${id}/decline`, { reason }),

  // Insurer workflow endpoints
  submitToInsurer: (id: number) =>
    apiPost<{ success: boolean; submitted_to_insurer_at: string; insurer_status: string }>(`/pdr-estimates/${id}/submit-to-insurer`, {}),

  insurerApprove: (id: number, data: {
    approved_total: number
    approved_labor?: number
    approved_ri?: number
    approved_materials?: number
    approved_tax?: number
    notes?: string
    reference?: string
  }) =>
    apiPost<{
      success: boolean
      insurer_approved_at: string
      insurer_status: string
      is_locked: boolean
      requested_total: number
      approved_total: number
      short_paid_amount: number | null
      has_partial_approval: boolean
    }>(`/pdr-estimates/${id}/insurer-approve`, data),

  updateInsurerApproval: (id: number, data: {
    approved_total?: number
    approved_labor?: number
    approved_ri?: number
    approved_materials?: number
    approved_tax?: number
    notes?: string
    reference?: string
  }) =>
    apiPost<{
      success: boolean
      requested_total: number
      approved_total: number | null
      short_paid_amount: number | null
      has_partial_approval: boolean
    }>(`/pdr-estimates/${id}/update-insurer-approval`, data),

  insurerDecline: (id: number, reason?: string) =>
    apiPost<{ success: boolean; insurer_declined_at: string; insurer_status: string }>(`/pdr-estimates/${id}/insurer-decline`, { reason }),

  insurerNeedsRevision: (id: number, reason?: string) =>
    apiPost<{ success: boolean; insurer_status: string }>(`/pdr-estimates/${id}/insurer-needs-revision`, { reason }),

  requestSignature: (id: number, expiresInDays?: number) =>
    apiPost<{
      success: boolean
      share_url: string
      expires_at: string
    }>(`/pdr-estimates/${id}/request-signature`, { expires_in_days: expiresInDays }),

  signEstimate: (id: number, signatureBase64: string, signedByName: string) =>
    apiPost<{ success: boolean; signed_at: string; signed_by_name: string; approval_status: string }>(`/pdr-estimates/${id}/sign`, {
      signature: signatureBase64,  // Data URL format
      name: signedByName
    }),

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
    mutationFn: (id: number) => pdrApi.approveEstimate(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
    },
  })
}

export function useDeclinePDREstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      pdrApi.declineEstimate(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
    },
  })
}

export function useRequestSignature() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, expiresInDays }: { id: number; expiresInDays?: number }) =>
      pdrApi.requestSignature(id, expiresInDays),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
      // Instant refresh: workflow state changed
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(id) })
    },
  })
}

export function useSignEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, signatureBase64, signedByName }: {
      id: number
      signatureBase64: string
      signedByName: string
    }) => pdrApi.signEstimate(id, signatureBase64, signedByName),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
      // Instant refresh: customer authorized - major workflow change
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(id) })
    },
  })
}

// ==============================================================================
// INSURER WORKFLOW HOOKS
// ==============================================================================

export function useSubmitToInsurer() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => pdrApi.submitToInsurer(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
      // Instant refresh: insurer workflow started
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(id) })
    },
  })
}

export interface InsurerApprovalData {
  approved_total: number
  approved_labor?: number
  approved_ri?: number
  approved_materials?: number
  approved_tax?: number
  notes?: string
  reference?: string
}

export function useInsurerApprove() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: InsurerApprovalData }) =>
      pdrApi.insurerApprove(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
      // Instant refresh: major workflow change - ready for job
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(id) })
    },
  })
}

export function useUpdateInsurerApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<InsurerApprovalData> }) =>
      pdrApi.updateInsurerApproval(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
    },
  })
}

export function useInsurerDecline() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      pdrApi.insurerDecline(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
      // Instant refresh: insurer declined
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(id) })
    },
  })
}

export function useInsurerNeedsRevision() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      pdrApi.insurerNeedsRevision(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', id] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', id] })
      // Instant refresh: needs revision is high priority
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(id) })
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

// Convert Estimate to Invoice
export function useConvertToInvoice() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (estimateId: number) =>
      apiPost<{ success: boolean; invoice_id: number; invoice_number: string }>(
        `/pdr-estimates/${estimateId}/convert-to-invoice`,
        {}
      ),
    onSuccess: (_, estimateId) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates'] })
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

// =============================================================================
// PANEL PERSISTENCE HELPERS
// =============================================================================

// Convert frontend countRange to middle dent count
export function countRangeToNumber(countRange: string | null): number {
  if (!countRange) return 0
  const ranges: Record<string, number> = {
    '1-5': 3,
    '6-15': 10,
    '16-30': 23,
    '31-50': 40,
    '51-75': 63,
    '76-100': 88,
    '101+': 120
  }
  return ranges[countRange] || 0
}

// Convert dent count back to range (for display)
export function numberToCountRange(count: number): string {
  if (count <= 0) return '1-5'
  if (count <= 5) return '1-5'
  if (count <= 15) return '6-15'
  if (count <= 30) return '16-30'
  if (count <= 50) return '31-50'
  if (count <= 75) return '51-75'
  if (count <= 100) return '76-100'
  return '101+'
}

// Add/Update panel with matrix pricing
export function useAddPanelMatrix() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, data }: {
      estimateId: number
      data: {
        panel_name: string
        total_dent_count: number
        majority_size: string
        oversized_count?: number
        is_aluminum?: boolean
        is_hss?: boolean
        requires_glue_pull?: boolean
        is_tall_roof?: boolean
      }
    }) => apiPost<{
      success: boolean
      panel: { id: number; panel_name: string; panel_total: number }
      pricing: { panel_total: number }
    }>(`/pdr-estimates/${estimateId}/panels`, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

export function useUpdatePanelMatrix() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId, data }: {
      estimateId: number
      panelId: number
      data: {
        panel_name?: string
        total_dent_count?: number
        majority_size?: string
        oversized_count?: number
        is_aluminum?: boolean
        is_hss?: boolean
        requires_glue_pull?: boolean
        is_tall_roof?: boolean
      }
    }) => apiPut<{
      success: boolean
      panel: { id: number; panel_name: string; panel_total: number }
      pricing: { panel_total: number }
    }>(`/pdr-estimates/${estimateId}/panels/${panelId}`, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

export function useDeletePanelMatrix() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId }: { estimateId: number; panelId: number }) =>
      apiDelete<{ success: boolean }>(`/pdr-estimates/${estimateId}/panels/${panelId}`),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

// ==============================================================================
// PDF EXPORT
// ==============================================================================

/**
 * Download estimate as PDF (GET from backend - uses persisted data)
 */
export async function downloadEstimatePDF(estimateId: number): Promise<void> {
  const token = localStorage.getItem('token')

  const response = await fetch(`/api/pdr-estimates/${estimateId}/pdf`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'PDF generation failed' }))
    throw new Error(error.error || 'PDF generation failed')
  }

  // Get filename from Content-Disposition header
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `Estimate-${estimateId}.pdf`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) {
      filename = match[1]
    }
  }

  // Create blob and trigger download
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Hook for PDF download with loading state
 */
export function useDownloadEstimatePDF() {
  return useMutation({
    mutationFn: (estimateId: number) => downloadEstimatePDF(estimateId),
  })
}

// ==============================================================================
// PHOTO SHEET PDF EXPORT
// ==============================================================================

/**
 * Download estimate photo sheet as PDF (GET from backend - uses persisted data)
 */
export async function downloadEstimatePhotoSheetPDF(estimateId: number): Promise<void> {
  const token = localStorage.getItem('token')

  const response = await fetch(`/api/pdr-estimates/${estimateId}/photosheet.pdf`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Photo sheet generation failed' }))
    throw new Error(error.error || 'Photo sheet generation failed')
  }

  // Get filename from Content-Disposition header
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `PhotoSheet-${estimateId}.pdf`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) {
      filename = match[1]
    }
  }

  // Create blob and trigger download
  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

/**
 * Hook for photo sheet PDF download with loading state
 */
export function useDownloadEstimatePhotoSheetPDF() {
  return useMutation({
    mutationFn: (estimateId: number) => downloadEstimatePhotoSheetPDF(estimateId),
  })
}

/**
 * Download dispute pack as ZIP (GET from backend - uses persisted data)
 * Contains: Estimate PDF, Photo Sheet PDF, all Supplements, Activity Log
 */
export async function downloadEstimateDisputePack(estimateId: number): Promise<void> {
  const token = localStorage.getItem('token')

  const response = await fetch(`/api/pdr-estimates/${estimateId}/dispute-pack.zip`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Dispute pack generation failed' }))
    throw new Error(error.error || 'Dispute pack generation failed')
  }

  // Get filename from Content-Disposition header
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `DisputePack-${estimateId}.zip`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) {
      filename = match[1]
    }
  }

  // Create blob and trigger download
  const blob = await response.blob()
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

/**
 * Hook for dispute pack ZIP download with loading state
 */
export function useDownloadEstimateDisputePack() {
  return useMutation({
    mutationFn: (estimateId: number) => downloadEstimateDisputePack(estimateId),
  })
}

/**
 * Hook to get photos for an estimate
 */
export function useEstimatePhotos(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-photos', estimateId],
    queryFn: () => apiGet<{ photos: Array<{
      id: number
      file_path: string
      panel_name: string | null
      photo_type: string
      caption: string | null
      is_supplement_evidence: boolean
      created_at: string
    }>; count: number }>(`/pdr-estimates/${estimateId}/photos`),
    enabled: !!estimateId,
  })
}

// ==============================================================================
// EMAIL SEND
// ==============================================================================

export interface SendEstimatePackageParams {
  estimateId: number
  to: string
  cc?: string[]
  subject?: string
  message?: string
}

export interface SendEstimatePackageResult {
  status: 'sent' | 'failed'
  message_id?: string
  error?: string
}

/**
 * Send estimate package (PDF + Photo Sheet) to adjuster via email
 */
export async function sendEstimatePackage(params: SendEstimatePackageParams): Promise<SendEstimatePackageResult> {
  const { estimateId, to, cc, subject, message } = params
  const token = localStorage.getItem('token')

  const response = await fetch(`/api/pdr-estimates/${estimateId}/send`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ to, cc, subject, message })
  })

  const result = await response.json()
  return result as SendEstimatePackageResult
}

/**
 * Hook for sending estimate package with loading state
 */
export function useSendEstimatePackage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: SendEstimatePackageParams) => sendEstimatePackage(params),
    onSuccess: (_, variables) => {
      // Invalidate activities to show new send in timeline
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', variables.estimateId] })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(variables.estimateId) })
    }
  })
}

// ==============================================================================
// ACTIVITY LOG
// ==============================================================================

export interface EstimateActivity {
  id: number
  estimate_id: number
  activity_type: string
  user_id: number | null
  metadata: Record<string, unknown>
  created_at: string
}

/**
 * Hook to get activities for an estimate
 */
export function useEstimateActivities(estimateId: number | null, options?: { limit?: number; type?: string }) {
  const { limit = 20, type } = options || {}

  return useQuery({
    queryKey: ['estimate-activities', estimateId, limit, type],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (limit) params.set('limit', limit.toString())
      if (type) params.set('type', type)

      const queryString = params.toString()
      const url = `/pdr-estimates/${estimateId}/activities${queryString ? `?${queryString}` : ''}`

      return apiGet<{ activities: EstimateActivity[]; count: number }>(url)
    },
    enabled: !!estimateId,
  })
}

// ==============================================================================
// ESTIMATE VERSIONS (BASELINE SNAPSHOTS)
// ==============================================================================

export interface EstimateVersion {
  id: number
  estimate_id: number
  version_number: number
  snapshot_json: Record<string, unknown>
  description: string | null
  created_at: string
  created_by: number | null
}

/**
 * Hook to get versions for an estimate
 */
export function useEstimateVersions(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-versions', estimateId],
    queryFn: () => apiGet<{ versions: EstimateVersion[]; count: number }>(`/pdr-estimates/${estimateId}/versions`),
    enabled: !!estimateId,
  })
}

/**
 * Hook to create a baseline version snapshot
 */
export function useCreateEstimateVersion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, snapshot, description }: {
      estimateId: number
      snapshot: Record<string, unknown>
      description?: string
    }) => {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/pdr-estimates/${estimateId}/versions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ snapshot, description })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create version')
      }

      return response.json() as Promise<{ version: EstimateVersion }>
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['estimate-versions', variables.estimateId] })
    }
  })
}

// ==============================================================================
// SUPPLEMENTS
// ==============================================================================

export interface EstimateSupplement {
  id: number
  estimate_id: number
  baseline_version_id: number
  supplement_number: number
  discovery_type: string
  summary: string | null
  narrative: string | null
  delta_json: Record<string, unknown> | null
  original_total: number | null
  revised_total: number | null
  delta_amount: number | null
  status: 'draft' | 'sent' | 'approved' | 'rejected'
  created_at: string
  created_by: number | null
  sent_at: string | null
  approved_at: string | null
}

export const DISCOVERY_TYPES = [
  { value: 'hidden_damage', label: 'Hidden Damage' },
  { value: 'additional_panels', label: 'Additional Panels' },
  { value: 'severity_increase', label: 'Severity Increase' },
  { value: 'access_limitation', label: 'Access Limitation' },
  { value: 'part_condition', label: 'Part Condition' },
  { value: 'corrosion', label: 'Corrosion' },
  { value: 'prior_damage', label: 'Prior Damage' },
  { value: 'manufacturer_spec', label: 'Manufacturer Spec' },
  { value: 'other', label: 'Other' }
] as const

export type DiscoveryType = typeof DISCOVERY_TYPES[number]['value']

/**
 * Hook to get supplements for an estimate
 */
export function useEstimateSupplements(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-supplements', estimateId],
    queryFn: () => apiGet<{ supplements: EstimateSupplement[]; count: number }>(`/pdr-estimates/${estimateId}/supplements`),
    enabled: !!estimateId,
  })
}

/**
 * Hook to get a single supplement
 */
export function useSupplement(supplementId: number | null) {
  return useQuery({
    queryKey: ['supplement', supplementId],
    queryFn: () => apiGet<{ supplement: EstimateSupplement }>(`/pdr-supplements/${supplementId}`),
    enabled: !!supplementId,
  })
}

/**
 * Hook to create a new supplement
 */
export function useCreateSupplement() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, baselineVersionId, currentState, discoveryType, summary, photoIds }: {
      estimateId: number
      baselineVersionId: number
      currentState: Record<string, unknown>
      discoveryType: string
      summary?: string
      photoIds?: number[]
    }) => {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/pdr-estimates/${estimateId}/supplements`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          baseline_version_id: baselineVersionId,
          current_state: currentState,
          discovery_type: discoveryType,
          summary,
          photo_ids: photoIds
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create supplement')
      }

      return response.json() as Promise<{
        supplement: EstimateSupplement
        delta: Record<string, unknown>
        narrative: string
      }>
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['estimate-supplements', variables.estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', variables.estimateId] })
    }
  })
}

/**
 * Download supplement PDF
 */
export async function downloadSupplementPDF(supplementId: number): Promise<void> {
  const token = localStorage.getItem('token')

  const response = await fetch(`/api/pdr-supplements/${supplementId}/pdf`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'PDF generation failed' }))
    throw new Error(error.error || 'PDF generation failed')
  }

  // Get filename from Content-Disposition header
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `Supplement-${supplementId}.pdf`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) {
      filename = match[1]
    }
  }

  // Create blob and trigger download
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Hook for supplement PDF download
 */
export function useDownloadSupplementPDF() {
  return useMutation({
    mutationFn: (supplementId: number) => downloadSupplementPDF(supplementId),
  })
}

/**
 * Send supplement via email
 */
export async function sendSupplement(supplementId: number, params: {
  to: string
  cc?: string[]
  subject?: string
  message?: string
}): Promise<{ status: 'sent' | 'failed'; message_id?: string; error?: string }> {
  const token = localStorage.getItem('token')

  const response = await fetch(`/api/pdr-supplements/${supplementId}/send`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(params)
  })

  return response.json()
}

/**
 * Hook for sending supplement
 */
export function useSendSupplement() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ supplementId, ...params }: {
      supplementId: number
      to: string
      cc?: string[]
      subject?: string
      message?: string
    }) => sendSupplement(supplementId, params),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['supplement', variables.supplementId] })
    }
  })
}

// ==============================================================================
// SHARE LINK
// ==============================================================================

export interface ShareLinkPermissions {
  estimate_pdf: boolean
  photosheet: boolean
  dispute_pack: boolean
  supplements: boolean
  signing: boolean
}

export interface ShareLinkResult {
  url: string
  token: string
  expires_at: string
  permissions: ShareLinkPermissions
}

export interface SharedEstimateData {
  estimate: {
    id: number
    estimate_number: string
    vehicle_year: number
    vehicle_make: string
    vehicle_model: string
    status: string
    total: number | null
    // Customer authorization
    customer_status: CustomerStatus
    is_customer_authorized: boolean
    signed_at: string | null
    signed_by_name: string | null
    // Insurer approval
    insurer_status: InsurerStatus
    is_insurer_approved: boolean
    is_locked: boolean
    combined_status_display: string
    // Legacy (for backward compatibility)
    approval_status: 'draft' | 'pending_signature' | 'signed' | 'approved' | 'declined'
    is_signed: boolean  // Alias for is_customer_authorized
  }
  permissions: ShareLinkPermissions
  supplements: Array<{
    id: number
    supplement_number: number
    status: string
    delta_amount: number | null
    created_at: string | null
  }>
  expires_at: string
}

/**
 * Create a share link for an estimate (authenticated)
 */
export function useCreateShareLink() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ estimateId, expiresInDays, allowPhotosheet, allowDisputePack, allowSupplements, allowSigning }: {
      estimateId: number
      expiresInDays?: number
      allowPhotosheet?: boolean
      allowDisputePack?: boolean
      allowSupplements?: boolean
      allowSigning?: boolean
    }) => {
      const token = localStorage.getItem('token')
      const response = await fetch(`/api/pdr-estimates/${estimateId}/share-link`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          expires_in_days: expiresInDays,
          allow_photosheet: allowPhotosheet,
          allow_dispute_pack: allowDisputePack,
          allow_supplements: allowSupplements,
          allow_signing: allowSigning
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create share link')
      }

      return response.json() as Promise<ShareLinkResult>
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', variables.estimateId] })
    }
  })
}

/**
 * Fetch shared estimate data (public, no auth)
 */
export function useSharedEstimate(token: string | null) {
  return useQuery({
    queryKey: ['shared-estimate', token],
    queryFn: async () => {
      const response = await fetch(`/api/public/share/estimate/${token}`)

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to load shared estimate')
      }

      return response.json() as Promise<SharedEstimateData>
    },
    enabled: !!token,
    retry: false // Don't retry on 401 (expired/invalid)
  })
}

/**
 * Download shared estimate PDF (public, no auth)
 */
export async function downloadSharedEstimatePDF(token: string): Promise<void> {
  const response = await fetch(`/api/public/share/estimate/${token}/pdf`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Download failed' }))
    throw new Error(error.error || 'Download failed')
  }

  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = 'Estimate.pdf'
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) filename = match[1]
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Download shared photo sheet (public, no auth)
 */
export async function downloadSharedPhotoSheet(token: string): Promise<void> {
  const response = await fetch(`/api/public/share/estimate/${token}/photosheet.pdf`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Download failed' }))
    throw new Error(error.error || 'Download failed')
  }

  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = 'PhotoSheet.pdf'
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) filename = match[1]
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Download shared dispute pack (public, no auth)
 */
export async function downloadSharedDisputePack(token: string): Promise<void> {
  const response = await fetch(`/api/public/share/estimate/${token}/dispute-pack.zip`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Download failed' }))
    throw new Error(error.error || 'Download failed')
  }

  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = 'DisputePack.zip'
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) filename = match[1]
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Sign estimate via portal (public, no auth - uses share token)
 */
export async function signEstimateViaPortal(
  token: string,
  signatureBase64: string,
  signedByName: string
): Promise<{ success: boolean; signed_at: string }> {
  const response = await fetch(`/api/public/share/estimate/${token}/sign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      signature: signatureBase64,  // Data URL format (data:image/png;base64,...)
      name: signedByName
    })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Signing failed' }))
    throw new Error(error.error || 'Signing failed')
  }

  return response.json()
}

/**
 * Hook for portal signing
 */
export function useSignEstimateViaPortal() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ token, signatureBase64, signedByName }: {
      token: string
      signatureBase64: string
      signedByName: string
    }) => signEstimateViaPortal(token, signatureBase64, signedByName),
    onSuccess: (_, { token }) => {
      queryClient.invalidateQueries({ queryKey: ['shared-estimate', token] })
    },
  })
}

/**
 * Download shared supplement PDF (public, no auth)
 */
export async function downloadSharedSupplementPDF(token: string, supplementId: number): Promise<void> {
  const response = await fetch(`/api/public/share/supplement/${token}/${supplementId}/pdf`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Download failed' }))
    throw new Error(error.error || 'Download failed')
  }

  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `Supplement-${supplementId}.pdf`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (match) filename = match[1]
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// ============ JOB TYPES ============

export type JobStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'rescheduled'

export interface Job {
  id: number
  tenant_id: number
  estimate_id: number | null
  lead_id: number | null
  job_number: string
  customer_id: number | null
  customer_name: string | null
  vehicle_year: number | null
  vehicle_make: string | null
  vehicle_model: string | null
  vehicle_display: string | null
  status: JobStatus
  vehicle_count: number
  total_amount: number | null
  scheduled_date: string | null
  scheduled_time: string | null
  estimated_hours: number | null
  completed_date: string | null
  assigned_tech: number | null
  notes: string | null
  created_at: string
  updated_at: string
  created_by: number | null
  estimate?: {
    id: number
    estimate_number: string
    total_price: number
    insurer_approved_total: number | null
    insurer_status: InsurerStatus
    customer_status: CustomerStatus
    is_locked: boolean
  }
}

export interface CreateJobData {
  scheduled_date?: string
  assigned_tech?: number
  notes?: string
}

export interface UpdateJobData {
  scheduled_date?: string | null
  scheduled_time?: string | null
  assigned_tech?: number | null
  estimated_hours?: number | null
  notes?: string | null
  status?: JobStatus
}

// ============ JOB API FUNCTIONS ============

/**
 * Get the job linked to an estimate
 */
async function getEstimateJob(estimateId: number): Promise<{ job: Job; has_job: boolean }> {
  return apiGet<{ job: Job; has_job: boolean }>(`/customer/pdr-estimates/${estimateId}/job`)
}

/**
 * Create a job from an approved estimate
 */
async function createJobFromEstimate(estimateId: number, data?: CreateJobData): Promise<{ job: Job; message: string }> {
  return apiPost<{ job: Job; message: string }>(`/customer/pdr-estimates/${estimateId}/job`, data || {})
}

/**
 * Get a job by ID
 */
async function getJob(jobId: number): Promise<{ job: Job }> {
  return apiGet<{ job: Job }>(`/customer/jobs/${jobId}`)
}

/**
 * List jobs
 */
async function listJobs(params?: { status?: JobStatus; assigned_tech?: number; limit?: number }): Promise<{ jobs: Job[]; count: number }> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.assigned_tech) searchParams.set('assigned_tech', String(params.assigned_tech))
  if (params?.limit) searchParams.set('limit', String(params.limit))
  const query = searchParams.toString()
  return apiGet<{ jobs: Job[]; count: number }>(`/customer/jobs${query ? `?${query}` : ''}`)
}

/**
 * Update a job
 */
async function updateJob(jobId: number, data: UpdateJobData): Promise<{ job: Job; status_changed: boolean }> {
  return apiPut<{ job: Job; status_changed: boolean }>(`/customer/jobs/${jobId}`, data)
}

// ============ JOB HOOKS ============

/**
 * Hook to get the job linked to an estimate
 */
export function useEstimateJob(estimateId: number | undefined) {
  return useQuery({
    queryKey: ['estimate-job', estimateId],
    queryFn: () => getEstimateJob(estimateId!),
    enabled: !!estimateId,
    retry: false, // Don't retry 404s
  })
}

/**
 * Hook to create a job from an estimate
 */
export function useCreateJobFromEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, data }: { estimateId: number; data?: CreateJobData }) =>
      createJobFromEstimate(estimateId, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['estimate-job', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
      // Instant refresh: job created from estimate
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(estimateId) })
    },
  })
}

/**
 * Hook to get a single job
 */
export function useJob(jobId: number | undefined) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
  })
}

/**
 * Hook to list jobs
 */
export function useJobs(params?: { status?: JobStatus; assigned_tech?: number; limit?: number }) {
  return useQuery({
    queryKey: ['jobs', params],
    queryFn: () => listJobs(params),
  })
}

/**
 * Hook to update a job
 */
export function useUpdateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ jobId, data }: { jobId: number; data: UpdateJobData }) =>
      updateJob(jobId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['job', result.job.id] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      if (result.job.estimate_id) {
        queryClient.invalidateQueries({ queryKey: ['estimate-job', result.job.estimate_id] })
        queryClient.invalidateQueries({ queryKey: ['estimate-activities', result.job.estimate_id] })
        queryClient.invalidateQueries({ queryKey: queryKeys.workflow.estimate(result.job.estimate_id) })
      }
      // Instant refresh: job status affects ops dashboard
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.job(result.job.id) })
    },
  })
}

// Export API for direct use if needed
export { pdrApi }
