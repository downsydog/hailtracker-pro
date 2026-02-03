import { apiClient } from './client'

export interface Deal {
  id: number
  name: string
  title?: string
  customer_id: number
  customer_name: string
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  value: number
  stage: string
  probability: number
  expected_close_date?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface Pipeline {
  id: number
  name: string
  stages: PipelineStage[]
}

export interface PipelineStage {
  id: number
  name: string
  stage?: string
  order: number
  deals_count: number
  deals_value: number
  deals?: Deal[]
}

export interface Task {
  id: number
  title: string
  description?: string
  due_date?: string
  priority: 'low' | 'medium' | 'high'
  status: 'pending' | 'completed' | 'COMPLETED' | 'PENDING'
  assigned_to?: number
  assigned_to_name?: string
  deal_id?: number
  customer_id?: number
  created_at: string
}

// Alias for components that use CRMTask
export type CRMTask = Task

export interface Interaction {
  id: number
  type: 'call' | 'email' | 'meeting' | 'note'
  interaction_type?: string
  subject: string
  description?: string
  notes?: string
  deal_id?: number
  customer_id?: number
  contact_id?: number
  contact_name?: string
  created_by: number
  created_at: string
}

export interface Contact {
  id: number
  name: string
  email?: string
  phone?: string
  company?: string
  title?: string
  notes?: string
  created_at: string
}

export const crmApi = {
  // Deals
  getDeals: (params?: { stage?: string; page?: number; search?: string }) =>
    apiClient.get<{ deals: Deal[]; total: number }>('/crm/deals', params),

  getDeal: (id: number) =>
    apiClient.get<Deal>(`/crm/deals/${id}`),

  createDeal: (data: Partial<Deal>) =>
    apiClient.post<Deal>('/crm/deals', data),

  updateDeal: (id: number, data: Partial<Deal>) =>
    apiClient.patch<Deal>(`/crm/deals/${id}`, data),

  deleteDeal: (id: number) =>
    apiClient.delete(`/crm/deals/${id}`),

  moveDealToStage: (dealId: number, stageId: number) =>
    apiClient.post(`/crm/deals/${dealId}/move`, { stage_id: stageId }),

  updateDealStage: (dealId: number, stage: string) =>
    apiClient.patch(`/crm/deals/${dealId}`, { stage }),

  // Pipeline
  getPipelines: () =>
    apiClient.get<{ pipelines: Pipeline[] }>('/crm/pipelines'),

  getPipeline: (id?: number) =>
    apiClient.get<{ pipeline: PipelineStage[] }>(id ? `/crm/pipelines/${id}` : '/crm/pipeline/view'),

  getPipelineStats: () =>
    apiClient.get<{
      total_deals: number
      total_value: number
      by_stage: Record<string, { count: number; value: number }>
    }>('/crm/pipeline/stats'),

  // Tasks
  getTasks: (params?: { status?: string; page?: number }) =>
    apiClient.get<{ tasks: Task[]; total: number }>('/crm/tasks', params),

  getOverdueTasks: () =>
    apiClient.get<{ tasks: Task[]; total: number }>('/crm/tasks', { status: 'overdue' }),

  createTask: (data: Partial<Task>) =>
    apiClient.post<Task>('/crm/tasks', data),

  updateTask: (id: number, data: Partial<Task>) =>
    apiClient.patch<Task>(`/crm/tasks/${id}`, data),

  completeTask: (id: number) =>
    apiClient.post(`/crm/tasks/${id}/complete`),

  // Contacts
  getContacts: (params?: { search?: string; page?: number }) =>
    apiClient.get<{ contacts: Contact[]; total: number }>('/crm/contacts', params),

  createContact: (data: Partial<Contact>) =>
    apiClient.post<Contact>('/crm/contacts', data),

  updateContact: (id: number, data: Partial<Contact>) =>
    apiClient.patch<Contact>(`/crm/contacts/${id}`, data),

  // Dashboard stats
  getDashboardStats: () =>
    apiClient.get<{
      deals_count: number
      deals_value: number
      tasks_pending: number
      tasks_overdue: number
      recent_activities: Array<{ type: string; description: string; created_at: string }>
    }>('/crm/dashboard'),

  // Alias for getDashboardStats
  getDashboard: () =>
    apiClient.get<{
      total_deals: number
      total_value: number
      overdue_tasks: Task[]
      upcoming_tasks: Task[]
      recent_interactions: Interaction[]
      recent_deals: Deal[]
      deals_by_stage: Record<string, number>
    }>('/crm/dashboard'),
}

export default crmApi
