/**
 * PDR Estimate Review Screen - Matrix-Based Pricing
 *
 * Two tabs: CUSTOMER VIEW (simplified) | DETAIL VIEW (full breakdown)
 * Customer view for signature approval
 * Detail view for internal/insurance use with matrix format
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ArrowLeft,
  Printer,
  Send,
  Wrench,
  Car,
  DollarSign,
  Clock,
  CheckCircle2,
  Download,
  Loader2,
  Eye,
  User,
  AlertTriangle,
  Shield,
  FileSpreadsheet,
  CircleDot,
  Plus,
  FileText,
  Package,
  Sparkles,
  Check,
  X,
  Archive
} from 'lucide-react'

import { SignaturePad } from '@/components/estimating/SignaturePad'

import {
  usePDREstimate,
  useApprovePDREstimate,
  useSignEstimate,
  useCreateWorkOrder,
  useEstimateJob,
  useCreateJobFromEstimate,
  useDownloadEstimateDisputePack,
  useEstimateSupplements,
  PANEL_NAMES,
  SIZE_LABELS,
  Panel
} from '@/hooks/use-pdr-estimates'
import {
  useEstimateInvoices,
  useCreateInvoiceFromEstimate,
  useEstimateBillingSummary,
  useUpdateBilling,
  useCreateInsurerInvoice,
  useCreateCustomerInvoice,
  allocationTypeLabels
} from '@/hooks/use-invoices'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { WorkflowCard } from '@/components/workflow/WorkflowCard'
import { useEstimateWorkflow, useCloseClaim } from '@/hooks/use-workflow'
import {
  useEstimatePartsSuggestions,
  useEstimatePartsRequests,
  useCreateEstimatePartsRequests,
  PartsSuggestion
} from '@/hooks/use-jobs'
import { PARTS_STATUS_OPTIONS, PartsPricingPreview } from '@/hooks/use-ops'
import { Checkbox } from '@/components/ui/checkbox'
import { useEstimateRI } from '@/hooks/use-ri'

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700 border-slate-300',
  in_progress: 'bg-amber-100 text-amber-700 border-amber-300',
  approved: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  completed: 'bg-blue-100 text-blue-700 border-blue-300'
}

const SIZE_COLORS: Record<string, string> = {
  dime: 'bg-green-500',
  nickel: 'bg-yellow-500',
  quarter: 'bg-orange-500',
  half: 'bg-red-500'
}

export function EstimateReview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState('customer')
  const [signature, setSignature] = useState<string | null>(null)
  const [showMatrixDialog, setShowMatrixDialog] = useState(false)
  const [isApproving, setIsApproving] = useState(false)

  // API hooks
  const { data: estimate, isLoading, refetch } = usePDREstimate(id ? parseInt(id) : null)
  const signEstimate = useSignEstimate()
  const approveEstimate = useApprovePDREstimate()
  const createWorkOrder = useCreateWorkOrder()

  // Job hooks
  const estimateId = id ? parseInt(id) : undefined
  const { data: jobData, isLoading: isLoadingJob } = useEstimateJob(estimateId)
  const createJob = useCreateJobFromEstimate()

  // Invoice hooks
  const { data: invoicesData } = useEstimateInvoices(estimateId || null)
  const createInvoice = useCreateInvoiceFromEstimate()

  // Split billing hooks
  const { data: billingData, refetch: refetchBilling } = useEstimateBillingSummary(estimateId || null)
  const updateBilling = useUpdateBilling()
  const createInsurerInvoice = useCreateInsurerInvoice()
  const createCustomerInvoice = useCreateCustomerInvoice()

  // Workflow hooks
  const { data: workflow, isLoading: isLoadingWorkflow, refetch: refetchWorkflow } = useEstimateWorkflow(estimateId || null)
  const closeClaim = useCloseClaim()
  const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null)

  // Billing state (local edits before saving)
  const [deductibleInput, setDeductibleInput] = useState<string>('')
  const [oopInput, setOopInput] = useState<string>('')
  const [billingDirty, setBillingDirty] = useState(false)

  // Parts requests state (Stage 5R)
  const [showPartsSuggestionsModal, setShowPartsSuggestionsModal] = useState(false)
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set())

  // Parts hooks (Stage 5R)
  const { data: partsSuggestionsData, isLoading: isLoadingSuggestions, refetch: refetchSuggestions } = useEstimatePartsSuggestions(estimateId || null)
  const { data: partsRequestsData, refetch: refetchPartsRequests } = useEstimatePartsRequests(estimateId || null)
  const createPartsRequests = useCreateEstimatePartsRequests()

  // R&I Justification hooks (Phase 6B)
  const { data: riData } = useEstimateRI(estimateId || 0)

  // Stage 7E: Adjuster Pack / Supplements
  const downloadDisputePack = useDownloadEstimateDisputePack()
  const { data: supplementsData } = useEstimateSupplements(estimateId || null)
  const supplementCount = supplementsData?.count || 0

  // Sync billing inputs when data loads
  useMemo(() => {
    if (billingData?.billing_summary) {
      setDeductibleInput(String(billingData.billing_summary.deductible || 0))
      setOopInput(String(billingData.billing_summary.customer_oop || 0))
    }
  }, [billingData?.billing_summary])

  // Calculate stats
  const stats = useMemo(() => {
    if (!estimate?.panels) return { totalDents: 0, totalPanels: 0, crPanels: 0, laborTotal: 0, riTotal: 0 }

    const totalDents = estimate.panels.reduce((sum, p) => sum + (p.total_dent_count || 0), 0)
    const crPanels = estimate.panels.filter(p => p.is_conventional_repair).length
    const laborTotal = estimate.panels.reduce((sum, p) => sum + (p.panel_total || 0), 0)
    const riTotal = estimate.panels.reduce((sum, p) =>
      sum + (p.ri_items?.reduce((s, ri) => s + ri.price, 0) || 0), 0)

    return {
      totalDents,
      totalPanels: estimate.panels.length,
      crPanels,
      laborTotal,
      riTotal
    }
  }, [estimate])

  // Handle approve (sign then approve)
  const handleApprove = async () => {
    if (!estimate || !signature) return

    setIsApproving(true)
    try {
      // First sign the estimate
      await signEstimate.mutateAsync({
        id: estimate.id,
        signatureBase64: signature,
        signedByName: estimate.customer_name || 'Customer'
      })
      // Then approve it
      await approveEstimate.mutateAsync(estimate.id)
      refetch()
    } finally {
      setIsApproving(false)
    }
  }

  // Handle create work order
  const handleCreateWorkOrder = async () => {
    if (!estimate) return

    await createWorkOrder.mutateAsync({ estimateId: estimate.id })
    navigate(`/estimates/${estimate.id}/work-order`)
  }

  // Handle create job from approved estimate
  const handleCreateJob = async () => {
    if (!estimate || !estimate.is_insurer_approved) return

    try {
      const result = await createJob.mutateAsync({ estimateId: estimate.id })
      // Navigate to the job
      navigate(`/jobs/${result.job.id}`)
    } catch {
      // Error handled by mutation
    }
  }

  // Handle create invoice from approved estimate
  const handleCreateInvoice = async () => {
    if (!estimate || !estimate.is_insurer_approved) return

    try {
      const invoice = await createInvoice.mutateAsync({
        estimateId: estimate.id,
        params: { payer_type: 'insurer' }
      })
      navigate(`/invoices/${invoice.id}`)
    } catch {
      // Error handled by mutation
    }
  }

  // Handle save billing changes
  const handleSaveBilling = async () => {
    if (!estimate) return

    try {
      await updateBilling.mutateAsync({
        estimateId: estimate.id,
        params: {
          deductible: parseFloat(deductibleInput) || 0,
          customer_oop: parseFloat(oopInput) || 0
        }
      })
      setBillingDirty(false)
      refetchBilling()
    } catch {
      // Error handled by mutation
    }
  }

  // Handle create insurer invoice (split billing)
  const handleCreateInsurerInvoice = async () => {
    if (!estimate || !estimate.is_insurer_approved) return

    try {
      const result = await createInsurerInvoice.mutateAsync({
        estimateId: estimate.id
      })
      navigate(`/invoices/${result.invoice.id}`)
    } catch {
      // Error handled by mutation
    }
  }

  // Handle create customer invoice (split billing)
  const handleCreateCustomerInvoice = async () => {
    if (!estimate || !estimate.is_insurer_approved) return

    try {
      const result = await createCustomerInvoice.mutateAsync({
        estimateId: estimate.id,
        includeOop: true
      })
      navigate(`/invoices/${result.invoice.id}`)
    } catch {
      // Error handled by mutation
    }
  }

  // Handle workflow actions
  const handleWorkflowAction = async (actionKey: string) => {
    if (!estimate) return

    setActionLoadingKey(actionKey)

    try {
      switch (actionKey) {
        case 'request_customer_auth':
          // Switch to customer view for signature
          setActiveTab('customer')
          break

        case 'submit_to_insurer':
          // TODO: Implement submit to insurer flow
          console.log('Submit to insurer - not yet implemented')
          break

        case 'mark_insurer_approved':
          // TODO: Implement insurer approval
          console.log('Mark insurer approved - not yet implemented')
          break

        case 'create_job':
          await handleCreateJob()
          break

        case 'start_job':
          if (linkedJob) {
            navigate(`/jobs/${linkedJob.id}`)
          }
          break

        case 'complete_job':
          if (linkedJob) {
            navigate(`/jobs/${linkedJob.id}`)
          }
          break

        case 'create_insurer_invoice':
          await handleCreateInsurerInvoice()
          break

        case 'create_customer_invoice':
          await handleCreateCustomerInvoice()
          break

        case 'collect_payment':
          // Navigate to the first invoice
          if (latestInvoice) {
            navigate(`/invoices/${latestInvoice.id}`)
          }
          break

        case 'close_claim':
          await closeClaim.mutateAsync(estimate.id)
          refetch()
          refetchWorkflow()
          break

        default:
          console.log('Unknown action:', actionKey)
      }
    } catch (error: unknown) {
      const err = error as { message?: string; response?: { data?: { error?: string } } }
      console.error('Workflow action failed:', err?.response?.data?.error || err?.message)
    } finally {
      setActionLoadingKey(null)
      refetchWorkflow()
    }
  }

  // Computed values for job UI
  const hasJob = !isLoadingJob && jobData?.has_job
  const linkedJob = jobData?.job
  const canCreateJob = estimate?.is_insurer_approved && !hasJob

  // Computed values for invoice UI
  const hasInvoice = invoicesData?.invoices && invoicesData.invoices.length > 0
  const latestInvoice = hasInvoice ? invoicesData.invoices[0] : null
  const canCreateInvoice = estimate?.is_insurer_approved && !hasInvoice

  // Computed values for split billing UI
  const billingSummary = billingData?.billing_summary
  const hasInsurerInvoice = billingData?.has_insurer_invoice ?? false
  const hasCustomerInvoice = billingData?.has_customer_invoice ?? false
  const existingInvoices = billingData?.invoices ?? []

  // Get panel modifiers as badges
  const getPanelModifiers = (panel: Panel) => {
    const mods = []
    if (panel.is_aluminum) mods.push({ label: 'Aluminum', color: 'bg-amber-100 text-amber-700 border-amber-300' })
    if (panel.is_hss) mods.push({ label: 'HSS', color: 'bg-blue-100 text-blue-700 border-blue-300' })
    if (panel.requires_glue_pull) mods.push({ label: 'Glue Pull', color: 'bg-purple-100 text-purple-700 border-purple-300' })
    if (panel.is_tall_roof) mods.push({ label: 'Tall Roof', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' })
    return mods
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading estimate...</p>
        </div>
      </div>
    )
  }

  if (!estimate) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Estimate not found</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/estimates')}>
            Back to Estimates
          </Button>
        </div>
      </div>
    )
  }

  const grandTotal = stats.laborTotal + stats.riTotal

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-white border-b shadow-sm">
        <div className="flex items-center justify-between p-4 max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(`/estimates/${estimate.id}`)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-bold flex items-center gap-2">
                Review: Estimate #{estimate.estimate_number || estimate.id}
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={cn('text-xs border', STATUS_STYLES[estimate.status])}>
                  {estimate.status.replace('_', ' ')}
                </Badge>
                {estimate.matrix_profile_name && (
                  <Badge variant="outline" className="text-xs">
                    <Shield className="h-3 w-3 mr-1" />
                    {estimate.matrix_profile_name}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Printer className="h-4 w-4 mr-1" />
              Print
            </Button>

            {/* Job button - only show when insurer approved */}
            {estimate.is_insurer_approved && (
              hasJob && linkedJob ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/jobs/${linkedJob.id}`)}
                >
                  <Wrench className="h-4 w-4 mr-1" />
                  <span className="hidden sm:inline">{linkedJob.job_number}</span>
                  <Badge
                    variant="outline"
                    className={cn(
                      'ml-2 text-xs',
                      linkedJob.status === 'completed' && 'bg-green-100 text-green-700 border-green-300',
                      linkedJob.status === 'in_progress' && 'bg-blue-100 text-blue-700 border-blue-300',
                      linkedJob.status === 'scheduled' && 'bg-amber-100 text-amber-700 border-amber-300'
                    )}
                  >
                    {linkedJob.status.replace('_', ' ')}
                  </Badge>
                </Button>
              ) : canCreateJob ? (
                <Button
                  size="sm"
                  onClick={handleCreateJob}
                  disabled={createJob.isPending}
                >
                  {createJob.isPending && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  <Plus className="h-4 w-4 mr-1" />
                  Create Job
                </Button>
              ) : null
            )}

            {/* Invoice button - only show when insurer approved */}
            {estimate.is_insurer_approved && (
              hasInvoice && latestInvoice ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/invoices/${latestInvoice.id}`)}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  <span className="hidden sm:inline">{latestInvoice.invoice_number}</span>
                  <Badge
                    variant="outline"
                    className={cn(
                      'ml-2 text-xs',
                      latestInvoice.status === 'paid' && 'bg-green-100 text-green-700 border-green-300',
                      latestInvoice.status === 'issued' && 'bg-blue-100 text-blue-700 border-blue-300',
                      latestInvoice.status === 'partial_paid' && 'bg-yellow-100 text-yellow-700 border-yellow-300',
                      latestInvoice.status === 'draft' && 'bg-gray-100 text-gray-700 border-gray-300'
                    )}
                  >
                    {latestInvoice.status.replace('_', ' ')}
                  </Badge>
                </Button>
              ) : canCreateInvoice ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCreateInvoice}
                  disabled={createInvoice.isPending}
                >
                  {createInvoice.isPending && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  <FileText className="h-4 w-4 mr-1" />
                  Generate Invoice
                </Button>
              ) : null
            )}

            {/* Create Work Order - legacy button */}
            {estimate.status === 'approved' && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleCreateWorkOrder}
                disabled={createWorkOrder.isPending}
              >
                {createWorkOrder.isPending && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                <Wrench className="h-4 w-4 mr-1" />
                Work Order
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full max-w-md mx-auto grid grid-cols-2 mb-6">
            <TabsTrigger value="customer" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Customer View
            </TabsTrigger>
            <TabsTrigger value="detail" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Detail View
            </TabsTrigger>
          </TabsList>

          {/* Customer View Tab */}
          <TabsContent value="customer">
            <div className="max-w-lg mx-auto space-y-4">
              {/* Vehicle Info */}
              <Card className="shadow-sm">
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-blue-100 rounded-full">
                      <Car className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-bold text-lg">
                        {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                      </p>
                      {estimate.vin && (
                        <p className="text-sm text-muted-foreground font-mono">
                          VIN: {estimate.vin}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Customer Info */}
              {estimate.customer_name && (
                <Card className="shadow-sm">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-purple-100 rounded-full">
                        <User className="h-6 w-6 text-purple-600" />
                      </div>
                      <div>
                        <p className="font-medium">{estimate.customer_name}</p>
                        {estimate.customer_phone && (
                          <p className="text-sm text-muted-foreground">{estimate.customer_phone}</p>
                        )}
                        {estimate.claim_number && (
                          <p className="text-sm text-muted-foreground">Claim: {estimate.claim_number}</p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Panel Summary (simplified) */}
              <Card className="shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Repair Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {estimate.panels?.map(panel => (
                    <div
                      key={panel.id}
                      className={cn(
                        "flex justify-between items-center p-2 rounded-lg",
                        panel.is_conventional_repair ? "bg-red-50" : "bg-slate-50"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {PANEL_NAMES[panel.panel_name] || panel.panel_name}
                        </span>
                        {panel.is_conventional_repair && (
                          <Badge variant="destructive" className="text-xs">CR</Badge>
                        )}
                      </div>
                      <div className="text-right">
                        <Badge variant="secondary" className="mb-1">
                          {panel.total_dent_count} dent{panel.total_dent_count !== 1 ? 's' : ''}
                        </Badge>
                        <p className="text-sm font-medium text-emerald-600">
                          ${panel.panel_total.toFixed(0)}
                        </p>
                      </div>
                    </div>
                  ))}
                  <Separator />
                  <div className="flex justify-between font-medium">
                    <span>Total Dents</span>
                    <span>{stats.totalDents}</span>
                  </div>
                  <div className="flex justify-between font-medium">
                    <span>Panels Repaired</span>
                    <span>{stats.totalPanels}</span>
                  </div>
                </CardContent>
              </Card>

              {/* CR Warning */}
              {stats.crPanels > 0 && (
                <Card className="shadow-sm border-red-300 bg-red-50">
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-red-800">Conventional Repair Required</p>
                        <p className="text-sm text-red-700 mt-1">
                          {stats.crPanels} panel{stats.crPanels > 1 ? 's' : ''} exceed PDR limits
                          and will require conventional body repair.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Grand Total */}
              <Card className="shadow-sm bg-emerald-50 border-emerald-200">
                <CardContent className="pt-6 pb-6">
                  <div className="text-center">
                    <p className="text-muted-foreground mb-1">Estimate Total</p>
                    <p className="text-4xl font-bold text-emerald-700">
                      ${grandTotal.toFixed(2)}
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Terms */}
              <Card className="shadow-sm">
                <CardContent className="pt-4">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    By signing below, I authorize the paintless dent repair work described
                    in this estimate. I understand that additional charges may apply if
                    hidden damage is discovered during the repair process. Any additional
                    work will be documented and communicated before proceeding.
                  </p>
                </CardContent>
              </Card>

              {/* Signature */}
              {estimate.status === 'draft' || estimate.status === 'in_progress' ? (
                <>
                  <SignaturePad
                    onSignatureChange={setSignature}
                    title="Customer Signature"
                  />

                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    size="lg"
                    onClick={handleApprove}
                    disabled={!signature || isApproving}
                  >
                    {isApproving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Approving...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        I Approve This Estimate
                      </>
                    )}
                  </Button>
                </>
              ) : (
                <Card className="shadow-sm bg-emerald-50 border-emerald-200">
                  <CardContent className="pt-4 text-center">
                    <CheckCircle2 className="h-10 w-10 text-emerald-600 mx-auto mb-2" />
                    <p className="font-medium text-emerald-700">Estimate Approved</p>
                    <p className="text-sm text-emerald-600">
                      Approved on {new Date(estimate.updated_at).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Detail View Tab */}
          <TabsContent value="detail">
            {/* Workflow Progress Card */}
            {workflow && (
              <WorkflowCard
                workflow={workflow}
                isLoading={isLoadingWorkflow}
                onAction={handleWorkflowAction}
                actionLoadingKey={actionLoadingKey}
                className="mb-6"
              />
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left: Info & Stats */}
              <div className="space-y-4">
                {/* Vehicle */}
                <Card className="shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Car className="h-4 w-4 text-blue-600" />
                      Vehicle
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="font-medium">
                      {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                    </p>
                    {estimate.vin && (
                      <p className="text-xs text-muted-foreground font-mono mt-1">
                        VIN: {estimate.vin}
                      </p>
                    )}
                    {estimate.is_tall_roof_vehicle && (
                      <Badge variant="outline" className="mt-2 text-xs">
                        Tall Roof Vehicle
                      </Badge>
                    )}
                  </CardContent>
                </Card>

                {/* Insurance Matrix */}
                {estimate.matrix_profile_name && (
                  <Card className="shadow-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Shield className="h-4 w-4 text-emerald-600" />
                        Insurance Matrix
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="font-medium">{estimate.matrix_profile_name}</p>
                      {estimate.claim_number && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Claim: {estimate.claim_number}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Customer */}
                {estimate.customer_name && (
                  <Card className="shadow-sm">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <User className="h-4 w-4 text-purple-600" />
                        Customer
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="font-medium">{estimate.customer_name}</p>
                      {estimate.customer_email && (
                        <p className="text-sm text-muted-foreground">{estimate.customer_email}</p>
                      )}
                      {estimate.customer_phone && (
                        <p className="text-sm text-muted-foreground">{estimate.customer_phone}</p>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Stats */}
                <Card className="shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Dents</span>
                      <span className="font-medium">{stats.totalDents}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Panels</span>
                      <span className="font-medium">{stats.totalPanels}</span>
                    </div>
                    {stats.crPanels > 0 && (
                      <div className="flex justify-between text-red-600">
                        <span>CR Panels</span>
                        <span className="font-medium">{stats.crPanels}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Totals */}
                <Card className="shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-emerald-600" />
                      Totals
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">PDR Labor</span>
                      <span className="font-medium">${stats.laborTotal.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">R&I Operations</span>
                      <span className="font-medium">${stats.riTotal.toFixed(2)}</span>
                    </div>
                    <Separator />
                    <div className="flex justify-between text-lg">
                      <span className="font-bold">Grand Total</span>
                      <span className="font-bold text-emerald-600">
                        ${grandTotal.toFixed(2)}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                {/* Billing - Split Billing Card (show when insurer approved) */}
                {estimate.is_insurer_approved && billingSummary && (
                  <Card className="shadow-sm border-purple-200 bg-purple-50/30">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-purple-600" />
                        Billing Allocation
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Approved Total */}
                      <div className="bg-white rounded-lg p-3 border">
                        <div className="flex justify-between items-center">
                          <span className="text-muted-foreground text-sm">Insurer Approved</span>
                          <span className="font-bold text-lg text-emerald-600">
                            ${billingSummary.approved_total?.toFixed(2) || grandTotal.toFixed(2)}
                          </span>
                        </div>
                      </div>

                      {/* Deductible Input */}
                      <div className="space-y-2">
                        <Label htmlFor="deductible" className="text-sm text-muted-foreground">
                          Customer Deductible
                        </Label>
                        <div className="relative">
                          <span className="absolute left-3 top-2.5 text-muted-foreground">$</span>
                          <Input
                            id="deductible"
                            type="number"
                            min="0"
                            step="0.01"
                            value={deductibleInput}
                            onChange={(e) => {
                              setDeductibleInput(e.target.value)
                              setBillingDirty(true)
                            }}
                            className="pl-7"
                            placeholder="0.00"
                          />
                        </div>
                      </div>

                      {/* OOP Input */}
                      <div className="space-y-2">
                        <Label htmlFor="oop" className="text-sm text-muted-foreground">
                          Customer Out-of-Pocket
                        </Label>
                        <div className="relative">
                          <span className="absolute left-3 top-2.5 text-muted-foreground">$</span>
                          <Input
                            id="oop"
                            type="number"
                            min="0"
                            step="0.01"
                            value={oopInput}
                            onChange={(e) => {
                              setOopInput(e.target.value)
                              setBillingDirty(true)
                            }}
                            className="pl-7"
                            placeholder="0.00"
                          />
                        </div>
                      </div>

                      {/* Save button when dirty */}
                      {billingDirty && (
                        <Button
                          size="sm"
                          className="w-full"
                          onClick={handleSaveBilling}
                          disabled={updateBilling.isPending}
                        >
                          {updateBilling.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                          Save Billing Changes
                        </Button>
                      )}

                      <Separator />

                      {/* Suggested Invoice Amounts */}
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Suggested Insurer Invoice</span>
                          <span className="font-medium text-purple-600">
                            ${billingSummary.insurer_suggested?.toFixed(2) || '0.00'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Suggested Customer Invoice</span>
                          <span className="font-medium text-orange-600">
                            ${billingSummary.customer_suggested?.toFixed(2) || '0.00'}
                          </span>
                        </div>
                        {billingSummary.short_paid > 0 && (
                          <div className="flex justify-between text-red-600">
                            <span>Short Paid</span>
                            <span className="font-medium">${billingSummary.short_paid.toFixed(2)}</span>
                          </div>
                        )}
                      </div>

                      <Separator />

                      {/* Existing Invoices */}
                      {existingInvoices.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs text-muted-foreground font-medium">Existing Invoices</p>
                          {existingInvoices.map(inv => (
                            <div
                              key={inv.id}
                              className="flex justify-between items-center p-2 bg-white rounded border cursor-pointer hover:bg-slate-50"
                              onClick={() => navigate(`/invoices/${inv.id}`)}
                            >
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs">
                                  {allocationTypeLabels[inv.allocation_type as keyof typeof allocationTypeLabels] || inv.allocation_type}
                                </Badge>
                                <span className="text-sm">{inv.invoice_number}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">${inv.total?.toFixed(2)}</span>
                                <Badge
                                  variant="outline"
                                  className={cn(
                                    'text-xs',
                                    inv.status === 'paid' && 'bg-green-100 text-green-700',
                                    inv.status === 'issued' && 'bg-blue-100 text-blue-700',
                                    inv.status === 'draft' && 'bg-gray-100 text-gray-700'
                                  )}
                                >
                                  {inv.status}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Create Invoice Buttons */}
                      <div className="space-y-2">
                        {!hasInsurerInvoice && billingSummary.insurer_suggested > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full border-purple-300 text-purple-700 hover:bg-purple-100"
                            onClick={handleCreateInsurerInvoice}
                            disabled={createInsurerInvoice.isPending || billingDirty}
                          >
                            {createInsurerInvoice.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                            <FileText className="h-4 w-4 mr-2" />
                            Create Insurer Invoice (${billingSummary.insurer_suggested.toFixed(0)})
                          </Button>
                        )}
                        {!hasCustomerInvoice && billingSummary.customer_suggested > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full border-orange-300 text-orange-700 hover:bg-orange-100"
                            onClick={handleCreateCustomerInvoice}
                            disabled={createCustomerInvoice.isPending || billingDirty}
                          >
                            {createCustomerInvoice.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                            <FileText className="h-4 w-4 mr-2" />
                            Create Customer Invoice (${billingSummary.customer_suggested.toFixed(0)})
                          </Button>
                        )}
                        {billingDirty && (
                          <p className="text-xs text-amber-600 text-center">
                            Save billing changes before creating invoices
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Parts Requests Card (Stage 5R) */}
                <Card className="shadow-sm border-amber-200 bg-amber-50/30">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Package className="h-4 w-4 text-amber-600" />
                      Parts Requests
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {/* Summary stats */}
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Active Requests</span>
                      <span className="font-medium">{partsRequestsData?.count || 0}</span>
                    </div>

                    {/* Stage 5T: Approval status summary */}
                    {(() => {
                      const requests = partsRequestsData?.requests as Array<{
                        id: number
                        approved_to_order?: boolean
                      }>[] | undefined
                      if (!requests?.length) return null

                      const approvedCount = (requests as Array<{ approved_to_order?: boolean }>).filter(r => r.approved_to_order).length
                      const pendingCount = requests.length - approvedCount

                      return (
                        <div className="flex items-center gap-2">
                          <Badge className="bg-green-100 text-green-700 text-xs" title="Approved ≠ Ordered. Approval is internal only.">
                            {approvedCount} approved
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {pendingCount} pending
                          </Badge>
                        </div>
                      )
                    })()}

                    {/* Stage 5S: Parts exposure summary */}
                    {(() => {
                      const requests = partsRequestsData?.requests as Array<{
                        id: number
                        description: string
                        parts_status: string
                        qty: number
                        pricing_preview?: PartsPricingPreview
                      }> | undefined
                      if (!requests?.length) return null

                      const totalTypical = requests.reduce((sum, req) => {
                        return sum + (req.pricing_preview?.typical_estimate || 0)
                      }, 0)

                      if (totalTypical <= 0) return null

                      return (
                        <div
                          className="p-2 bg-amber-100 rounded-lg"
                          title="Estimates only. Final pricing may vary."
                        >
                          <span className="text-sm text-amber-800">
                            Estimated parts exposure: <strong>~${Math.round(totalTypical).toLocaleString()}</strong>
                            <span className="text-xs text-amber-600 ml-1">(preview)</span>
                          </span>
                        </div>
                      )
                    })()}

                    {/* Existing requests list */}
                    {partsRequestsData?.requests && partsRequestsData.requests.length > 0 && (
                      <div className="space-y-2">
                        {(partsRequestsData.requests as Array<{
                          id: number
                          description: string
                          parts_status: string
                          qty: number
                        }>).slice(0, 3).map(req => {
                          const statusOption = PARTS_STATUS_OPTIONS.find(o => o.value === req.parts_status)
                          return (
                            <div key={req.id} className="flex items-center justify-between p-2 bg-white rounded border text-sm">
                              <span className="truncate flex-1 mr-2">{req.description}</span>
                              <Badge className={`${statusOption?.color || 'bg-gray-100'} text-xs`}>
                                {statusOption?.label || req.parts_status}
                              </Badge>
                            </div>
                          )
                        })}
                        {partsRequestsData.requests.length > 3 && (
                          <p className="text-xs text-muted-foreground text-center">
                            +{partsRequestsData.requests.length - 3} more
                          </p>
                        )}
                      </div>
                    )}

                    {/* Suggestions preview */}
                    {(partsSuggestionsData?.stats?.new_suggestions ?? 0) > 0 && (
                      <div className="flex items-center gap-2 p-2 bg-amber-100 rounded-lg">
                        <Sparkles className="h-4 w-4 text-amber-600" />
                        <span className="text-sm text-amber-800">
                          {partsSuggestionsData?.stats?.new_suggestions ?? 0} parts suggestion{(partsSuggestionsData?.stats?.new_suggestions ?? 0) !== 1 ? 's' : ''} available
                        </span>
                      </div>
                    )}

                    {/* Generate Parts button */}
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full border-amber-300 text-amber-700 hover:bg-amber-100"
                      onClick={() => {
                        refetchSuggestions()
                        setShowPartsSuggestionsModal(true)
                        // Pre-select all new suggestions
                        const newSet = new Set<number>()
                        partsSuggestionsData?.suggestions?.forEach((s: PartsSuggestion, i: number) => {
                          if (!s.already_exists) newSet.add(i)
                        })
                        setSelectedSuggestions(newSet)
                      }}
                      disabled={isLoadingSuggestions}
                    >
                      {isLoadingSuggestions ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4 mr-2" />
                      )}
                      Generate Parts List
                    </Button>
                  </CardContent>
                </Card>

                {/* R&I Justification Card (Phase 6B) */}
                {riData && riData.operation_count > 0 && (
                  <Card className="shadow-sm border-blue-200 bg-blue-50/30">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Clock className="h-4 w-4 text-blue-600" />
                        R&I Justification
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {/* Summary */}
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Operations</span>
                        <span className="font-medium">{riData.operation_count}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Total R&I Time</span>
                        <span className="font-medium text-blue-700">
                          {riData.total_ri_time_hours.toFixed(2)} hrs
                        </span>
                      </div>

                      {/* Operations list */}
                      <div className="space-y-2">
                        {riData.operations.slice(0, 2).map(op => (
                          <div key={op.estimate_ri_operation_id} className="flex items-center justify-between p-2 bg-white rounded border text-sm">
                            <span className="truncate flex-1 mr-2">{op.display_name}</span>
                            <Badge className="bg-blue-100 text-blue-700 text-xs">
                              {op.totals.total_time} hrs
                            </Badge>
                          </div>
                        ))}
                        {riData.operations.length > 2 && (
                          <p className="text-xs text-muted-foreground text-center">
                            +{riData.operations.length - 2} more
                          </p>
                        )}
                      </div>

                      {/* Edit R&I button */}
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full border-blue-300 text-blue-700 hover:bg-blue-100"
                        onClick={() => navigate(`/estimates/${estimateId}?tab=ri`)}
                      >
                        <Wrench className="h-4 w-4 mr-2" />
                        Edit R&I Operations
                      </Button>
                    </CardContent>
                  </Card>
                )}

                {/* Actions */}
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => setShowMatrixDialog(true)}
                  >
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    View Matrix Format
                  </Button>
                  <Button variant="outline" className="w-full">
                    <Download className="h-4 w-4 mr-2" />
                    Export PDF
                  </Button>
                  <Button variant="outline" className="w-full">
                    <Send className="h-4 w-4 mr-2" />
                    Email to Customer
                  </Button>
                  {estimate.matrix_profile_name && (
                    <Button variant="outline" className="w-full">
                      <Send className="h-4 w-4 mr-2" />
                      Email to Insurance
                    </Button>
                  )}

                  {/* Stage 7E: Adjuster Pack Button */}
                  <Button
                    variant="default"
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    onClick={() => {
                      if (estimateId) {
                        downloadDisputePack.mutate(estimateId)
                      }
                    }}
                    disabled={downloadDisputePack.isPending}
                  >
                    {downloadDisputePack.isPending ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Archive className="h-4 w-4 mr-2" />
                    )}
                    Generate Adjuster Pack
                    {supplementCount > 0 && (
                      <span className="ml-1 text-xs opacity-75">
                        ({supplementCount} supp{supplementCount !== 1 ? 's' : ''})
                      </span>
                    )}
                  </Button>
                </div>
              </div>

              {/* Right: Panel Details */}
              <div className="lg:col-span-2 space-y-4">
                {estimate.panels?.map(panel => {
                  const mods = getPanelModifiers(panel)

                  return (
                    <Card
                      key={panel.id}
                      className={cn(
                        "shadow-sm",
                        panel.is_conventional_repair && "border-red-300 bg-red-50/50"
                      )}
                    >
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span>{PANEL_NAMES[panel.panel_name] || panel.panel_name}</span>
                            {panel.is_conventional_repair && (
                              <Badge variant="destructive" className="text-xs">
                                <AlertTriangle className="h-3 w-3 mr-1" />
                                CR Required
                              </Badge>
                            )}
                          </div>
                          <span className="text-lg text-emerald-600 font-bold">
                            ${panel.panel_total.toFixed(0)}
                          </span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Matrix Info */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="bg-slate-100 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-blue-600">{panel.total_dent_count}</p>
                            <p className="text-xs text-muted-foreground">Total Dents</p>
                          </div>
                          <div className="bg-slate-100 rounded-lg p-3 text-center">
                            <div className="flex items-center justify-center gap-1 mb-1">
                              <CircleDot className={cn("h-4 w-4", SIZE_COLORS[panel.majority_size])} />
                              <span className="font-bold">{SIZE_LABELS[panel.majority_size]}</span>
                            </div>
                            <p className="text-xs text-muted-foreground">Majority Size</p>
                          </div>
                          <div className="bg-slate-100 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-amber-600">{panel.oversized_count}</p>
                            <p className="text-xs text-muted-foreground">Oversized</p>
                          </div>
                          <div className="bg-slate-100 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold">${panel.matrix_base_price.toFixed(0)}</p>
                            <p className="text-xs text-muted-foreground">Base Price</p>
                          </div>
                        </div>

                        {/* Modifiers */}
                        {mods.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {mods.map((mod, i) => (
                              <Badge key={i} className={cn("text-xs border", mod.color)}>
                                <Plus className="h-3 w-3 mr-1" />
                                {mod.label} +25%
                              </Badge>
                            ))}
                          </div>
                        )}

                        {/* Price Breakdown */}
                        {(panel.upcharge_total > 0 || panel.oversized_count > 0) && (
                          <div className="bg-emerald-50 rounded-lg p-3 space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Matrix Base</span>
                              <span>${panel.matrix_base_price.toFixed(0)}</span>
                            </div>
                            {panel.is_aluminum && (
                              <div className="flex justify-between text-amber-700">
                                <span>+ Aluminum (25%)</span>
                                <span>+${(panel.matrix_base_price * 0.25).toFixed(0)}</span>
                              </div>
                            )}
                            {panel.is_hss && (
                              <div className="flex justify-between text-blue-700">
                                <span>+ HSS (25%)</span>
                                <span>+${(panel.matrix_base_price * 0.25).toFixed(0)}</span>
                              </div>
                            )}
                            {panel.requires_glue_pull && (
                              <div className="flex justify-between text-purple-700">
                                <span>+ Glue Pull (25%)</span>
                                <span>+${(panel.matrix_base_price * 0.25).toFixed(0)}</span>
                              </div>
                            )}
                            {panel.is_tall_roof && (
                              <div className="flex justify-between text-emerald-700">
                                <span>+ Tall Roof (25%)</span>
                                <span>+${(panel.matrix_base_price * 0.25).toFixed(0)}</span>
                              </div>
                            )}
                            {panel.oversized_count > 0 && (
                              <div className="flex justify-between text-orange-700">
                                <span>+ Oversized ({panel.oversized_count} @ $50)</span>
                                <span>+${(panel.oversized_count * 50).toFixed(0)}</span>
                              </div>
                            )}
                            <Separator className="my-1" />
                            <div className="flex justify-between font-bold">
                              <span>Panel Total</span>
                              <span className="text-emerald-600">${panel.panel_total.toFixed(0)}</span>
                            </div>
                          </div>
                        )}

                        {/* R&I Items */}
                        {panel.ri_items && panel.ri_items.length > 0 && (
                          <div>
                            <p className="text-xs text-muted-foreground mb-2 font-medium">
                              R&I Operations ({panel.ri_items.length})
                            </p>
                            <div className="space-y-2">
                              {panel.ri_items.map((ri, idx) => (
                                <div
                                  key={ri.id || idx}
                                  className="p-2 bg-slate-100 rounded-lg"
                                >
                                  <div className="flex justify-between">
                                    <span className="font-medium text-sm">
                                      {ri.item_name}
                                    </span>
                                    <span className="font-medium">
                                      ${ri.price.toFixed(0)}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                                    <Clock className="h-3 w-3" />
                                    <span>{ri.time_hours.toFixed(2)} hrs</span>
                                    {ri.operation_code && (
                                      <>
                                        <span className="text-slate-300">|</span>
                                        <span className="font-mono">{ri.operation_code}</span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Matrix Dialog */}
      <Dialog open={showMatrixDialog} onOpenChange={setShowMatrixDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              Insurance Matrix Format
            </DialogTitle>
          </DialogHeader>

          {/* Header Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-100 rounded-lg mb-4">
            <div>
              <p className="text-xs text-muted-foreground">Estimate #</p>
              <p className="font-medium">{estimate.estimate_number}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Vehicle</p>
              <p className="font-medium">
                {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Matrix</p>
              <p className="font-medium">{estimate.matrix_profile_name || 'Default'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Date</p>
              <p className="font-medium">{new Date(estimate.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          {/* Matrix Table */}
          <div className="overflow-x-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead className="font-bold">Panel</TableHead>
                  <TableHead className="text-center">Dents</TableHead>
                  <TableHead className="text-center">Size</TableHead>
                  <TableHead className="text-center">O/S</TableHead>
                  <TableHead className="text-center">Mods</TableHead>
                  <TableHead className="text-center">Base</TableHead>
                  <TableHead className="text-right font-bold">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {estimate.panels?.map(panel => (
                  <TableRow
                    key={panel.id}
                    className={panel.is_conventional_repair ? 'bg-red-50' : ''}
                  >
                    <TableCell className="font-medium">
                      {PANEL_NAMES[panel.panel_name] || panel.panel_name}
                      {panel.is_conventional_repair && (
                        <Badge variant="destructive" className="ml-2 text-xs">CR</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-center">{panel.total_dent_count}</TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline" className="text-xs">
                        {SIZE_LABELS[panel.majority_size]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      {panel.oversized_count || '-'}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex flex-wrap justify-center gap-1">
                        {panel.is_aluminum && <Badge className="text-[10px] bg-amber-100 text-amber-700">AL</Badge>}
                        {panel.is_hss && <Badge className="text-[10px] bg-blue-100 text-blue-700">HSS</Badge>}
                        {panel.requires_glue_pull && <Badge className="text-[10px] bg-purple-100 text-purple-700">GP</Badge>}
                        {panel.is_tall_roof && <Badge className="text-[10px] bg-emerald-100 text-emerald-700">TR</Badge>}
                        {!panel.is_aluminum && !panel.is_hss && !panel.requires_glue_pull && !panel.is_tall_roof && '-'}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">${panel.matrix_base_price.toFixed(0)}</TableCell>
                    <TableCell className="text-right font-bold">${panel.panel_total.toFixed(0)}</TableCell>
                  </TableRow>
                ))}
                {/* Totals Row */}
                <TableRow className="bg-slate-100 font-bold">
                  <TableCell>PDR LABOR TOTAL</TableCell>
                  <TableCell className="text-center">{stats.totalDents}</TableCell>
                  <TableCell colSpan={4}></TableCell>
                  <TableCell className="text-right text-emerald-600">
                    ${stats.laborTotal.toFixed(0)}
                  </TableCell>
                </TableRow>
                {stats.riTotal > 0 && (
                  <TableRow className="font-bold">
                    <TableCell>R&I OPERATIONS</TableCell>
                    <TableCell colSpan={5}></TableCell>
                    <TableCell className="text-right">
                      ${stats.riTotal.toFixed(0)}
                    </TableCell>
                  </TableRow>
                )}
                <TableRow className="bg-emerald-100 font-bold text-lg">
                  <TableCell>GRAND TOTAL</TableCell>
                  <TableCell colSpan={5}></TableCell>
                  <TableCell className="text-right text-emerald-700">
                    ${grandTotal.toFixed(0)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground mt-4">
            <span><strong>AL</strong> = Aluminum (+25%)</span>
            <span><strong>HSS</strong> = High Strength Steel (+25%)</span>
            <span><strong>GP</strong> = Glue Pull (+25%)</span>
            <span><strong>TR</strong> = Tall Roof (+25%)</span>
            <span><strong>O/S</strong> = Oversized ($50/dent)</span>
            <span><strong>CR</strong> = Conventional Repair Required</span>
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowMatrixDialog(false)}>
              Close
            </Button>
            <Button>
              <Download className="h-4 w-4 mr-2" />
              Export to Excel
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Parts Suggestions Modal (Stage 5R) */}
      <Dialog open={showPartsSuggestionsModal} onOpenChange={setShowPartsSuggestionsModal}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-amber-600" />
              Parts Suggestions
            </DialogTitle>
          </DialogHeader>

          {isLoadingSuggestions ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              {/* Stats summary */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-slate-100 rounded-lg mb-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-slate-700">
                    {partsSuggestionsData?.stats?.total_suggestions || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Total Found</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-amber-600">
                    {partsSuggestionsData?.stats?.new_suggestions || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">New</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-slate-400">
                    {partsSuggestionsData?.stats?.duplicates || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Already Exist</p>
                </div>
              </div>

              {/* Suggestions list */}
              {partsSuggestionsData?.suggestions && partsSuggestionsData.suggestions.length > 0 ? (
                <div className="space-y-2">
                  {/* Select all toggle */}
                  <div className="flex items-center justify-between pb-2 border-b">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id="select-all"
                        checked={selectedSuggestions.size === partsSuggestionsData.new_suggestions?.length}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            const newSet = new Set<number>()
                            partsSuggestionsData.suggestions.forEach((s: PartsSuggestion, i: number) => {
                              if (!s.already_exists) newSet.add(i)
                            })
                            setSelectedSuggestions(newSet)
                          } else {
                            setSelectedSuggestions(new Set())
                          }
                        }}
                      />
                      <Label htmlFor="select-all" className="text-sm font-medium">
                        Select all new ({partsSuggestionsData.stats?.new_suggestions || 0})
                      </Label>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {selectedSuggestions.size} selected
                    </Badge>
                  </div>

                  {/* Individual suggestions */}
                  {partsSuggestionsData.suggestions.map((suggestion: PartsSuggestion, index: number) => (
                    <div
                      key={index}
                      className={cn(
                        "flex items-start gap-3 p-3 rounded-lg border",
                        suggestion.already_exists
                          ? "bg-slate-50 opacity-60"
                          : selectedSuggestions.has(index)
                            ? "bg-amber-50 border-amber-300"
                            : "bg-white hover:bg-slate-50"
                      )}
                    >
                      <Checkbox
                        checked={selectedSuggestions.has(index)}
                        onCheckedChange={(checked) => {
                          const newSet = new Set(selectedSuggestions)
                          if (checked) {
                            newSet.add(index)
                          } else {
                            newSet.delete(index)
                          }
                          setSelectedSuggestions(newSet)
                        }}
                        disabled={suggestion.already_exists}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{suggestion.description}</span>
                          {suggestion.already_exists && (
                            <Badge variant="outline" className="text-xs bg-slate-100">
                              <Check className="h-3 w-3 mr-1" />
                              Exists
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{suggestion.reason}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {suggestion.source_type === 'panel_ri' && 'R&I Operation'}
                            {suggestion.source_type === 'supplement' && 'Supplement'}
                            {suggestion.source_type === 'panel_cr' && 'Conv. Repair'}
                          </Badge>
                          {suggestion.part_number && (
                            <span className="text-xs text-muted-foreground font-mono">
                              #{suggestion.part_number}
                            </span>
                          )}
                          {suggestion.qty > 1 && (
                            <span className="text-xs text-muted-foreground">
                              Qty: {suggestion.qty}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No parts suggestions found</p>
                  <p className="text-sm mt-1">This estimate doesn't have R&I operations or supplements that typically require parts.</p>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
                <Button variant="outline" onClick={() => setShowPartsSuggestionsModal(false)}>
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
                <Button
                  onClick={async () => {
                    if (!estimateId || selectedSuggestions.size === 0) return
                    try {
                      await createPartsRequests.mutateAsync({
                        estimateId,
                        selectedIndices: Array.from(selectedSuggestions),
                        skipDuplicates: true,
                      })
                      refetchPartsRequests()
                      refetchSuggestions()
                      setShowPartsSuggestionsModal(false)
                      setSelectedSuggestions(new Set())
                    } catch {
                      // Error handled by mutation
                    }
                  }}
                  disabled={selectedSuggestions.size === 0 || createPartsRequests.isPending}
                  className="bg-amber-600 hover:bg-amber-700"
                >
                  {createPartsRequests.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Create {selectedSuggestions.size} Request{selectedSuggestions.size !== 1 ? 's' : ''}
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default EstimateReview
