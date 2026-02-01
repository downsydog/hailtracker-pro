import { apiGet, apiPost, apiDelete } from './client'
import { Notification } from '@/types'

interface NotificationsResponse {
  notifications: Notification[]
  total: number
  unread_count: number
}

export const notificationsApi = {
  list: () => apiGet<NotificationsResponse>('/notifications'),
  get: (id: number) => apiGet<Notification>(`/notifications/${id}`),
  markRead: (id: number) => apiPost<Notification>(`/notifications/${id}/read`),
  markAllRead: () => apiPost<{ success: boolean }>('/notifications/mark-all-read'),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/notifications/${id}`),
}
