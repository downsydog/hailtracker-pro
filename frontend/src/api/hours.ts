import { apiGet, apiPost, apiPut, apiDelete } from './client'

export interface TimeEntry {
  id: number
  user_id: number
  user_name: string
  job_id?: number
  job_number?: string
  entry_date: string
  clock_in: string
  clock_out?: string
  break_minutes: number
  total_hours: number
  entry_type: 'regular' | 'overtime' | 'pto' | 'sick' | 'holiday'
  notes?: string
  approved: boolean
  approved_by?: number
  approved_at?: string
  created_at: string
  updated_at: string
}

export interface ActiveClockIn {
  id: number
  user_id: number
  clock_in: string
  job_id?: number
  job_number?: string
  elapsed_minutes: number
}

export interface WeekSummary {
  week_start: string
  week_end: string
  total_hours: number
  regular_hours: number
  overtime_hours: number
  pto_hours: number
  entries: TimeEntry[]
}

export interface PayPeriodSummary {
  period_start: string
  period_end: string
  user_id: number
  user_name: string
  total_hours: number
  regular_hours: number
  overtime_hours: number
  pto_hours: number
  sick_hours: number
  entries_count: number
  approved_entries: number
  pending_entries: number
}

export interface TimeEntryCreateData {
  entry_date: string
  clock_in: string
  clock_out?: string
  break_minutes?: number
  job_id?: number
  entry_type?: TimeEntry['entry_type']
  notes?: string
}

export interface TimeFilters {
  user_id?: number
  start_date?: string
  end_date?: string
  entry_type?: string
  approved?: boolean
  job_id?: number
}

export const hoursApi = {
  // Clock in/out
  clockIn: (jobId?: number, notes?: string) =>
    apiPost<{ success: boolean; entry_id: number; clock_in: string }>('/api/hours/clock-in', {
      job_id: jobId,
      notes
    }),

  clockOut: (breakMinutes?: number, notes?: string) =>
    apiPost<{ success: boolean; entry_id: number; total_hours: number }>('/api/hours/clock-out', {
      break_minutes: breakMinutes,
      notes
    }),

  // Get active clock-in status
  getActiveClockIn: () =>
    apiGet<{ active: ActiveClockIn | null }>('/api/hours/active'),

  // Get time entries
  getEntries: (filters?: TimeFilters) =>
    apiGet<{ entries: TimeEntry[]; total: number }>('/api/hours/entries', { params: filters }),

  // Get single entry
  getEntry: (id: number) =>
    apiGet<TimeEntry>(`/api/hours/entries/${id}`),

  // Create manual entry
  createEntry: (data: TimeEntryCreateData) =>
    apiPost<{ success: boolean; entry_id: number }>('/api/hours/entries', data),

  // Update entry
  updateEntry: (id: number, data: Partial<TimeEntryCreateData>) =>
    apiPut<{ success: boolean }>(`/api/hours/entries/${id}`, data),

  // Delete entry
  deleteEntry: (id: number) =>
    apiDelete<{ success: boolean }>(`/api/hours/entries/${id}`),

  // Get current week summary
  getWeekSummary: (userId?: number, weekStart?: string) =>
    apiGet<WeekSummary>('/api/hours/week-summary', {
      params: { user_id: userId, week_start: weekStart }
    }),

  // Get pay period summary (admin)
  getPayPeriodSummary: (periodStart: string, periodEnd: string, userId?: number) =>
    apiGet<{ summaries: PayPeriodSummary[] }>('/api/hours/pay-period', {
      params: { period_start: periodStart, period_end: periodEnd, user_id: userId }
    }),

  // Approve entry (admin/manager)
  approveEntry: (id: number) =>
    apiPost<{ success: boolean }>(`/api/hours/entries/${id}/approve`),

  // Reject entry (admin/manager)
  rejectEntry: (id: number, reason: string) =>
    apiPost<{ success: boolean }>(`/api/hours/entries/${id}/reject`, { reason }),

  // Bulk approve entries
  bulkApprove: (entryIds: number[]) =>
    apiPost<{ success: boolean; approved: number }>('/api/hours/bulk-approve', { entry_ids: entryIds }),

  // Request PTO
  requestPto: (data: {
    start_date: string
    end_date: string
    hours_per_day?: number
    reason?: string
  }) =>
    apiPost<{ success: boolean; entry_ids: number[] }>('/api/hours/request-pto', data),

  // Get PTO balance
  getPtoBalance: (userId?: number) =>
    apiGet<{
      accrued: number
      used: number
      available: number
      pending: number
    }>('/api/hours/pto-balance', { params: { user_id: userId } }),

  // Get user's hours stats
  getStats: (userId?: number, year?: number) =>
    apiGet<{
      total_hours_ytd: number
      regular_hours_ytd: number
      overtime_hours_ytd: number
      avg_hours_per_week: number
      most_worked_jobs: Array<{ job_id: number; job_number: string; hours: number }>
    }>('/api/hours/stats', { params: { user_id: userId, year } }),

  // Export timesheet
  exportTimesheet: (filters: TimeFilters, format: 'csv' | 'pdf') =>
    apiGet<Blob>('/api/hours/export', {
      params: { ...filters, format },
      responseType: 'blob'
    }),
}
