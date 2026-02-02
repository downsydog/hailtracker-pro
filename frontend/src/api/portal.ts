import { apiClient } from './client'

export interface PortalJob {
  id: number
  job_number: string
  vehicle_info?: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
  vehicle_color?: string
  vehicle_vin?: string
  damage_type?: string
  status: string
  status_label?: string
  scheduled_date?: string
  estimated_completion?: string
  tech_name?: string
  progress?: number
  progress_percent?: number
  notes?: string
  documents_count?: number
  messages_count?: number
  photos_count?: number
  created_at?: string
  updated_at?: string
  timeline?: PortalTimelineEvent[]
  photos?: PortalPhoto[]
  documents?: PortalDocument[]
  estimate?: PortalEstimate
  [key: string]: unknown  // Allow additional properties
}

export interface PortalAppointment {
  id: number
  job_id?: number
  date?: string
  time?: string
  scheduled_at?: string
  type: string
  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | string
  vehicle_info?: string
  location?: string
  notes?: string
  [key: string]: unknown  // Allow additional properties
}

export interface PortalMessage {
  id: number
  from?: string
  subject?: string
  body?: string
  message?: string
  is_read?: boolean
  created_at: string
  job_id?: number
  sender_type?: 'customer' | 'shop' | 'system' | string
  sender_name?: string
  read_at?: string
  attachments?: Array<{ id?: number; name?: string; url?: string } | string>
  [key: string]: unknown
}

export interface PortalEstimate {
  id?: number
  estimate_number?: string
  created_at?: string
  status?: 'draft' | 'sent' | 'approved' | 'rejected' | string
  items?: Array<{ id?: number; description: string; service_type?: string; quantity?: number; unit_price?: number; total?: number }>
  subtotal?: number
  tax?: number
  total?: number
  [key: string]: unknown
}

export interface PortalDocument {
  id: number
  name: string
  type: string
  url: string
  created_at: string
}

export interface PortalPhoto {
  id: number
  job_id: number
  url: string
  thumbnail_url: string
  caption?: string
  description?: string
  stage: 'before' | 'during' | 'after'
  type?: 'before' | 'during' | 'after' | string
  created_at: string
  uploaded_at?: string
  [key: string]: unknown
}

export interface PortalPayment {
  id: number
  amount?: number
  status: 'pending' | 'completed' | 'failed' | 'partial' | string
  method?: string
  date?: string
  transaction_id?: string
  paid_at?: string
  [key: string]: unknown
}

export interface PortalReview {
  id: number
  rating: number
  comment?: string
  response?: string
  job_id: number
  is_public?: boolean
  would_recommend?: boolean
  created_at: string
  responded_at?: string
  response_at?: string
  [key: string]: unknown
}

export interface PortalReferral {
  id: number
  referred_name: string
  referred_phone: string
  referred_email?: string
  status: 'pending' | 'contacted' | 'converted'
  reward_amount?: number
  reward_status?: 'pending' | 'paid' | 'APPROVED' | string
  created_at: string
  converted_at?: string
  [key: string]: unknown
}

export interface PortalSettings {
  email_notifications: boolean
  sms_notifications: boolean
  marketing_emails: boolean
}

export interface PortalInsurance {
  id: number
  provider: string
  policy_number: string
  claim_number?: string
  deductible: number
  status: string
}

export interface PortalFlyer {
  id: number
  title: string
  name?: string
  description: string
  image_url: string
  thumbnail_url?: string
  valid_until?: string
  discount_code?: string
  views?: number
  clicks?: number
  type?: string
}

export interface LoyaltyInfo {
  points: number
  tier: string
  next_tier?: string
  next_tier_points?: number
  points_to_next_tier?: number
  tier_progress?: number
  lifetime_points?: number
  rewards_redeemed?: number
  rewards_available?: Array<{ id: number; name: string; points_required: number }>
  available_rewards?: LoyaltyReward[]
  point_history?: PointHistory[]
  [key: string]: unknown
}

// Additional types for components
export interface PortalDashboardData {
  jobs?: PortalJob[]
  appointments?: PortalAppointment[]
  unread_messages?: number
  recent_activity?: Array<{ type: string; description: string; date: string }>
  customer?: Record<string, unknown>
  active_jobs?: Array<PortalJob & Record<string, unknown>>
  completed_jobs?: Array<PortalJob & Record<string, unknown>>
  upcoming_appointments?: Array<PortalAppointment & Record<string, unknown>>
  pending_actions?: Array<{ id?: string; type: string; title?: string; description: string; action?: string; job_id?: number; priority?: string }>
  [key: string]: unknown  // Allow additional properties
}

export interface DigitalFlyer {
  id: number
  title: string
  name?: string
  description: string
  image_url: string
  thumbnail_url?: string
  valid_until?: string
  discount_code?: string
  views?: number
  clicks?: number
  type?: string
}

export interface PersonalizedFlyer {
  id: number
  flyer_id: number
  customer_name: string
  personalized_url: string
  flyer_url?: string
  views?: number
  clicks?: number
  created_at: string
}

export interface FlyerAnalytics {
  total_views: number
  total_clicks: number
  conversion_rate?: number
  flyers_shared?: number
  leads_generated?: number
  by_flyer: Array<{ flyer_id: number; title: string; views: number; clicks: number }>
}

export interface InsuranceSupplement {
  id: number
  amount: number
  status: string
  date?: string
  reason?: string
  submitted_at?: string
  [key: string]: unknown
}

export interface InsuranceTimelineEvent {
  id?: number
  date?: string
  event?: string
  details?: string
  type?: string
  title?: string
  description?: string
  timestamp?: string
  color?: string
  [key: string]: unknown
}

export interface InsuranceStatus {
  id?: number
  provider?: string
  insurance_company?: string
  policy_number?: string
  claim_number?: string
  deductible?: number
  status: 'pending' | 'approved' | 'denied' | 'in_progress' | 'submitted' | 'supplement_needed' | string
  status_label?: string
  coverage_amount?: number
  approved_amount?: number
  adjuster_name?: string
  adjuster_phone?: string
  adjuster_email?: string
  notes?: string
  supplements?: InsuranceSupplement[]
  timeline?: InsuranceTimelineEvent[]
  [key: string]: unknown
}

export interface PortalTimelineEvent {
  id: number
  type: 'status_change' | 'photo_added' | 'message' | 'payment' | 'appointment'
  title: string
  description: string
  timestamp: string
  color?: string
  metadata?: Record<string, unknown>
}

export interface LoyaltyData {
  points: number
  tier: string
  next_tier?: string
  next_tier_points?: number
  points_to_next_tier?: number
  tier_progress?: number
  lifetime_points?: number
  rewards_redeemed?: number
  available_rewards?: LoyaltyReward[]
  point_history?: PointHistory[]
  [key: string]: unknown
}

export interface LoyaltyReward {
  id: number
  name: string
  description: string
  points_required: number
  category: string
  type?: string
  is_available: boolean
  [key: string]: unknown
}

export interface PointHistory {
  id: number
  points: number
  type: 'earned' | 'redeemed' | 'expired'
  description: string
  created_at: string
}

export interface PortalInvoice {
  id: number
  invoice_number: string
  amount?: number
  subtotal?: number
  tax?: number
  total?: number
  amount_paid?: number
  balance_due?: number
  status: 'pending' | 'paid' | 'overdue' | 'partial' | string
  due_date: string
  paid_date?: string
  created_at?: string
  payments?: Array<PortalPayment>
  items?: Array<{ description: string; amount: number }>
  [key: string]: unknown
}

export interface Referral {
  id: number
  referred_name: string
  referred_email?: string
  referred_phone: string
  status: 'pending' | 'contacted' | 'converted' | 'lost'
  reward_amount?: number
  reward_status?: 'pending' | 'paid' | 'APPROVED' | string
  created_at: string
  converted_at?: string
  [key: string]: unknown
}

export interface ReferralStats {
  total_referrals: number
  converted?: number
  converted_referrals?: number
  pending?: number
  pending_rewards?: number
  total_rewards_earned?: number
  total_earned?: number
  conversion_rate?: number
  share_url?: string
  referral_code?: string
  [key: string]: unknown
}

export interface Review {
  id: number
  job_id: number
  rating: number
  comment?: string
  response?: string
  is_public?: boolean
  would_recommend?: boolean
  created_at: string
  responded_at?: string
  response_at?: string
  [key: string]: unknown
}

export interface PendingReview {
  id: number
  job_id: number
  job_number: string
  vehicle_info: string
  vehicle?: string
  completed_date: string
  completed_at?: string
  [key: string]: unknown
}

export interface PortalNotificationPrefs {
  email_job_updates?: boolean
  email_appointment_reminders?: boolean
  email_promotions?: boolean
  email_enabled?: boolean
  sms_job_updates?: boolean
  sms_appointment_reminders?: boolean
  sms_enabled?: boolean
  push_enabled?: boolean
  notify_on_status?: boolean
  notify_on_status_change?: boolean
  notify_on_message?: boolean
  notify_on_appointment?: boolean
  notify_on_completion?: boolean
  [key: string]: boolean | undefined  // Allow additional boolean properties
}

export const portalApi = {
  // Dashboard
  getDashboard: () =>
    apiClient.get<{ jobs: PortalJob[]; appointments: PortalAppointment[]; unread_messages: number }>('/portal/dashboard'),

  // Jobs
  getJobs: () =>
    apiClient.get<{ jobs: PortalJob[] }>('/portal/jobs'),

  getJob: (id: number) =>
    apiClient.get<PortalJob>(`/portal/jobs/${id}`),

  // Appointments
  getAppointments: () =>
    apiClient.get<{ appointments: PortalAppointment[] }>('/portal/appointments'),

  scheduleAppointment: (data: { date: string; time: string; type: string }) =>
    apiClient.post<PortalAppointment>('/portal/appointments', data),

  cancelAppointment: (id: number) =>
    apiClient.delete(`/portal/appointments/${id}`),

  // Messages
  getMessages: (_jobId?: number) =>
    apiClient.get<{ messages: PortalMessage[] }>('/portal/messages'),

  markMessageRead: (id: number) =>
    apiClient.post(`/portal/messages/${id}/read`),

  sendMessage: (data: { subject: string; body: string }) =>
    apiClient.post('/portal/messages', data),

  // Documents
  getDocuments: () =>
    apiClient.get<{ documents: PortalDocument[] }>('/portal/documents'),

  // Photos
  getPhotos: (jobId?: number) =>
    apiClient.get<{ photos: PortalPhoto[] }>('/portal/photos', { job_id: jobId }),

  // Payments
  getPayments: () =>
    apiClient.get<{ payments: PortalPayment[] }>('/portal/payments'),

  getPaymentHistory: () =>
    apiClient.get<{ payments: PortalPayment[]; invoices?: PortalInvoice[] }>('/portal/payments/history'),

  makePayment: (data: { amount: number; method: string }) =>
    apiClient.post<PortalPayment>('/portal/payments', data),

  // Reviews
  getReviews: () =>
    apiClient.get<{ reviews: PortalReview[]; pending_reviews?: PendingReview[] }>('/portal/reviews'),

  submitReview: (jobId: number, data?: { rating: number; comment?: string }) =>
    apiClient.post<PortalReview>(`/portal/reviews`, typeof data === 'object' ? { ...data, job_id: jobId } : { job_id: jobId }),

  // Referrals
  getReferrals: () =>
    apiClient.get<{ referrals: PortalReferral[]; stats?: ReferralStats }>('/portal/referrals'),

  submitReferral: (data: { name: string; phone: string; email?: string }) =>
    apiClient.post<PortalReferral>('/portal/referrals', data),

  createReferral: (data: { referred_name: string; referred_email?: string; referred_phone?: string; notes?: string }) =>
    apiClient.post<PortalReferral>('/portal/referrals', data),

  // Settings
  getSettings: () =>
    apiClient.get<PortalSettings>('/portal/settings'),

  updateSettings: (data: Partial<PortalSettings>) =>
    apiClient.patch<PortalSettings>('/portal/settings', data),

  // Insurance
  getInsurance: () =>
    apiClient.get<{ insurance: PortalInsurance[] }>('/portal/insurance'),

  getInsuranceStatus: (jobId?: number) =>
    apiClient.get<InsuranceStatus>(`/portal/insurance/status${jobId ? `?job_id=${jobId}` : ''}`),

  // Flyers
  getFlyers: () =>
    apiClient.get<{ flyers: PortalFlyer[]; personalized?: PersonalizedFlyer[] }>('/portal/flyers'),

  // Loyalty
  getLoyalty: () =>
    apiClient.get<LoyaltyInfo>('/portal/loyalty'),

  redeemReward: (rewardId: number) =>
    apiClient.post(`/portal/loyalty/redeem/${rewardId}`),

  // Additional functions
  requestReschedule: (appointmentId: number, data: { new_date?: string; new_time?: string; reason?: string }) =>
    apiClient.post(`/portal/appointments/${appointmentId}/reschedule`, data),

  downloadDocument: (documentId: number) =>
    apiClient.get<Blob>(`/portal/documents/${documentId}/download`),

  getFlyerAnalytics: () =>
    apiClient.get<FlyerAnalytics>('/portal/flyers/analytics'),

  generateFlyer: (data: { flyer_id: number; customer_name?: string }) =>
    apiClient.post<PersonalizedFlyer>('/portal/flyers/generate', data),

  getNotificationPrefs: () =>
    apiClient.get<PortalNotificationPrefs>('/portal/settings/notifications'),

  updateNotificationPrefs: (data: Partial<PortalNotificationPrefs>) =>
    apiClient.patch<PortalNotificationPrefs>('/portal/settings/notifications', data),

  // Profile
  updateProfile: (data: { name?: string; email?: string; phone?: string; [key: string]: unknown }) =>
    apiClient.patch('/portal/profile', data),

  changeAccessCode: (currentCode: string, newCode: string) =>
    apiClient.post('/portal/access-code', { current_code: currentCode, new_code: newCode }),
}

export default portalApi
