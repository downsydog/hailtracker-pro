/**
 * Workflow hooks for TanStack Query.
 *
 * Provides hooks for:
 * - Fetching workflow state and next actions
 * - Closing claims
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiGet, apiPost } from "@/api/client"
import type { WorkflowData } from "@/components/workflow/WorkflowCard"
import { queryKeys } from "@/lib/queryKeys"

// Re-export types for convenience
export type { WorkflowData, WorkflowAction, WorkflowState } from "@/components/workflow/WorkflowCard"

// Query keys
export const workflowKeys = {
  all: ["workflow"] as const,
  estimate: (id: number) => [...workflowKeys.all, "estimate", id] as const,
  job: (id: number) => [...workflowKeys.all, "job", id] as const,
}

/**
 * Fetch workflow state for an estimate.
 */
export function useEstimateWorkflow(estimateId: number | null) {
  return useQuery({
    queryKey: workflowKeys.estimate(estimateId!),
    queryFn: () => apiGet<WorkflowData>(`/pdr-estimates/${estimateId}/workflow`),
    enabled: estimateId !== null,
    // Refetch on window focus to keep workflow state current
    refetchOnWindowFocus: true,
    // Stale after 30 seconds
    staleTime: 30000,
  })
}

/**
 * Fetch workflow state for a job.
 */
export function useJobWorkflow(jobId: number | null) {
  return useQuery({
    queryKey: workflowKeys.job(jobId!),
    queryFn: () => apiGet<WorkflowData>(`/jobs/${jobId}/workflow`),
    enabled: jobId !== null,
    refetchOnWindowFocus: true,
    staleTime: 30000,
  })
}

/**
 * Close an estimate claim.
 */
export function useCloseClaim() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (estimateId: number) => {
      return apiPost<{ estimate: unknown; message: string }>(
        `/pdr-estimates/${estimateId}/close`
      )
    },
    onSuccess: (_, estimateId) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: workflowKeys.estimate(estimateId) })
      queryClient.invalidateQueries({ queryKey: ["pdr-estimates", estimateId] })
      queryClient.invalidateQueries({ queryKey: ["invoices"] })
      // Instant refresh: claim closed - major workflow completion
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}

/**
 * Issue an invoice with workflow guardrails.
 */
export function useIssueInvoiceWithGuard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (invoiceId: number) => {
      return apiPost<{ invoice: unknown; message: string }>(
        `/invoices/${invoiceId}/issue`
      )
    },
    onSuccess: () => {
      // Invalidate invoice and workflow queries
      queryClient.invalidateQueries({ queryKey: ["invoices"] })
      queryClient.invalidateQueries({ queryKey: workflowKeys.all })
      // Instant refresh: invoice issued
      queryClient.invalidateQueries({ queryKey: queryKeys.opsOverview })
    },
  })
}
