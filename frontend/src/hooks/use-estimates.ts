import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiPut, apiDelete } from '@/api/client'
import { Estimate } from '@/types'

export interface EstimatesQueryParams {
  status?: string
  customer_id?: number
  search?: string
  page?: number
  per_page?: number
}

interface EstimatesResponse {
  estimates: Estimate[]
  total: number
  page: number
  per_page: number
}

export type CreateEstimateData = Partial<Estimate> & {
  line_items?: Array<{
    service_type: string
    description: string
    quantity: number
    unit_price: number
  }>
}

export type UpdateEstimateData = Partial<Estimate>

const estimatesApi = {
  list: (filters?: EstimatesQueryParams) =>
    apiGet<EstimatesResponse>('/api/estimates', { params: filters as Record<string, string | number | boolean | undefined> }),
  get: (id: number) => apiGet<Estimate>(`/api/estimates/${id}`),
  create: (data: CreateEstimateData) => apiPost<Estimate>('/api/estimates', data),
  update: (id: number, data: UpdateEstimateData) => apiPut<Estimate>(`/api/estimates/${id}`, data),
  delete: (id: number) => apiDelete<{ success: boolean }>(`/api/estimates/${id}`),
  send: (id: number) => apiPost<Estimate>(`/api/estimates/${id}/send`),
  approve: (id: number) => apiPost<Estimate>(`/api/estimates/${id}/approve`),
  convertToJob: (id: number) => apiPost<{ job_id: number }>(`/api/estimates/${id}/convert-to-job`),
}

export function useEstimates(filters?: EstimatesQueryParams) {
  return useQuery({
    queryKey: ['estimates', filters],
    queryFn: () => estimatesApi.list(filters),
  })
}

export function useEstimate(id: number) {
  return useQuery({
    queryKey: ['estimates', id],
    queryFn: () => estimatesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateEstimateData) => estimatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
  })
}

export function useUpdateEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateEstimateData }) =>
      estimatesApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['estimates'] })
      queryClient.invalidateQueries({ queryKey: ['estimates', id] })
    },
  })
}

export function useDeleteEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => estimatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['estimates'] })
    },
  })
}

export function useSendEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => estimatesApi.send(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['estimates'] })
      queryClient.invalidateQueries({ queryKey: ['estimates', id] })
    },
  })
}

export function useApproveEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => estimatesApi.approve(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['estimates'] })
      queryClient.invalidateQueries({ queryKey: ['estimates', id] })
    },
  })
}

export function useConvertEstimateToJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => estimatesApi.convertToJob(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['estimates'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}
