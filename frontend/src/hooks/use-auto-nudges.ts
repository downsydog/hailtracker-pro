/**
 * Auto-Nudges Settings Hook
 *
 * Manages auto-nudges configuration for the tenant.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPatch, apiPost } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

// Auto-nudges configuration types
export interface AutoNudgesRecipients {
  mode: 'roles' | 'explicit'
  roles: string[]
  emails: string[]
}

export interface AutoNudgesThresholds {
  send_if_at_least: {
    warn: number
    high: number
    critical: number
  }
  include_types: string[] | null
}

export interface AutoNudgesRateLimits {
  per_entity_per_type_hours: {
    critical: number
    high: number
    warn: number
  }
  max_emails_per_run: number
}

export interface AutoNudgesConfig {
  enabled: boolean
  digest_schedule: 'daily' | 'hourly'
  digest_time_local: string
  recipients: AutoNudgesRecipients
  thresholds: AutoNudgesThresholds
  rate_limits: AutoNudgesRateLimits
  dry_run: boolean
}

export interface AutoNudgesSettingsResponse {
  config: AutoNudgesConfig
  timezone: string
}

export interface AutoNudgesTestResponse {
  would_send: boolean
  reason: string
  recipients: string[]
  escalation_counts: {
    critical: number
    high: number
    warn: number
  }
  sample_items: Array<{
    severity: string
    title: string
    subtitle: string | null
    alert_type: string
  }>
  config: AutoNudgesConfig
}

/**
 * Fetch auto-nudges settings.
 */
export function useAutoNudgesSettings() {
  return useQuery({
    queryKey: queryKeys.settings.autoNudges,
    queryFn: () => apiGet<AutoNudgesSettingsResponse>('/settings/auto-nudges'),
    staleTime: 60000,
  })
}

/**
 * Update auto-nudges settings.
 */
export function useUpdateAutoNudges() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { config?: Partial<AutoNudgesConfig>; timezone?: string }) =>
      apiPatch<AutoNudgesSettingsResponse>('/settings/auto-nudges', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings.autoNudges })
    },
  })
}

/**
 * Test auto-nudges configuration.
 */
export function useTestAutoNudges() {
  return useMutation({
    mutationFn: () => apiPost<AutoNudgesTestResponse>('/settings/auto-nudges/test'),
  })
}

// Alert type options for filtering
export const ALERT_TYPE_OPTIONS = [
  { value: 'insurer_waiting', label: 'Insurer Waiting' },
  { value: 'needs_revision', label: 'Needs Revision' },
  { value: 'draft_supplement', label: 'Draft Supplement' },
  { value: 'stale_job', label: 'Stale Job' },
  { value: 'overdue_invoice', label: 'Overdue Invoice' },
  { value: 'lead_followup', label: 'Lead Follow-up' },
]

// Role options for recipient filtering
export const ROLE_OPTIONS = [
  { value: 'owner', label: 'Owner' },
  { value: 'manager', label: 'Manager' },
  { value: 'desk', label: 'Desk' },
  { value: 'estimator', label: 'Estimator' },
  { value: 'tech', label: 'Technician' },
  { value: 'sales', label: 'Sales' },
]

// Common timezone options
export const TIMEZONE_OPTIONS = [
  { value: 'America/New_York', label: 'Eastern (ET)' },
  { value: 'America/Chicago', label: 'Central (CT)' },
  { value: 'America/Denver', label: 'Mountain (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific (PT)' },
  { value: 'America/Phoenix', label: 'Arizona (no DST)' },
]
