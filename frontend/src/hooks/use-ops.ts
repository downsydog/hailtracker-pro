/**
 * Ops Command Center hooks.
 *
 * Single aggregation hook that reuses existing models/services on backend.
 * No duplicate data fetching - efficiently aggregates for ops dashboard.
 */

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/api/client'
import { queryKeys } from '@/lib/queryKeys'

// Types for ops overview response
export interface NeedsAttentionItem {
  type: 'estimate' | 'job' | 'invoice' | 'lead'
  id: number
  identifier: string
  customer_name?: string
  vehicle_display?: string
  status?: string
  customer_status?: string
  insurer_status?: string
  is_overdue?: boolean
  payer_name?: string
  payer_type?: string
  total_price?: number
  total_amount?: number
  total?: number
  balance_due?: number
  scheduled_date?: string
  due_at?: string
  assigned_tech?: number
  tech_name?: string
  primary_action?: {
    key: string
    label: string
    description?: string
  }
  priority_score?: number  // Higher = more urgent (0-100)
  priority_reason?: string | null  // Human-readable urgency explanation
  updated_at?: string
  // Job blocker info (Stage 5G, extended with parts in 5O)
  is_blocked?: boolean
  blocker_info?: {
    issue_type: string
    notes: string
    flagged_at: string
    parts?: PartsInfo | null
  } | null
}

export interface JobStats {
  scheduled: number
  in_progress: number
  completed: number
  cancelled: number
}

export interface InvoiceStats {
  draft: number
  draft_total: number
  issued: number
  issued_balance: number
  partial_paid: number
  partial_balance: number
  paid: number
  void: number
  overdue: number
  overdue_total: number
}

export interface BottleneckItem {
  id: number
  estimate_number: string
  customer_name: string
  insurance_company: string
  insurer_status: string
  days_waiting: number
  submitted_at: string | null
  total_price: number
}

export interface FollowupLead {
  id: number
  business_name: string
  contact_name: string
  phone: string
  status: string
  source: string
  created_at: string
}

export interface TeamMember {
  id: number
  name: string
  role: string
}

// Stage 5O: Parts blocker info (extended Stage 5P)
export interface PartsInfo {
  ordered: boolean
  vendor?: string | null
  po_number?: string | null
  eta?: string | null
  // Stage 5P fields
  parts_status?: 'needed' | 'approved_to_order' | 'ordered' | 'shipped' | 'received' | 'installed' | 'exception' | null
  approved_to_order?: boolean
  approved_amount?: number | null
  parts_notes?: string | null
}

// Stage 5P: Valid parts status values
export const PARTS_STATUS_OPTIONS = [
  { value: 'needed', label: 'Needed', color: 'bg-gray-100 text-gray-800' },
  { value: 'approved_to_order', label: 'Approved', color: 'bg-blue-100 text-blue-800' },
  { value: 'ordered', label: 'Ordered', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'shipped', label: 'Shipped', color: 'bg-purple-100 text-purple-800' },
  { value: 'received', label: 'Received', color: 'bg-green-100 text-green-800' },
  { value: 'installed', label: 'Installed', color: 'bg-emerald-100 text-emerald-800' },
  { value: 'exception', label: 'Exception', color: 'bg-red-100 text-red-800' },
] as const

// Stage 5H: Dispatch Inbox item (extended with parts in 5O)
export interface DispatchInboxItem {
  id: number
  job_number: string
  status: string
  scheduled_date?: string | null
  assigned_tech?: number | null
  tech_name?: string | null
  customer_name?: string
  vehicle_display?: string
  is_blocked?: boolean
  blocker_info?: {
    issue_type: string
    notes: string
    flagged_at: string
    parts?: PartsInfo | null
  } | null
  age_hours?: number | null
  primary_action?: {
    key: string
    label: string
  }
  priority_score: number
  priority_reason: string
  updated_at?: string
}

// Stage 5H: Tech load stats
export interface TechLoad {
  tech_id: number
  tech_name: string
  scheduled_today: number
  in_progress: number
  blocked: number
  total_assigned: number
  // Stage 5N: Current job and check-in info
  in_progress_job?: {
    job_id: number
    job_number: string
  } | null
  last_checkin?: {
    job_id: number
    job_number: string
    location: 'shop' | 'field' | null
    at: string
  } | null
}

// Stage 5I: Supplement queue item
export interface SupplementQueueItem {
  estimate_id: number
  estimate_number: string
  supplement_id: number
  supplement_number: number
  status: 'draft' | 'sent'
  discovery_type: string
  delta_amount: number
  customer_name?: string
  created_at?: string
  sent_at?: string | null
  days_open: number
  priority_score: number
  priority_reason: string
}

// Stage 5I: Revisions queue item
export interface RevisionsQueueItem {
  estimate_id: number
  estimate_number: string
  customer_name?: string
  insurance_company?: string
  insurer_status: 'needs_revision' | 'submitted'
  submitted_at?: string | null
  days_waiting: number
  total_price: number
  priority_score: number
  priority_reason: string
}

// Stage 5I: Revenue at risk summary
export interface RevenueAtRisk {
  needs_revision_total: number
  needs_revision_count: number
  submitted_waiting_total: number
  submitted_waiting_count: number
  draft_supplements_total: number
  draft_supplements_count: number
}

// Stage 5M: Dispatch suggestion for auto-assign
export interface DispatchSuggestion {
  job_id: number
  job_number: string
  scheduled_date?: string | null
  status: string
  priority_score: number
  priority_reason?: string | null
  suggested_tech_id: number | null
  suggested_tech_name: string | null
  confidence: number
  reasons: string[]
  alternatives: Array<{
    tech_id: number
    tech_name: string
    score: number
    reason: string
  }>
}

// Stage 5S: Parts pricing preview (read-only context)
export interface PartsPricingPreview {
  low_estimate?: number | null
  typical_estimate?: number | null
  high_estimate?: number | null
  source: 'historical' | 'vendor_table' | 'manual' | 'unknown'
  confidence: 'high' | 'medium' | 'low'
  notes?: string | null
}

// Stage 5Q: Part Request item
export interface PartRequestItem {
  id: number
  tenant_id: number
  estimate_id?: number | null
  job_id?: number | null
  description: string
  part_number?: string | null
  qty: number
  parts_status: string
  approved_to_order: boolean
  approved_amount?: number | null
  approved_by?: number | null
  approved_at?: string | null
  approval_notes?: string | null  // Stage 5T
  vendor?: string | null
  po_number?: string | null
  eta?: string | null
  notes?: string | null
  priority: number
  priority_reason?: string | null  // Stage 5V: priority reason from attention
  priority_score?: number  // Stage 5V: priority score for attention items
  is_overdue: boolean
  created_at?: string
  updated_at?: string
  created_by?: number | null
  // Enriched fields from job
  job_number?: string
  customer_name?: string
  vehicle_display?: string
  tech_name?: string | null
  // Stage 5S: Pricing preview
  pricing_preview?: PartsPricingPreview
  // Stage 5U: Timeline fields
  status_updated_at?: string | null
  status_updated_by?: number | null
  ordered_at?: string | null
  shipped_at?: string | null
  received_at?: string | null
  installed_at?: string | null
  previous_status?: string | null
  allowed_transitions?: string[]
}

// Stage 5Q: Parts requests counts by status
export interface PartsRequestsCounts {
  needed: number
  approved_to_order: number
  ordered: number
  shipped: number
  received: number
  installed: number
  exception: number
}

// Stage 5S: Parts exposure summary
export interface PartsExposure {
  total_typical: number
  total_low: number
  total_high: number
  count_priced: number
  count_unknown: number
}

// Stage 5V: Parts request attention item (extends PartRequestItem with severity)
export interface PartsRequestAttentionItem extends PartRequestItem {
  severity: 'critical' | 'high' | 'warn'
  age_days?: number
  eta_days_overdue?: number
}

// Stage 5V: Parts requests stats summary
export interface PartsRequestsStats {
  counts_by_status: PartsRequestsCounts
  counts_by_severity: {
    critical: number
    high: number
    warn: number
  }
  total_open: number
  total_attention: number
  total_approved_exposure: number
}

export interface OpsOverview {
  needs_attention: NeedsAttentionItem[]
  job_stats: JobStats
  invoice_stats: InvoiceStats
  bottlenecks: BottleneckItem[]
  leads_needing_followup: FollowupLead[]
  team: TeamMember[]
  dispatch_inbox: DispatchInboxItem[]
  tech_load: TechLoad[]
  dispatch_suggestions: DispatchSuggestion[]
  supplements_queue: SupplementQueueItem[]
  revisions_queue: RevisionsQueueItem[]
  revenue_at_risk: RevenueAtRisk
  // Stage 5Q: Parts requests
  parts_requests?: PartRequestItem[]
  parts_requests_counts?: PartsRequestsCounts
  // Stage 5S: Parts exposure
  parts_exposure?: PartsExposure
  // Stage 5V: Parts requests attention + stats
  parts_requests_attention?: PartsRequestAttentionItem[]
  parts_requests_stats?: PartsRequestsStats
}

/**
 * Fetch ops overview data - single aggregated endpoint.
 *
 * Reuses existing models and WorkflowService on backend.
 * Refreshes every 30 seconds for near-real-time updates.
 */
export function useOpsOverview() {
  const query = useQuery({
    queryKey: queryKeys.opsOverview,
    queryFn: () => apiGet<OpsOverview>('/ops/overview'),
    // Refetch periodically for dashboard freshness
    refetchInterval: 30000, // 30 seconds
    refetchOnWindowFocus: true,
    staleTime: 15000, // Consider stale after 15 seconds
  })

  return {
    ...query,
    // Add dataUpdatedAt for "Updated just now" display
    lastUpdated: query.dataUpdatedAt ? new Date(query.dataUpdatedAt) : null,
  }
}

/**
 * Query key for manual invalidation.
 */
export const opsQueryKeys = {
  overview: queryKeys.opsOverview,
}
