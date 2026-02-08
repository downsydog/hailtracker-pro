/**
 * PDR Estimates API Hooks
 * TanStack Query hooks for PDR estimating module
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiPut, apiDelete } from '@/api/client'

// ============ Types ============

export interface VehicleInfo {
  year: number
  make: string
  model: string
  vin?: string
  vehicle_tier: 'economy' | 'standard' | 'premium' | 'luxury' | 'ev_adas'
  aluminum_panels?: string[]
  is_ev?: boolean
  adas_features?: string[]
}

export interface Dent {
  id: number
  size: 'dime' | 'nickel' | 'quarter' | 'half_dollar' | 'silver_dollar' | 'oversized'
  zone: 'center' | 'edge' | 'crease' | 'body_line'
  depth: 'shallow' | 'medium' | 'deep' | 'severe'
  base_price: number
  final_price: number
}

export interface RIItem {
  id: number
  operation_code: string
  operation_name: string
  category: string
  base_time_hours: number
  calculated_time_hours: number
  labor_rate: number
  price: number
  scope_min?: string
  scope_typical?: string
  scope_max?: string
}

export interface Panel {
  id: number
  panel_name: string
  display_name: string
  material: 'steel' | 'aluminum' | 'high_strength_steel'
  dents: Dent[]
  ri_items: RIItem[]
  panel_total: number
}

export interface Discovery {
  id: number
  discovery_type: string
  description: string
  additional_time_hours: number
  additional_cost: number
  photo_url?: string
  panel_name?: string
  narrative?: string
  acknowledged: boolean
  created_at: string
}

export interface InsuranceProfile {
  id: number
  carrier_name: string
  labor_rate: number
  pdr_rate_per_dent?: number
  max_dents_per_panel?: number
  requires_photos: boolean
  supplement_email?: string
}

export interface PDREstimate {
  id: number
  estimate_number: string
  status: 'draft' | 'pending' | 'approved' | 'completed'
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_vin?: string
  vehicle_tier: string
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  lead_id?: number
  contact_id?: number
  job_id?: number
  insurance_profile_id?: number
  insurance_profile?: InsuranceProfile
  claim_number?: string
  panels: Panel[]
  dent_total: number
  ri_total: number
  grand_total: number
  expires_at?: string
  created_at: string
  updated_at: string
}

export interface WorkOrder {
  id: number
  estimate_id: number
  work_order_number: string
  status: 'assigned' | 'in_progress' | 'completed'
  assigned_tech_id?: number
  assigned_tech_name?: string
  customer_name: string
  vehicle: string
  panels: Panel[]
  discoveries: Discovery[]
  start_time?: string
  end_time?: string
  total_time_minutes?: number
  created_at: string
}

export interface RILibraryItem {
  operation_code: string
  operation_name: string
  category: string
  base_time_hours: number
  scope_bullets: {
    min: string
    typical: string
    max: string
  }
}

export interface VINDecodeResult {
  year: number
  make: string
  model: string
  vehicle_tier: string
  aluminum_panels: string[]
  is_ev: boolean
  adas_features: string[]
}

// ============ API Functions ============

const pdrApi = {
  // Estimates
  listEstimates: (filters?: Record<string, string | number>) =>
    apiGet<{ estimates: PDREstimate[]; total: number }>('/pdr-estimates', { params: filters }),

  getEstimate: (id: number) =>
    apiGet<PDREstimate>(`/pdr-estimates/${id}`),

  createEstimate: (data: Partial<PDREstimate>) =>
    apiPost<PDREstimate>('/pdr-estimates', data),

  updateEstimate: (id: number, data: Partial<PDREstimate>) =>
    apiPut<PDREstimate>(`/pdr-estimates/${id}`, data),

  deleteEstimate: (id: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${id}`),

  approveEstimate: (id: number, signature?: string) =>
    apiPost<PDREstimate>(`/pdr-estimates/${id}/approve`, { signature }),

  calculateTotals: (id: number) =>
    apiPost<{ dent_total: number; ri_total: number; grand_total: number }>(`/pdr-estimates/${id}/calculate`),

  linkToCRM: (id: number, data: { lead_id?: number; contact_id?: number; job_id?: number }) =>
    apiPut<PDREstimate>(`/pdr-estimates/${id}/link`, data),

  // Panels
  addPanel: (estimateId: number, data: { panel_name: string; material?: string }) =>
    apiPost<Panel>(`/pdr-estimates/${estimateId}/panels`, data),

  updatePanel: (estimateId: number, panelId: number, data: Partial<Panel>) =>
    apiPut<Panel>(`/pdr-estimates/${estimateId}/panels/${panelId}`, data),

  deletePanel: (estimateId: number, panelId: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${estimateId}/panels/${panelId}`),

  // Dents
  addDent: (estimateId: number, panelId: number, data: { size: string; zone: string; depth?: string }) =>
    apiPost<Dent>(`/pdr-estimates/${estimateId}/panels/${panelId}/dents`, data),

  addDentsBatch: (estimateId: number, panelId: number, dents: Array<{ size: string; zone: string; depth?: string; count?: number }>) =>
    apiPost<{ dents: Dent[]; count: number }>(`/pdr-estimates/${estimateId}/panels/${panelId}/dents/batch`, { dents }),

  deleteDent: (estimateId: number, dentId: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${estimateId}/dents/${dentId}`),

  // R&I
  getRILibrary: () =>
    apiGet<{ items: RILibraryItem[] }>('/pdr-estimates/ri-library'),

  getRISuggestions: (estimateId: number, panelId: number) =>
    apiGet<{ suggestions: RILibraryItem[] }>(`/pdr-estimates/${estimateId}/panels/${panelId}/ri-suggestions`),

  addRIFromLibrary: (estimateId: number, panelId: number, operationCode: string) =>
    apiPost<RIItem>(`/pdr-estimates/${estimateId}/panels/${panelId}/ri-from-library`, { operation_code: operationCode }),

  deleteRI: (estimateId: number, riId: number) =>
    apiDelete<{ success: boolean }>(`/pdr-estimates/${estimateId}/ri/${riId}`),

  // VIN Decode
  decodeVIN: (vin: string) =>
    apiGet<VINDecodeResult>(`/pdr-estimates/vin/decode/${vin}`),

  // Insurance Profiles
  getInsuranceProfiles: () =>
    apiGet<{ profiles: InsuranceProfile[] }>('/pdr-estimates/insurance-profiles'),

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
    apiGet<{ photos: Array<{ id: number; url: string; description?: string }> }>(`/pdr-estimates/${estimateId}/photos`),

  // Work Orders
  createWorkOrder: (estimateId: number, techId?: number) =>
    apiPost<WorkOrder>(`/pdr-estimates/${estimateId}/work-order`, { assigned_tech_id: techId }),

  getWorkOrder: (workOrderId: number) =>
    apiGet<WorkOrder>(`/pdr-estimates/work-orders/${workOrderId}`),

  updateWorkOrder: (workOrderId: number, data: Partial<WorkOrder>) =>
    apiPut<WorkOrder>(`/pdr-estimates/work-orders/${workOrderId}`, data),

  addDiscovery: (workOrderId: number, data: {
    discovery_type: string
    description?: string
    additional_time_hours?: number
    additional_cost?: number
    photo_base64?: string
    panel_name?: string
  }) =>
    apiPost<Discovery>(`/pdr-estimates/work-orders/${workOrderId}/discoveries`, data),

  // Supplements
  getSupplement: (estimateId: number) =>
    apiGet<{
      original_total: number
      supplement_total: number
      grand_total: number
      discoveries: Discovery[]
      narrative: string
    }>(`/pdr-estimates/${estimateId}/supplement`),

  // Matrix format
  getMatrix: (estimateId: number) =>
    apiGet<{ matrix: Record<string, unknown> }>(`/pdr-estimates/${estimateId}/matrix`),

  // Leads (for linking)
  searchLeads: (query: string) =>
    apiGet<{ leads: Array<{ id: number; business_name: string; contact_name: string; phone: string }> }>('/leads', { params: { search: query } }),
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

// Panels
export function useAddPanel() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, data }: { estimateId: number; data: { panel_name: string; material?: string } }) =>
      pdrApi.addPanel(estimateId, data),
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

// Dents
export function useAddDent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId, data }: {
      estimateId: number
      panelId: number
      data: { size: string; zone: string; depth?: string }
    }) => pdrApi.addDent(estimateId, panelId, data),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

export function useAddDentsBatch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, panelId, dents }: {
      estimateId: number
      panelId: number
      dents: Array<{ size: string; zone: string; depth?: string; count?: number }>
    }) => pdrApi.addDentsBatch(estimateId, panelId, dents),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

export function useDeleteDent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, dentId }: { estimateId: number; dentId: number }) =>
      pdrApi.deleteDent(estimateId, dentId),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: ['pdr-estimates', estimateId] })
    },
  })
}

// R&I
export function useRILibrary() {
  return useQuery({
    queryKey: ['ri-library'],
    queryFn: () => pdrApi.getRILibrary(),
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
    mutationFn: ({ estimateId, panelId, operationCode }: {
      estimateId: number
      panelId: number
      operationCode: string
    }) => pdrApi.addRIFromLibrary(estimateId, panelId, operationCode),
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

// Insurance Profiles
export function useInsuranceProfiles() {
  return useQuery({
    queryKey: ['insurance-profiles'],
    queryFn: () => pdrApi.getInsuranceProfiles(),
    staleTime: 1000 * 60 * 30, // Cache for 30 minutes
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
      data: {
        discovery_type: string
        description?: string
        additional_time_hours?: number
        additional_cost?: number
        photo_base64?: string
        panel_name?: string
      }
    }) => pdrApi.addDiscovery(workOrderId, data),
    onSuccess: (_, { workOrderId }) => {
      queryClient.invalidateQueries({ queryKey: ['work-orders', workOrderId] })
    },
  })
}

// Supplement
export function useSupplement(estimateId: number | null) {
  return useQuery({
    queryKey: ['supplement', estimateId],
    queryFn: () => pdrApi.getSupplement(estimateId!),
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
