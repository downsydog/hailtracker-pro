import { apiGet, apiPost, apiPut } from './client'

// Customer Portal API - separate authentication context for customers

export interface PortalLoginData {
  access_code: string
  email?: string
  phone?: string
}

export interface PortalAuthResponse {
  success: boolean
  token?: string
  customer?: PortalCustomer
  error?: string
}

export interface PortalCustomer {
  id: number
  first_name: string
  last_name: string
  email: string
  phone?: string
  avatar_url?: string
}

export interface PortalJob {
  id: number
  job_number: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_color?: string
  vehicle_vin?: string
  status: string
  status_label: string
  damage_type?: string
  estimated_completion?: string
  scheduled_date?: string
  actual_start?: string
  actual_completion?: string
  tech_name?: string
  tech_photo?: string
  progress_percent?: number
  photos_count: number
  documents_count: number
  messages_count: number
  created_at: string
  updated_at: string
}

export interface PortalJobDetail extends PortalJob {
  timeline: PortalTimelineEvent[]
  photos: PortalPhoto[]
  documents: PortalDocument[]
  estimate?: PortalEstimate
  invoice?: PortalInvoice
}

export interface PortalTimelineEvent {
  id: number
  type: string
  title: string
  description?: string
  timestamp: string
  icon?: string
  color?: string
}

export interface PortalPhoto {
  id: number
  url: string
  thumbnail_url?: string
  description?: string
  type: string // before, during, after
  uploaded_at: string
}

export interface PortalDocument {
  id: number
  type: string // estimate, invoice, insurance, other
  name: string
  url: string
  created_at: string
}

export interface PortalEstimate {
  id: number
  estimate_number: string
  subtotal: number
  tax: number
  total: number
  status: string
  items: PortalEstimateItem[]
  created_at: string
  approved_at?: string
}

export interface PortalEstimateItem {
  id: number
  service_type: string
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface PortalInvoice {
  id: number
  invoice_number: string
  subtotal: number
  tax: number
  total: number
  amount_paid: number
  balance_due: number
  status: string
  due_date?: string
  items: PortalInvoiceItem[]
  payments: PortalPayment[]
  created_at: string
}

export interface PortalInvoiceItem {
  id: number
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface PortalPayment {
  id: number
  amount: number
  method: string
  status: string
  transaction_id?: string
  paid_at: string
}

export interface PortalMessage {
  id: number
  job_id: number
  sender_type: 'customer' | 'staff'
  sender_name: string
  message: string
  attachments?: string[]
  read_at?: string
  created_at: string
}

export interface PortalAppointment {
  id: number
  job_id: number
  type: string // drop_off, pick_up, check_in
  scheduled_at: string
  location?: string
  notes?: string
  status: string // scheduled, confirmed, completed, cancelled
  reminder_sent?: boolean
}

export interface PortalNotificationPrefs {
  email_enabled: boolean
  sms_enabled: boolean
  push_enabled: boolean
  notify_on_status_change: boolean
  notify_on_message: boolean
  notify_on_appointment: boolean
  notify_on_completion: boolean
}

export interface PortalDashboardData {
  customer: PortalCustomer
  active_jobs: PortalJob[]
  completed_jobs: PortalJob[]
  upcoming_appointments: PortalAppointment[]
  unread_messages: number
  pending_actions: PendingAction[]
}

export interface PendingAction {
  id: string
  type: string // approve_estimate, sign_document, make_payment
  title: string
  description: string
  job_id?: number
  url?: string
  priority: 'high' | 'normal' | 'low'
}

export interface InsuranceStatus {
  claim_number?: string
  insurance_company?: string
  adjuster_name?: string
  adjuster_phone?: string
  adjuster_email?: string
  status: string // pending, submitted, approved, denied, supplement_needed
  status_label: string
  deductible?: number
  approved_amount?: number
  supplements: InsuranceSupplement[]
  timeline: PortalTimelineEvent[]
}

export interface InsuranceSupplement {
  id: number
  amount: number
  reason: string
  status: string
  submitted_at: string
  approved_at?: string
}

// API Functions
export const portalApi = {
  // Authentication
  login: (data: PortalLoginData) =>
    apiPost<PortalAuthResponse>('/api/portal/login', data),

  logout: () =>
    apiPost<{ success: boolean }>('/api/portal/logout'),

  verifyToken: () =>
    apiGet<PortalAuthResponse>('/api/portal/verify'),

  // Dashboard
  getDashboard: () =>
    apiGet<PortalDashboardData>('/api/portal/dashboard'),

  // Jobs
  getJobs: () =>
    apiGet<{ jobs: PortalJob[] }>('/api/portal/jobs'),

  getJob: (jobId: number) =>
    apiGet<PortalJobDetail>(`/api/portal/jobs/${jobId}`),

  getJobTimeline: (jobId: number) =>
    apiGet<{ events: PortalTimelineEvent[] }>(`/api/portal/jobs/${jobId}/timeline`),

  // Documents
  getDocuments: (jobId?: number) =>
    apiGet<{ documents: PortalDocument[] }>('/api/portal/documents', { params: { job_id: jobId } }),

  downloadDocument: (documentId: number) =>
    apiGet<Blob>(`/api/portal/documents/${documentId}/download`, { responseType: 'blob' }),

  // Photos
  getPhotos: (jobId: number) =>
    apiGet<{ photos: PortalPhoto[] }>(`/api/portal/jobs/${jobId}/photos`),

  // Messages
  getMessages: (jobId?: number) =>
    apiGet<{ messages: PortalMessage[] }>('/api/portal/messages', { params: { job_id: jobId } }),

  sendMessage: (jobId: number, message: string, attachments?: File[]) => {
    const formData = new FormData()
    formData.append('message', message)
    formData.append('job_id', jobId.toString())
    if (attachments) {
      attachments.forEach(file => formData.append('attachments', file))
    }
    return apiPost<PortalMessage>('/api/portal/messages', formData)
  },

  markMessageRead: (messageId: number) =>
    apiPost<{ success: boolean }>(`/api/portal/messages/${messageId}/read`),

  // Appointments
  getAppointments: () =>
    apiGet<{ appointments: PortalAppointment[] }>('/api/portal/appointments'),

  requestReschedule: (appointmentId: number, data: { preferred_date: string; preferred_time?: string; reason?: string }) =>
    apiPost<{ success: boolean; message: string }>(`/api/portal/appointments/${appointmentId}/reschedule`, data),

  // Insurance
  getInsuranceStatus: (jobId: number) =>
    apiGet<InsuranceStatus>(`/api/portal/jobs/${jobId}/insurance`),

  // Estimates
  getEstimate: (jobId: number) =>
    apiGet<PortalEstimate>(`/api/portal/jobs/${jobId}/estimate`),

  approveEstimate: (estimateId: number, signature?: string) =>
    apiPost<{ success: boolean }>(`/api/portal/estimates/${estimateId}/approve`, { signature }),

  // Invoices & Payments
  getInvoice: (jobId: number) =>
    apiGet<PortalInvoice>(`/api/portal/jobs/${jobId}/invoice`),

  getPaymentHistory: () =>
    apiGet<{ payments: PortalPayment[] }>('/api/portal/payments'),

  initiatePayment: (invoiceId: number, amount: number, method: string) =>
    apiPost<{ payment_url?: string; success: boolean }>(`/api/portal/invoices/${invoiceId}/pay`, { amount, method }),

  // Account
  getProfile: () =>
    apiGet<PortalCustomer>('/api/portal/profile'),

  updateProfile: (data: Partial<PortalCustomer>) =>
    apiPut<PortalCustomer>('/api/portal/profile', data),

  getNotificationPrefs: () =>
    apiGet<PortalNotificationPrefs>('/api/portal/notifications/preferences'),

  updateNotificationPrefs: (prefs: Partial<PortalNotificationPrefs>) =>
    apiPut<PortalNotificationPrefs>('/api/portal/notifications/preferences', prefs),

  changeAccessCode: (currentCode: string, newCode: string) =>
    apiPost<{ success: boolean }>('/api/portal/change-access-code', { current_code: currentCode, new_code: newCode }),

  // =========================================================================
  // REFERRALS
  // =========================================================================
  getReferrals: () =>
    apiGet<{ referrals: Referral[]; stats: ReferralStats }>('/portal/referrals'),

  getReferralStats: () =>
    apiGet<ReferralStats>('/portal/api/referral-stats'),

  createReferral: (data: { referred_name: string; referred_email?: string; referred_phone?: string; notes?: string }) =>
    apiPost<{ success: boolean; referral_id: number; share_url: string }>('/portal/referrals/create', data),

  getShareLink: () =>
    apiGet<{ share_url: string; qr_code_url: string }>('/portal/referrals/share'),

  trackReferralClick: (referralCode: string) =>
    apiPost<{ success: boolean }>('/portal/referrals/track-click', { code: referralCode }),

  // =========================================================================
  // DIGITAL FLYERS
  // =========================================================================
  getFlyers: () =>
    apiGet<{ flyers: DigitalFlyer[]; personalized: PersonalizedFlyer[] }>('/portal/flyers'),

  generateFlyer: (flyerId: number) =>
    apiPost<{ success: boolean; flyer_url: string; flyer_token: string }>(`/portal/flyers/generate/${flyerId}`),

  getFlyerAnalytics: () =>
    apiGet<FlyerAnalytics>('/portal/flyers/analytics'),

  // =========================================================================
  // LOYALTY PROGRAM
  // =========================================================================
  getLoyalty: () =>
    apiGet<LoyaltyData>('/portal/loyalty'),

  // =========================================================================
  // REVIEWS
  // =========================================================================
  getReviews: () =>
    apiGet<{ reviews: Review[]; pending_reviews: PendingReview[] }>('/portal/reviews'),

  submitReview: (jobId: number, data: { rating: number; comment?: string; would_recommend: boolean }) =>
    apiPost<{ success: boolean }>(`/portal/reviews/submit/${jobId}`, data),

  // =========================================================================
  // REAL-TIME NOTIFICATIONS (SSE)
  // =========================================================================
  getNotifications: (limit?: number) =>
    apiGet<{ notifications: PortalNotification[] }>('/portal/api/notifications', { params: { limit } }),

  getUnreadCount: () =>
    apiGet<{ count: number }>('/portal/api/notifications/unread-count'),

  markNotificationRead: (notificationId: number) =>
    apiPost<{ success: boolean }>(`/portal/api/notifications/${notificationId}/read`),

  markAllNotificationsRead: () =>
    apiPost<{ success: boolean }>('/portal/api/notifications/mark-all-read'),

  dismissNotification: (notificationId: number) =>
    apiPost<{ success: boolean }>(`/portal/api/notifications/${notificationId}/dismiss`),

  // SSE stream URL - use with EventSource
  getNotificationStreamUrl: () => '/portal/api/notifications/stream',

  // =========================================================================
  // PUSH NOTIFICATIONS
  // =========================================================================
  getVapidPublicKey: () =>
    apiGet<{ public_key: string }>('/portal/api/push/vapid-public-key'),

  subscribeToPush: (subscription: PushSubscriptionJSON) =>
    apiPost<{ success: boolean }>('/portal/api/push/subscribe', subscription),

  unsubscribeFromPush: (endpoint: string) =>
    apiPost<{ success: boolean }>('/portal/api/push/unsubscribe', { endpoint }),

  testPushNotification: () =>
    apiPost<{ success: boolean }>('/portal/api/push/test'),
}

// =========================================================================
// ADDITIONAL TYPES
// =========================================================================

export interface Referral {
  id: number
  referred_name: string
  referred_email?: string
  referred_phone?: string
  status: 'PENDING' | 'CONTACTED' | 'CONVERTED' | 'EXPIRED'
  reward_amount?: number
  reward_status?: 'PENDING' | 'APPROVED' | 'PAID'
  created_at: string
  converted_at?: string
}

export interface ReferralStats {
  total_referrals: number
  converted_referrals: number
  pending_rewards: number
  total_earned: number
  conversion_rate: number
  share_url: string
  referral_code: string
}

export interface DigitalFlyer {
  id: number
  name: string
  description: string
  thumbnail_url: string
  type: 'HAIL_EVENT' | 'SEASONAL' | 'PROMOTION'
}

export interface PersonalizedFlyer {
  id: number
  flyer_id: number
  flyer_url: string
  token: string
  views: number
  clicks: number
  created_at: string
}

export interface FlyerAnalytics {
  total_views: number
  total_clicks: number
  flyers_shared: number
  leads_generated: number
  by_flyer: Array<{
    flyer_id: number
    flyer_name: string
    views: number
    clicks: number
  }>
}

export interface LoyaltyData {
  points: number
  tier: 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM'
  tier_progress: number
  next_tier_points: number
  lifetime_points: number
  available_rewards: LoyaltyReward[]
  point_history: PointHistory[]
}

export interface LoyaltyReward {
  id: number
  name: string
  description: string
  points_required: number
  type: 'DISCOUNT' | 'FREE_SERVICE' | 'GIFT_CARD'
}

export interface PointHistory {
  id: number
  points: number
  type: 'EARNED' | 'REDEEMED' | 'BONUS'
  description: string
  created_at: string
}

export interface Review {
  id: number
  job_id: number
  rating: number
  comment?: string
  would_recommend: boolean
  created_at: string
  response?: string
  response_at?: string
}

export interface PendingReview {
  job_id: number
  job_number: string
  vehicle: string
  completed_at: string
}

export interface PortalNotification {
  id: number
  type: string
  title: string
  message: string
  status: 'UNREAD' | 'READ' | 'DISMISSED'
  job_id?: number
  created_at: string
  read_at?: string
}
