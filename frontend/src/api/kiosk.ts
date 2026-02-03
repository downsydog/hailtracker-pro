import { apiClient } from './client'

export interface KioskCheckIn {
  id: number
  customer_name: string
  phone: string
  email?: string
  vehicle_info: string
  appointment_id?: number
  check_in_time: string
  status: 'waiting' | 'in_service' | 'completed'
  queue_position?: number
  estimated_wait_minutes?: number
}

export interface QueueItem {
  id?: number
  customer_name: string
  vehicle_info?: string
  vehicle?: string
  job_number?: string
  position?: number
  service_type?: string
  check_in_time?: string
  status: string
  estimated_completion?: string
  estimated_time?: string
  tech_name?: string
  [key: string]: unknown  // Allow additional properties
}

// Alias for components
export type KioskQueueItem = QueueItem

// Check-in form data
export interface KioskCheckInData {
  phone: string
  customer_id?: number
  first_name: string
  last_name: string
  email?: string
  vehicle_id?: number
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_color?: string
  damage_type: string
  damage_description?: string
  insurance_company?: string
  claim_number?: string
  preferred_contact?: 'phone' | 'email' | 'text'
}

// Vehicle from customer lookup
export interface KioskVehicle {
  id: number
  year: number
  make: string
  model: string
  color?: string
  license_plate?: string
  vin?: string
}

// Customer lookup response
export interface CustomerLookupResponse {
  customer_id?: number
  first_name?: string
  last_name?: string
  email?: string
  vehicles?: KioskVehicle[]
}

// Check-in response
export interface KioskCheckInResponse {
  success: boolean
  job_number?: string
  queue_position?: number
  access_code?: string
  error?: string
}

// Constants for forms
export const DAMAGE_TYPES = [
  { id: 'hail', label: 'Hail Damage', icon: '🌨️' },
  { id: 'dent', label: 'Dents', icon: '🔘' },
  { id: 'scratch', label: 'Scratches', icon: '✏️' },
  { id: 'collision', label: 'Collision', icon: '💥' },
  { id: 'paint', label: 'Paint Damage', icon: '🎨' },
  { id: 'other', label: 'Other', icon: '❓' },
]

export const VEHICLE_MAKES = [
  'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler',
  'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jaguar',
  'Jeep', 'Kia', 'Land Rover', 'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz',
  'Mini', 'Mitsubishi', 'Nissan', 'Porsche', 'Ram', 'Subaru', 'Tesla',
  'Toyota', 'Volkswagen', 'Volvo', 'Other'
]

export const INSURANCE_COMPANIES = [
  'State Farm', 'Geico', 'Progressive', 'Allstate', 'USAA',
  'Liberty Mutual', 'Farmers', 'Nationwide', 'Travelers', 'American Family',
  'Auto-Owners', 'Erie Insurance', 'Shelter Insurance', 'Texas Farm Bureau',
  'Self Pay', 'Other'
]

export const kioskApi = {
  // Check-in
  checkIn: (data: KioskCheckInData) =>
    apiClient.post<KioskCheckInResponse>('/kiosk/check-in', data),

  // Customer lookup by phone
  lookupCustomer: (phone: string) =>
    apiClient.get<CustomerLookupResponse>('/kiosk/lookup', { phone }),

  // Queue
  getQueue: () =>
    apiClient.get<{ queue: QueueItem[]; average_wait_minutes: number; average_wait?: number }>('/kiosk/queue'),

  getQueuePosition: (checkInId: number) =>
    apiClient.get<{ position: number; estimated_wait_minutes: number }>(`/kiosk/queue/${checkInId}`),

  // Status
  getCheckInStatus: (checkInId: number) =>
    apiClient.get<KioskCheckIn>(`/kiosk/check-in/${checkInId}`),

  // Lookup appointment
  lookupAppointment: (phone: string) =>
    apiClient.get<{ appointments: Array<{ id: number; date: string; time: string; service: string }> }>('/kiosk/appointments', { phone }),
}

export default kioskApi
