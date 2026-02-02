// Core pages - eagerly loaded in App.tsx
// All other pages are lazy-loaded directly in App.tsx for better code-splitting

// Auth
export { LoginPage } from "./auth/login"

// Dashboard
export { DashboardPage } from "./dashboard"

// Jobs - core CRUD
export { JobsPage } from "./jobs"
export { JobDetailPage } from "./jobs/job-detail"
export { JobFormPage } from "./jobs/job-form"

// Customers - core CRUD
export { CustomersPage } from "./customers"
export { CustomerDetailPage } from "./customers/customer-detail"
export { CustomerFormPage } from "./customers/customer-form"

// Leads - core CRUD
export { LeadsPage } from "./leads"
export { LeadDetailPage } from "./leads/lead-detail"
export { LeadFormPage } from "./leads/lead-form"

// Notifications
export { NotificationsPage } from "./notifications"

// Profile
export { ProfilePage } from "./profile"
