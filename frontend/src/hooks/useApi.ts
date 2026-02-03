import { apiClient, ApiParams } from '../api/client'

// Types used by customer pages
export interface UsageStats {
  current_month: {
    used: number
    limit: number
    percentage: number
  }
}

export interface TeamMember {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
}

export interface Business {
  id: number
  name: string
  address: string
  city: string
  state: string
  zip: string
  phone: string
  category: string
  website?: string
  email?: string
}

export interface Lead {
  id: number
  business: Business
  status: string
  notes?: string
  user_id: number
  created_at: string
  updated_at: string
}

export interface Storm {
  id: number
  name: string
  city: string
  state: string
  event_date: string
  hail_size: number
  business_count: number
  status: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// Hook that provides API methods with same interface as apiClient
export function useApi() {
  return {
    get: <T>(endpoint: string, params?: ApiParams) =>
      apiClient.get<T>(endpoint, params),

    post: <T>(endpoint: string, data?: unknown) =>
      apiClient.post<T>(endpoint, data),

    put: <T>(endpoint: string, data?: unknown) =>
      apiClient.put<T>(endpoint, data),

    patch: <T>(endpoint: string, data?: unknown) =>
      apiClient.patch<T>(endpoint, data),

    delete: <T>(endpoint: string) =>
      apiClient.delete<T>(endpoint),
  }
}

export default useApi
