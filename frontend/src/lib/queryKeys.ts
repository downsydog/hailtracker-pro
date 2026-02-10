/**
 * Centralized React Query Keys
 *
 * Single source of truth for all query keys.
 * Enables precise invalidation across the app.
 */

export const queryKeys = {
  // ============================================================================
  // OPS / DASHBOARD
  // ============================================================================
  opsOverview: ['ops-overview'] as const,

  // ============================================================================
  // WORK INBOX / NOTIFICATIONS
  // ============================================================================
  workInbox: {
    all: ['work-inbox'] as const,
    feed: (params?: Record<string, unknown>) => ['work-inbox', 'feed', params] as const,
  },

  // ============================================================================
  // ESTIMATES
  // ============================================================================
  estimates: {
    all: ['pdr-estimates'] as const,
    lists: () => [...queryKeys.estimates.all] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.estimates.all, filters] as const,
    detail: (id: number) => [...queryKeys.estimates.all, id] as const,
    workflow: (id: number) => ['workflow', 'estimate', id] as const,
    activities: (id: number) => ['estimate-activities', id] as const,
    versions: (id: number) => ['estimate-versions', id] as const,
    supplements: (id: number) => ['estimate-supplements', id] as const,
    photos: (id: number) => ['estimate-photos', id] as const,
    invoices: (id: number) => ['estimate-invoices', id] as const,
    job: (id: number) => ['estimate-job', id] as const,
  },

  // ============================================================================
  // JOBS
  // ============================================================================
  jobs: {
    all: ['jobs'] as const,
    lists: () => [...queryKeys.jobs.all] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.jobs.all, filters] as const,
    detail: (id: number) => [...queryKeys.jobs.all, id] as const,
    myJobs: (userId?: number, statusFilter?: string[]) => ['jobs', 'my-jobs', userId, statusFilter] as const,
    workflow: (id: number) => ['workflow', 'job', id] as const,
  },

  // ============================================================================
  // INVOICES
  // ============================================================================
  invoices: {
    all: ['invoices'] as const,
    lists: () => [...queryKeys.invoices.all, 'list'] as const,
    list: (params?: Record<string, unknown>) => [...queryKeys.invoices.lists(), params] as const,
    detail: (id: number) => [...queryKeys.invoices.all, 'detail', id] as const,
    payments: (id: number) => [...queryKeys.invoices.detail(id), 'payments'] as const,
  },

  // ============================================================================
  // LEADS
  // ============================================================================
  leads: {
    all: ['leads'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.leads.all, filters] as const,
    detail: (id: number) => [...queryKeys.leads.all, id] as const,
  },

  // ============================================================================
  // CUSTOMERS
  // ============================================================================
  customers: {
    all: ['customers'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.customers.all, filters] as const,
    detail: (id: number) => [...queryKeys.customers.all, id] as const,
  },

  // ============================================================================
  // WORK ORDERS
  // ============================================================================
  workOrders: {
    all: ['work-orders'] as const,
    detail: (id: number) => [...queryKeys.workOrders.all, id] as const,
  },

  // ============================================================================
  // WORKFLOW (generic)
  // ============================================================================
  workflow: {
    all: ['workflow'] as const,
    estimate: (id: number) => ['workflow', 'estimate', id] as const,
    job: (id: number) => ['workflow', 'job', id] as const,
  },

  // ============================================================================
  // SETTINGS
  // ============================================================================
  settings: {
    all: ['settings'] as const,
    autoNudges: ['settings', 'auto-nudges'] as const,
    laborRates: ['settings', 'labor-rates'] as const,
  },
} as const

/**
 * Helper to invalidate ops-related queries after workflow changes.
 * Call this from mutation onSuccess handlers.
 */
export function getOpsInvalidationKeys() {
  return [queryKeys.opsOverview]
}

/**
 * Helper to get all estimate-related keys for a given estimate.
 * Useful when a workflow action affects multiple parts of an estimate.
 */
export function getEstimateInvalidationKeys(estimateId: number) {
  return [
    queryKeys.estimates.detail(estimateId),
    queryKeys.estimates.workflow(estimateId),
    queryKeys.estimates.activities(estimateId),
    queryKeys.estimates.invoices(estimateId),
    queryKeys.estimates.job(estimateId),
  ]
}

/**
 * Helper to get job-related keys for invalidation.
 */
export function getJobInvalidationKeys(jobId: number, estimateId?: number) {
  const baseKeys = [
    queryKeys.jobs.detail(jobId),
    queryKeys.jobs.workflow(jobId),
    queryKeys.jobs.lists(),
  ] as const

  if (estimateId) {
    return [...baseKeys, queryKeys.estimates.job(estimateId)] as const
  }

  return baseKeys
}
