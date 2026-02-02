import { apiGet, apiPost } from './client'

// Kiosk API for self-service check-in

export interface KioskCustomerLookup {
  customer_id?: number
  first_name?: string
  last_name?: string
  email?: string
  phone?: string
  vehicles?: KioskVehicle[]
}

export interface KioskVehicle {
  id: number
  year: number
  make: string
  model: string
  color?: string
  vin?: string
  license_plate?: string
}

export interface KioskCheckInData {
  // Step 1: Customer lookup/creation
  customer_id?: number
  first_name: string
  last_name: string
  phone: string
  email: string

  // Step 2: Vehicle
  vehicle_id?: number
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_color?: string
  vehicle_vin?: string
  vehicle_license_plate?: string

  // Step 3: Damage assessment
  damage_type: string
  damage_description?: string
  damage_photos?: string[]

  // Step 4: Additional info
  insurance_company?: string
  claim_number?: string
  has_rental_coverage?: boolean
  preferred_contact: 'phone' | 'email' | 'text'

  // Signature
  signature?: string
}

export interface KioskCheckInResponse {
  success: boolean
  job_id?: number
  job_number?: string
  queue_position?: number
  estimated_wait?: string
  access_code?: string
  error?: string
}

export interface KioskQueueItem {
  position: number
  job_number: string
  customer_name: string
  vehicle: string
  status: string
  estimated_time?: string
}

export interface KioskQueueResponse {
  queue: KioskQueueItem[]
  now_serving?: string
  average_wait: number
}

export interface DamageType {
  id: string
  label: string
  icon: string
  description: string
}

export const DAMAGE_TYPES: DamageType[] = [
  {
    id: 'hail',
    label: 'Hail Damage',
    icon: '🌧️',
    description: 'Dents caused by hailstones',
  },
  {
    id: 'door_ding',
    label: 'Door Dings',
    icon: '🚗',
    description: 'Small dents from car doors',
  },
  {
    id: 'minor_dent',
    label: 'Minor Dents',
    icon: '🔧',
    description: 'Small dents from various causes',
  },
  {
    id: 'crease',
    label: 'Crease Damage',
    icon: '📐',
    description: 'Linear dents or creases',
  },
  {
    id: 'large_dent',
    label: 'Large Dents',
    icon: '⚠️',
    description: 'Significant body damage',
  },
  {
    id: 'other',
    label: 'Other',
    icon: '❓',
    description: 'Other damage types',
  },
]

export const VEHICLE_MAKES = [
  'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler',
  'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jeep', 'Kia',
  'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'Mitsubishi', 'Nissan',
  'Porsche', 'Ram', 'Subaru', 'Tesla', 'Toyota', 'Volkswagen', 'Volvo',
]

export const INSURANCE_COMPANIES = [
  'State Farm', 'GEICO', 'Progressive', 'Allstate', 'USAA', 'Liberty Mutual',
  'Farmers', 'Nationwide', 'Travelers', 'American Family', 'Auto-Owners',
  'Erie Insurance', 'Safeco', 'The Hartford', 'MetLife', 'Other',
]

export const kioskApi = {
  // Customer lookup by phone
  lookupCustomer: (phone: string) =>
    apiGet<KioskCustomerLookup>('/api/kiosk/lookup', { params: { phone } }),

  // Submit check-in
  checkIn: (data: KioskCheckInData) =>
    apiPost<KioskCheckInResponse>('/api/kiosk/check-in', data),

  // Get current queue
  getQueue: () =>
    apiGet<KioskQueueResponse>('/api/kiosk/queue'),

  // Upload damage photo
  uploadPhoto: (file: File) => {
    const formData = new FormData()
    formData.append('photo', file)
    return apiPost<{ url: string; id: string }>('/api/kiosk/upload-photo', formData)
  },

  // Get damage types
  getDamageTypes: () =>
    apiGet<{ types: DamageType[] }>('/api/kiosk/damage-types'),
}
