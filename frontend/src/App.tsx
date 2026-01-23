import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider } from "./contexts/auth-context"
import { AppLayout } from "./layouts/app-layout"
import { AuthLayout } from "./layouts/auth-layout"
import {
  LoginPage,
  DashboardPage,
  JobsPage,
  JobDetailPage,
  JobFormPage,
  CustomersPage,
  CustomerDetailPage,
  CustomerFormPage,
  VehiclesPage,
  VehicleDetailPage,
  VehicleFormPage,
  LeadsPage,
  LeadDetailPage,
  LeadFormPage,
  EstimatesPage,
  EstimateDetailPage,
  EstimateFormPage,
  SchedulePage,
  NotificationsPage,
  ReportsPage,
  SettingsPage,
  UsersPage,
  TechDashboardPage,
  SalesDashboardPage,
  SalesRoutesPage,
  FieldLeadsPage,
  CompetitorsPage,
  LeaderboardPage,
  ScriptsPage,
  DNKPage,
  WeatherPage,
  HailMapPage,
  InvoicesPage,
  InvoiceDetailPage,
  InvoiceFormPage,
  ClaimsPage,
  ClaimDetailPage,
  ClaimFormPage,
  ProfilePage,
  FleetMapPage,
  EstimatorDashboardPage,
  HoursPage,
} from "./pages"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Auth routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
            </Route>

            {/* Protected app routes */}
            <Route element={<AppLayout />}>
              <Route path="/" element={<DashboardPage />} />

              {/* Jobs */}
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/jobs/new" element={<JobFormPage />} />
              <Route path="/jobs/:id" element={<JobDetailPage />} />
              <Route path="/jobs/:id/edit" element={<JobFormPage />} />

              {/* Customers */}
              <Route path="/customers" element={<CustomersPage />} />
              <Route path="/customers/new" element={<CustomerFormPage />} />
              <Route path="/customers/:id" element={<CustomerDetailPage />} />
              <Route path="/customers/:id/edit" element={<CustomerFormPage />} />

              {/* Vehicles */}
              <Route path="/vehicles" element={<VehiclesPage />} />
              <Route path="/vehicles/new" element={<VehicleFormPage />} />
              <Route path="/vehicles/:id" element={<VehicleDetailPage />} />
              <Route path="/vehicles/:id/edit" element={<VehicleFormPage />} />

              {/* Leads */}
              <Route path="/leads" element={<LeadsPage />} />
              <Route path="/leads/new" element={<LeadFormPage />} />
              <Route path="/leads/:id" element={<LeadDetailPage />} />
              <Route path="/leads/:id/edit" element={<LeadFormPage />} />

              {/* Estimates */}
              <Route path="/estimates" element={<EstimatesPage />} />
              <Route path="/estimates/new" element={<EstimateFormPage />} />
              <Route path="/estimates/:id" element={<EstimateDetailPage />} />
              <Route path="/estimates/:id/edit" element={<EstimateFormPage />} />

              {/* Schedule */}
              <Route path="/schedule" element={<SchedulePage />} />

              {/* Tech Dashboard */}
              <Route path="/tech" element={<TechDashboardPage />} />

              {/* Sales Dashboard */}
              <Route path="/sales" element={<SalesDashboardPage />} />

              {/* Elite Sales / Canvassing */}
              <Route path="/sales/routes" element={<SalesRoutesPage />} />
              <Route path="/sales/field-leads" element={<FieldLeadsPage />} />
              <Route path="/sales/competitors" element={<CompetitorsPage />} />
              <Route path="/sales/leaderboard" element={<LeaderboardPage />} />
              <Route path="/sales/scripts" element={<ScriptsPage />} />
              <Route path="/sales/dnk" element={<DNKPage />} />

              {/* Estimator Dashboard */}
              <Route path="/estimator" element={<EstimatorDashboardPage />} />

              {/* Hours/Time Tracking */}
              <Route path="/hours" element={<HoursPage />} />

              {/* Weather */}
              <Route path="/weather" element={<WeatherPage />} />

              {/* Hail Map */}
              <Route path="/hail-map" element={<HailMapPage />} />

              {/* Fleet Map */}
              <Route path="/fleet" element={<FleetMapPage />} />

              {/* Notifications */}
              <Route path="/notifications" element={<NotificationsPage />} />

              {/* Reports */}
              <Route path="/reports" element={<ReportsPage />} />

              {/* Invoices */}
              <Route path="/invoices" element={<InvoicesPage />} />
              <Route path="/invoices/new" element={<InvoiceFormPage />} />
              <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
              <Route path="/invoices/:id/edit" element={<InvoiceFormPage />} />

              {/* Claims */}
              <Route path="/claims" element={<ClaimsPage />} />
              <Route path="/claims/new" element={<ClaimFormPage />} />
              <Route path="/claims/:id" element={<ClaimDetailPage />} />
              <Route path="/claims/:id/edit" element={<ClaimFormPage />} />

              {/* Profile */}
              <Route path="/profile" element={<ProfilePage />} />

              {/* Admin */}
              <Route path="/admin/settings" element={<SettingsPage />} />
              <Route path="/admin/users" element={<UsersPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
