export interface User {
  id: number
  username: string
  email: string
  name: string
  first_name?: string
  last_name?: string
  phone?: string
  role: string
  permissions: string[]
  is_active: boolean
  created_at?: string
}

export interface Lead {
  id: number
  first_name: string
  last_name: string
  name?: string
  display_name?: string
  email: string
  phone: string
  status: string
  temperature: string
  source: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
  damage_type?: string
  damage_description?: string
  estimated_repair_cost?: number
  score?: number
  created_at: string
  company_name?: string
  notes?: string
  latitude?: number
  longitude?: number
}

export interface Customer {
  id: number
  name?: string
  first_name: string
  last_name: string
  company_name?: string
  email: string
  phone: string
  street_address?: string
  address?: string
  city: string
  state: string
  zip_code?: string
  zip?: string
  customer_type?: string
  status?: string
  source?: string
  vehicles_count?: number
  jobs_count?: number
  created_at: string
}

export interface Vehicle {
  id: number
  customer_id: number
  customer_name: string
  year: number
  make: string
  model: string
  color: string
  vin: string
  license_plate: string
  status: string
}

export interface Job {
  id: number
  job_number: string
  customer_id: number
  customer_name: string
  customer_email?: string
  customer_phone?: string
  vehicle_id: number
  vehicle_name: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
  vehicle_vin?: string
  vehicle_color?: string
  license_plate?: string
  damage_type?: string
  tech_notes?: string
  internal_notes?: string
  insurance_company?: string
  claim_number?: string
  deductible?: number
  notes?: string
  status: string
  tech_id: number | null
  tech_name: string | null
  scheduled_date?: string | null
  scheduled_drop_off?: string | null
  estimated_completion?: string | null
  total: number
  created_at: string
}

export interface Estimate {
  id: number
  estimate_number: string
  customer_id: number
  customer_name: string
  vehicle_id: number
  vehicle_name: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
  status: string
  subtotal: number
  tax: number
  total: number
  created_at: string
  sent_at: string | null
  approved_at: string | null
}

export interface SearchResult {
  id: number
  type: string
  title: string
  subtitle?: string
  url: string
}

export interface JobStats {
  total: number
  in_progress: number
  completed?: number
  completed_this_week?: number
  total_revenue?: number
  scheduled_today?: number
  new_jobs?: number
  total_customers?: number
  monthly_revenue?: number
  completion_rate?: number
}

export interface EstimateLineItem {
  id: number
  estimate_id: number
  service_type: string
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface Notification {
  id: number
  type: string
  title: string
  message: string
  is_read: boolean | number
  created_at: string
  link: string | null
  relative_time?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface ApiError {
  error: string
  message?: string
}

export interface DashboardStats {
  leads_count: number
  leads_trend?: string
  leads_trend_up?: boolean
  active_jobs: number
  pending_estimates: number
  revenue_mtd: number
  revenue_trend?: string
  revenue_trend_up?: boolean
}

export interface Tech {
  id: number
  name: string
  email: string
  phone: string
  active: boolean
}
