import { useState, useEffect, useCallback } from 'react'
import { apiClient, ApiParams } from '../api/client'
import { Vehicle, PaginatedResponse } from '../types'

export interface VehicleFilters {
  customer_id?: number
  status?: string
  search?: string
  page?: number
  per_page?: number
}

export function useVehicles(filters: VehicleFilters = {}) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadVehicles = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.get<PaginatedResponse<Vehicle>>('/vehicles', filters as unknown as ApiParams)
      setVehicles(data.items)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load vehicles')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    loadVehicles()
  }, [loadVehicles])

  const createVehicle = async (data: Partial<Vehicle>) => {
    const vehicle = await apiClient.post<Vehicle>('/vehicles', data)
    loadVehicles()
    return vehicle
  }

  const updateVehicle = async (id: number, data: Partial<Vehicle>) => {
    const vehicle = await apiClient.put<Vehicle>(`/vehicles/${id}`, data)
    loadVehicles()
    return vehicle
  }

  const deleteVehicle = async (id: number) => {
    await apiClient.delete(`/vehicles/${id}`)
    loadVehicles()
  }

  return {
    vehicles,
    total,
    loading,
    error,
    createVehicle,
    updateVehicle,
    deleteVehicle,
    refresh: loadVehicles
  }
}

export function useVehicle(id: number | null) {
  const [vehicle, setVehicle] = useState<Vehicle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadVehicle = useCallback(async () => {
    if (!id) {
      setVehicle(null)
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const data = await apiClient.get<Vehicle>(`/vehicles/${id}`)
      setVehicle(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load vehicle')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadVehicle()
  }, [loadVehicle])

  return { vehicle, data: vehicle, loading, isLoading: loading, error, refetch: loadVehicle }
}

export function useCreateVehicle() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutateAsync = async (data: Partial<Vehicle>) => {
    setIsLoading(true)
    setError(null)
    try {
      return await apiClient.post<Vehicle>('/vehicles', data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create vehicle')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, error }
}

export function useUpdateVehicle() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutateAsync = async ({ id, data }: { id: number; data: Partial<Vehicle> }) => {
    setIsLoading(true)
    setError(null)
    try {
      return await apiClient.put<Vehicle>(`/vehicles/${id}`, data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update vehicle')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, error }
}

export function useDeleteVehicle() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutateAsync = async (id: number) => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.delete(`/vehicles/${id}`)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete vehicle')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, error }
}

export function useDecodeVIN() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutateAsync = async (vin: string) => {
    setIsLoading(true)
    setError(null)
    try {
      return await apiClient.get<{ year: number; make: string; model: string }>(`/vehicles/decode-vin/${vin}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to decode VIN')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, error }
}

export default useVehicles
