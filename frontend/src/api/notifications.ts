import { apiGet, apiPost, apiDelete } from './client'
import { Notification } from '@/types'

interface NotificationsResponse {
  notifications: Notification[]
  total: number
  unread_count: number
}

export const notificationsApi = {
  list: () => apiGet<NotificationsResponse>('/api/notifications'),
  get: (id: number) => apiGet<Notification>(`/api/notifications/${id}`),
  markRead: (id: number) => apiPost<Notification>(`/api/notifications/${id}/read`),
  markAllRead: () => apiPost<{ success: boolean }>('/api/notifications/mark-all-read'),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/notifications/${id}`),
}
