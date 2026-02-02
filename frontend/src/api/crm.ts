/**
 * CRM API Client
 * Deal pipeline, tasks, notes, analytics
 */

import { apiGet, apiPost, apiPut } from './client'

// =============================================================================
// TYPES
// =============================================================================

export interface Deal {
  id: number
  location_id: number
  location_name?: string
  title: string
  stage: 'LEAD' | 'CONTACTED' | 'QUALIFIED' | 'PROPOSAL' | 'NEGOTIATION' | 'CLOSED_WON' | 'CLOSED_LOST'
  value: number
  probability: number
  expected_close_date?: string
  assigned_to?: number
  assigned_to_name?: string
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface CRMTask {
  id: number
  deal_id?: number
  location_id?: number
  title: string
  description?: string
  due_date?: string
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT'
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
  assigned_to?: number
  assigned_to_name?: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export interface CRMNote {
  id: number
  deal_id?: number
  location_id?: number
  content: string
  created_by?: number
  created_by_name?: string
  created_at: string
}

export interface Interaction {
  id: number
  location_id: number
  interaction_type: 'CALL' | 'EMAIL' | 'MEETING' | 'VISIT' | 'OTHER'
  contact_name?: string
  notes?: string
  outcome?: string
  follow_up_date?: string
  created_by?: number
  created_by_name?: string
  created_at: string
}

export interface CRMUser {
  id: number
  username: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export interface PipelineStage {
  stage: string
  count: number
  total_value: number
  deals: Deal[]
}

export interface FunnelData {
  stage: string
  count: number
  conversion_rate: number
}

export interface RevenueData {
  period: string
  revenue: number
  deals_closed: number
}

export interface PerformanceData {
  user_id: number
  user_name: string
  deals_won: number
  deals_lost: number
  total_value: number
  win_rate: number
}

export interface ActivityData {
  date: string
  interactions: number
  tasks_completed: number
  deals_moved: number
}

export interface DashboardStats {
  total_deals: number
  total_value: number
  deals_by_stage: Record<string, number>
  recent_deals: Deal[]
  overdue_tasks: CRMTask[]
  upcoming_tasks: CRMTask[]
  recent_interactions: Interaction[]
}

// =============================================================================
// CRM API
// =============================================================================

export const crmApi = {
  // Dashboard
  getDashboard: () =>
    apiGet<DashboardStats>('/crm/api/dashboard'),

  // Deals
  getDeals: (filters?: { stage?: string; assigned_to?: number; search?: string }) =>
    apiGet<{ deals: Deal[]; count: number }>('/crm/api/deals', { params: filters }),

  getDeal: (dealId: number) =>
    apiGet<{ deal: Deal; interactions: Interaction[]; tasks: CRMTask[]; notes: CRMNote[] }>(`/crm/api/deal/${dealId}`),

  createDeal: (data: Partial<Deal>) =>
    apiPost<{ success: boolean; deal_id: number }>('/crm/api/deal', data),

  updateDeal: (dealId: number, data: Partial<Deal>) =>
    apiPut<{ success: boolean }>(`/crm/api/deal/${dealId}`, data),

  updateDealStage: (dealId: number, stage: string, notes?: string) =>
    apiPut<{ success: boolean }>(`/crm/api/deal/${dealId}/stage`, { stage, notes }),

  // Pipeline
  getPipeline: () =>
    apiGet<{ pipeline: PipelineStage[] }>('/crm/api/pipeline'),

  // Tasks
  getTasks: (filters?: { status?: string; assigned_to?: number; deal_id?: number }) =>
    apiGet<{ tasks: CRMTask[]; count: number }>('/crm/api/tasks', { params: filters }),

  getTask: (taskId: number) =>
    apiGet<CRMTask>(`/crm/api/task/${taskId}`),

  createTask: (data: Partial<CRMTask>) =>
    apiPost<{ success: boolean; task_id: number }>('/crm/api/task', data),

  updateTaskStatus: (taskId: number, status: string) =>
    apiPut<{ success: boolean }>(`/crm/api/task/${taskId}/status`, { status }),

  completeTask: (taskId: number) =>
    apiPut<{ success: boolean }>(`/crm/api/task/${taskId}/complete`),

  getOverdueTasks: () =>
    apiGet<{ tasks: CRMTask[]; count: number }>('/crm/api/tasks/overdue'),

  // Notes
  getNotes: (filters?: { deal_id?: number; location_id?: number }) =>
    apiGet<{ notes: CRMNote[]; count: number }>('/crm/api/notes', { params: filters }),

  createNote: (data: { deal_id?: number; location_id?: number; content: string }) =>
    apiPost<{ success: boolean; note_id: number }>('/crm/api/note', data),

  // Interactions
  getInteractions: (locationId: number) =>
    apiGet<{ interactions: Interaction[] }>(`/crm/api/interactions/${locationId}`),

  getRecentInteractions: (limit?: number) =>
    apiGet<{ interactions: Interaction[] }>('/crm/api/interactions/recent', { params: { limit } }),

  logInteraction: (data: Partial<Interaction>) =>
    apiPost<{ success: boolean; interaction_id: number }>('/crm/api/interaction', data),

  // Users
  getUsers: () =>
    apiGet<{ users: CRMUser[] }>('/crm/api/users'),

  createUser: (data: Partial<CRMUser>) =>
    apiPost<{ success: boolean; user_id: number }>('/crm/api/user', data),

  // Analytics
  getFunnelAnalytics: () =>
    apiGet<{ funnel: FunnelData[] }>('/crm/api/analytics/funnel'),

  getRevenueAnalytics: (period?: string) =>
    apiGet<{ revenue: RevenueData[] }>('/crm/api/analytics/revenue', { params: { period } }),

  getPerformanceAnalytics: () =>
    apiGet<{ performance: PerformanceData[] }>('/crm/api/analytics/performance'),

  getActivityAnalytics: (days?: number) =>
    apiGet<{ activity: ActivityData[] }>('/crm/api/analytics/activity', { params: { days } }),
}

export default crmApi
