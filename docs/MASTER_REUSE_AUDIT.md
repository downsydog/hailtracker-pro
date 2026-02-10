# HailTracker Pro - Master Reuse Audit

**Generated**: 2026-02-08
**Purpose**: Comprehensive system inventory to prevent duplicate development and guide future feature connections.

---

## PHASE 1: Route & Endpoint Inventory

### Frontend Routes (89 routes across 4 layouts)

#### AppLayout (Main App - Protected)
| Route | Page Component | Purpose |
|-------|----------------|---------|
| `/` | DashboardPage | Main dashboard with stats |
| `/jobs` | JobsPage | Job list |
| `/jobs/new` | JobFormPage | Create job |
| `/jobs/:id` | JobDetailPage | Job details + workflow |
| `/jobs/:id/edit` | JobFormPage | Edit job |
| `/customers` | CustomersPage | Customer list |
| `/customers/new` | CustomerFormPage | Create customer |
| `/customers/:id` | CustomerDetailPage | Customer details |
| `/customers/:id/edit` | CustomerFormPage | Edit customer |
| `/vehicles` | VehiclesPage | Vehicle list |
| `/vehicles/new` | VehicleFormPage | Create vehicle |
| `/vehicles/:id` | VehicleDetailPage | Vehicle details |
| `/vehicles/:id/edit` | VehicleFormPage | Edit vehicle |
| `/leads` | LeadsPage | Lead list |
| `/leads/new` | LeadFormPage | Create lead |
| `/leads/:id` | LeadDetailPage | Lead details |
| `/leads/:id/edit` | LeadFormPage | Edit lead |
| `/estimates` | EstimatesPage | PDR estimate list |
| `/estimates/new` | EstimateBuilderPage | Create estimate |
| `/estimates/:id` | EstimateBuilderPage | View/edit estimate |
| `/estimates/:id/edit` | EstimateBuilderPage | Edit estimate |
| `/estimates/:id/review` | EstimateReviewPage | Review + approval flow |
| `/estimates/:id/work-order` | WorkOrderPage | Work order view |
| `/estimates/:id/invoice` | InvoiceSupplementPage | Invoice from estimate |
| `/schedule` | SchedulePage | Job scheduling |
| `/schedule/tokens` | SchedulingTokensPage | Scheduling tokens |
| `/tech` | TechDashboardPage | Tech dashboard |
| `/sales` | SalesDashboardPage | Sales dashboard |
| `/sales/routes` | SalesRoutesPage | Canvassing routes |
| `/sales/field-leads` | FieldLeadsPage | Field leads |
| `/sales/competitors` | CompetitorsPage | Competitor tracking |
| `/sales/leaderboard` | LeaderboardPage | Sales leaderboard |
| `/sales/scripts` | ScriptsPage | Call scripts |
| `/sales/dnk` | DNKPage | Do Not Knock list |
| `/estimator` | EstimatorDashboardPage | Estimator dashboard |
| `/hours` | HoursPage | Time tracking |
| `/weather` | WeatherPage | Weather dashboard |
| `/hail-map` | HailMapPage | Hail swath map |
| `/hail-lookup` | HailLookupPage | Address hail lookup |
| `/fleet` | FleetMapPage | Fleet/business map |
| `/notifications` | NotificationsPage | User notifications |
| `/reports` | ReportsPage | Reports |
| `/invoices` | InvoicesPage | Invoice list + exports |
| `/invoices/new` | InvoiceFormPage | Create invoice |
| `/invoices/:id` | InvoiceDetailPage | Invoice + payments |
| `/invoices/:id/edit` | InvoiceFormPage | Edit invoice |
| `/claims` | ClaimsPage | Insurance claims |
| `/claims/new` | ClaimFormPage | Create claim |
| `/claims/:id` | ClaimDetailPage | Claim details |
| `/claims/:id/edit` | ClaimFormPage | Edit claim |
| `/profile` | ProfilePage | User profile |
| `/admin/settings` | SettingsPage | Tenant settings |
| `/admin/users` | UsersPage | User management |
| `/crm` | CRMDashboardPage | CRM dashboard |
| `/crm/deals` | CRMDealsPage | Deals list |
| `/crm/deals/:id` | CRMDealsPage | Deal details |
| `/crm/tasks` | CRMTasksPage | CRM tasks |
| `/crm/pipeline` | CRMPipelinePage | Pipeline view |
| `/parts` | PartsPage | Parts inventory |
| `/parts/:id` | PartsPage | Part details |
| `/parts/orders` | PartOrdersPage | Part orders |
| `/parts/orders/:id` | PartOrdersPage | Order details |
| `/ri` | RIOperationsPage | R&I operations |
| `/ri/times` | RITimesPage | R&I times |

#### PortalLayout (Customer Portal)
| Route | Page Component | Purpose |
|-------|----------------|---------|
| `/portal/login` | PortalLoginPage | Portal login |
| `/portal` | PortalDashboardPage | Portal home |
| `/portal/jobs` | PortalJobsPage | Customer's jobs |
| `/portal/jobs/:id` | PortalJobDetailPage | Job details |
| `/portal/jobs/:id/photos` | PortalPhotosPage | Job photos |
| `/portal/jobs/:id/insurance` | PortalInsurancePage | Insurance info |
| `/portal/messages` | PortalMessagesPage | Messages |
| `/portal/appointments` | PortalAppointmentsPage | Appointments |
| `/portal/documents` | PortalDocumentsPage | Documents |
| `/portal/photos` | PortalPhotosPage | Photos |
| `/portal/payments` | PortalPaymentsPage | Payments |
| `/portal/insurance` | PortalInsurancePage | Insurance |
| `/portal/settings` | PortalSettingsPage | Settings |
| `/portal/referrals` | PortalReferralsPage | Referrals |
| `/portal/flyers` | PortalFlyersPage | Flyers |
| `/portal/loyalty` | PortalLoyaltyPage | Loyalty program |
| `/portal/reviews` | PortalReviewsPage | Reviews |

#### KioskLayout (Check-in Kiosk)
| Route | Page Component | Purpose |
|-------|----------------|---------|
| `/kiosk` | KioskWelcomePage | Welcome screen |
| `/kiosk/check-in` | KioskCheckInPage | Check-in form |
| `/kiosk/confirmation` | KioskConfirmationPage | Confirmation |
| `/kiosk/queue` | KioskQueuePage | Queue display |

#### DealershipLayout (B2B Portal)
| Route | Page Component | Purpose |
|-------|----------------|---------|
| `/dealership` | DealershipDashboardPage | Dashboard |
| `/dealership/vehicles` | DealershipVehiclesPage | Vehicle list |
| `/dealership/upload` | DealershipUploadPage | Batch upload |
| `/dealership/locations` | DealershipLocationsPage | Locations |
| `/dealership/api` | DealershipApiPage | API access |

#### Public (No Auth)
| Route | Page Component | Purpose |
|-------|----------------|---------|
| `/login` | LoginPage | Login |
| `/share/estimate/:token` | SharedEstimatePage | Public estimate share |

---

### Backend API Endpoints (99+ endpoints across 3 blueprints)

#### Auth Blueprint (`/api/auth`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/register` | Register new tenant |
| POST | `/login` | User login |
| POST | `/refresh` | Refresh JWT token |
| GET | `/me` | Current user info |
| PATCH | `/profile` | Update profile |
| POST | `/change-password` | Change password |
| POST | `/forgot-password` | Password reset |
| GET | `/team` | List team members |
| GET | `/team/active` | Active team members |
| POST | `/team` | Invite team member |
| GET | `/team/:id` | Team member details |
| PUT | `/team/:id` | Update team member |
| DELETE | `/team/:id` | Deactivate member |
| POST | `/team/:id/reactivate` | Reactivate member |
| POST | `/team/:id/reset-password` | Admin password reset |
| GET | `/roles` | Available roles |

#### Admin Blueprint (`/api/admin`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dashboard` | Admin dashboard stats |
| GET | `/usage` | API usage stats |
| GET | `/billing` | Billing info |
| PUT | `/company` | Update company settings |
| GET | `/customers` | Customer list (super admin) |
| GET | `/customers/:id` | Customer details |
| POST | `/customers` | Create customer |
| PATCH | `/customers/:id` | Update customer |
| GET | `/customers/:id/users` | Customer's users |
| GET | `/customers/stats` | Customer stats |
| GET | `/storms` | Storm list |
| POST | `/storms/:id/process` | Process storm |
| POST | `/storms/:id/reprocess` | Reprocess storm |
| GET | `/tasks/:id` | Celery task status |
| GET | `/storms/pending` | Pending storms |
| POST | `/storms/process-batch` | Batch process storms |
| GET | `/storms/stats` | Storm stats |

#### Customer Blueprint (`/api`) - Main Tenant API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| **Storms** | | |
| GET | `/storms` | List storms |
| GET | `/storms/:id` | Storm details |
| GET | `/storms/:id/businesses` | Businesses in storm swath |
| GET | `/storms/:id/categories` | Business categories |
| GET | `/storms/search` | Search storms |
| GET | `/storms/by-date/:date` | Storms by date |
| **Leads** | | |
| GET | `/leads` | List leads |
| POST | `/leads` | Create lead |
| POST | `/leads/bulk` | Bulk create leads |
| GET | `/leads/:id` | Lead details |
| PATCH | `/leads/:id` | Update lead |
| POST | `/leads/:id/contacts` | Add contact |
| POST | `/leads/:id/calls` | Log call |
| GET | `/leads/stats` | Lead stats |
| **Dashboard** | | |
| GET | `/dashboard` | Dashboard stats |
| **Team** | | |
| GET | `/team` | Team list |
| POST | `/team` | Add team member |
| PATCH | `/team/:id` | Update member |
| **Settings** | | |
| PATCH | `/settings/company` | Company settings |
| **PDR Estimates** | | |
| GET | `/pdr-estimates/:id/pdf` | Estimate PDF |
| POST | `/pdr-estimates/:id/pdf/preview` | PDF preview |
| GET | `/pdr-estimates/:id/photosheet.pdf` | Photo sheet |
| POST | `/pdr-estimates/:id/photosheet/preview` | Photo sheet preview |
| GET | `/pdr-estimates/:id/photos` | Estimate photos |
| POST | `/pdr-estimates/:id/photos` | Upload photos |
| POST | `/pdr-estimates/:id/send` | Send estimate email |
| GET | `/pdr-estimates/:id/activities` | Activity log |
| GET | `/pdr-estimates/:id/versions` | Version history |
| POST | `/pdr-estimates/:id/versions` | Create version |
| GET | `/pdr-estimates/:id/supplements` | Supplements list |
| POST | `/pdr-estimates/:id/supplements` | Create supplement |
| GET | `/pdr-supplements/:id` | Supplement details |
| GET | `/pdr-supplements/:id/pdf` | Supplement PDF |
| POST | `/pdr-supplements/:id/send` | Send supplement |
| GET | `/pdr-estimates/:id/dispute-pack.zip` | Dispute pack ZIP |
| POST | `/pdr-estimates/:id/share-link` | Create share link |
| POST | `/pdr-estimates/:id/request-signature` | Request signature |
| POST | `/pdr-estimates/:id/sign` | Sign estimate |
| POST | `/pdr-estimates/:id/approve` | Customer approve |
| POST | `/pdr-estimates/:id/decline` | Customer decline |
| POST | `/pdr-estimates/:id/submit-to-insurer` | Submit to insurer |
| POST | `/pdr-estimates/:id/insurer-approve` | Insurer approve |
| POST | `/pdr-estimates/:id/update-insurer-approval` | Update approval |
| POST | `/pdr-estimates/:id/insurer-decline` | Insurer decline |
| POST | `/pdr-estimates/:id/insurer-needs-revision` | Request revision |
| GET | `/pdr-estimates/:id/job` | Get linked job |
| POST | `/pdr-estimates/:id/job` | Create job from estimate |
| GET | `/pdr-estimates/:id/workflow` | Estimate workflow state |
| POST | `/pdr-estimates/:id/close` | Close estimate/claim |
| PATCH | `/pdr-estimates/:id/billing` | Update billing (deductible/OOP) |
| GET | `/pdr-estimates/:id/invoices` | Estimate's invoices |
| POST | `/pdr-estimates/:id/invoices/insurer` | Create insurer invoice |
| POST | `/pdr-estimates/:id/invoices/customer` | Create customer invoice |
| POST | `/pdr-estimates/:id/invoice` | Create invoice (general) |
| **Public Share** | | |
| GET | `/public/share/estimate/:token` | Public estimate view |
| GET | `/public/share/estimate/:token/pdf` | Public estimate PDF |
| GET | `/public/share/estimate/:token/photosheet.pdf` | Public photo sheet |
| GET | `/public/share/estimate/:token/dispute-pack.zip` | Public dispute pack |
| GET | `/public/share/supplement/:token/:id/pdf` | Public supplement PDF |
| POST | `/public/share/estimate/:token/sign` | Public signature submit |
| **Jobs** | | |
| GET | `/jobs` | List jobs |
| GET | `/jobs/:id` | Job details |
| PUT/PATCH | `/jobs/:id` | Update job |
| GET | `/jobs/:id/workflow` | Job workflow state |
| **Invoices** | | |
| GET | `/invoices` | List invoices |
| GET | `/invoices/:id` | Invoice details |
| PUT/PATCH | `/invoices/:id` | Update invoice |
| POST | `/invoices/:id/issue` | Issue invoice |
| POST | `/invoices/:id/void` | Void invoice |
| GET | `/invoices/:id/payments` | Invoice payments |
| POST | `/invoices/:id/payments` | Record payment |
| GET | `/invoices/:id/payments/:id/receipt.pdf` | Payment receipt PDF |
| **Exports** | | |
| GET | `/exports/invoices.csv` | Export invoices CSV |
| GET | `/exports/payments.csv` | Export payments CSV |

---

## PHASE 2: Model Inventory

### Master Models (Multi-tenant platform)
| Model | File | Key Fields | Purpose |
|-------|------|------------|---------|
| `Storm` | `master/storm.py` | date, state, counties | Hail storm event |
| `Swath` | `master/swath.py` | storm_id, geom, severity | Storm swath polygon |
| `Business` | `master/business.py` | name, address, category | Business in swath |
| `StormBusiness` | `master/business.py` | storm_id, business_id | M2M junction |
| `Tenant` | `master/tenant.py` | name, slug, settings | Tenant organization |
| `Subscription` | `master/tenant.py` | tier, billing | Tenant subscription |
| `User` | `master/user.py` | email, role, tenant_id | User account |
| `ApiUsage` | `master/api_usage.py` | endpoint, count | Usage tracking |

### Tenant Models (Per-tenant data)
| Model | File | Key Fields | Purpose |
|-------|------|------------|---------|
| `Lead` | `tenant/lead.py` | storm_id, status, source | Sales lead |
| `Contact` | `tenant/contact.py` | lead_id, name, phone | Lead contact |
| `Call` | `tenant/call.py` | lead_id, outcome | Call log |
| `Estimate` | `tenant/estimate.py` | lead_id, total | Legacy estimate |
| `PDREstimate` | `tenant/pdr_estimate.py` | panels, zones, total_price | PDR zone estimate |
| `PDREstimatePanel` | `tenant/pdr_estimate_panel.py` | estimate_id, zone, count | Panel damage entry |
| `EstimatePhoto` | `tenant/estimate_photo.py` | estimate_id, url | Estimate photo |
| `EstimateActivity` | `tenant/estimate_activity.py` | action, user_id | Activity log |
| `EstimateVersion` | `tenant/estimate_version.py` | snapshot_json | Version history |
| `EstimateSupplement` | `tenant/estimate_supplement.py` | original, delta | Supplement |
| `Job` | `tenant/job.py` | estimate_id, status, tech | Scheduled job |
| `Invoice` | `tenant/invoice.py` | estimate_id, total, payer | Invoice |
| `InvoiceLineItem` | `tenant/invoice.py` | invoice_id, description | Line item |
| `Payment` | `tenant/invoice.py` | invoice_id, amount, method | Payment received |

---

## PHASE 3: Service Inventory

| Service | File | Purpose |
|---------|------|---------|
| `auth_service` | `services/auth_service.py` | Authentication, JWT |
| `storm_service` | `services/storm_service.py` | Storm data processing |
| `lead_service` | `services/lead_service.py` | Lead management |
| `usage_service` | `services/usage_service.py` | API usage tracking |
| `email_service` | `services/email_service.py` | Email sending |
| `pdf_generator` | `services/pdf_generator.py` | PDR estimate PDFs |
| `photo_sheet_generator` | `services/photo_sheet_generator.py` | Photo sheet PDFs |
| `supplement_pdf_generator` | `services/supplement_pdf_generator.py` | Supplement PDFs |
| `receipt_pdf_generator` | `services/receipt_pdf_generator.py` | Payment receipt PDFs |
| `supplement_diff` | `services/supplement_diff.py` | Supplement diffing |
| `dispute_pack_generator` | `services/dispute_pack_generator.py` | Dispute pack ZIPs |
| `share_token_service` | `services/share_token_service.py` | Share link tokens |
| `permissions_service` | `services/permissions_service.py` | RBAC permissions |
| `workflow_service` | `services/workflow_service.py` | Workflow state machine |

---

## PHASE 4: Frontend Hook Inventory

| Hook | File | Purpose |
|------|------|---------|
| `useApi` | `hooks/useApi.ts` | Base API fetch wrapper |
| `useLeads` | `hooks/use-leads.ts` | Lead CRUD + queries |
| `useJobs` | `hooks/use-jobs.ts` | Job CRUD + queries |
| `useEstimates` | `hooks/use-estimates.ts` | Legacy estimate hooks |
| `usePDREstimates` | `hooks/use-pdr-estimates.ts` | PDR estimate CRUD |
| `useCustomers` | `hooks/use-customers.ts` | Customer CRUD |
| `useVehicles` | `hooks/use-vehicles.ts` | Vehicle CRUD |
| `useInvoices` | `hooks/use-invoices.ts` | Invoice CRUD + payments |
| `useTech` | `hooks/use-tech.ts` | Tech data hooks |
| `useTimeTracking` | `hooks/use-time-tracking.ts` | Time tracking |
| `useWorkflow` | `hooks/use-workflow.ts` | Workflow state queries |
| `useExports` | `hooks/use-exports.ts` | CSV export mutations |
| `useDebounce` | `hooks/use-debounce.ts` | Debounce utility |

---

## PHASE 5: Component Inventory

### UI Components (Shadcn)
`components/ui/`: alert, alert-dialog, badge, button, card, checkbox, collapsible, dialog, dropdown-menu, input, label, progress, select, separator, sheet, skeleton, slider, switch, table, tabs, textarea, tooltip

### App Components
| Component | File | Purpose |
|-----------|------|---------|
| `PageHeader` | `app/page-header.tsx` | Page title + breadcrumbs |
| `Sidebar` | `app/sidebar.tsx` | Navigation sidebar |
| `Topbar` | `app/topbar.tsx` | Top navigation |
| `StatCard` | `app/stat-card.tsx` | Stat display card |
| `DataTable` | `app/data-table.tsx` | Data table with sorting |
| `EmptyState` | `app/empty-state.tsx` | Empty state display |
| `GlobalSearch` | `app/global-search.tsx` | Global search |
| `TerritoryAlerts` | `app/territory-alerts.tsx` | Territory alert banner |
| `StormCalendar` | `app/storm-calendar.tsx` | Storm date picker |
| `RadarReplay` | `app/radar-replay.tsx` | Radar animation |
| `TimeStatusBanner` | `app/time-status-banner.tsx` | Time tracking banner |
| `LogTimeDialog` | `app/log-time-dialog.tsx` | Time entry dialog |
| `WeekSummary` | `app/week-summary.tsx` | Weekly time summary |

### Chart Components
`components/app/charts/`: RevenueChart, JobsStatusChart, LeadSourcesChart, TechPerformanceChart

### Estimate Components
| Component | File | Purpose |
|-----------|------|---------|
| `PanelEntryModal` | `estimates/PanelEntry/` | Panel entry form |
| `EstimateBottomNav` | `estimates/BottomNav/` | Mobile bottom nav |
| `PanelListSidebar` | `estimates/PanelList/` | Panel list sidebar |
| `CustomerPicker` | `estimates/CustomerPicker/` | Customer search/select |
| `VehiclePicker` | `estimates/VehiclePicker/` | Vehicle search/select |
| `EstimateSummary` | `estimating/EstimateSummary.tsx` | Estimate totals |
| `PanelSelector` | `estimating/PanelSelector.tsx` | Panel selection |
| `RISuggestions` | `estimating/RISuggestions.tsx` | R&I suggestions |
| `SignaturePad` | `estimating/SignaturePad.tsx` | Signature capture |
| `DiscoveryForm` | `estimating/DiscoveryForm.tsx` | Discovery questions |
| `VehicleDiagram` | `estimates/VehicleDiagram/` | Car/Truck/SUV SVG |
| `QuickEntryOverlay` | `estimates/QuickEntry/` | Quick damage entry |
| `SendToAdjusterModal` | `estimates/SendToAdjusterModal.tsx` | Email to adjuster |
| `CreateSupplementModal` | `estimates/CreateSupplementModal.tsx` | Create supplement |
| `CreateShareLinkModal` | `estimates/CreateShareLinkModal.tsx` | Share link creation |
| `EstimateStatusBar` | `estimates/EstimateStatusBar.tsx` | Status progress bar |
| `SignatureCapture` | `estimates/SignatureCapture.tsx` | Signature modal |
| `InsurerApprovalModal` | `estimates/InsurerApprovalModal.tsx` | Insurer approval form |
| `InsuranceApprovalDisplay` | `estimates/InsuranceApprovalDisplay.tsx` | Approval display |

### Workflow Components
| Component | File | Purpose |
|-----------|------|---------|
| `WorkflowCard` | `workflow/WorkflowCard.tsx` | Workflow progress display |

### Fleet Components
| Component | File | Purpose |
|-----------|------|---------|
| `RecentStormsPicker` | `fleet/RecentStormsPicker.tsx` | Storm selection |
| `CallScriptModal` | `fleet/CallScriptModal.tsx` | Call script display |
| `EmailTemplateModal` | `fleet/EmailTemplateModal.tsx` | Email template |
| `BatchScrapePanel` | `fleet/BatchScrapePanel.tsx` | Batch business scrape |

---

## PHASE 6: System Flow Map

### Complete Workflow: Storm → Lead → Customer → Estimate → Job → Invoice → Payment → Close

```
┌──────────────┐
│    STORM     │
│  (External)  │
└──────┬───────┘
       │ GET /storms
       │ Storm table (master.storm)
       ▼
┌──────────────┐
│    LEAD      │
│ /leads/:id   │
└──────┬───────┘
       │ POST /leads (from storm businesses)
       │ Lead table (tenant.lead)
       │ Activity: lead_created
       ▼
┌──────────────┐
│   CUSTOMER   │
│ /customers   │
└──────┬───────┘
       │ POST /leads/:id → convert
       │ Lead.status = 'won'
       │ Activity: lead_converted
       ▼
┌──────────────┐
│   ESTIMATE   │
│ /estimates   │
└──────┬───────┘
       │ POST /pdr-estimates (creates from lead)
       │ PDREstimate table
       │ Activity: estimate_created
       │
       ├─── Customer Approval Flow ───┐
       │ POST /pdr-estimates/:id/sign │
       │ customer_status = 'signed'   │
       │ Activity: customer_signed    │
       │                              │
       ├─── Insurer Approval Flow ────┤
       │ POST /submit-to-insurer      │
       │ insurer_status = 'submitted' │
       │ Activity: submitted_insurer  │
       │                              │
       │ POST /insurer-approve        │
       │ insurer_status = 'approved'  │
       │ Activity: insurer_approved   │
       ▼
┌──────────────┐
│     JOB      │
│ /jobs/:id    │
└──────┬───────┘
       │ POST /pdr-estimates/:id/job
       │ Job table (tenant.job)
       │ status = 'scheduled'
       │ Activity: job_created
       │
       │ PATCH /jobs/:id (start)
       │ status = 'in_progress'
       │ Activity: job_started
       │
       │ PATCH /jobs/:id (complete)
       │ status = 'completed'
       │ Activity: job_completed
       ▼
┌──────────────┐
│   INVOICE    │
│ /invoices/:id│
└──────┬───────┘
       │ POST /pdr-estimates/:id/invoices/insurer
       │ → Creates insurer invoice (allocation=insurer)
       │ Invoice table + InvoiceLineItem table
       │ Activity: invoice_created_insurer
       │
       │ POST /pdr-estimates/:id/invoices/customer
       │ → Creates customer invoice (allocation=customer_deductible)
       │ Activity: invoice_created_customer
       │
       │ POST /invoices/:id/issue
       │ status = 'issued', issued_at = now
       │ Activity: invoice_issued
       ▼
┌──────────────┐
│   PAYMENT    │
│ (embedded)   │
└──────┬───────┘
       │ POST /invoices/:id/payments
       │ Payment table
       │ Invoice.amount_paid += payment.amount
       │ Invoice.status = 'partial_paid' or 'paid'
       │ Activity: payment_received
       │
       │ GET /invoices/:id/payments/:id/receipt.pdf
       │ → Downloads receipt PDF
       ▼
┌──────────────┐
│    CLOSE     │
│  (workflow)  │
└──────────────┘
       │ POST /pdr-estimates/:id/close
       │ estimate.closed = true
       │ estimate.closed_at = now
       │ Activity: estimate_closed
```

### Detailed Flow Table

| Step | Trigger | Endpoint | Page | Model(s) | Activity Type |
|------|---------|----------|------|----------|---------------|
| 1. Storm Created | External/Admin | `POST /admin/storms/:id/process` | Admin dashboard | Storm, Swath, Business | — |
| 2. View Storm Leads | User click | `GET /storms/:id/businesses` | `/fleet` | Business, StormBusiness | — |
| 3. Create Lead | "Add Lead" button | `POST /leads` | `/fleet` or `/leads/new` | Lead | `lead_created` |
| 4. Log Call | Call logged | `POST /leads/:id/calls` | `/leads/:id` | Call | `call_logged` |
| 5. Convert Lead | "Convert to Customer" | `PATCH /leads/:id` + `POST /customers` | `/leads/:id` | Lead, Customer | `lead_converted` |
| 6. Create Estimate | "New Estimate" | `POST /pdr-estimates` | `/estimates/new` | PDREstimate | `estimate_created` |
| 7. Add Panels | Panel entry | `PUT /pdr-estimates/:id` | `/estimates/:id` | PDREstimatePanel | `estimate_updated` |
| 8. Request Signature | "Request Signature" | `POST /pdr-estimates/:id/request-signature` | `/estimates/:id/review` | PDREstimate | `signature_requested` |
| 9. Customer Signs | Signature pad | `POST /pdr-estimates/:id/sign` | `/estimates/:id/review` | PDREstimate | `customer_signed` |
| 10. Submit to Insurer | "Submit to Insurer" | `POST /pdr-estimates/:id/submit-to-insurer` | `/estimates/:id/review` | PDREstimate | `submitted_to_insurer` |
| 11. Insurer Approves | Approval form | `POST /pdr-estimates/:id/insurer-approve` | `/estimates/:id/review` | PDREstimate | `insurer_approved` |
| 12. Create Job | "Create Job" | `POST /pdr-estimates/:id/job` | `/estimates/:id/review` | Job | `job_created` |
| 13. Start Job | "Start" button | `PATCH /jobs/:id` | `/jobs/:id` | Job | `job_started` |
| 14. Complete Job | "Complete" button | `PATCH /jobs/:id` | `/jobs/:id` | Job | `job_completed` |
| 15. Create Insurer Invoice | "Create Invoice" | `POST /pdr-estimates/:id/invoices/insurer` | `/estimates/:id/review` | Invoice | `invoice_created` |
| 16. Create Customer Invoice | "Create Invoice" | `POST /pdr-estimates/:id/invoices/customer` | `/estimates/:id/review` | Invoice | `invoice_created` |
| 17. Issue Invoice | "Issue" button | `POST /invoices/:id/issue` | `/invoices/:id` | Invoice | `invoice_issued` |
| 18. Record Payment | Payment form | `POST /invoices/:id/payments` | `/invoices/:id` | Payment, Invoice | `payment_received` |
| 19. Download Receipt | "Receipt" button | `GET /invoices/:id/payments/:id/receipt.pdf` | `/invoices/:id` | — | — |
| 20. Close Claim | "Close" button | `POST /pdr-estimates/:id/close` | `/estimates/:id/review` | PDREstimate | `estimate_closed` |

---

## PHASE 7: "Do Not Build New" Connection Plan

### For Ops Dashboard / Command Center

**DO NOT create new:**
1. ❌ New job status fields → Use existing `Job.status` (scheduled, in_progress, completed, cancelled)
2. ❌ New payment tracking → Use existing `Invoice` + `Payment` models
3. ❌ New estimate states → Use existing `PDREstimate.customer_status` + `insurer_status`
4. ❌ New activity log → Use existing `EstimateActivity` model
5. ❌ New workflow engine → Use existing `WorkflowService.get_workflow()`
6. ❌ New PDF generators → Use existing `pdf_generator`, `receipt_pdf_generator`, etc.
7. ❌ New export system → Use existing `/exports/invoices.csv`, `/exports/payments.csv`

**INSTEAD, wire up:**

| Ops Feature | Existing Asset | How to Connect |
|-------------|----------------|----------------|
| Job board | `GET /jobs` | Filter by status, date, tech |
| Revenue tracking | `GET /invoices` | Sum by status, date range |
| Payment overview | `GET /exports/payments.csv` | Already filterable by date |
| Customer pipeline | `GET /pdr-estimates/:id/workflow` | Use workflow state for stage |
| Tech utilization | `GET /jobs` + `assigned_tech` | Group by tech, count status |
| Overdue invoices | `Invoice.is_overdue` property | Query `status != paid` and `due_at < now` |
| Approval bottleneck | `PDREstimate.insurer_status` | Query `submitted` older than X days |

### For Future Features

| New Feature | Reuse Path |
|-------------|------------|
| Email notifications | Extend `email_service.py` |
| SMS notifications | Add to `email_service.py` pattern |
| Batch invoicing | Reuse `Invoice.create_from_estimate()` |
| Scheduled reports | Reuse export hooks + cron |
| Mobile tech app | Reuse all `/jobs` + `/invoices` endpoints |
| Customer SMS updates | Reuse workflow states for triggers |

---

## Summary Statistics

- **Frontend Routes**: 89
- **Backend Endpoints**: 99+
- **Master Models**: 8
- **Tenant Models**: 15
- **Services**: 14
- **React Hooks**: 13
- **Components**: 70+

**Key Principle**: Before building anything new, check this audit first. If a similar capability exists, extend or connect to it rather than duplicating.
