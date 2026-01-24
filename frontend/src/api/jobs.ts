import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { Job, JobStats } from '@/types'

export interface JobsQueryParams {
  status?: string
  tech_id?: number
  start_date?: string
  end_date?: string
  search?: string
  page?: number
  per_page?: number
  limit?: number
}

export type CreateJobData = Partial<Job>
export type UpdateJobData = Partial<Job>

interface JobsResponse {
  jobs: Job[]
  stats?: JobStats
  total: number
  page: number
  per_page: number
}

interface CreateJobResponse {
  success: boolean
  job_id: number
  job_number: string
  message: string
}

export const jobsApi = {
  list: (filters?: JobsQueryParams) => apiGet<JobsResponse>('/api/jobs', { params: filters }),
  get: (id: number) => apiGet<Job>(`/api/jobs/${id}`),
  create: (data: CreateJobData) => apiPost<CreateJobResponse>('/api/jobs', data),
  update: (id: number, data: UpdateJobData) => apiPut<Job>(`/api/jobs/${id}`, data),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/jobs/${id}`),
  updateStatus: (id: number, status: string, notes?: string) => apiPost<Job>(`/api/jobs/${id}/status`, { status, notes }),
  assign: (id: number, techId: number) => apiPost<Job>(`/api/jobs/${id}/assign`, { tech_id: techId }),
}
