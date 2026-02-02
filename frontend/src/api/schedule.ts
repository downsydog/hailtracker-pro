import { apiGet, apiPost, apiPut, apiDelete } from './client'

export interface ScheduleEvent {
  id: number
  title: string
  event_type: 'job' | 'appointment' | 'inspection' | 'delivery' | 'pickup' | 'meeting' | 'other'
  job_id?: number
  customer_id?: number
  customer_name?: string
  vehicle_info?: string
  assigned_to?: number
  assigned_to_name?: string
  start_time: string
  end_time: string
  all_day: boolean
  location?: string
  notes?: string
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show'
  color?: string
  reminder_sent: boolean
  created_at: string
  updated_at: string
}

export interface ScheduleSlot {
  start_time: string
  end_time: string
  available: boolean
  technician_id?: number
  technician_name?: string
}

export interface TechnicianSchedule {
  technician_id: number
  technician_name: string
  events: ScheduleEvent[]
  available_slots: ScheduleSlot[]
}

export interface ScheduleCreateData {
  title: string
  event_type: ScheduleEvent['event_type']
  job_id?: number
  customer_id?: number
  assigned_to?: number
  start_time: string
  end_time: string
  all_day?: boolean
  location?: string
  notes?: string
  send_reminder?: boolean
}

export interface ScheduleFilters {
  start_date: string
  end_date: string
  event_type?: string
  assigned_to?: number
  status?: string
  customer_id?: number
  job_id?: number
}

export const scheduleApi = {
  // Get events for date range
  getEvents: (filters: ScheduleFilters) =>
    apiGet<{ events: ScheduleEvent[] }>('/api/schedule/events', { params: filters }),

  // Get single event
  getEvent: (id: number) =>
    apiGet<ScheduleEvent>(`/api/schedule/events/${id}`),

  // Create event
  createEvent: (data: ScheduleCreateData) =>
    apiPost<{ success: boolean; event_id: number }>('/api/schedule/events', data),

  // Update event
  updateEvent: (id: number, data: Partial<ScheduleCreateData>) =>
    apiPut<{ success: boolean }>(`/api/schedule/events/${id}`, data),

  // Delete event
  deleteEvent: (id: number) =>
    apiDelete<{ success: boolean }>(`/api/schedule/events/${id}`),

  // Update event status
  updateStatus: (id: number, status: ScheduleEvent['status']) =>
    apiPost<{ success: boolean }>(`/api/schedule/events/${id}/status`, { status }),

  // Get technician schedules
  getTechnicianSchedules: (date: string) =>
    apiGet<{ schedules: TechnicianSchedule[] }>('/api/schedule/technicians', { params: { date } }),

  // Get available slots for a date
  getAvailableSlots: (date: string, duration?: number, technicianId?: number) =>
    apiGet<{ slots: ScheduleSlot[] }>('/api/schedule/available-slots', {
      params: { date, duration, technician_id: technicianId }
    }),

  // Book appointment (customer-facing)
  bookAppointment: (data: {
    customer_id: number
    job_id?: number
    preferred_date: string
    preferred_time?: string
    event_type: string
    notes?: string
  }) =>
    apiPost<{ success: boolean; event_id: number; scheduled_time: string }>('/api/schedule/book', data),

  // Reschedule appointment
  reschedule: (id: number, newStart: string, newEnd: string) =>
    apiPost<{ success: boolean }>(`/api/schedule/events/${id}/reschedule`, {
      start_time: newStart,
      end_time: newEnd
    }),

  // Get today's schedule summary
  getTodaySummary: () =>
    apiGet<{
      total_events: number
      completed: number
      upcoming: number
      events_by_type: Record<string, number>
      next_event?: ScheduleEvent
    }>('/api/schedule/today'),

  // Send reminder for event
  sendReminder: (id: number, method?: 'email' | 'sms' | 'both') =>
    apiPost<{ success: boolean }>(`/api/schedule/events/${id}/send-reminder`, { method }),

  // Bulk update events (drag & drop)
  bulkUpdate: (updates: Array<{ id: number; start_time: string; end_time: string }>) =>
    apiPost<{ success: boolean; updated: number }>('/api/schedule/bulk-update', { updates }),

  // ==========================================================================
  // SELF-SCHEDULING TOKENS
  // ==========================================================================

  // Get active self-scheduling tokens
  getSchedulingTokens: () =>
    apiGet<{ tokens: SchedulingToken[] }>('/scheduling/tokens'),

  // Create a self-scheduling token/link for customer
  createSchedulingToken: (data: {
    customer_id?: number
    job_id?: number
    appointment_type?: string
    expires_hours?: number
    max_uses?: number
  }) =>
    apiPost<{
      success: boolean
      token: string
      scheduling_url: string
      expires_at: string
    }>('/scheduling/tokens', data),
}

// Self-scheduling token type
export interface SchedulingToken {
  id: number
  token: string
  customer_id?: number
  customer_name?: string
  job_id?: number
  organization_id: number
  appointment_type: string
  expires_at: string
  max_uses: number
  times_used: number
  is_active: boolean
  created_at: string
}
