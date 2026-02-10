import { lazy, Suspense } from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import { PortalProvider } from "./contexts/portal-context"
import { AppLayout } from "./layouts/app-layout"
import { AuthLayout } from "./layouts/auth-layout"

// Loading fallback component
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  )
}

// Core pages - eagerly loaded for fast initial render
import {
  LoginPage,
  DashboardPage,
  JobsPage,
  JobDetailPage,
  JobFormPage,
  CustomersPage,
  CustomerDetailPage,
  CustomerFormPage,
  LeadsPage,
  LeadDetailPage,
  LeadFormPage,
  NotificationsPage,
  ProfilePage,
} from "./pages"

// Lazy-loaded page groups - split into separate chunks

// Vehicles (secondary CRUD)
const VehiclesPage = lazy(() => import("./pages/vehicles").then(m => ({ default: m.VehiclesPage })))
const VehicleDetailPage = lazy(() => import("./pages/vehicles/vehicle-detail").then(m => ({ default: m.VehicleDetailPage })))
const VehicleFormPage = lazy(() => import("./pages/vehicles/vehicle-form").then(m => ({ default: m.VehicleFormPage })))

// Estimates - PDR zone-based pricing (replaces old generic estimates)
const EstimatesPage = lazy(() => import("./pages/estimates").then(m => ({ default: m.EstimatesPage })))
const EstimateBuilderPage = lazy(() => import("./pages/estimating/EstimateBuilder").then(m => ({ default: m.EstimateBuilder })))
const EstimateReviewPage = lazy(() => import("./pages/estimating/EstimateReview").then(m => ({ default: m.EstimateReview })))
const WorkOrderPage = lazy(() => import("./pages/estimating/WorkOrder").then(m => ({ default: m.WorkOrder })))
const InvoiceSupplementPage = lazy(() => import("./pages/estimating/InvoiceSupplement").then(m => ({ default: m.InvoiceSupplement })))

// Schedule
const SchedulePage = lazy(() => import("./pages/schedule").then(m => ({ default: m.SchedulePage })))
const SchedulingTokensPage = lazy(() => import("./pages/schedule/scheduling-tokens").then(m => ({ default: m.SchedulingTokensPage })))

// Tech
const TechDashboardPage = lazy(() => import("./pages/tech").then(m => ({ default: m.TechDashboardPage })))

// Sales - heavy with maps
const SalesDashboardPage = lazy(() => import("./pages/sales").then(m => ({ default: m.SalesDashboardPage })))
const SalesRoutesPage = lazy(() => import("./pages/sales/routes").then(m => ({ default: m.SalesRoutesPage })))
const FieldLeadsPage = lazy(() => import("./pages/sales/field-leads").then(m => ({ default: m.FieldLeadsPage })))
const CompetitorsPage = lazy(() => import("./pages/sales/competitors").then(m => ({ default: m.CompetitorsPage })))
const LeaderboardPage = lazy(() => import("./pages/sales/leaderboard").then(m => ({ default: m.LeaderboardPage })))
const ScriptsPage = lazy(() => import("./pages/sales/scripts").then(m => ({ default: m.ScriptsPage })))
const DNKPage = lazy(() => import("./pages/sales/dnk").then(m => ({ default: m.DNKPage })))

// Estimator
const EstimatorDashboardPage = lazy(() => import("./pages/estimator").then(m => ({ default: m.EstimatorDashboardPage })))

// Hours
const HoursPage = lazy(() => import("./pages/hours").then(m => ({ default: m.HoursPage })))

// Weather & Maps - heavy Leaflet chunks
const WeatherPage = lazy(() => import("./pages/weather").then(m => ({ default: m.WeatherPage })))
const HailMapPage = lazy(() => import("./pages/hail-map").then(m => ({ default: m.HailMapPage })))
const HailLookupPage = lazy(() => import("./pages/hail-lookup").then(m => ({ default: m.HailLookupPage })))
const FleetMapPage = lazy(() => import("./pages/fleet").then(m => ({ default: m.FleetMapPage })))

// Reports
const ReportsPage = lazy(() => import("./pages/reports").then(m => ({ default: m.ReportsPage })))

// Invoices
const InvoicesPage = lazy(() => import("./pages/invoices").then(m => ({ default: m.InvoicesPage })))
const InvoiceDetailPage = lazy(() => import("./pages/invoices/invoice-detail").then(m => ({ default: m.InvoiceDetailPage })))
const InvoiceFormPage = lazy(() => import("./pages/invoices/invoice-form").then(m => ({ default: m.InvoiceFormPage })))

// Claims
const ClaimsPage = lazy(() => import("./pages/claims").then(m => ({ default: m.ClaimsPage })))
const ClaimDetailPage = lazy(() => import("./pages/claims/claim-detail").then(m => ({ default: m.ClaimDetailPage })))
const ClaimFormPage = lazy(() => import("./pages/claims/claim-form").then(m => ({ default: m.ClaimFormPage })))

// Admin
const SettingsPage = lazy(() => import("./pages/admin/settings").then(m => ({ default: m.SettingsPage })))
const UsersPage = lazy(() => import("./pages/admin/users").then(m => ({ default: m.UsersPage })))

// CRM - separate chunk
const CRMDashboardPage = lazy(() => import("./pages/crm").then(m => ({ default: m.CRMDashboardPage })))
const CRMDealsPage = lazy(() => import("./pages/crm/deals").then(m => ({ default: m.CRMDealsPage })))
const CRMTasksPage = lazy(() => import("./pages/crm/tasks").then(m => ({ default: m.CRMTasksPage })))
const CRMPipelinePage = lazy(() => import("./pages/crm/pipeline").then(m => ({ default: m.CRMPipelinePage })))

// Parts
const PartsPage = lazy(() => import("./pages/parts").then(m => ({ default: m.PartsPage })))
const PartOrdersPage = lazy(() => import("./pages/parts/orders").then(m => ({ default: m.PartOrdersPage })))

// R&I
const RIOperationsPage = lazy(() => import("./pages/ri").then(m => ({ default: m.RIOperationsPage })))
const RITimesPage = lazy(() => import("./pages/ri/times").then(m => ({ default: m.RITimesPage })))


// Portal - separate chunk (different user type)
const PortalLayout = lazy(() => import("./pages/portal").then(m => ({ default: m.PortalLayout })))
const PortalLoginPage = lazy(() => import("./pages/portal/login").then(m => ({ default: m.PortalLoginPage })))
const PortalDashboardPage = lazy(() => import("./pages/portal/dashboard").then(m => ({ default: m.PortalDashboardPage })))
const PortalJobsPage = lazy(() => import("./pages/portal/jobs").then(m => ({ default: m.PortalJobsPage })))
const PortalJobDetailPage = lazy(() => import("./pages/portal/job-detail").then(m => ({ default: m.PortalJobDetailPage })))
const PortalMessagesPage = lazy(() => import("./pages/portal/messages").then(m => ({ default: m.PortalMessagesPage })))
const PortalAppointmentsPage = lazy(() => import("./pages/portal/appointments").then(m => ({ default: m.PortalAppointmentsPage })))
const PortalDocumentsPage = lazy(() => import("./pages/portal/documents").then(m => ({ default: m.PortalDocumentsPage })))
const PortalPhotosPage = lazy(() => import("./pages/portal/photos").then(m => ({ default: m.PortalPhotosPage })))
const PortalPaymentsPage = lazy(() => import("./pages/portal/payments").then(m => ({ default: m.PortalPaymentsPage })))
const PortalInsurancePage = lazy(() => import("./pages/portal/insurance").then(m => ({ default: m.PortalInsurancePage })))
const PortalSettingsPage = lazy(() => import("./pages/portal/settings").then(m => ({ default: m.PortalSettingsPage })))
const PortalReferralsPage = lazy(() => import("./pages/portal/referrals").then(m => ({ default: m.PortalReferralsPage })))
const PortalFlyersPage = lazy(() => import("./pages/portal/flyers").then(m => ({ default: m.PortalFlyersPage })))
const PortalLoyaltyPage = lazy(() => import("./pages/portal/loyalty").then(m => ({ default: m.PortalLoyaltyPage })))
const PortalReviewsPage = lazy(() => import("./pages/portal/reviews").then(m => ({ default: m.PortalReviewsPage })))

// Kiosk - separate chunk (standalone system)
const KioskLayout = lazy(() => import("./pages/kiosk").then(m => ({ default: m.KioskLayout })))
const KioskWelcomePage = lazy(() => import("./pages/kiosk/welcome").then(m => ({ default: m.KioskWelcomePage })))
const KioskCheckInPage = lazy(() => import("./pages/kiosk/check-in").then(m => ({ default: m.KioskCheckInPage })))
const KioskConfirmationPage = lazy(() => import("./pages/kiosk/confirmation").then(m => ({ default: m.KioskConfirmationPage })))
const KioskQueuePage = lazy(() => import("./pages/kiosk/queue").then(m => ({ default: m.KioskQueuePage })))

// Dealership - separate chunk (B2B portal)
const DealershipLayout = lazy(() => import("./pages/dealership").then(m => ({ default: m.DealershipLayout })))
const DealershipDashboardPage = lazy(() => import("./pages/dealership/dashboard").then(m => ({ default: m.DealershipDashboardPage })))
const DealershipVehiclesPage = lazy(() => import("./pages/dealership/vehicles").then(m => ({ default: m.DealershipVehiclesPage })))
const DealershipUploadPage = lazy(() => import("./pages/dealership/upload").then(m => ({ default: m.DealershipUploadPage })))
const DealershipLocationsPage = lazy(() => import("./pages/dealership/locations").then(m => ({ default: m.DealershipLocationsPage })))
const DealershipApiPage = lazy(() => import("./pages/dealership/api").then(m => ({ default: m.DealershipApiPage })))

// Public Share - no auth required
const SharedEstimatePage = lazy(() => import("./pages/share/SharedEstimate").then(m => ({ default: m.SharedEstimate })))

function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        {/* Protected app routes */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<Navigate to="/" replace />} />

          {/* Jobs - core, eagerly loaded */}
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/new" element={<JobFormPage />} />
          <Route path="/jobs/:id" element={<JobDetailPage />} />
          <Route path="/jobs/:id/edit" element={<JobFormPage />} />

          {/* Customers - core, eagerly loaded */}
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/customers/new" element={<CustomerFormPage />} />
          <Route path="/customers/:id" element={<CustomerDetailPage />} />
          <Route path="/customers/:id/edit" element={<CustomerFormPage />} />

          {/* Vehicles - lazy */}
          <Route path="/vehicles" element={<Suspense fallback={<PageLoader />}><VehiclesPage /></Suspense>} />
          <Route path="/vehicles/new" element={<Suspense fallback={<PageLoader />}><VehicleFormPage /></Suspense>} />
          <Route path="/vehicles/:id" element={<Suspense fallback={<PageLoader />}><VehicleDetailPage /></Suspense>} />
          <Route path="/vehicles/:id/edit" element={<Suspense fallback={<PageLoader />}><VehicleFormPage /></Suspense>} />

          {/* Leads - core, eagerly loaded */}
          <Route path="/leads" element={<LeadsPage />} />
          <Route path="/leads/new" element={<LeadFormPage />} />
          <Route path="/leads/:id" element={<LeadDetailPage />} />
          <Route path="/leads/:id/edit" element={<LeadFormPage />} />

          {/* Estimates - PDR zone-based pricing */}
          <Route path="/estimates" element={<Suspense fallback={<PageLoader />}><EstimatesPage /></Suspense>} />
          <Route path="/estimates/new" element={<Suspense fallback={<PageLoader />}><EstimateBuilderPage /></Suspense>} />
          <Route path="/estimates/:id" element={<Suspense fallback={<PageLoader />}><EstimateBuilderPage /></Suspense>} />
          <Route path="/estimates/:id/edit" element={<Suspense fallback={<PageLoader />}><EstimateBuilderPage /></Suspense>} />
          <Route path="/estimates/:id/review" element={<Suspense fallback={<PageLoader />}><EstimateReviewPage /></Suspense>} />
          <Route path="/estimates/:id/work-order" element={<Suspense fallback={<PageLoader />}><WorkOrderPage /></Suspense>} />
          <Route path="/estimates/:id/invoice" element={<Suspense fallback={<PageLoader />}><InvoiceSupplementPage /></Suspense>} />

          {/* Schedule - lazy */}
          <Route path="/schedule" element={<Suspense fallback={<PageLoader />}><SchedulePage /></Suspense>} />
          <Route path="/schedule/tokens" element={<Suspense fallback={<PageLoader />}><SchedulingTokensPage /></Suspense>} />

          {/* Tech Dashboard - lazy */}
          <Route path="/tech" element={<Suspense fallback={<PageLoader />}><TechDashboardPage /></Suspense>} />

          {/* Sales Dashboard - lazy */}
          <Route path="/sales" element={<Suspense fallback={<PageLoader />}><SalesDashboardPage /></Suspense>} />

          {/* Elite Sales / Canvassing - lazy (heavy maps) */}
          <Route path="/sales/routes" element={<Suspense fallback={<PageLoader />}><SalesRoutesPage /></Suspense>} />
          <Route path="/sales/field-leads" element={<Suspense fallback={<PageLoader />}><FieldLeadsPage /></Suspense>} />
          <Route path="/sales/competitors" element={<Suspense fallback={<PageLoader />}><CompetitorsPage /></Suspense>} />
          <Route path="/sales/leaderboard" element={<Suspense fallback={<PageLoader />}><LeaderboardPage /></Suspense>} />
          <Route path="/sales/scripts" element={<Suspense fallback={<PageLoader />}><ScriptsPage /></Suspense>} />
          <Route path="/sales/dnk" element={<Suspense fallback={<PageLoader />}><DNKPage /></Suspense>} />

          {/* Estimator Dashboard - lazy */}
          <Route path="/estimator" element={<Suspense fallback={<PageLoader />}><EstimatorDashboardPage /></Suspense>} />

          {/* Hours/Time Tracking - lazy */}
          <Route path="/hours" element={<Suspense fallback={<PageLoader />}><HoursPage /></Suspense>} />

          {/* Weather - lazy */}
          <Route path="/weather" element={<Suspense fallback={<PageLoader />}><WeatherPage /></Suspense>} />

          {/* Hail Map - lazy (heavy Leaflet) */}
          <Route path="/hail-map" element={<Suspense fallback={<PageLoader />}><HailMapPage /></Suspense>} />

          {/* Hail Lookup - lazy */}
          <Route path="/hail-lookup" element={<Suspense fallback={<PageLoader />}><HailLookupPage /></Suspense>} />

          {/* Fleet Map - lazy (heavy Leaflet) */}
          <Route path="/fleet" element={<Suspense fallback={<PageLoader />}><FleetMapPage /></Suspense>} />

          {/* Notifications - core, eagerly loaded */}
          <Route path="/notifications" element={<NotificationsPage />} />

          {/* Reports - lazy */}
          <Route path="/reports" element={<Suspense fallback={<PageLoader />}><ReportsPage /></Suspense>} />

          {/* Invoices - lazy */}
          <Route path="/invoices" element={<Suspense fallback={<PageLoader />}><InvoicesPage /></Suspense>} />
          <Route path="/invoices/new" element={<Suspense fallback={<PageLoader />}><InvoiceFormPage /></Suspense>} />
          <Route path="/invoices/:id" element={<Suspense fallback={<PageLoader />}><InvoiceDetailPage /></Suspense>} />
          <Route path="/invoices/:id/edit" element={<Suspense fallback={<PageLoader />}><InvoiceFormPage /></Suspense>} />

          {/* Claims - lazy */}
          <Route path="/claims" element={<Suspense fallback={<PageLoader />}><ClaimsPage /></Suspense>} />
          <Route path="/claims/new" element={<Suspense fallback={<PageLoader />}><ClaimFormPage /></Suspense>} />
          <Route path="/claims/:id" element={<Suspense fallback={<PageLoader />}><ClaimDetailPage /></Suspense>} />
          <Route path="/claims/:id/edit" element={<Suspense fallback={<PageLoader />}><ClaimFormPage /></Suspense>} />

          {/* Profile - core, eagerly loaded */}
          <Route path="/profile" element={<ProfilePage />} />

          {/* Admin - lazy */}
          <Route path="/admin/settings" element={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />
          <Route path="/admin/users" element={<Suspense fallback={<PageLoader />}><UsersPage /></Suspense>} />

          {/* CRM - lazy */}
          <Route path="/crm" element={<Suspense fallback={<PageLoader />}><CRMDashboardPage /></Suspense>} />
          <Route path="/crm/deals" element={<Suspense fallback={<PageLoader />}><CRMDealsPage /></Suspense>} />
          <Route path="/crm/deals/:id" element={<Suspense fallback={<PageLoader />}><CRMDealsPage /></Suspense>} />
          <Route path="/crm/tasks" element={<Suspense fallback={<PageLoader />}><CRMTasksPage /></Suspense>} />
          <Route path="/crm/pipeline" element={<Suspense fallback={<PageLoader />}><CRMPipelinePage /></Suspense>} />

          {/* Parts - lazy */}
          <Route path="/parts" element={<Suspense fallback={<PageLoader />}><PartsPage /></Suspense>} />
          <Route path="/parts/:id" element={<Suspense fallback={<PageLoader />}><PartsPage /></Suspense>} />
          <Route path="/parts/orders" element={<Suspense fallback={<PageLoader />}><PartOrdersPage /></Suspense>} />
          <Route path="/parts/orders/:id" element={<Suspense fallback={<PageLoader />}><PartOrdersPage /></Suspense>} />

          {/* R&I Operations - lazy */}
          <Route path="/ri" element={<Suspense fallback={<PageLoader />}><RIOperationsPage /></Suspense>} />
          <Route path="/ri/times" element={<Suspense fallback={<PageLoader />}><RITimesPage /></Suspense>} />

        </Route>

        {/* Customer Portal - lazy loaded separate chunk */}
        <Route path="/portal/login" element={
          <PortalProvider>
            <Suspense fallback={<PageLoader />}>
              <PortalLoginPage />
            </Suspense>
          </PortalProvider>
        } />
        <Route path="/portal" element={
          <PortalProvider>
            <Suspense fallback={<PageLoader />}>
              <PortalLayout />
            </Suspense>
          </PortalProvider>
        }>
          <Route index element={<Suspense fallback={<PageLoader />}><PortalDashboardPage /></Suspense>} />
          <Route path="jobs" element={<Suspense fallback={<PageLoader />}><PortalJobsPage /></Suspense>} />
          <Route path="jobs/:id" element={<Suspense fallback={<PageLoader />}><PortalJobDetailPage /></Suspense>} />
          <Route path="jobs/:id/photos" element={<Suspense fallback={<PageLoader />}><PortalPhotosPage /></Suspense>} />
          <Route path="jobs/:id/insurance" element={<Suspense fallback={<PageLoader />}><PortalInsurancePage /></Suspense>} />
          <Route path="messages" element={<Suspense fallback={<PageLoader />}><PortalMessagesPage /></Suspense>} />
          <Route path="appointments" element={<Suspense fallback={<PageLoader />}><PortalAppointmentsPage /></Suspense>} />
          <Route path="documents" element={<Suspense fallback={<PageLoader />}><PortalDocumentsPage /></Suspense>} />
          <Route path="photos" element={<Suspense fallback={<PageLoader />}><PortalPhotosPage /></Suspense>} />
          <Route path="payments" element={<Suspense fallback={<PageLoader />}><PortalPaymentsPage /></Suspense>} />
          <Route path="insurance" element={<Suspense fallback={<PageLoader />}><PortalInsurancePage /></Suspense>} />
          <Route path="settings" element={<Suspense fallback={<PageLoader />}><PortalSettingsPage /></Suspense>} />
          <Route path="referrals" element={<Suspense fallback={<PageLoader />}><PortalReferralsPage /></Suspense>} />
          <Route path="flyers" element={<Suspense fallback={<PageLoader />}><PortalFlyersPage /></Suspense>} />
          <Route path="loyalty" element={<Suspense fallback={<PageLoader />}><PortalLoyaltyPage /></Suspense>} />
          <Route path="reviews" element={<Suspense fallback={<PageLoader />}><PortalReviewsPage /></Suspense>} />
        </Route>

        {/* Kiosk System - lazy loaded separate chunk */}
        <Route path="/kiosk" element={<Suspense fallback={<PageLoader />}><KioskLayout /></Suspense>}>
          <Route index element={<Suspense fallback={<PageLoader />}><KioskWelcomePage /></Suspense>} />
          <Route path="check-in" element={<Suspense fallback={<PageLoader />}><KioskCheckInPage /></Suspense>} />
          <Route path="confirmation" element={<Suspense fallback={<PageLoader />}><KioskConfirmationPage /></Suspense>} />
        </Route>
        <Route path="/kiosk/queue" element={<Suspense fallback={<PageLoader />}><KioskQueuePage /></Suspense>} />

        {/* Dealership Portal - lazy loaded separate chunk */}
        <Route path="/dealership" element={<Suspense fallback={<PageLoader />}><DealershipLayout /></Suspense>}>
          <Route index element={<Suspense fallback={<PageLoader />}><DealershipDashboardPage /></Suspense>} />
          <Route path="vehicles" element={<Suspense fallback={<PageLoader />}><DealershipVehiclesPage /></Suspense>} />
          <Route path="upload" element={<Suspense fallback={<PageLoader />}><DealershipUploadPage /></Suspense>} />
          <Route path="locations" element={<Suspense fallback={<PageLoader />}><DealershipLocationsPage /></Suspense>} />
          <Route path="api" element={<Suspense fallback={<PageLoader />}><DealershipApiPage /></Suspense>} />
        </Route>

        {/* Public Share Portal - no auth required */}
        <Route path="/share/estimate/:token" element={<Suspense fallback={<PageLoader />}><SharedEstimatePage /></Suspense>} />
      </Routes>
    </Suspense>
  )
}

export default App
