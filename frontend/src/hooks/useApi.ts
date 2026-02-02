import { useCallback } from 'react'
import { useAuth } from '@/contexts/auth-context'

const API_BASE = '/api'

interface ApiOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>
}

interface ApiError {
  error: string
  message?: string
  status?: number
}

export function useApi() {
  const { token, logout } = useAuth()

  const request = useCallback(async <T>(
    endpoint: string,
    options: ApiOptions = {}
  ): Promise<T> => {
    const { params, ...fetchOptions } = options

    // Build URL with query params
    let url = `${API_BASE}${endpoint}`
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, String(value))
        }
      })
      const queryString = searchParams.toString()
      if (queryString) {
        url += `?${queryString}`
      }
    }

    // Set up headers with auth token
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(fetchOptions.headers || {}),
    }

    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    })

    // Handle 401 - unauthorized
    if (response.status === 401) {
      logout()
      throw new Error('Session expired. Please log in again.')
    }

    // Handle error responses
    if (!response.ok) {
      const errorData: ApiError = await response.json().catch(() => ({
        error: 'Request failed',
        status: response.status,
      }))
      throw new Error(errorData.error || errorData.message || 'Request failed')
    }

    // Handle empty responses
    const text = await response.text()
    if (!text) {
      return {} as T
    }

    return JSON.parse(text) as T
  }, [token, logout])

  // HTTP method helpers
  const get = useCallback(<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>) => {
    return request<T>(endpoint, { method: 'GET', params })
  }, [request])

  const post = useCallback(<T>(endpoint: string, data?: unknown) => {
    return request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }, [request])

  const put = useCallback(<T>(endpoint: string, data?: unknown) => {
    return request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }, [request])

  const patch = useCallback(<T>(endpoint: string, data?: unknown) => {
    return request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }, [request])

  const del = useCallback(<T>(endpoint: string) => {
    return request<T>(endpoint, { method: 'DELETE' })
  }, [request])

  return {
    request,
    get,
    post,
    put,
    patch,
    delete: del,
  }
}

// Type-safe API response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface Storm {
  id: number
  name: string
  event_date: string
  state: string
  city: string
  latitude: number
  longitude: number
  radius_miles: number
  hail_size: number
  status: string
  business_count: number
  processed_at: string | null
  created_at: string
}

export interface Business {
  id: number
  storm_id: number
  name: string
  address: string
  city: string
  state: string
  zip_code: string
  phone: string
  category: string
  latitude: number
  longitude: number
  source: string
}

export interface Lead {
  id: number
  business_id: number
  status: string
  notes: string
  assigned_to: number | null
  assigned_name: string | null
  contacted_at: string | null
  created_at: string
  business: Business
}

export interface TeamMember {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  created_at: string
}

export interface UsageStats {
  current_month: {
    used: number
    limit: number
    percentage: number
  }
  daily: Array<{
    date: string
    count: number
  }>
}
