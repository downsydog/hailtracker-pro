/**
 * Labor Rate hooks for tenant configurable R&I rates.
 *
 * Stage 6E: Tenant Labor Rate Engine.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPatch, apiPost } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

// Types for labor rate configuration
export interface LaborRateRule {
  id: string
  name: string
  country: string
  state?: string | null
  zip_prefixes?: string[]
  city_keywords?: string[]
  effective_from?: string | null
  effective_to?: string | null
  ri_rate: number
}

export interface LaborRatesConfig {
  default_ri_rate: number
  currency: 'USD' | 'CAD'
  rules: LaborRateRule[]
}

export interface LaborRatesResponse {
  config: LaborRatesConfig
}

export interface LaborRatePreviewRequest {
  state?: string
  zip_code?: string
  date?: string
}

export interface LaborRatePreviewResponse {
  rate: number
  source: 'default' | 'rule' | 'override'
  rule_id: string | null
  rule_name: string | null
  reason: string
}

export interface LaborRateOverrideRequest {
  ri_labor_rate: number | null
}

export interface LaborRateOverrideResponse {
  success: boolean
  estimate_id: number
  old_rate: number | null
  new_rate: number | null
  source: string
}

/**
 * Fetch labor rates configuration.
 */
export function useLaborRatesSettings() {
  return useQuery({
    queryKey: queryKeys.settings.laborRates,
    queryFn: () => apiGet<LaborRatesResponse>('/settings/labor-rates'),
    staleTime: 60000, // 1 minute
  })
}

/**
 * Update labor rates configuration.
 */
export function useUpdateLaborRates() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (config: Partial<LaborRatesConfig>) =>
      apiPatch<LaborRatesResponse>('/settings/labor-rates', { config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.laborRates })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}

/**
 * Preview labor rate resolution for testing.
 */
export function usePreviewLaborRate() {
  return useMutation({
    mutationFn: (data: LaborRatePreviewRequest) =>
      apiPost<LaborRatePreviewResponse>('/settings/labor-rates/preview', data),
  })
}

/**
 * Get resolved labor rate for an estimate.
 */
export function useEstimateLaborRate(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-labor-rate', estimateId],
    queryFn: () => apiGet<LaborRatePreviewResponse>(`/pdr-estimates/${estimateId}/labor-rate`),
    enabled: !!estimateId,
    staleTime: 30000, // 30 seconds
  })
}

/**
 * Set or clear labor rate override on an estimate.
 */
export function useSetLaborRateOverride(estimateId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: LaborRateOverrideRequest) =>
      apiPost<LaborRateOverrideResponse>(
        `/pdr-estimates/${estimateId}/labor-rate/override`,
        data
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['estimate-labor-rate', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate-ri', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate', estimateId] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}

// Default configuration for new tenants
export const DEFAULT_LABOR_RATES_CONFIG: LaborRatesConfig = {
  default_ri_rate: 85,
  currency: 'USD',
  rules: [],
}

// Common US states for dropdown
export const US_STATES = [
  { value: 'AL', label: 'Alabama' },
  { value: 'AK', label: 'Alaska' },
  { value: 'AZ', label: 'Arizona' },
  { value: 'AR', label: 'Arkansas' },
  { value: 'CA', label: 'California' },
  { value: 'CO', label: 'Colorado' },
  { value: 'CT', label: 'Connecticut' },
  { value: 'DE', label: 'Delaware' },
  { value: 'FL', label: 'Florida' },
  { value: 'GA', label: 'Georgia' },
  { value: 'HI', label: 'Hawaii' },
  { value: 'ID', label: 'Idaho' },
  { value: 'IL', label: 'Illinois' },
  { value: 'IN', label: 'Indiana' },
  { value: 'IA', label: 'Iowa' },
  { value: 'KS', label: 'Kansas' },
  { value: 'KY', label: 'Kentucky' },
  { value: 'LA', label: 'Louisiana' },
  { value: 'ME', label: 'Maine' },
  { value: 'MD', label: 'Maryland' },
  { value: 'MA', label: 'Massachusetts' },
  { value: 'MI', label: 'Michigan' },
  { value: 'MN', label: 'Minnesota' },
  { value: 'MS', label: 'Mississippi' },
  { value: 'MO', label: 'Missouri' },
  { value: 'MT', label: 'Montana' },
  { value: 'NE', label: 'Nebraska' },
  { value: 'NV', label: 'Nevada' },
  { value: 'NH', label: 'New Hampshire' },
  { value: 'NJ', label: 'New Jersey' },
  { value: 'NM', label: 'New Mexico' },
  { value: 'NY', label: 'New York' },
  { value: 'NC', label: 'North Carolina' },
  { value: 'ND', label: 'North Dakota' },
  { value: 'OH', label: 'Ohio' },
  { value: 'OK', label: 'Oklahoma' },
  { value: 'OR', label: 'Oregon' },
  { value: 'PA', label: 'Pennsylvania' },
  { value: 'RI', label: 'Rhode Island' },
  { value: 'SC', label: 'South Carolina' },
  { value: 'SD', label: 'South Dakota' },
  { value: 'TN', label: 'Tennessee' },
  { value: 'TX', label: 'Texas' },
  { value: 'UT', label: 'Utah' },
  { value: 'VT', label: 'Vermont' },
  { value: 'VA', label: 'Virginia' },
  { value: 'WA', label: 'Washington' },
  { value: 'WV', label: 'West Virginia' },
  { value: 'WI', label: 'Wisconsin' },
  { value: 'WY', label: 'Wyoming' },
]
