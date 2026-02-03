import { useState, useEffect, useCallback } from 'react'
import { apiClient, ApiParams } from '../api/client'
import { Customer, PaginatedResponse } from '../types'

export interface CustomerFilters {
  status?: string
  search?: string
  page?: number
  per_page?: number
}

export function useCustomers(filters: CustomerFilters = {}) {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadCustomers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.get<PaginatedResponse<Customer>>('/customers', filters as unknown as ApiParams)
      setCustomers(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load customers')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    loadCustomers()
  }, [loadCustomers])

  const createCustomer = async (data: Partial<Customer>) => {
    const customer = await apiClient.post<Customer>('/customers', data)
    loadCustomers()
    return customer
  }

  const updateCustomer = async (id: number, data: Partial<Customer>) => {
    const customer = await apiClient.put<Customer>(`/customers/${id}`, data)
    loadCustomers()
    return customer
  }

  const deleteCustomer = async (id: number) => {
    await apiClient.delete(`/customers/${id}`)
    loadCustomers()
  }

  return {
    customers,
    total,
    loading,
    error,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    refresh: loadCustomers
  }
}

export function useCustomer(id: number | null) {
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadCustomer = useCallback(async () => {
    if (!id) {
      setCustomer(null)
      setLoading(false)
      return
    }

    setLoading(true)
    try {
      const response = await apiClient.get<Customer>(`/customers/${id}`)
      setCustomer(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load customer')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadCustomer()
  }, [loadCustomer])

  // Return both naming conventions for compatibility
  return {
    customer,
    data: customer,
    loading,
    isLoading: loading,
    error,
    refetch: loadCustomer
  }
}

export function useDeleteCustomer() {
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const deleteCustomer = async (id: number) => {
    setIsDeleting(true)
    setError(null)
    try {
      await apiClient.delete(`/customers/${id}`)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete customer')
      return false
    } finally {
      setIsDeleting(false)
    }
  }

  return {
    deleteCustomer,
    mutate: deleteCustomer,
    isDeleting,
    isLoading: isDeleting,
    error
  }
}

export function useCreateCustomer() {
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createCustomer = async (data: Partial<Customer>) => {
    setIsCreating(true)
    setError(null)
    try {
      const customer = await apiClient.post<Customer>('/customers', data)
      return customer
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create customer')
      throw err
    } finally {
      setIsCreating(false)
    }
  }

  return {
    createCustomer,
    mutate: createCustomer,
    mutateAsync: createCustomer,
    isCreating,
    isLoading: isCreating,
    error
  }
}

export function useUpdateCustomer() {
  const [isUpdating, setIsUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateCustomer = async (id: number, data: Partial<Customer>) => {
    setIsUpdating(true)
    setError(null)
    try {
      const customer = await apiClient.put<Customer>(`/customers/${id}`, data)
      return customer
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update customer')
      throw err
    } finally {
      setIsUpdating(false)
    }
  }

  return {
    updateCustomer,
    mutate: updateCustomer,
    mutateAsync: updateCustomer,
    isUpdating,
    isLoading: isUpdating,
    error
  }
}

export default useCustomers
