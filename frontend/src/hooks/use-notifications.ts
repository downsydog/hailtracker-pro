/**
 * Work Inbox / Notifications hooks.
 *
 * Aggregates activity feed and attention items from backend.
 * Role-aware: tech/sales see only their scope.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

// Feed item from backend
export interface WorkInboxItem {
  id: string                    // Synthetic ID (e.g., "act:123" or "wf:estimate:88" or "sla:...")
  kind: 'activity' | 'attention' | 'escalation'
  entity: 'estimate' | 'supplement' | 'job' | 'invoice' | 'lead'
  entity_id: number
  title: string
  subtitle: string | null
  timestamp: string             // ISO datetime
  priority_score: number
  priority_reason: string | null
  route: string                 // Existing route to view
  primary_action: {
    key: string
    label: string
    route: string
  } | null
  meta: {
    // For escalations
    severity?: 'warn' | 'high' | 'critical'
    alert_type?: string
    age_days?: number
    age_hours?: number
    // Other meta fields
    [key: string]: unknown
  } | null
}

export interface EscalationsSummary {
  critical: number
  high: number
  warn: number
  total: number
}

export interface WorkInboxSummary {
  critical: number   // priority_score >= 80
  high: number       // priority_score 60-79
  standard: number   // priority_score < 60
  escalations?: EscalationsSummary
}

export interface WorkInboxResponse {
  feed: WorkInboxItem[]
  summary: WorkInboxSummary
}

export interface UseWorkInboxOptions {
  limit?: number
  since?: string        // ISO datetime
  types?: string[]      // Activity type filter
  assignedToMe?: boolean
  escalations?: boolean // Include SLA escalations
  enabled?: boolean
}

/**
 * Fetch work inbox / notifications feed.
 *
 * Combines recent activities with attention items.
 * Refreshes every 60 seconds for near-real-time updates.
 */
export function useWorkInbox(options: UseWorkInboxOptions = {}) {
  const {
    limit = 50,
    since,
    types,
    assignedToMe = false,
    escalations = false,
    enabled = true,
  } = options

  // Build query params
  const params: Record<string, string> = {}
  if (limit !== 50) params.limit = String(limit)
  if (since) params.since = since
  if (types && types.length > 0) params.types = types.join(',')
  if (assignedToMe) params.assigned_to_me = '1'
  if (escalations) params.escalations = '1'

  const queryString = Object.keys(params).length > 0
    ? '?' + new URLSearchParams(params).toString()
    : ''

  const query = useQuery({
    queryKey: queryKeys.workInbox.feed(params),
    queryFn: () => apiGet<WorkInboxResponse>(`/notifications${queryString}`),
    enabled,
    // Refresh periodically for inbox freshness
    refetchInterval: 60000, // 60 seconds
    refetchOnWindowFocus: true,
    staleTime: 30000, // Consider stale after 30 seconds
  })

  const defaultEscalationsSummary: EscalationsSummary = { critical: 0, high: 0, warn: 0, total: 0 }

  return {
    ...query,
    feed: query.data?.feed || [],
    summary: query.data?.summary || { critical: 0, high: 0, standard: 0 },
    escalationsSummary: query.data?.summary?.escalations || defaultEscalationsSummary,
    lastUpdated: query.dataUpdatedAt ? new Date(query.dataUpdatedAt) : null,
  }
}

/**
 * Send SLA nudge mutation.
 */
export interface SendNudgeParams {
  alert_type: string
  entity: string
  entity_id: number
  to?: string
  to_internal?: boolean
  subject?: string
  message?: string
}

export interface SendNudgeResponse {
  ok: boolean
  recipients?: string[]
  error?: string
}

export function useSendNudge() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (params: SendNudgeParams) =>
      apiPost<SendNudgeResponse>('/notifications/nudge', params),
    onSuccess: () => {
      // Invalidate work inbox to reflect any logged activity
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
    },
  })
}

/**
 * Query keys for manual invalidation.
 */
export const workInboxQueryKeys = {
  all: queryKeys.workInbox.all,
  feed: queryKeys.workInbox.feed,
}

/**
 * Priority badge variant helper.
 * Uses available Badge variants: default, secondary, destructive, outline
 */
export function getPriorityBadgeVariant(score: number): 'destructive' | 'default' | 'secondary' {
  if (score >= 80) return 'destructive'
  if (score >= 60) return 'default'  // Uses primary color for high priority
  return 'secondary'
}

/**
 * Severity badge variant helper for escalations.
 */
export function getSeverityBadgeVariant(severity: string | undefined): 'destructive' | 'default' | 'secondary' {
  if (severity === 'critical') return 'destructive'
  if (severity === 'high') return 'default'
  return 'secondary'
}

/**
 * Priority label helper.
 */
export function getPriorityLabel(score: number): string {
  if (score >= 80) return 'Critical'
  if (score >= 60) return 'High'
  return 'Standard'
}

/**
 * Severity label helper.
 */
export function getSeverityLabel(severity: string | undefined): string {
  switch (severity) {
    case 'critical': return 'Critical'
    case 'high': return 'High'
    case 'warn': return 'Warning'
    default: return 'Standard'
  }
}

/**
 * Format relative time (e.g., "5m ago", "2h ago", "3d ago").
 */
export function formatRelativeTime(timestamp: string | null | undefined): string {
  if (!timestamp) return ''

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

/**
 * Format age display (e.g., "5 days", "12 hours").
 */
export function formatAge(ageDays?: number, ageHours?: number): string {
  if (ageDays !== undefined && ageDays > 0) {
    return `${ageDays}d`
  }
  if (ageHours !== undefined && ageHours > 0) {
    return `${ageHours}h`
  }
  return ''
}

/**
 * Entity icon helper (returns lucide icon name).
 */
export function getEntityIcon(entity: WorkInboxItem['entity']): string {
  switch (entity) {
    case 'estimate': return 'FileText'
    case 'supplement': return 'FilePlus'
    case 'job': return 'Wrench'
    case 'invoice': return 'Receipt'
    case 'lead': return 'Users'
    default: return 'Bell'
  }
}
