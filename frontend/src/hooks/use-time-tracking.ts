import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { techApi } from '@/api/tech'

export function useTimeStatus() {
  return useQuery({
    queryKey: ['tech', 'time-status'],
    queryFn: techApi.getTimeStatus,
    refetchInterval: 60000, // Refetch every minute
  })
}

export function useWeekTime() {
  return useQuery({
    queryKey: ['tech', 'week-time'],
    queryFn: techApi.getWeekTime,
  })
}

export function useTodayTime() {
  return useQuery({
    queryKey: ['tech', 'today-time'],
    queryFn: techApi.getTodayTime,
  })
}

export function useClockIn() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data?: { location?: string; notes?: string }) => techApi.clockIn(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech', 'time-status'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'today-time'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'week-time'] })
    },
  })
}

export function useClockOut() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data?: { location?: string; notes?: string }) => techApi.clockOut(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech', 'time-status'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'today-time'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'week-time'] })
    },
  })
}

export function useStartBreak() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => techApi.startBreak(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech', 'time-status'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'today-time'] })
    },
  })
}

export function useEndBreak() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => techApi.endBreak(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech', 'time-status'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'today-time'] })
    },
  })
}

export function useLogTime() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { job_id: number; hours: number; description?: string }) =>
      techApi.logTime(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech', 'time-status'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'today-time'] })
      queryClient.invalidateQueries({ queryKey: ['tech', 'week-time'] })
    },
  })
}

// Helper to format hours as HH:MM
export function formatHoursMinutes(hours: number): string {
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  return `${h}h ${m}m`
}

// Helper to format time string to local time
export function formatTime(timeString: string | null): string {
  if (!timeString) return '--:--'
  const date = new Date(timeString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Helper to calculate elapsed time since a timestamp
export function getElapsedTime(startTime: string | null): string {
  if (!startTime) return '0h 0m'
  const start = new Date(startTime).getTime()
  const now = Date.now()
  const elapsed = (now - start) / 1000 / 60 / 60 // hours
  return formatHoursMinutes(elapsed)
}
