import { apiGet } from './client'

// Report filter options
export interface ReportFilters {
  start_date?: string
  end_date?: string
  group_by?: 'day' | 'week' | 'month'
}

// Dashboard stats
export interface DashboardStats {
  revenue: {
    total: number
    change: number
    period: string
  }
  jobs_completed: {
    total: number
    change: number
  }
  avg_job_value: {
    total: number
    change: number
  }
  lead_conversion: {
    rate: number
    change: number
  }
}

// Revenue report types
export interface RevenueReport {
  chart_data: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  service_breakdown: {
    labels: string[]
    values: number[]
  }
  stats: {
    total_revenue: number
    avg_per_job: number
    best_day: string
    best_day_revenue: number
    projected_monthly: number
  }
  top_jobs: {
    id: number
    customer: string
    vehicle: string
    service: string
    amount: number
    date: string
  }[]
}

// Jobs report types
export interface JobsReport {
  over_time: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  by_status: {
    labels: string[]
    values: number[]
  }
  by_tech: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  stats: {
    total_jobs: number
    avg_completion_time: number
    jobs_in_progress: number
    completed_this_period: number
  }
}

// Jobs by status
export interface JobsByStatus {
  labels: string[]
  values: number[]
}

// Leads report types
export interface LeadsReport {
  over_time: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  by_source: {
    labels: string[]
    values: number[]
  }
  by_status: {
    labels: string[]
    values: number[]
  }
  conversion_funnel: {
    labels: string[]
    values: number[]
  }
  stats: {
    total_leads: number
    converted: number
    conversion_rate: number
    avg_response_time: number
  }
}

// Lead sources
export interface LeadSources {
  labels: string[]
  values: number[]
}

// Tech performance
export interface TechPerformance {
  techs: {
    id: number
    name: string
    role: string
    jobs_completed: number
    hours_worked: number
    revenue: number
    avg_job_time: number
    efficiency: number
    customer_rating: number
    revenue_per_hour: number
    rank: number
  }[]
  jobs_comparison: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  revenue_comparison: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  stats: {
    total_jobs: number
    total_revenue: number
    avg_efficiency: number
    top_performer: string
  }
}

export interface TechDetail {
  tech_id: number
  name: string
  jobs_completed: number
  revenue_generated: number
  avg_job_time: number
  rating: number
  jobs_by_type: {
    labels: string[]
    values: number[]
  }
  monthly_performance: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
}

// Estimates report
export interface EstimatesReport {
  over_time: {
    labels: string[]
    datasets: { label: string; data: number[] }[]
  }
  by_status: {
    labels: string[]
    values: number[]
  }
  stats: {
    total_estimates: number
    approved: number
    approval_rate: number
    avg_value: number
    total_value: number
  }
}

// API functions
export const reportsApi = {
  dashboard: (filters?: ReportFilters) =>
    apiGet<DashboardStats>('/api/reports/dashboard', { params: filters }),

  revenue: (filters?: ReportFilters) =>
    apiGet<RevenueReport>('/api/reports/revenue', { params: filters }),

  jobs: (filters?: ReportFilters) =>
    apiGet<JobsReport>('/api/reports/jobs', { params: filters }),

  jobsByStatus: () =>
    apiGet<JobsByStatus>('/api/reports/jobs/by-status'),

  leads: (filters?: ReportFilters) =>
    apiGet<LeadsReport>('/api/reports/leads', { params: filters }),

  leadSources: () =>
    apiGet<LeadSources>('/api/reports/leads/sources'),

  techs: (filters?: ReportFilters) =>
    apiGet<TechPerformance>('/api/reports/techs', { params: filters }),

  techDetail: (techId: number, filters?: ReportFilters) =>
    apiGet<TechDetail>(`/api/reports/techs/${techId}`, { params: filters }),

  estimates: (filters?: ReportFilters) =>
    apiGet<EstimatesReport>('/api/reports/estimates', { params: filters }),
}
