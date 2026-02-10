import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useJob, useUpdateJobStatus } from "@/hooks/use-jobs"
import {
  useEstimateInvoices,
  useCreateInvoiceFromEstimate,
  useEstimateBillingSummary,
  invoiceStatusColors,
  invoiceStatusLabels,
  allocationTypeLabels,
  allocationTypeColors,
  AllocationType,
} from "@/hooks/use-invoices"
import {
  ArrowLeft,
  Calendar,
  Car,
  User,
  Phone,
  Mail,
  Wrench,
  DollarSign,
  FileText,
  Clock,
  Plus,
  Loader2,
  ExternalLink,
  Receipt,
} from "lucide-react"
import { useState } from "react"
import { WorkflowCard } from "@/components/workflow/WorkflowCard"
import { useJobWorkflow } from "@/hooks/use-workflow"

const statusColors: Record<string, string> = {
  SCHEDULED: "bg-blue-100 text-blue-800",
  IN_PROGRESS: "bg-yellow-100 text-yellow-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
  ON_HOLD: "bg-gray-100 text-gray-800",
  scheduled: "bg-blue-100 text-blue-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
  rescheduled: "bg-amber-100 text-amber-800",
}

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: job, isLoading } = useJob(Number(id))
  const updateStatus = useUpdateJobStatus()

  // Invoice hooks - fetch invoices for linked estimate using billing summary
  const estimateId = job?.estimate_id || null
  const { data: billingData, isLoading: isLoadingInvoices } = useEstimateBillingSummary(estimateId)
  const { data: invoicesData } = useEstimateInvoices(estimateId)
  const createInvoice = useCreateInvoiceFromEstimate()

  const invoices = billingData?.invoices || invoicesData?.invoices || []
  const hasInvoice = invoices.length > 0
  const latestInvoice = hasInvoice ? invoices[0] : null

  // Combined totals from all invoices
  const totals = billingData?.totals || {
    total_invoiced: invoices.reduce((sum, inv) => sum + (inv.total || 0), 0),
    total_paid: invoices.reduce((sum, inv) => sum + (inv.amount_paid || 0), 0),
    total_balance: invoices.reduce((sum, inv) => sum + (inv.balance_due || 0), 0),
  }

  // Workflow hooks
  const jobId = job?.id || null
  const { data: workflow, isLoading: isLoadingWorkflow, refetch: refetchWorkflow } = useJobWorkflow(jobId)
  const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null)

  // Can create invoice if job is completed or has estimate_id
  const canCreateInvoice = estimateId && !hasInvoice && (
    job?.status === 'COMPLETED' ||
    job?.status === 'completed'
  )

  const handleCreateInvoice = async () => {
    if (!estimateId) return
    try {
      const invoice = await createInvoice.mutateAsync({
        estimateId,
        params: { payer_type: 'insurer', job_id: job?.id }
      })
      navigate(`/invoices/${invoice.id}`)
    } catch {
      // Error handled by mutation
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="space-y-6">
        <PageHeader title="Job Not Found" />
        <p className="text-muted-foreground">The job you're looking for doesn't exist.</p>
        <Button onClick={() => navigate("/jobs")}>Back to Jobs</Button>
      </div>
    )
  }

  const handleStatusChange = async (newStatus: string) => {
    await updateStatus.mutateAsync({ id: job.id, status: newStatus })
  }

  const formatCurrency = (amount: number | null) => {
    if (amount == null) return "$0.00"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  // Handle workflow actions
  const handleWorkflowAction = async (actionKey: string) => {
    setActionLoadingKey(actionKey)

    try {
      switch (actionKey) {
        case 'start_job':
          await handleStatusChange('IN_PROGRESS')
          break

        case 'complete_job':
          await handleStatusChange('COMPLETED')
          break

        case 'create_insurer_invoice':
        case 'create_customer_invoice':
          if (estimateId) {
            navigate(`/estimates/${estimateId}/review`)
          }
          break

        case 'collect_payment':
          if (latestInvoice) {
            navigate(`/invoices/${latestInvoice.id}`)
          }
          break

        case 'close_claim':
          if (estimateId) {
            navigate(`/estimates/${estimateId}/review`)
          }
          break

        default:
          if (estimateId) {
            navigate(`/estimates/${estimateId}/review`)
          }
      }
    } catch (error: unknown) {
      const err = error as { message?: string; response?: { data?: { error?: string } } }
      console.error('Workflow action failed:', err?.response?.data?.error || err?.message)
    } finally {
      setActionLoadingKey(null)
      refetchWorkflow()
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/jobs")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={`Job ${job.job_number}`}
          description={`Created ${new Date(job.created_at).toLocaleDateString()}`}
        >
          <Badge className={statusColors[job.status] || "bg-gray-100 text-gray-800"}>
            {job.status.replace("_", " ")}
          </Badge>
        </PageHeader>
      </div>

      {/* Workflow Progress Card */}
      {workflow && (
        <WorkflowCard
          workflow={workflow}
          isLoading={isLoadingWorkflow}
          onAction={handleWorkflowAction}
          actionLoadingKey={actionLoadingKey}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Customer Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Customer Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="font-medium">{job.customer_name}</p>
            </div>
            {job.customer_phone && (
              <div className="flex items-center gap-2 text-sm">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <a href={`tel:${job.customer_phone}`} className="hover:underline">
                  {job.customer_phone}
                </a>
              </div>
            )}
            {job.customer_email && (
              <div className="flex items-center gap-2 text-sm">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <a href={`mailto:${job.customer_email}`} className="hover:underline">
                  {job.customer_email}
                </a>
              </div>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link to={`/customers/${job.customer_id}`}>View Customer</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Vehicle Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicle Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="font-medium">
                {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
              </p>
              {job.vehicle_color && (
                <p className="text-sm text-muted-foreground">Color: {job.vehicle_color}</p>
              )}
            </div>
            {job.vehicle_vin && (
              <div className="text-sm">
                <span className="text-muted-foreground">VIN:</span> {job.vehicle_vin}
              </div>
            )}
            {job.license_plate && (
              <div className="text-sm">
                <span className="text-muted-foreground">License Plate:</span> {job.license_plate}
              </div>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link to={`/vehicles/${job.vehicle_id}`}>View Vehicle</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Job Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              Job Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {job.damage_type && (
              <div>
                <p className="text-sm text-muted-foreground">Damage Type</p>
                <p className="font-medium">{job.damage_type}</p>
              </div>
            )}
            {job.tech_name && (
              <div>
                <p className="text-sm text-muted-foreground">Assigned Technician</p>
                <p className="font-medium">{job.tech_name}</p>
              </div>
            )}
            {job.scheduled_date && (
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Scheduled Date</p>
                  <p className="font-medium">
                    {new Date(job.scheduled_date).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}
            {job.estimated_completion && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Est. Completion</p>
                  <p className="font-medium">
                    {new Date(job.estimated_completion).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}
            {/* Link to Estimate */}
            {estimateId && (
              <div className="pt-2 border-t">
                <Link
                  to={`/estimates/${estimateId}`}
                  className="flex items-center gap-2 text-sm text-primary hover:underline"
                >
                  <FileText className="h-4 w-4" />
                  View Linked Estimate
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Financial Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Financial Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">${job.total?.toLocaleString() || "0"}</p>
            </div>
            {job.insurance_company && (
              <div>
                <p className="text-sm text-muted-foreground">Insurance</p>
                <p className="font-medium">{job.insurance_company}</p>
                {job.claim_number && (
                  <p className="text-sm text-muted-foreground">
                    Claim #: {job.claim_number}
                  </p>
                )}
              </div>
            )}
            {job.deductible && (
              <div>
                <p className="text-sm text-muted-foreground">Deductible</p>
                <p className="font-medium">${job.deductible.toLocaleString()}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Invoice Section - Only show if job has estimate */}
        {estimateId && (
          <Card className="lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Receipt className="h-5 w-5" />
                Invoices
              </CardTitle>
              {canCreateInvoice && (
                <Button
                  onClick={handleCreateInvoice}
                  disabled={createInvoice.isPending}
                >
                  {createInvoice.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Generate Invoice
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {isLoadingInvoices ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : hasInvoice && latestInvoice ? (
                <div className="space-y-4">
                  {/* Combined totals for multiple invoices */}
                  {invoices.length > 1 && (
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border mb-4">
                      <span className="text-sm font-medium text-muted-foreground">Combined Total</span>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Invoiced</p>
                          <p className="font-medium">{formatCurrency(totals.total_invoiced)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Paid</p>
                          <p className="font-medium text-green-600">{formatCurrency(totals.total_paid)}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground">Balance</p>
                          <p className={`font-bold ${totals.total_balance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {formatCurrency(totals.total_balance)}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {invoices.map((invoice) => (
                    <div
                      key={invoice.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 cursor-pointer"
                      onClick={() => navigate(`/invoices/${invoice.id}`)}
                    >
                      <div className="flex items-center gap-4">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Receipt className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{invoice.invoice_number}</p>
                            {invoice.allocation_type && invoice.allocation_type !== 'other' && (
                              <Badge className={`text-xs ${allocationTypeColors[invoice.allocation_type as AllocationType]}`}>
                                {allocationTypeLabels[invoice.allocation_type as AllocationType]}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {invoice.payer_name || 'Insurance'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-medium">{formatCurrency(invoice.total)}</p>
                          {invoice.balance_due > 0 ? (
                            <p className="text-sm text-red-600">
                              Due: {formatCurrency(invoice.balance_due)}
                            </p>
                          ) : (
                            <p className="text-sm text-green-600">Paid</p>
                          )}
                        </div>
                        <Badge className={invoiceStatusColors[invoice.status]}>
                          {invoiceStatusLabels[invoice.status]}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Receipt className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                  <p className="text-muted-foreground">No invoice created yet</p>
                  {!canCreateInvoice && (job?.status === 'SCHEDULED' || job?.status === 'scheduled' || job?.status === 'IN_PROGRESS' || job?.status === 'in_progress') && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Complete the job to generate an invoice
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Notes */}
        {(job.notes || job.tech_notes || job.internal_notes) && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Notes
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {job.notes && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Customer Notes</p>
                  <p className="mt-1">{job.notes}</p>
                </div>
              )}
              {job.tech_notes && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Tech Notes</p>
                  <p className="mt-1">{job.tech_notes}</p>
                </div>
              )}
              {job.internal_notes && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Internal Notes</p>
                  <p className="mt-1">{job.internal_notes}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button asChild>
              <Link to={`/jobs/${job.id}/edit`}>Edit Job</Link>
            </Button>
            {(job.status === "SCHEDULED" || job.status === "scheduled") && (
              <Button
                variant="outline"
                onClick={() => handleStatusChange("IN_PROGRESS")}
                disabled={updateStatus.isPending}
              >
                {updateStatus.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Start Job
              </Button>
            )}
            {(job.status === "IN_PROGRESS" || job.status === "in_progress") && (
              <Button
                variant="outline"
                onClick={() => handleStatusChange("COMPLETED")}
                disabled={updateStatus.isPending}
              >
                {updateStatus.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Complete Job
              </Button>
            )}
            {estimateId && (
              <Button variant="outline" asChild>
                <Link to={`/estimates/${estimateId}`}>
                  <FileText className="h-4 w-4 mr-2" />
                  View Estimate
                </Link>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
