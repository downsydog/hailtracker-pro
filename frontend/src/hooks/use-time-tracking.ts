import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'

// Utility function to format minutes as "Xh Ym"
export function formatHoursMinutes(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes}m`
  if (minutes === 0) return `${hours}h`
  return `${hours}h ${minutes}m`
}

// Format time as "HH:MM AM/PM"
export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

// Get elapsed time in minutes from a start time
export function getElapsedTime(startTime: string): number {
  const start = new Date(startTime)
  const now = new Date()
  return Math.floor((now.getTime() - start.getTime()) / 60000)
}

export interface TimeEntry {
  id: number
  user_id: number
  job_id?: number
  task_type: string
  start_time: string
  end_time?: string
  duration_minutes?: number
  notes?: string
  created_at: string
}

export interface TimeTrackingState {
  isTracking: boolean
  currentEntry: TimeEntry | null
  todayEntries: TimeEntry[]
  weekEntries: TimeEntry[]
  totalToday: number
  totalWeek: number
}

export function useTimeTracking() {
  const [state, setState] = useState<TimeTrackingState>({
    isTracking: false,
    currentEntry: null,
    todayEntries: [],
    weekEntries: [],
    totalToday: 0,
    totalWeek: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadEntries = useCallback(async () => {
    try {
      const data = await apiClient.get<TimeTrackingState>('/time-tracking/status')
      setState(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load time entries')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadEntries()
  }, [loadEntries])

  const startTracking = async (taskType: string, jobId?: number) => {
    try {
      const entry = await apiClient.post<TimeEntry>('/time-tracking/start', { task_type: taskType, job_id: jobId })
      setState(prev => ({ ...prev, isTracking: true, currentEntry: entry }))
      return entry
    } catch (err) {
      throw err
    }
  }

  const stopTracking = async (notes?: string) => {
    try {
      await apiClient.post('/time-tracking/stop', { notes })
      setState(prev => ({ ...prev, isTracking: false, currentEntry: null }))
      loadEntries()
    } catch (err) {
      throw err
    }
  }

  const logTime = async (data: { task_type: string; duration_minutes: number; job_id?: number; notes?: string }) => {
    try {
      const entry = await apiClient.post<TimeEntry>('/time-tracking/log', data)
      loadEntries()
      return entry
    } catch (err) {
      throw err
    }
  }

  return {
    ...state,
    loading,
    error,
    startTracking,
    stopTracking,
    logTime,
    refresh: loadEntries
  }
}

// Time status hook
export interface TimeStatus {
  success?: boolean
  status?: {
    is_clocked_in?: boolean
    is_on_break?: boolean
    clock_in_time?: string
    current_break_start?: string
    total_hours_today?: number
    break_minutes_today?: number
  }
  today?: {
    total_hours?: number
    break_minutes?: number
  }
  // Legacy fields for backwards compatibility
  isClockedIn?: boolean
  isOnBreak?: boolean
  clockInTime?: string
  breakStartTime?: string
  todayTotal?: number
  weekTotal?: number
}

export function useTimeStatus() {
  const [data, setData] = useState<TimeStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setIsLoading(true)
    try {
      const status = await apiClient.get<TimeStatus>('/time-tracking/status')
      setData(status)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load time status')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { data, isLoading, error, refetch }
}

export function useClockIn() {
  const [isLoading, setIsLoading] = useState(false)

  const mutateAsync = async (_data?: Record<string, unknown>) => {
    setIsLoading(true)
    try {
      await apiClient.post('/time-tracking/clock-in')
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, isPending: isLoading }
}

export function useClockOut() {
  const [isLoading, setIsLoading] = useState(false)

  const mutateAsync = async (_data?: Record<string, unknown>) => {
    setIsLoading(true)
    try {
      await apiClient.post('/time-tracking/clock-out')
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, isPending: isLoading }
}

export function useStartBreak() {
  const [isLoading, setIsLoading] = useState(false)

  const mutateAsync = async () => {
    setIsLoading(true)
    try {
      await apiClient.post('/time-tracking/break/start')
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, isPending: isLoading }
}

export function useEndBreak() {
  const [isLoading, setIsLoading] = useState(false)

  const mutateAsync = async () => {
    setIsLoading(true)
    try {
      await apiClient.post('/time-tracking/break/end')
    } finally {
      setIsLoading(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isLoading, isPending: isLoading }
}

// Week time summary hook
export interface WeekDay {
  date: string
  day_name: string
  hours: number
}

export interface WeekData {
  days: WeekDay[]
  total_hours: number
  break_hours: number
}

export interface WeekTimeResponse {
  success: boolean
  week: WeekData
}

export function useWeekTime() {
  const [data, setData] = useState<WeekTimeResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.get<WeekTimeResponse>('/time-tracking/week')
      setData(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load week time')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { data, isLoading, error, refetch }
}

// Log time mutation hook
export interface LogTimeData {
  job_id: number
  hours: number
  description?: string
}

export function useLogTime() {
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mutateAsync = async (data: LogTimeData) => {
    setIsPending(true)
    setError(null)
    try {
      return await apiClient.post<TimeEntry>('/time-tracking/log-job', data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log time')
      throw err
    } finally {
      setIsPending(false)
    }
  }

  return { mutateAsync, mutate: mutateAsync, isPending, isLoading: isPending, error }
}

export default useTimeTracking
