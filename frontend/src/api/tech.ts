import { apiGet, apiPost } from './client'

// Time tracking types
export interface TimeStatus {
  is_clocked_in: boolean
  is_on_break: boolean
  clock_in_time: string | null
  current_break_start: string | null
  total_hours_today: number
  break_minutes_today: number
}

export interface TodayTime {
  clock_in: string | null
  clock_out: string | null
  total_hours: number
  break_minutes: number
  entries: TimeEntry[]
}

export interface TimeEntry {
  id: number
  type: string // 'CLOCK_IN', 'CLOCK_OUT', 'BREAK_START', 'BREAK_END', 'JOB_TIME'
  timestamp: string
  job_id?: number
  job_number?: string
  hours?: number
  description?: string
}

export interface WeekSummary {
  total_hours: number
  break_hours: number
  days: DaySummary[]
}

export interface DaySummary {
  date: string
  day_name: string
  hours: number
  jobs_worked: number
}

export interface TimeStatusResponse {
  success: boolean
  status: TimeStatus
  today: TodayTime
}

export interface ClockResponse {
  success: boolean
  message?: string
  time?: string
  error?: string
}

export interface LogTimeResponse {
  success: boolean
  message?: string
  entry_id?: number
  error?: string
}

export interface WeekTimeResponse {
  success: boolean
  week: WeekSummary
}

// Tech dashboard types
export interface TechDashboardData {
  success: boolean
  is_admin_view?: boolean
  // Tech-specific data (when logged in as tech)
  stats?: {
    assigned_jobs: number
    in_progress: number
    completed_today: number
    completed_this_week: number
    avg_hours_per_job: number
  }
  current_job?: TechJob | null
  today_jobs?: TechJob[]
  time_status?: TimeStatus
  // Admin view data (when admin/owner without tech record)
  jobs_today?: number
  jobs_in_progress?: number
  jobs_completed_today?: number
  active_techs?: number
  technicians?: Array<{
    id: number
    name: string
    first_name?: string
    last_name?: string
    status: string
    current_job?: string
    jobs_today?: number
  }>
}

export interface TechJob {
  id: number
  job_number: string
  customer_name: string
  customer_id?: number
  vehicle_id?: number
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_color?: string
  status: string
  damage_type?: string
  scheduled_date?: string
  scheduled_drop_off?: string
  started_at?: string
  hours_logged: number
}

// API functions
export const techApi = {
  // Dashboard
  getDashboard: () => apiGet<TechDashboardData>('/api/tech/dashboard'),

  // Time tracking
  getTimeStatus: () => apiGet<TimeStatusResponse>('/api/tech/time/status'),

  clockIn: (data?: { location?: string; notes?: string }) =>
    apiPost<ClockResponse>('/api/tech/time/clock-in', data),

  clockOut: (data?: { location?: string; notes?: string }) =>
    apiPost<ClockResponse>('/api/tech/time/clock-out', data),

  startBreak: () => apiPost<ClockResponse>('/api/tech/time/break/start'),

  endBreak: () => apiPost<ClockResponse>('/api/tech/time/break/end'),

  logTime: (data: { job_id: number; hours: number; description?: string }) =>
    apiPost<LogTimeResponse>('/api/tech/time/log', data),

  getTodayTime: () => apiGet<TodayTime>('/api/tech/time/today'),

  getWeekTime: () => apiGet<WeekTimeResponse>('/api/tech/time/week'),

  // Jobs
  getJobs: (filter?: 'CURRENT' | 'ALL') =>
    apiGet<{ success: boolean; jobs: TechJob[] }>('/api/tech/jobs', { params: { filter } }),

  startJob: (jobId: number) =>
    apiPost<{ success: boolean; message: string }>(`/api/tech/jobs/${jobId}/start`),

  updateProgress: (jobId: number, data: { progress_percent?: number; notes?: string }) =>
    apiPost<{ success: boolean; message: string }>(`/api/tech/jobs/${jobId}/progress`, data),

  completeJob: (jobId: number, data?: { notes?: string }) =>
    apiPost<{ success: boolean; message: string }>(`/api/tech/jobs/${jobId}/complete`, data),

  pauseJob: (jobId: number, data?: { reason?: string }) =>
    apiPost<{ success: boolean; message: string }>(`/api/tech/jobs/${jobId}/pause`, data),
}
