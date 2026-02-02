import { apiGet, apiPut, apiDelete } from './client'
import { Notification } from '@/types'

interface NotificationsResponse {
  notifications: Notification[]
  pagination: {
    page: number
    per_page: number
    total: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
  }
}

export const notificationsApi = {
  list: (filter?: 'all' | 'unread' | 'read') => apiGet<NotificationsResponse>('/api/notifications', { params: { filter } }),
  getUnreadCount: () => apiGet<{ count: number }>('/api/notifications/unread-count'),
  markRead: (id: number) => apiPut<{ success: boolean }>(`/api/notifications/${id}/read`),
  markAllRead: () => apiPut<{ success: boolean }>('/api/notifications/read-all'),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/notifications/${id}`),
}
