import { apiGet, apiPost, apiPut, apiDelete } from './client'
import { User, Tech } from '@/types'

interface UsersResponse {
  users: User[]
}

export const adminApi = {
  // Users
  getUsers: () => apiGet<UsersResponse>('/api/admin/users'),
  listUsers: () => apiGet<User[]>('/api/admin/users'),
  getUser: (id: number) => apiGet<User>(`/api/admin/users/${id}`),
  createUser: (data: Partial<User> & { password: string }) => apiPost<User>('/api/admin/users', data),
  updateUser: (id: number, data: Partial<User>) => apiPut<User>(`/api/admin/users/${id}`, data),
  deleteUser: (id: number) => apiDelete<{ success: boolean }>(`/api/admin/users/${id}`),
  resetPassword: (id: number) => apiPost<{ success: boolean }>(`/api/admin/users/${id}/reset-password`),

  // Techs
  listTechs: () => apiGet<Tech[]>('/api/admin/techs'),

  // Roles
  listRoles: () => apiGet<{ id: number, name: string, permissions: string[] }[]>('/api/admin/roles'),

  // Settings
  getSettings: () => apiGet<Record<string, unknown>>('/api/admin/settings'),
  updateSettings: (data: Record<string, unknown>) => apiPut<Record<string, unknown>>('/api/admin/settings', data),
}
