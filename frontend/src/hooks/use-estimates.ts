import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { estimatesApi, EstimatesQueryParams, CreateEstimateData, UpdateEstimateData } from "@/api/estimates"

export function useEstimates(params?: EstimatesQueryParams) {
  return useQuery({
    queryKey: ["estimates", params],
    queryFn: () => estimatesApi.list(params),
  })
}

export function useEstimate(id: number) {
  return useQuery({
    queryKey: ["estimates", id],
    queryFn: () => estimatesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateEstimateData) => estimatesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estimates"] })
    },
  })
}

export function useUpdateEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateEstimateData }) =>
      estimatesApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["estimates"] })
      queryClient.invalidateQueries({ queryKey: ["estimates", id] })
    },
  })
}

export function useDeleteEstimate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => estimatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["estimates"] })
    },
  })
}
