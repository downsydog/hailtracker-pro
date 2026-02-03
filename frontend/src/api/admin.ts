import { apiClient } from './client'

export interface AdminUser {
  id: number
  email: string
  name: string
  username?: string
  role: string
  permissions?: string[]
  is_active: boolean
  last_login?: string
  created_at: string
}

export interface AdminSettings {
  company_name: string
  company_email: string
  company_phone: string
  company_address: string
  timezone: string
  date_format: string
  currency: string
  tax_rate: number
  email_notifications: boolean
  sms_notifications: boolean
  default_labor_rate?: number
  [key: string]: unknown  // Allow additional properties
}

export interface SystemStats {
  users_count: number
  active_users: number
  jobs_this_month: number
  revenue_this_month: number
  storage_used_mb: number
}

export const adminApi = {
  // Users
  getUsers: (params?: { role?: string; active?: boolean; page?: number }) =>
    apiClient.get<{ users: AdminUser[]; total: number }>('/admin/users', params),

  getUser: (id: number) =>
    apiClient.get<AdminUser>(`/admin/users/${id}`),

  createUser: (data: Partial<AdminUser> & { password: string }) =>
    apiClient.post<AdminUser>('/admin/users', data),

  updateUser: (id: number, data: Partial<AdminUser>) =>
    apiClient.patch<AdminUser>(`/admin/users/${id}`, data),

  deleteUser: (id: number) =>
    apiClient.delete(`/admin/users/${id}`),

  resetUserPassword: (id: number) =>
    apiClient.post<{ temp_password: string }>(`/admin/users/${id}/reset-password`),

  // Settings
  getSettings: () =>
    apiClient.get<AdminSettings>('/admin/settings'),

  updateSettings: (data: Partial<AdminSettings>) =>
    apiClient.patch<AdminSettings>('/admin/settings', data),

  // System
  getSystemStats: () =>
    apiClient.get<SystemStats>('/admin/system/stats'),

  // Logs
  getLogs: (params?: { type?: string; from?: string; to?: string; page?: number }) =>
    apiClient.get<{ logs: Array<{ id: number; type: string; message: string; created_at: string }>; total: number }>('/admin/logs', params),

  // Backups
  getBackups: () =>
    apiClient.get<{ backups: Array<{ id: number; filename: string; size_mb: number; created_at: string }> }>('/admin/backups'),

  createBackup: () =>
    apiClient.post<{ backup_id: number }>('/admin/backups'),
}

export default adminApi
