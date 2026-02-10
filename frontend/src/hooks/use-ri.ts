/**
 * R&I Justification Engine hooks.
 *
 * Phase 6B: Frontend integration for R&I operations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiPatch, apiDelete } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

// Types for R&I catalog
export interface RIStep {
  id: number
  tenant_id: number
  operation_id: number
  step_code: string
  label: string
  description?: string | null
  base_time_hours: number
  required: boolean
  denial_resistance: 'high' | 'medium' | 'low'
  risk_tags: string[]
  order_index: number
  created_at?: string
  updated_at?: string
}

export interface RIOperation {
  id: number
  tenant_id: number
  code: string
  display_name: string
  category: 'interior' | 'exterior' | 'structural'
  description?: string | null
  risk_level: 'low' | 'medium' | 'high'
  // Stage 6H-C fields
  difficulty_level?: 'economy' | 'standard' | 'luxury' | 'exotic'
  common_denials?: string[]
  default_required_steps?: string[]
  is_seeded?: boolean
  steps?: RIStep[]
  created_at?: string
  updated_at?: string
}

export interface RIModifier {
  id: number
  tenant_id: number
  modifier_code: string
  label: string
  adds_time_hours: number
  reason?: string | null
  category: 'risk' | 'complexity' | 'material'
  created_at?: string
  updated_at?: string
}

export interface RICatalog {
  operations: RIOperation[]
  modifiers: RIModifier[]
}

// Types for estimate R&I
export interface EstimateRIStepBreakdown {
  step_id: number
  step_code: string
  label: string
  description?: string | null
  base_time_hours: number
  effective_time_hours: number
  included: boolean
  required: boolean
  denial_resistance: string
  risk_tags: string[]
  override_notes?: string | null
}

export interface EstimateRIModifierBreakdown {
  modifier_id: number
  modifier_code: string
  label: string
  adds_time_hours: number
  reason?: string | null
  category: string
  notes?: string | null
}

export interface EstimateRIOperationSummary {
  estimate_ri_operation_id: number
  operation_id: number
  code: string
  display_name: string
  category: string
  risk_level: string
  description?: string | null
  steps: EstimateRIStepBreakdown[]
  modifiers: EstimateRIModifierBreakdown[]
  totals: {
    base_steps_time: number
    modifiers_time: number
    total_time: number
  }
  notes?: string | null
  justification_text: string
}

// Denial pack types (Stage 6F + 6G ammo)
export interface RIDenialPack {
  overall_score: number
  overall_rating: 'high' | 'medium' | 'low'
  resistance_counts: {
    high: number
    medium: number
    low: number
  }
  risk_tags: string[]
  required_steps_count: number
  optional_steps_count: number
  high_resistance_steps: Array<{
    step_code: string
    label: string
    operation_name: string
    risk_tags: string[]
  }>
  summary_text: string
  // Stage 6G: Denial Ammo
  adjuster_bullets?: string[]
  scope_clarifier?: string
  top_defensible_steps?: Array<{
    step_code: string
    operation_name: string
    label: string
    denial_resistance: 'high' | 'medium' | 'low'
    base_time_hours: number
    cite_line: string
    risk_tags?: string[]
  }>
  copy_blocks?: {
    short: string
    full: string
  }
}

export interface EstimateRISummary {
  estimate_id: number
  operations: EstimateRIOperationSummary[]
  total_ri_time_hours: number
  operation_count: number
  // Labor rate info (Stage 6E)
  ri_labor_rate?: number
  ri_labor_rate_source?: 'default' | 'rule' | 'override'
  ri_labor_rate_rule_id?: string | null
  ri_labor_rate_rule_name?: string | null
  ri_labor_rate_reason?: string
  total_ri_cost?: number
  // Denial pack (Stage 6F)
  ri_denial_pack?: RIDenialPack
}

// Query keys
export const riQueryKeys = {
  catalog: ['ri-catalog'] as const,
  estimateRI: (estimateId: number) => ['estimate-ri', estimateId] as const,
}

/**
 * Fetch R&I catalog (operations, steps, modifiers).
 */
export function useRiCatalog() {
  return useQuery({
    queryKey: riQueryKeys.catalog,
    queryFn: () => apiGet<RICatalog>('/ri/catalog'),
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  })
}

/**
 * Fetch R&I summary for an estimate.
 */
export function useEstimateRI(estimateId: number) {
  return useQuery({
    queryKey: riQueryKeys.estimateRI(estimateId),
    queryFn: () => apiGet<EstimateRISummary>(`/pdr-estimates/${estimateId}/ri`),
    enabled: !!estimateId,
  })
}

/**
 * Add an R&I operation to an estimate.
 */
export function useAddEstimateRI(estimateId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: {
      operationCode: string
      selectedModifierCodes?: string[]
      stepOverrides?: Array<{
        step_id: number
        included?: boolean
        time_override_hours?: number
        notes?: string
      }>
      notes?: string
    }) =>
      apiPost<{ success: boolean; estimate_ri_operation_id: number }>(
        `/pdr-estimates/${estimateId}/ri`,
        {
          operation_code: data.operationCode,
          selected_modifier_codes: data.selectedModifierCodes || [],
          step_overrides: data.stepOverrides || [],
          notes: data.notes,
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.estimateRI(estimateId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['estimate', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
    },
  })
}

/**
 * Update an R&I operation on an estimate.
 */
export function useUpdateEstimateRI(estimateId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: {
      estimateRiOpId: number
      selectedModifierCodes?: string[]
      stepOverrides?: Array<{
        step_id: number
        included?: boolean
        time_override_hours?: number
        notes?: string
      }>
      notes?: string
    }) =>
      apiPatch<{ success: boolean }>(
        `/pdr-estimates/${estimateId}/ri/${data.estimateRiOpId}`,
        {
          selected_modifier_codes: data.selectedModifierCodes,
          step_overrides: data.stepOverrides,
          notes: data.notes,
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.estimateRI(estimateId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['estimate', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
    },
  })
}

/**
 * Remove an R&I operation from an estimate.
 */
export function useRemoveEstimateRI(estimateId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (estimateRiOpId: number) =>
      apiDelete<{ success: boolean }>(
        `/pdr-estimates/${estimateId}/ri/${estimateRiOpId}`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.estimateRI(estimateId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['estimate', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
    },
  })
}

// =============================================================================
// STAGE 6H-A: DENIAL SIMULATOR TYPES & HOOKS
// =============================================================================

export interface DenialCode {
  code: string
  label: string
  description: string
}

export interface CitedStep {
  step_code: string
  operation_name: string
  label: string
  hours: number
  cite_line: string
  denial_resistance: 'high' | 'medium' | 'low'
  required: boolean
  risk_tags: string[]
}

export interface DenialRebuttal {
  success: boolean
  denial_code: string
  insurer_claim: string
  rebuttal_summary: string
  rebuttal_bullets: string[]
  cited_steps: CitedStep[]
  risk_exposure: string[]
  copy_blocks: {
    short: string
    full: string
  }
}

/**
 * Get available denial codes.
 */
export function useDenialCodes(estimateId: number) {
  return useQuery({
    queryKey: ['denial-codes', estimateId],
    queryFn: () => apiGet<{ codes: DenialCode[] }>(`/pdr-estimates/${estimateId}/ri/denial-simulator/codes`),
    enabled: !!estimateId,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  })
}

/**
 * Generate a denial rebuttal.
 */
export function useDenialSimulator(estimateId: number) {
  return useMutation({
    mutationFn: (denialCode: string) =>
      apiPost<DenialRebuttal>(
        `/pdr-estimates/${estimateId}/ri/denial-simulator`,
        { denial_code: denialCode }
      ),
  })
}

// =============================================================================
// STAGE 6H-B: SUPPLEMENT WRITER TYPES & HOOKS
// =============================================================================

export interface SupplementLetter {
  success: boolean
  letter_text: string
  estimate_number: string
  claim_number: string
  vehicle: string
  customer_name: string
  total_ri_hours: number
  total_ri_cost: number
  labor_rate: number
  labor_source: string
  denial_code?: string | null
}

/**
 * Generate a supplement letter.
 */
export function useSupplementWriter(estimateId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (denialCode?: string) =>
      apiPost<SupplementLetter>(
        `/pdr-estimates/${estimateId}/ri/supplement-preview`,
        { denial_code: denialCode }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['estimate-activities', estimateId] })
    },
  })
}

// =============================================================================
// STAGE 6H-C: R&I CATALOG BUILDER TYPES & HOOKS
// =============================================================================

export interface CatalogValidation {
  valid: boolean
  warnings: string[]
  errors: string[]
  denial_resistance_score: number
  step_counts: {
    high: number
    medium: number
    low: number
    total: number
  }
}

export interface CreateOperationData {
  code: string
  display_name: string
  category: 'interior' | 'exterior' | 'structural'
  description?: string
  risk_level: 'low' | 'medium' | 'high'
  difficulty_level?: 'economy' | 'standard' | 'luxury' | 'exotic'
  steps: Array<{
    step_code: string
    label: string
    description?: string
    base_time_hours: number
    required: boolean
    denial_resistance: 'high' | 'medium' | 'low'
    risk_tags: string[]
    oem_dependency?: boolean
    safety_critical?: boolean
  }>
}

export interface CreateStepData {
  step_code?: string
  label: string
  description?: string
  base_time_hours: number
  required: boolean
  denial_resistance: 'high' | 'medium' | 'low'
  risk_tags: string[]
  oem_dependency?: boolean
  safety_critical?: boolean
}

/**
 * Create a new R&I operation.
 */
export function useCreateRIOperation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateOperationData) =>
      apiPost<{ success: boolean; operation_id: number }>(
        '/ri/catalog/operation',
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.catalog })
    },
  })
}

/**
 * Delete an R&I operation.
 */
export function useDeleteRIOperation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (operationId: number) =>
      apiDelete<{ success: boolean }>(
        `/ri/catalog/operation/${operationId}`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.catalog })
    },
  })
}

/**
 * Add a step to an R&I operation.
 */
export function useAddRIStep(operationId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateStepData) =>
      apiPost<{ success: boolean; step_id: number }>(
        `/ri/catalog/operation/${operationId}/step`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.catalog })
    },
  })
}

/**
 * Delete an R&I step.
 */
export function useDeleteRIStep() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (stepId: number) =>
      apiDelete<{ success: boolean }>(
        `/ri/catalog/step/${stepId}`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riQueryKeys.catalog })
    },
  })
}

/**
 * Validate an R&I operation before saving.
 */
export function useValidateRIOperation() {
  return useMutation({
    mutationFn: (data: CreateOperationData) =>
      apiPost<CatalogValidation>(
        '/ri/catalog/validate',
        data
      ),
  })
}
