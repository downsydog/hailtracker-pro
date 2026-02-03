import { apiClient, ApiParams } from './client'

export interface ScheduleSlot {
  id: number
  date: string
  time: string
  tech_id?: number
  tech_name?: string
  job_id?: number
  job_number?: string
  customer_name?: string
  vehicle_name?: string
  status: 'available' | 'booked' | 'blocked'
  duration_minutes: number
}

export interface SchedulingToken {
  id: number
  token: string
  appointment_type: string
  expires_at: string
  max_uses: number
  uses: number
  is_active: boolean
  created_at: string
}

export interface CreateTokenParams {
  appointment_type: string
  expires_hours: number
  max_uses: number
}

export interface ScheduleParams {
  date?: string
  start_date?: string
  end_date?: string
  tech_id?: number
}

export async function getSchedule(params: ScheduleParams): Promise<{ slots: ScheduleSlot[] }> {
  return apiClient.get<{ slots: ScheduleSlot[] }>('/schedule', params as ApiParams)
}

export async function getAvailableSlots(date: string, appointmentType: string): Promise<{ slots: ScheduleSlot[] }> {
  return apiClient.get<{ slots: ScheduleSlot[] }>('/schedule/available', {
    date,
    appointment_type: appointmentType
  })
}

export async function bookSlot(slotId: number, jobId: number): Promise<ScheduleSlot> {
  return apiClient.post<ScheduleSlot>(`/schedule/slots/${slotId}/book`, { job_id: jobId })
}

export async function getSchedulingTokens(): Promise<{ tokens: SchedulingToken[] }> {
  return apiClient.get<{ tokens: SchedulingToken[] }>('/schedule/tokens')
}

export async function createSchedulingToken(params: CreateTokenParams): Promise<SchedulingToken> {
  return apiClient.post<SchedulingToken>('/schedule/tokens', params)
}

export async function revokeSchedulingToken(tokenId: number): Promise<void> {
  await apiClient.delete(`/schedule/tokens/${tokenId}`)
}

export const scheduleApi = {
  getSchedule,
  getAvailableSlots,
  bookSlot,
  getSchedulingTokens,
  createSchedulingToken,
  revokeSchedulingToken
}

export default scheduleApi
