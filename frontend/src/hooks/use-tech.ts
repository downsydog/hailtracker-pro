import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { techApi } from "@/api/tech"

/**
 * Hook to get tech dashboard data
 * Supports both tech view (specific tech data) and admin view (all techs overview)
 */
export function useTechDashboard() {
  return useQuery({
    queryKey: ["tech", "dashboard"],
    queryFn: () => techApi.getDashboard(),
    staleTime: 1000 * 30, // 30 seconds - dashboard should refresh frequently
  })
}

/**
 * Hook to get time tracking status
 */
export function useTimeStatus() {
  return useQuery({
    queryKey: ["tech", "time", "status"],
    queryFn: () => techApi.getTimeStatus(),
    staleTime: 1000 * 10, // 10 seconds
    refetchInterval: 1000 * 60, // Refetch every minute
  })
}

/**
 * Hook to get week summary
 */
export function useWeekSummary() {
  return useQuery({
    queryKey: ["tech", "time", "week"],
    queryFn: () => techApi.getWeekTime(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

/**
 * Hook to get tech jobs
 */
export function useTechJobs(filter?: "CURRENT" | "ALL") {
  return useQuery({
    queryKey: ["tech", "jobs", filter],
    queryFn: () => techApi.getJobs(filter),
  })
}

/**
 * Hook to clock in
 */
export function useClockIn() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data?: { location?: string; notes?: string }) =>
      techApi.clockIn(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "time"] })
      queryClient.invalidateQueries({ queryKey: ["tech", "dashboard"] })
    },
  })
}

/**
 * Hook to clock out
 */
export function useClockOut() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data?: { location?: string; notes?: string }) =>
      techApi.clockOut(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "time"] })
      queryClient.invalidateQueries({ queryKey: ["tech", "dashboard"] })
    },
  })
}

/**
 * Hook to start break
 */
export function useStartBreak() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => techApi.startBreak(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "time"] })
    },
  })
}

/**
 * Hook to end break
 */
export function useEndBreak() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => techApi.endBreak(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "time"] })
    },
  })
}

/**
 * Hook to log time to a job
 */
export function useLogTime() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { job_id: number; hours: number; description?: string }) =>
      techApi.logTime(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "time"] })
      queryClient.invalidateQueries({ queryKey: ["tech", "dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

/**
 * Hook to start a job
 */
export function useStartJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: number) => techApi.startJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "jobs"] })
      queryClient.invalidateQueries({ queryKey: ["tech", "dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

/**
 * Hook to update job progress
 */
export function useUpdateProgress() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      jobId,
      data,
    }: {
      jobId: number
      data: { progress_percent?: number; notes?: string }
    }) => techApi.updateProgress(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "jobs"] })
      queryClient.invalidateQueries({ queryKey: ["tech", "dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

/**
 * Hook to complete a job
 */
export function useCompleteJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ jobId, data }: { jobId: number; data?: { notes?: string } }) =>
      techApi.completeJob(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tech", "jobs"] })
      queryClient.invalidateQueries({ queryKey: ["tech", "dashboard"] })
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}
