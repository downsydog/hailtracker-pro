import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'
import { Tech, Job } from '../types'

export interface TechDashboardStats {
  assigned_jobs: number
  completed_today: number
  in_progress: number
  scheduled_today: number
}

export function useTech() {
  const [techs, setTechs] = useState<Tech[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTechs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.get<{ items: Tech[] }>('/techs')
      setTechs(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load techs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTechs()
  }, [loadTechs])

  return {
    techs,
    loading,
    error,
    refresh: loadTechs
  }
}

export function useTechDashboard() {
  const [stats, setStats] = useState<TechDashboardStats | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const [statsData, jobsData] = await Promise.all([
        apiClient.get<TechDashboardStats>('/tech/stats'),
        apiClient.get<{ items: Job[] }>('/tech/jobs')
      ])
      setStats(statsData)
      setJobs(jobsData.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const updateJobStatus = async (jobId: number, status: string) => {
    await apiClient.patch(`/jobs/${jobId}`, { status })
    loadDashboard()
  }

  return {
    stats,
    jobs,
    loading,
    error,
    updateJobStatus,
    refresh: loadDashboard
  }
}

export default useTech
