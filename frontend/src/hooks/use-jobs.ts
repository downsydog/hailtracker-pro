import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi, JobsQueryParams, CreateJobData, UpdateJobData } from '@/api/jobs'
import { apiGet, apiPost, apiPatch } from '@/api/client'
import { useAuth } from '@/contexts/auth-context'
import { queryKeys } from '@/lib/queryKeys'

// Issue types for job blockers
export const JOB_ISSUE_TYPES = [
  { value: 'waiting_on_parts', label: 'Waiting on Parts' },
  { value: 'needs_tools', label: 'Needs Tools' },
  { value: 'customer_no_show', label: 'Customer No-Show' },
  { value: 'access_problem', label: 'Access Problem' },
  { value: 'other', label: 'Other Issue' },
] as const

export type JobIssueType = typeof JOB_ISSUE_TYPES[number]['value']

export function useJobs(filters?: JobsQueryParams) {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => jobsApi.list(filters),
  })
}

/**
 * Fetch jobs assigned to the current user (for tech dashboard).
 * Only returns scheduled and in_progress jobs by default.
 */
export function useMyJobs(statusFilter?: string[]) {
  const { user } = useAuth()
  const techId = user?.id as number | undefined

  return useQuery({
    queryKey: ['jobs', 'my-jobs', techId, statusFilter],
    queryFn: () => jobsApi.list({
      tech_id: techId,
      status: statusFilter?.join(','),
    }),
    enabled: !!techId,
    refetchOnWindowFocus: true,
    staleTime: 30000,
  })
}

export function useJob(id: number) {
  return useQuery({
    queryKey: ['jobs', id],
    queryFn: () => jobsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateJobData) => jobsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}

export function useUpdateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateJobData }) =>
      jobsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.job(id) })
    },
  })
}

export function useDeleteJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => jobsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}

export function useUpdateJobStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, status, notes }: { id: number; status: string; notes?: string }) =>
      jobsApi.updateStatus(id, status, notes),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      // Instant refresh: invalidate ops dashboard and workflow
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow.job(id) })
    },
  })
}

export function useAssignJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, techId }: { id: number; techId: number }) =>
      jobsApi.assign(id, techId),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}

// Parts info when flagging a job issue (Stage 5P extended)
export interface FlagIssuePartsData {
  partsOrdered?: boolean
  vendor?: string
  poNumber?: string
  eta?: string
  // Stage 5P fields
  partsStatus?: string
  approvedToOrder?: boolean
  approvedAmount?: number
  partsNotes?: string
}

/**
 * Flag a job issue (blocker/needs help).
 * Used by tech portal to communicate blockers to office.
 * Extended in Stage 5O to support parts fields for waiting_on_parts.
 */
export function useFlagJobIssue() {
  const queryClient = useQueryClient()
  const { user } = useAuth()

  return useMutation({
    mutationFn: ({ id, issueType, notes, parts }: {
      id: number
      issueType: JobIssueType
      notes?: string
      parts?: FlagIssuePartsData
    }) =>
      apiPost<{ success: boolean; message: string }>(`/jobs/${id}/flag-issue`, {
        issue_type: issueType,
        notes: notes || '',
        parts_ordered: parts?.partsOrdered || false,
        vendor: parts?.vendor || '',
        po_number: parts?.poNumber || '',
        eta: parts?.eta || '',
        // Stage 5P fields
        parts_status: parts?.partsStatus || 'needed',
        approved_to_order: parts?.approvedToOrder || false,
        approved_amount: parts?.approvedAmount || null,
        parts_notes: parts?.partsNotes || '',
      }),
    onSuccess: (_, { id }) => {
      // Invalidate relevant queries (Stage 5O.1: include workInbox)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      queryClient.invalidateQueries({ queryKey: ['jobs', 'my-jobs', user?.id] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
    },
  })
}

/**
 * Clear a job blocker (dispatch roles only).
 */
export function useClearJobBlocker() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, notes, clearedReason }: { id: number; notes?: string; clearedReason?: string }) =>
      apiPost<{ success: boolean; message: string }>(`/jobs/${id}/clear-blocker`, {
        notes: notes || '',
        cleared_reason: clearedReason || 'resolved',
      }),
    onSuccess: (_, { id }) => {
      // Stage 5O.1: include workInbox in invalidation
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
    },
  })
}

// Parts update data for job blockers (Stage 5P extended)
export interface UpdateBlockerData {
  partsOrdered?: boolean
  vendor?: string
  poNumber?: string
  eta?: string
  notes?: string
  // Stage 5P fields
  partsStatus?: string
  approvedToOrder?: boolean
  approvedAmount?: number
  partsNotes?: string
}

/**
 * Update a job blocker (dispatch roles only) - set ETA, mark parts ordered, etc.
 */
export function useUpdateJobBlocker() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateBlockerData }) =>
      apiPost<{ success: boolean; message: string; parts: object }>(`/jobs/${id}/update-blocker`, {
        parts_ordered: data.partsOrdered || false,
        vendor: data.vendor || '',
        po_number: data.poNumber || '',
        eta: data.eta || '',
        notes: data.notes || '',
        // Stage 5P fields
        parts_status: data.partsStatus || null,
        approved_to_order: data.approvedToOrder || false,
        approved_amount: data.approvedAmount || null,
        parts_notes: data.partsNotes || '',
      }),
    onSuccess: (_, { id }) => {
      // Stage 5O.1: include workInbox in invalidation
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
    },
  })
}

// Location types for check-in
export type JobCheckInLocation = 'shop' | 'field' | null

/**
 * Check-in to a job (tech location tracking).
 * Used when starting a job to indicate shop vs field location.
 */
export function useCheckInJob() {
  const queryClient = useQueryClient()
  const { user } = useAuth()

  return useMutation({
    mutationFn: ({ id, location, notes }: { id: number; location: JobCheckInLocation; notes?: string }) =>
      apiPost<{ success: boolean; location: string | null; checked_in_at: string; job_id: number; job_number: string }>(
        `/jobs/${id}/check-in`,
        { location, notes: notes || '' }
      ),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', id] })
      queryClient.invalidateQueries({ queryKey: ['jobs', 'my-jobs', user?.id] })
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}


// ==============================================================================
// PART REQUESTS (Stage 5Q)
// ==============================================================================

export interface CreatePartRequestData {
  estimateId?: number
  jobId?: number
  description: string
  partNumber?: string
  qty?: number
  partsStatus?: string
  approvedToOrder?: boolean
  approvedAmount?: number
  vendor?: string
  poNumber?: string
  eta?: string
  notes?: string
}

export interface UpdatePartRequestData {
  description?: string
  partNumber?: string
  qty?: number
  partsStatus?: string
  approvedToOrder?: boolean
  approvedAmount?: number
  vendor?: string
  poNumber?: string
  eta?: string
  notes?: string
}

/**
 * Create a new part request.
 */
export function useCreatePartRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreatePartRequestData) =>
      apiPost<{ success: boolean; request: object }>('/parts/requests', {
        estimate_id: data.estimateId,
        job_id: data.jobId,
        description: data.description,
        part_number: data.partNumber,
        qty: data.qty || 1,
        parts_status: data.partsStatus || 'needed',
        approved_to_order: data.approvedToOrder || false,
        approved_amount: data.approvedAmount,
        vendor: data.vendor,
        po_number: data.poNumber,
        eta: data.eta,
        notes: data.notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
    },
  })
}

/**
 * Update a part request.
 */
export function useUpdatePartRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdatePartRequestData }) =>
      apiPatch<{ success: boolean; request: object }>(`/parts/requests/${id}`, {
        description: data.description,
        part_number: data.partNumber,
        qty: data.qty,
        parts_status: data.partsStatus,
        approved_to_order: data.approvedToOrder,
        approved_amount: data.approvedAmount,
        vendor: data.vendor,
        po_number: data.poNumber,
        eta: data.eta,
        notes: data.notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
    },
  })
}


// ==============================================================================
// ESTIMATE → PARTS REQUESTS BRIDGE (Stage 5R)
// ==============================================================================

export interface PartsSuggestion {
  description: string
  source_type: 'panel_ri' | 'supplement' | 'panel_cr' | 'manual'
  source_id: number
  part_number?: string | null
  qty: number
  notes?: string | null
  reason?: string
  already_exists: boolean
  existing_id?: number | null
}

export interface PartsSuggestionsResponse {
  success: boolean
  estimate_id: number
  estimate_number: string
  suggestions: PartsSuggestion[]
  new_suggestions: PartsSuggestion[]
  stats: {
    total_suggestions: number
    new_suggestions: number
    duplicates: number
    by_source_type: Record<string, number>
  }
}

export interface EstimatePartsRequestsResponse {
  success: boolean
  estimate_id: number
  requests: object[]
  count: number
}

/**
 * Fetch parts suggestions for an estimate (Stage 5R).
 * Preview only - no database writes.
 */
export function useEstimatePartsSuggestions(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-parts-suggestions', estimateId],
    queryFn: () => apiGet<PartsSuggestionsResponse>(`/pdr-estimates/${estimateId}/parts/suggestions`),
    enabled: !!estimateId,
    staleTime: 60000, // 1 minute - suggestions don't change often
  })
}

/**
 * Fetch part requests for an estimate (Stage 5R).
 */
export function useEstimatePartsRequests(estimateId: number | null) {
  return useQuery({
    queryKey: ['estimate-parts-requests', estimateId],
    queryFn: () => apiGet<EstimatePartsRequestsResponse>(`/pdr-estimates/${estimateId}/parts/requests`),
    enabled: !!estimateId,
    staleTime: 30000,
  })
}

/**
 * Bulk create parts requests from suggestions (Stage 5R).
 */
export function useCreateEstimatePartsRequests() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ estimateId, selectedIndices, skipDuplicates = true }: {
      estimateId: number
      selectedIndices?: number[]
      skipDuplicates?: boolean
    }) =>
      apiPost<{
        success: boolean
        estimate_id: number
        created_count: number
        skipped_duplicates: number
        created: object[]
      }>(`/pdr-estimates/${estimateId}/parts/requests`, {
        selected_indices: selectedIndices,
        skip_duplicates: skipDuplicates,
      }),
    onSuccess: (_, { estimateId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: queryKeys.workInbox.all })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
      queryClient.invalidateQueries({ queryKey: ['estimate-parts-suggestions', estimateId] })
      queryClient.invalidateQueries({ queryKey: ['estimate-parts-requests', estimateId] })
    },
  })
}


// ==============================================================================
// PARTS APPROVAL CONTROLS (Stage 5T)
// ==============================================================================

/**
 * Approve a part request for ordering.
 */
export function useApprovePartRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, approvedAmount, approvalNotes }: {
      id: number
      approvedAmount?: number
      approvalNotes?: string
    }) =>
      apiPatch<{ success: boolean; request: object }>(`/parts/requests/${id}/approve`, {
        approved_amount: approvedAmount,
        approval_notes: approvalNotes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
      queryClient.invalidateQueries({ queryKey: ['estimate-parts-requests'] })
    },
  })
}

/**
 * Revoke approval for a part request.
 */
export function useUnapprovePartRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) =>
      apiPatch<{ success: boolean; request: object }>(`/parts/requests/${id}/unapprove`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
      queryClient.invalidateQueries({ queryKey: ['estimate-parts-requests'] })
    },
  })
}

/**
 * Bulk approve multiple part requests.
 */
export function useBulkApprovePartRequests() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ requestIds, approvedAmountMap, approvalNotes }: {
      requestIds: number[]
      approvedAmountMap?: Record<string, number>
      approvalNotes?: string
    }) =>
      apiPost<{
        success: boolean
        approved_count: number
        requests: object[]
      }>('/parts/requests/bulk-approve', {
        request_ids: requestIds,
        approved_amount_map: approvedAmountMap,
        approval_notes: approvalNotes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
      queryClient.invalidateQueries({ queryKey: ['estimate-parts-requests'] })
    },
  })
}


// ==============================================================================
// PARTS STATUS TRANSITIONS (Stage 5U)
// ==============================================================================

/**
 * Update part request status with transition validation.
 */
export function useUpdatePartRequestStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, partsStatus, eta, vendor, poNumber, notes }: {
      id: number
      partsStatus: string
      eta?: string
      vendor?: string
      poNumber?: string
      notes?: string
    }) =>
      apiPatch<{ success: boolean; request: object }>(`/parts/requests/${id}/status`, {
        parts_status: partsStatus,
        eta,
        vendor,
        po_number: poNumber,
        notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
      queryClient.invalidateQueries({ queryKey: ['parts-requests'] })
      queryClient.invalidateQueries({ queryKey: ['estimate-parts-requests'] })
    },
  })
}

// ==============================================================================
// PARTS REQUEST NUDGE (Stage 5V)
// ==============================================================================

/**
 * Stage 5V: Send nudge notification for a part request.
 */
export function useNudgePartRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, nudgeType, targetRole, vendorEmail, message }: {
      id: number
      nudgeType: 'internal' | 'vendor'
      targetRole?: string
      vendorEmail?: string
      message?: string
    }) =>
      apiPost<{ success: boolean; nudge_id: string; recipients: number }>(`/parts/requests/${id}/nudge`, {
        nudge_type: nudgeType,
        target_role: targetRole,
        vendor_email: vendorEmail,
        message,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}
