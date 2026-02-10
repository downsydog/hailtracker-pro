import { Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  Users,
  DollarSign,
  FileText,
  Plus,
  UserPlus,
  Wrench,
  AlertCircle,
  Clock,
  CheckCircle,
  Phone,
  Send,
  ArrowRight,
  PlayCircle,
  ChevronRight,
  Building2,
  Truck,
  MapPin,
  RefreshCw,
  Calendar,
  XCircle,
  Filter,
  AlertTriangle,
  Wand2,
  Loader2,
  Sparkles,
  Package,
  ClockAlert,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { useOpsOverview, NeedsAttentionItem, DispatchInboxItem, DispatchSuggestion, PartsInfo, PARTS_STATUS_OPTIONS, PartRequestItem, PartsPricingPreview, PartsRequestAttentionItem } from '@/hooks/use-ops'
import { useAuth } from '@/contexts/auth-context'
import { useUpdateJobStatus, useAssignJob, useUpdateJob, useClearJobBlocker, useUpdateJobBlocker, useUpdatePartRequest, useApprovePartRequest, useUnapprovePartRequest, useBulkApprovePartRequests, useUpdatePartRequestStatus } from '@/hooks/use-jobs'
import { useIssueInvoice } from '@/hooks/use-invoices'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const quickActions = [
  { label: 'New Estimate', href: '/estimates/new', icon: FileText, color: 'text-blue-600 bg-blue-100' },
  { label: 'New Lead', href: '/leads/new', icon: UserPlus, color: 'text-green-600 bg-green-100' },
  { label: 'New Job', href: '/jobs/new', icon: Wrench, color: 'text-purple-600 bg-purple-100' },
  { label: 'New Customer', href: '/customers/new', icon: Users, color: 'text-orange-600 bg-orange-100' },
]

function formatCurrency(amount: number | undefined | null): string {
  if (amount == null) return '$0'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatRelativeTime(date: Date | null): string {
  if (!date) return ''
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getItemTypeIcon(type: string) {
  switch (type) {
    case 'estimate':
      return <FileText className="h-4 w-4 text-blue-500" />
    case 'job':
      return <Wrench className="h-4 w-4 text-purple-500" />
    case 'invoice':
      return <DollarSign className="h-4 w-4 text-green-500" />
    case 'lead':
      return <Users className="h-4 w-4 text-orange-500" />
    default:
      return <FileText className="h-4 w-4" />
  }
}

/**
 * Stage 5P: Parts Status Badge component
 */
function PartsStatusBadge({ status }: { status: string }) {
  const option = PARTS_STATUS_OPTIONS.find(o => o.value === status) || PARTS_STATUS_OPTIONS[0]
  return (
    <Badge className={`${option.color} text-xs`}>
      {option.label}
    </Badge>
  )
}

/**
 * Stage 5S: Pricing confidence badge
 */
function PricingConfidenceBadge({ confidence }: { confidence: 'high' | 'medium' | 'low' }) {
  const styles = {
    high: 'bg-green-100 text-green-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-gray-100 text-gray-500',
  }
  return (
    <Badge className={`${styles[confidence]} text-xs`}>
      {confidence}
    </Badge>
  )
}

/**
 * Stage 5S: Format price range for display
 */
function formatPriceRange(preview?: PartsPricingPreview | null): string {
  if (!preview) return '—'

  const { low_estimate, typical_estimate, high_estimate } = preview

  // If we have both low and high, show range
  if (low_estimate != null && high_estimate != null && low_estimate !== high_estimate) {
    return `$${Math.round(low_estimate)} – $${Math.round(high_estimate)}`
  }

  // If we only have typical, show with ~
  if (typical_estimate != null) {
    return `~$${Math.round(typical_estimate)}`
  }

  return '—'
}

/**
 * Shared blocker parts summary renderer (Stage 5O.1, extended 5P)
 *
 * Displays parts info consistently across dashboard components:
 * - Parts status badge (Stage 5P)
 * - Ordered badge (green)
 * - ETA with overdue warning (red if past)
 * - Vendor name
 */
function renderBlockerPartsSummary(
  blockerInfo: { issue_type: string; parts?: PartsInfo | null } | null | undefined,
  options: { compact?: boolean } = {}
) {
  if (!blockerInfo) return null

  const { issue_type, parts } = blockerInfo
  if (issue_type !== 'waiting_on_parts' || !parts) return null

  // Check if ETA is overdue
  const isEtaOverdue = () => {
    if (!parts.eta) return false
    try {
      const etaDate = new Date(parts.eta)
      return etaDate < new Date()
    } catch {
      return false
    }
  }

  const etaOverdue = isEtaOverdue()
  const { compact = false } = options

  return (
    <div className={`text-[10px] ${compact ? 'flex gap-2 items-center' : 'space-y-0.5'}`}>
      {/* Stage 5P: Show parts status */}
      {parts.parts_status && parts.parts_status !== 'needed' && (
        <PartsStatusBadge status={parts.parts_status} />
      )}
      {parts.ordered && !parts.parts_status && (
        <span className="inline-flex items-center gap-0.5 text-green-600">
          <Package className="h-2.5 w-2.5" />
          Ordered
        </span>
      )}
      {parts.eta && (
        <span className={`inline-flex items-center gap-0.5 ${etaOverdue ? 'text-red-600 font-medium' : 'text-muted-foreground'}`}>
          {etaOverdue && <ClockAlert className="h-2.5 w-2.5" />}
          ETA: {parts.eta.split('T')[0]}
        </span>
      )}
      {parts.vendor && !compact && (
        <span className="text-muted-foreground block truncate max-w-[100px]">
          {parts.vendor}
        </span>
      )}
    </div>
  )
}

/**
 * Stage 5U: Format parts request timeline for tooltip display.
 */
function formatPartRequestTimeline(req: PartRequestItem): string[] {
  const lines: string[] = []

  if (req.created_at) {
    lines.push(`Created: ${new Date(req.created_at).toLocaleDateString()}`)
  }
  if (req.approved_at) {
    lines.push(`Approved: ${new Date(req.approved_at).toLocaleDateString()}`)
  }
  if (req.ordered_at) {
    lines.push(`Ordered: ${new Date(req.ordered_at).toLocaleDateString()}`)
  }
  if (req.shipped_at) {
    lines.push(`Shipped: ${new Date(req.shipped_at).toLocaleDateString()}`)
  }
  if (req.received_at) {
    lines.push(`Received: ${new Date(req.received_at).toLocaleDateString()}`)
  }
  if (req.installed_at) {
    lines.push(`Installed: ${new Date(req.installed_at).toLocaleDateString()}`)
  }
  if (req.status_updated_at && lines.length === 0) {
    lines.push(`Updated: ${new Date(req.status_updated_at).toLocaleDateString()}`)
  }

  return lines
}

function getStatusBadge(item: NeedsAttentionItem) {
  if (item.type === 'estimate') {
    const status = item.insurer_status || item.customer_status || 'draft'
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      pending_signature: 'bg-yellow-100 text-yellow-800',
      authorized: 'bg-green-100 text-green-800',
      submitted: 'bg-blue-100 text-blue-800',
      approved: 'bg-green-100 text-green-800',
      needs_revision: 'bg-orange-100 text-orange-800',
      declined: 'bg-red-100 text-red-800',
    }
    return <Badge className={colors[status] || 'bg-gray-100'}>{status.replace('_', ' ')}</Badge>
  }

  if (item.type === 'job') {
    // Show blocked indicator if job is blocked
    if (item.is_blocked) {
      return (
        <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          Blocked
        </Badge>
      )
    }
    const colors: Record<string, string> = {
      scheduled: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
    }
    return <Badge className={colors[item.status || ''] || 'bg-gray-100'}>{item.status?.replace('_', ' ')}</Badge>
  }

  if (item.type === 'invoice') {
    if (item.is_overdue) {
      return <Badge className="bg-red-100 text-red-800">Overdue</Badge>
    }
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-800',
      issued: 'bg-blue-100 text-blue-800',
      partial_paid: 'bg-yellow-100 text-yellow-800',
      paid: 'bg-green-100 text-green-800',
    }
    return <Badge className={colors[item.status || ''] || 'bg-gray-100'}>{item.status?.replace('_', ' ')}</Badge>
  }

  return null
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data, isLoading, error, lastUpdated, isFetching } = useOpsOverview()

  // Force re-render every 10s to update relative time display
  const [, setTick] = useState(0)
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 10000)
    return () => clearInterval(interval)
  }, [])

  // Mutations for quick actions
  const updateJobStatus = useUpdateJobStatus()
  const issueInvoice = useIssueInvoice()
  const assignJob = useAssignJob()
  const updateJob = useUpdateJob()
  const clearJobBlocker = useClearJobBlocker()
  const updateJobBlocker = useUpdateJobBlocker()
  const updatePartRequest = useUpdatePartRequest()
  // Stage 5T: Parts approval mutations
  const approvePartRequest = useApprovePartRequest()
  const unapprovePartRequest = useUnapprovePartRequest()
  const bulkApprovePartRequests = useBulkApprovePartRequests()
  // Stage 5U: Parts status transitions
  const updatePartRequestStatus = useUpdatePartRequestStatus()

  // Stage 5T: Bulk selection state for parts requests
  const [selectedPartRequests, setSelectedPartRequests] = useState<Set<number>>(new Set())

  // Dispatch filter state
  const [jobFilter, setJobFilter] = useState<'all' | 'unassigned'>('all')
  // Dispatch inbox tech filter (null = all techs)
  const [dispatchTechFilter, setDispatchTechFilter] = useState<number | null>(null)
  // Show only jobs with suggestions toggle
  const [showOnlyWithSuggestions, setShowOnlyWithSuggestions] = useState(false)
  // Auto-assign progress state
  const [autoAssignProgress, setAutoAssignProgress] = useState<{
    isRunning: boolean
    current: number
    total: number
    results: Array<{ jobId: number; success: boolean; error?: string }>
  } | null>(null)

  // Update ETA modal state (Stage 5O, extended 5P)
  const [etaModalOpen, setEtaModalOpen] = useState(false)
  const [etaJobId, setEtaJobId] = useState<number | null>(null)
  const [etaPartsOrdered, setEtaPartsOrdered] = useState(false)
  const [etaVendor, setEtaVendor] = useState('')
  const [etaPoNumber, setEtaPoNumber] = useState('')
  const [etaValue, setEtaValue] = useState('')
  const [etaNotes, setEtaNotes] = useState('')
  // Stage 5P: Parts status and approval fields
  const [etaPartsStatus, setEtaPartsStatus] = useState<string>('needed')
  const [etaApprovedToOrder, setEtaApprovedToOrder] = useState(false)
  const [etaApprovedAmount, setEtaApprovedAmount] = useState<string>('')

  // Open Update ETA modal with existing parts info
  const openEtaModal = (jobId: number, existingParts?: PartsInfo | null) => {
    setEtaJobId(jobId)
    setEtaPartsOrdered(existingParts?.ordered || false)
    setEtaVendor(existingParts?.vendor || '')
    setEtaPoNumber(existingParts?.po_number || '')
    setEtaValue(existingParts?.eta?.split('T')[0] || '')
    setEtaNotes('')
    // Stage 5P fields
    setEtaPartsStatus(existingParts?.parts_status || 'needed')
    setEtaApprovedToOrder(existingParts?.approved_to_order || false)
    setEtaApprovedAmount(existingParts?.approved_amount?.toString() || '')
    setEtaModalOpen(true)
  }

  // Submit ETA update (Stage 5P extended)
  const handleUpdateEta = async () => {
    if (!etaJobId) return
    await updateJobBlocker.mutateAsync({
      id: etaJobId,
      data: {
        partsOrdered: etaPartsOrdered,
        vendor: etaVendor,
        poNumber: etaPoNumber,
        eta: etaValue,
        notes: etaNotes,
        // Stage 5P fields
        partsStatus: etaPartsStatus,
        approvedToOrder: etaApprovedToOrder,
        approvedAmount: etaApprovedAmount ? parseFloat(etaApprovedAmount) : undefined,
      },
    })
    setEtaModalOpen(false)
    setEtaJobId(null)
  }

  // Stage 5Q: Parts view toggle (blockers vs requests)
  const [partsViewMode, setPartsViewMode] = useState<'blockers' | 'requests'>('blockers')

  // Stage 5V: Attention filter for parts requests
  const [showPartsAttention, setShowPartsAttention] = useState(false)

  // Stage 5Q: Part request edit modal state
  const [partRequestModalOpen, setPartRequestModalOpen] = useState(false)
  const [editingPartRequest, setEditingPartRequest] = useState<PartRequestItem | null>(null)
  const [prDescription, setPrDescription] = useState('')
  const [prPartNumber, setPrPartNumber] = useState('')
  const [prQty, setPrQty] = useState('1')
  const [prStatus, setPrStatus] = useState('needed')
  const [prVendor, setPrVendor] = useState('')
  const [prPoNumber, setPrPoNumber] = useState('')
  const [prEta, setPrEta] = useState('')
  const [prApprovedToOrder, setPrApprovedToOrder] = useState(false)
  const [prApprovedAmount, setPrApprovedAmount] = useState('')
  const [prNotes, setPrNotes] = useState('')

  // Open part request edit modal
  const openPartRequestModal = (req: PartRequestItem) => {
    setEditingPartRequest(req)
    setPrDescription(req.description)
    setPrPartNumber(req.part_number || '')
    setPrQty(req.qty?.toString() || '1')
    setPrStatus(req.parts_status || 'needed')
    setPrVendor(req.vendor || '')
    setPrPoNumber(req.po_number || '')
    setPrEta(req.eta?.split('T')[0] || '')
    setPrApprovedToOrder(req.approved_to_order || false)
    setPrApprovedAmount(req.approved_amount?.toString() || '')
    setPrNotes(req.notes || '')
    setPartRequestModalOpen(true)
  }

  // Submit part request update
  const handleUpdatePartRequest = async () => {
    if (!editingPartRequest) return
    await updatePartRequest.mutateAsync({
      id: editingPartRequest.id,
      data: {
        description: prDescription,
        partNumber: prPartNumber || undefined,
        qty: parseInt(prQty) || 1,
        partsStatus: prStatus,
        vendor: prVendor || undefined,
        poNumber: prPoNumber || undefined,
        eta: prEta || undefined,
        approvedToOrder: prApprovedToOrder,
        approvedAmount: prApprovedAmount ? parseFloat(prApprovedAmount) : undefined,
        notes: prNotes || undefined,
      },
    })
    setPartRequestModalOpen(false)
    setEditingPartRequest(null)
  }

  // Check if user has ops access (owner, manager, desk)
  const hasOpsAccess = user?.role && ['owner', 'manager', 'desk', 'admin'].includes(user.role)

  // Build suggestion lookup map for quick access
  const suggestionsByJobId = new Map<number, DispatchSuggestion>()
  data?.dispatch_suggestions?.forEach(s => {
    suggestionsByJobId.set(s.job_id, s)
  })

  // Auto-assign all unassigned jobs with suggestions
  const handleAutoAssignAll = async () => {
    if (!data?.dispatch_suggestions) return

    // Filter to unassigned jobs with valid suggestions
    const toAssign = data.dispatch_suggestions.filter(
      s => s.suggested_tech_id !== null &&
           !data.dispatch_inbox.find(j => j.id === s.job_id)?.assigned_tech
    ).slice(0, 10) // Max 10 per click

    if (toAssign.length === 0) return

    setAutoAssignProgress({
      isRunning: true,
      current: 0,
      total: toAssign.length,
      results: [],
    })

    const results: Array<{ jobId: number; success: boolean; error?: string }> = []

    for (let i = 0; i < toAssign.length; i++) {
      const suggestion = toAssign[i]
      setAutoAssignProgress(prev => prev ? { ...prev, current: i + 1 } : null)

      try {
        await assignJob.mutateAsync({
          id: suggestion.job_id,
          techId: suggestion.suggested_tech_id!
        })
        results.push({ jobId: suggestion.job_id, success: true })
      } catch (err) {
        results.push({
          jobId: suggestion.job_id,
          success: false,
          error: err instanceof Error ? err.message : 'Failed'
        })
      }
    }

    setAutoAssignProgress(prev => prev ? { ...prev, isRunning: false, results } : null)

    // Clear after 3 seconds
    setTimeout(() => setAutoAssignProgress(null), 3000)
  }

  const handleQuickAction = async (item: NeedsAttentionItem) => {
    if (!item.primary_action) return

    const action = item.primary_action.key

    if (item.type === 'job' && action === 'start_job') {
      await updateJobStatus.mutateAsync({ id: item.id, status: 'in_progress' })
    } else if (item.type === 'job' && action === 'complete_job') {
      await updateJobStatus.mutateAsync({ id: item.id, status: 'completed' })
    } else if (item.type === 'invoice' && action === 'issue_invoice') {
      await issueInvoice.mutateAsync(item.id)
    } else {
      // Navigate to detail page for other actions
      navigateToItem(item)
    }
  }

  const navigateToItem = (item: NeedsAttentionItem) => {
    switch (item.type) {
      case 'estimate':
        navigate(`/estimates/${item.id}/review`)
        break
      case 'job':
        navigate(`/jobs/${item.id}`)
        break
      case 'invoice':
        navigate(`/invoices/${item.id}`)
        break
      case 'lead':
        navigate(`/leads/${item.id}`)
        break
    }
  }

  // If not ops role, show simple dashboard
  if (!hasOpsAccess) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">Welcome back, {user?.name || 'User'}!</p>
          </div>
          <Button asChild>
            <Link to="/estimates/new">
              <Plus className="h-4 w-4 mr-2" />
              New Estimate
            </Link>
          </Button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.label}
                to={action.href}
                className="flex flex-col items-center gap-2 p-4 bg-card rounded-lg border hover:bg-accent transition-colors"
              >
                <div className={`p-3 rounded-full ${action.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <span className="text-sm font-medium">{action.label}</span>
              </Link>
            )
          })}
        </div>
      </div>
    )
  }

  // Ops Command Center for owner/manager/desk
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">Ops Command Center</h1>
            {lastUpdated && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                {isFetching ? (
                  <RefreshCw className="h-3 w-3 animate-spin" />
                ) : (
                  <Clock className="h-3 w-3" />
                )}
                Updated {formatRelativeTime(lastUpdated)}
              </span>
            )}
          </div>
          <p className="text-muted-foreground">Real-time operational overview</p>
        </div>
        <div className="flex items-center gap-2">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Button key={action.label} variant="outline" size="sm" asChild>
                <Link to={action.href}>
                  <Icon className="h-4 w-4 mr-1" />
                  {action.label}
                </Link>
              </Button>
            )
          })}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-4">
            <p className="text-red-800">Failed to load ops data. Please refresh the page.</p>
          </CardContent>
        </Card>
      )}

      {/* Office Board - Quick Glance Panels */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Panel 1: Active Work (In Progress Jobs by Tech) */}
        <Card className="border-amber-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <PlayCircle className="h-4 w-4 text-amber-500" />
              Active Work
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (() => {
              const inProgressJobs = data?.needs_attention.filter(
                (i) => i.type === 'job' && i.status === 'in_progress'
              ) || []
              // Group by tech
              const byTech = inProgressJobs.reduce((acc, job) => {
                const tech = job.tech_name || 'Unassigned'
                if (!acc[tech]) acc[tech] = []
                acc[tech].push(job)
                return acc
              }, {} as Record<string, typeof inProgressJobs>)

              if (Object.keys(byTech).length === 0) {
                return <p className="text-sm text-muted-foreground text-center py-2">No active jobs</p>
              }
              return Object.entries(byTech).map(([tech, jobs]) => (
                <div key={tech} className="text-sm">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{tech}</span>
                    <Badge variant="secondary">{jobs.length}</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {jobs.slice(0, 2).map(j => j.identifier).join(', ')}
                    {jobs.length > 2 && ` +${jobs.length - 2} more`}
                  </div>
                </div>
              ))
            })()}
          </CardContent>
        </Card>

        {/* Panel 2: Waiting on Insurance */}
        <Card className="border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Building2 className="h-4 w-4 text-blue-500" />
              Insurance Queue
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (() => {
              const submitted = data?.bottlenecks?.filter(b => b.insurer_status === 'submitted') || []
              const needsRevision = data?.bottlenecks?.filter(b => b.insurer_status === 'needs_revision') || []
              return (
                <>
                  <div className="flex justify-between items-center text-sm">
                    <span>Submitted</span>
                    <span className="font-medium">{submitted.length}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-amber-600">Needs Revision</span>
                    <span className="font-medium text-amber-600">{needsRevision.length}</span>
                  </div>
                  {submitted.length + needsRevision.length > 0 && (
                    <div className="text-xs text-muted-foreground pt-1">
                      {formatCurrency(
                        [...submitted, ...needsRevision].reduce((sum, b) => sum + (b.total_price || 0), 0)
                      )} pending
                    </div>
                  )}
                </>
              )
            })()}
          </CardContent>
        </Card>

        {/* Panel 3: Money Risk */}
        <Card className={data?.invoice_stats.overdue ? 'border-red-200' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <DollarSign className={`h-4 w-4 ${data?.invoice_stats.overdue ? 'text-red-500' : 'text-green-500'}`} />
              Money Risk
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <>
                {data?.invoice_stats.overdue ? (
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-red-600">Overdue</span>
                    <span className="font-medium text-red-600">
                      {data.invoice_stats.overdue} ({formatCurrency(data.invoice_stats.overdue_total)})
                    </span>
                  </div>
                ) : null}
                <div className="flex justify-between items-center text-sm">
                  <span>Partial Paid</span>
                  <span className="font-medium">
                    {data?.invoice_stats.partial_paid || 0} ({formatCurrency(data?.invoice_stats.partial_balance)})
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span>Issued</span>
                  <span className="font-medium">
                    {data?.invoice_stats.issued || 0} ({formatCurrency(data?.invoice_stats.issued_balance)})
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Panel 4: Follow-ups */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Phone className="h-4 w-4 text-orange-500" />
              Follow-ups
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <div className="space-y-1">
                <div className="flex justify-between items-center text-sm">
                  <span>Leads to call</span>
                  <span className="font-medium">{data?.leads_needing_followup?.length || 0}</span>
                </div>
                {data?.leads_needing_followup?.slice(0, 2).map((lead) => (
                  <div key={lead.id} className="text-xs text-muted-foreground truncate">
                    {lead.business_name || lead.contact_name}
                  </div>
                ))}
                {(data?.leads_needing_followup?.length || 0) > 2 && (
                  <div className="text-xs text-blue-600">
                    +{(data?.leads_needing_followup?.length || 0) - 2} more
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Scheduled Jobs</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{data?.job_stats.scheduled || 0}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <PlayCircle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{data?.job_stats.in_progress || 0}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Draft Invoices</CardTitle>
            <FileText className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className="text-2xl font-bold">{data?.invoice_stats.draft || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {formatCurrency(data?.invoice_stats.draft_total)} pending
                </p>
              </>
            )}
          </CardContent>
        </Card>
        <Card className={data?.invoice_stats.overdue ? 'border-red-200 bg-red-50' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertCircle className={`h-4 w-4 ${data?.invoice_stats.overdue ? 'text-red-500' : 'text-gray-400'}`} />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <div className={`text-2xl font-bold ${data?.invoice_stats.overdue ? 'text-red-600' : ''}`}>
                  {data?.invoice_stats.overdue || 0}
                </div>
                {data?.invoice_stats.overdue_total ? (
                  <p className="text-xs text-red-600">
                    {formatCurrency(data.invoice_stats.overdue_total)} outstanding
                  </p>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Content - Tabs */}
      <Tabs defaultValue="attention" className="space-y-4">
        <TabsList>
          <TabsTrigger value="attention" className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Needs Attention
            {data?.needs_attention?.length ? (
              <Badge variant="secondary" className="ml-1">{data.needs_attention.length}</Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="dispatch" className="flex items-center gap-2">
            <Send className="h-4 w-4" />
            Dispatch
            {data?.dispatch_inbox?.length ? (
              <Badge variant="secondary" className="ml-1 bg-amber-100 text-amber-700">{data.dispatch_inbox.length}</Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="jobs" className="flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            Job Board
          </TabsTrigger>
          <TabsTrigger value="bottlenecks" className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Insurance
            {data?.bottlenecks?.length ? (
              <Badge variant="secondary" className="ml-1">{data.bottlenecks.length}</Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="money" className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Money
          </TabsTrigger>
          <TabsTrigger value="followup" className="flex items-center gap-2">
            <Phone className="h-4 w-4" />
            Follow-up
            {data?.leads_needing_followup?.length ? (
              <Badge variant="secondary" className="ml-1">{data.leads_needing_followup.length}</Badge>
            ) : null}
          </TabsTrigger>
          {/* Stage 5P: Parts Control Tower tab */}
          <TabsTrigger value="parts" className="flex items-center gap-2">
            <Package className="h-4 w-4" />
            Parts
            {data?.dispatch_inbox?.filter(j => j.is_blocked && j.blocker_info?.issue_type === 'waiting_on_parts').length ? (
              <Badge variant="secondary" className="ml-1">
                {data.dispatch_inbox.filter(j => j.is_blocked && j.blocker_info?.issue_type === 'waiting_on_parts').length}
              </Badge>
            ) : null}
          </TabsTrigger>
        </TabsList>

        {/* 1. NEEDS ATTENTION TAB */}
        <TabsContent value="attention">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Items Requiring Action</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : !data?.needs_attention?.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                  <p>All caught up! No items need attention.</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">Type</TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Customer / Vehicle</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                      <TableHead>Next Action</TableHead>
                      <TableHead className="w-[100px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.needs_attention.map((item) => (
                      <TableRow
                        key={`${item.type}-${item.id}`}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => navigateToItem(item)}
                      >
                        <TableCell>{getItemTypeIcon(item.type)}</TableCell>
                        <TableCell className="font-medium">{item.identifier}</TableCell>
                        <TableCell>
                          {item.priority_reason && (
                            <span className={`text-xs ${(item.priority_score || 0) >= 70 ? 'text-red-600 font-medium' : (item.priority_score || 0) >= 55 ? 'text-amber-600' : 'text-muted-foreground'}`}>
                              {item.priority_reason}
                            </span>
                          )}
                        </TableCell>
                        <TableCell>{getStatusBadge(item)}</TableCell>
                        <TableCell>
                          <div>
                            <p className="font-medium">{item.customer_name || item.payer_name || '—'}</p>
                            {item.vehicle_display && (
                              <p className="text-sm text-muted-foreground">{item.vehicle_display}</p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(item.total_price || item.total_amount || item.total)}
                        </TableCell>
                        <TableCell>
                          {item.primary_action && (
                            <Badge variant="outline" className="flex items-center gap-1 w-fit">
                              <ArrowRight className="h-3 w-3" />
                              {item.primary_action.label}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          {item.primary_action && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleQuickAction(item)}
                              disabled={updateJobStatus.isPending || issueInvoice.isPending}
                            >
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 2. DISPATCH INBOX TAB */}
        <TabsContent value="dispatch">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* Tech Load Sidebar */}
            <Card className="lg:col-span-1">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4 text-purple-500" />
                  Tech Load
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {isLoading ? (
                  <Skeleton className="h-20 w-full" />
                ) : !data?.tech_load?.length ? (
                  <p className="text-sm text-muted-foreground text-center py-4">No technicians</p>
                ) : (
                  <>
                    {/* All techs button */}
                    <button
                      className={`w-full p-2 rounded-lg text-left text-sm transition-colors ${
                        dispatchTechFilter === null
                          ? 'bg-purple-100 border-purple-300 border'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => setDispatchTechFilter(null)}
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium">All Techs</span>
                        <Badge variant="secondary">{data.dispatch_inbox?.length || 0}</Badge>
                      </div>
                    </button>
                    {data.tech_load.map((tech) => (
                      <button
                        key={tech.tech_id}
                        className={`w-full p-2 rounded-lg text-left text-sm transition-colors ${
                          dispatchTechFilter === tech.tech_id
                            ? 'bg-purple-100 border-purple-300 border'
                            : 'hover:bg-muted'
                        }`}
                        onClick={() => setDispatchTechFilter(tech.tech_id)}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-medium truncate">{tech.tech_name}</span>
                          <div className="flex items-center gap-1">
                            {/* Location badge from last check-in */}
                            {tech.last_checkin?.location && (
                              <Badge
                                variant="outline"
                                className={`h-5 px-1.5 text-[10px] ${
                                  tech.last_checkin.location === 'shop'
                                    ? 'border-blue-300 text-blue-600'
                                    : 'border-green-300 text-green-600'
                                }`}
                                title={`Last check-in: ${tech.last_checkin.job_number} at ${new Date(tech.last_checkin.at).toLocaleTimeString()}`}
                              >
                                {tech.last_checkin.location === 'shop' ? (
                                  <Building2 className="h-2.5 w-2.5 mr-0.5" />
                                ) : (
                                  <Truck className="h-2.5 w-2.5 mr-0.5" />
                                )}
                                {tech.last_checkin.location === 'shop' ? 'Shop' : 'Field'}
                              </Badge>
                            )}
                            <Badge variant="secondary">{tech.total_assigned}</Badge>
                          </div>
                        </div>
                        <div className="flex gap-2 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {tech.scheduled_today} today
                          </span>
                          <span className="flex items-center gap-1">
                            <PlayCircle className="h-3 w-3" />
                            {tech.in_progress}
                          </span>
                          {tech.blocked > 0 && (
                            <span className="flex items-center gap-1 text-red-600">
                              <AlertTriangle className="h-3 w-3" />
                              {tech.blocked}
                            </span>
                          )}
                        </div>
                        {/* Current job indicator if in progress */}
                        {tech.in_progress_job && (
                          <div className="mt-1 text-[10px] text-amber-600 flex items-center gap-1">
                            <MapPin className="h-2.5 w-2.5" />
                            Working on {tech.in_progress_job.job_number}
                          </div>
                        )}
                      </button>
                    ))}
                  </>
                )}
              </CardContent>
            </Card>

            {/* Dispatch Inbox Table */}
            <Card className="lg:col-span-3">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Send className="h-5 w-5 text-amber-500" />
                    Dispatch Inbox
                    {dispatchTechFilter !== null && (
                      <Badge variant="outline" className="ml-2">
                        Filtered by tech
                        <button
                          className="ml-1 hover:text-red-500"
                          onClick={() => setDispatchTechFilter(null)}
                        >
                          <XCircle className="h-3 w-3" />
                        </button>
                      </Badge>
                    )}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {/* Show only with suggestions toggle */}
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showOnlyWithSuggestions}
                        onChange={(e) => setShowOnlyWithSuggestions(e.target.checked)}
                        className="rounded"
                      />
                      <span className="flex items-center gap-1">
                        <Sparkles className="h-3 w-3" />
                        With suggestions
                      </span>
                    </label>
                    {/* Auto-Assign All button */}
                    {hasOpsAccess && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex items-center gap-1"
                        onClick={handleAutoAssignAll}
                        disabled={
                          autoAssignProgress?.isRunning ||
                          !data?.dispatch_suggestions?.some(s =>
                            s.suggested_tech_id !== null &&
                            !data.dispatch_inbox.find(j => j.id === s.job_id)?.assigned_tech
                          )
                        }
                      >
                        {autoAssignProgress?.isRunning ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin" />
                            {autoAssignProgress.current}/{autoAssignProgress.total}
                          </>
                        ) : (
                          <>
                            <Wand2 className="h-3 w-3" />
                            Auto-Assign All
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
                {/* Auto-assign results */}
                {autoAssignProgress && !autoAssignProgress.isRunning && autoAssignProgress.results.length > 0 && (
                  <div className={`mt-2 p-2 rounded text-sm ${
                    autoAssignProgress.results.every(r => r.success)
                      ? 'bg-green-50 text-green-700'
                      : 'bg-amber-50 text-amber-700'
                  }`}>
                    Assigned {autoAssignProgress.results.filter(r => r.success).length} of {autoAssignProgress.results.length} jobs
                    {autoAssignProgress.results.some(r => !r.success) && (
                      <span className="ml-2">
                        ({autoAssignProgress.results.filter(r => !r.success).length} failed)
                      </span>
                    )}
                  </div>
                )}
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3, 4].map((i) => (
                      <Skeleton key={i} className="h-14 w-full" />
                    ))}
                  </div>
                ) : (() => {
                  let filteredDispatch = dispatchTechFilter === null
                    ? data?.dispatch_inbox || []
                    : (data?.dispatch_inbox || []).filter(
                        (item) => item.assigned_tech === dispatchTechFilter
                      )

                  // Apply suggestions filter
                  if (showOnlyWithSuggestions) {
                    filteredDispatch = filteredDispatch.filter(
                      item => suggestionsByJobId.has(item.id) &&
                              suggestionsByJobId.get(item.id)?.suggested_tech_id !== null
                    )
                  }

                  if (filteredDispatch.length === 0) {
                    return (
                      <div className="text-center py-8 text-muted-foreground">
                        <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                        <p>No jobs need dispatch attention</p>
                      </div>
                    )
                  }

                  return (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[100px]">Priority</TableHead>
                          <TableHead>Job #</TableHead>
                          <TableHead>Customer / Vehicle</TableHead>
                          <TableHead className="w-[150px]">Tech</TableHead>
                          <TableHead className="w-[180px]">Suggested</TableHead>
                          <TableHead className="w-[120px]">Scheduled</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="w-[150px]">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredDispatch.map((item) => (
                          <DispatchInboxRow
                            key={item.id}
                            item={item}
                            suggestion={suggestionsByJobId.get(item.id)}
                            team={data?.team || []}
                            onAssign={(techId) => assignJob.mutate({ id: item.id, techId })}
                            onApplySuggestion={() => {
                              const suggestion = suggestionsByJobId.get(item.id)
                              if (suggestion?.suggested_tech_id) {
                                assignJob.mutate({ id: item.id, techId: suggestion.suggested_tech_id })
                              }
                            }}
                            onSchedule={(date) => updateJob.mutate({ id: item.id, data: { scheduled_date: date } })}
                            onStart={() => updateJobStatus.mutate({ id: item.id, status: 'in_progress' })}
                            onComplete={() => updateJobStatus.mutate({ id: item.id, status: 'completed' })}
                            onClearBlocker={() => clearJobBlocker.mutate({ id: item.id })}
                            onUpdateEta={() => openEtaModal(item.id, item.blocker_info?.parts)}
                            isUpdating={updateJobStatus.isPending || assignJob.isPending || updateJob.isPending || clearJobBlocker.isPending || updateJobBlocker.isPending}
                            userRole={user?.role}
                            navigate={navigate}
                          />
                        ))}
                      </TableBody>
                    </Table>
                  )
                })()}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 3. JOB BOARD TAB - Office Dispatch */}
        <TabsContent value="jobs">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Wrench className="h-5 w-5 text-purple-500" />
                  Office Dispatch
                </CardTitle>
                <div className="flex items-center gap-2">
                  {/* Filter Chips */}
                  <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
                    <Button
                      size="sm"
                      variant={jobFilter === 'all' ? 'default' : 'ghost'}
                      className="h-7 px-3 text-xs"
                      onClick={() => setJobFilter('all')}
                    >
                      All
                    </Button>
                    <Button
                      size="sm"
                      variant={jobFilter === 'unassigned' ? 'default' : 'ghost'}
                      className="h-7 px-3 text-xs"
                      onClick={() => setJobFilter('unassigned')}
                    >
                      <Filter className="h-3 w-3 mr-1" />
                      Unassigned
                    </Button>
                  </div>
                  {/* Quick Stats */}
                  <Badge variant="outline" className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {data?.job_stats.scheduled || 0} scheduled
                  </Badge>
                  <Badge variant="outline" className="flex items-center gap-1 border-yellow-300 text-yellow-700">
                    <PlayCircle className="h-3 w-3" />
                    {data?.job_stats.in_progress || 0} active
                  </Badge>
                  <Badge variant="outline" className="flex items-center gap-1 border-green-300 text-green-700">
                    <CheckCircle className="h-3 w-3" />
                    {data?.job_stats.completed || 0} done
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : (() => {
                // Get all jobs and apply filter
                const allJobs = data?.needs_attention.filter(
                  (item) => item.type === 'job' && (item.status === 'scheduled' || item.status === 'in_progress')
                ) || []

                const filteredJobs = jobFilter === 'unassigned'
                  ? allJobs.filter(job => !job.assigned_tech)
                  : allJobs

                // Group by technician
                const groupedByTech = filteredJobs.reduce((acc, job) => {
                  const techKey = job.tech_name || 'Unassigned'
                  if (!acc[techKey]) acc[techKey] = []
                  acc[techKey].push(job)
                  return acc
                }, {} as Record<string, typeof filteredJobs>)

                // Sort: Unassigned first, then alphabetically
                const sortedTechs = Object.keys(groupedByTech).sort((a, b) => {
                  if (a === 'Unassigned') return -1
                  if (b === 'Unassigned') return 1
                  return a.localeCompare(b)
                })

                if (filteredJobs.length === 0) {
                  return (
                    <div className="text-center py-8 text-muted-foreground">
                      <Wrench className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p>{jobFilter === 'unassigned' ? 'No unassigned jobs' : 'No active jobs'}</p>
                      <Button variant="link" asChild className="mt-2">
                        <Link to="/jobs/new">Create a new job</Link>
                      </Button>
                    </div>
                  )
                }

                return (
                  <div className="space-y-6">
                    {sortedTechs.map((techName) => (
                      <div key={techName}>
                        {/* Tech Header */}
                        <div className="flex items-center gap-2 mb-3">
                          <Users className="h-4 w-4 text-muted-foreground" />
                          <span className={`font-semibold ${techName === 'Unassigned' ? 'text-amber-600' : ''}`}>
                            {techName}
                          </span>
                          <Badge variant="secondary" className="text-xs">
                            {groupedByTech[techName].length} job{groupedByTech[techName].length !== 1 ? 's' : ''}
                          </Badge>
                        </div>

                        {/* Jobs Table */}
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-[100px]">Job #</TableHead>
                              <TableHead>Customer / Vehicle</TableHead>
                              <TableHead className="w-[150px]">Assign Tech</TableHead>
                              <TableHead className="w-[140px]">Schedule</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead className="w-[200px]">Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {groupedByTech[techName].map((job) => (
                              <DispatchRow
                                key={job.id}
                                job={job}
                                team={data?.team || []}
                                onAssign={(techId) => assignJob.mutate({ id: job.id, techId })}
                                onSchedule={(date) => updateJob.mutate({ id: job.id, data: { scheduled_date: date } })}
                                onStart={() => updateJobStatus.mutate({ id: job.id, status: 'in_progress' })}
                                onComplete={() => updateJobStatus.mutate({ id: job.id, status: 'completed' })}
                                onCancel={() => updateJobStatus.mutate({ id: job.id, status: 'cancelled' })}
                                isUpdating={updateJobStatus.isPending || assignJob.isPending || updateJob.isPending}
                                userRole={user?.role}
                                navigate={navigate}
                              />
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    ))}
                  </div>
                )
              })()}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 3. INSURANCE & SUPPLEMENTS TAB */}
        <TabsContent value="bottlenecks">
          <div className="space-y-4">
            {/* Revenue at Risk Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className={data?.revenue_at_risk?.needs_revision_count ? 'border-red-200 bg-red-50' : ''}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    Needs Revision
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <Skeleton className="h-12 w-full" />
                  ) : (
                    <>
                      <p className="text-2xl font-bold text-red-600">
                        {data?.revenue_at_risk?.needs_revision_count || 0}
                      </p>
                      <p className="text-sm text-red-600">
                        {formatCurrency(data?.revenue_at_risk?.needs_revision_total)} at risk
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card className={data?.revenue_at_risk?.submitted_waiting_count ? 'border-amber-200' : ''}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Clock className="h-4 w-4 text-amber-500" />
                    Waiting on Insurer
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <Skeleton className="h-12 w-full" />
                  ) : (
                    <>
                      <p className="text-2xl font-bold text-amber-600">
                        {data?.revenue_at_risk?.submitted_waiting_count || 0}
                      </p>
                      <p className="text-sm text-amber-600">
                        {formatCurrency(data?.revenue_at_risk?.submitted_waiting_total)} pending
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card className={data?.revenue_at_risk?.draft_supplements_count ? 'border-purple-200' : ''}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4 text-purple-500" />
                    Draft Supplements
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <Skeleton className="h-12 w-full" />
                  ) : (
                    <>
                      <p className="text-2xl font-bold text-purple-600">
                        {data?.revenue_at_risk?.draft_supplements_count || 0}
                      </p>
                      <p className="text-sm text-purple-600">
                        {formatCurrency(data?.revenue_at_risk?.draft_supplements_total)} unsent
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Revisions Queue */}
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  Insurer Revisions & Waiting
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-12 w-full" />
                    ))}
                  </div>
                ) : !data?.revisions_queue?.length ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <CheckCircle className="h-10 w-10 mx-auto mb-2 text-green-500" />
                    <p>No pending insurer items</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[100px]">Priority</TableHead>
                        <TableHead>Estimate #</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Insurance</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Waiting</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.revisions_queue.map((item) => (
                        <TableRow
                          key={item.estimate_id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/estimates/${item.estimate_id}/review`)}
                        >
                          <TableCell>
                            <span className={`text-xs ${
                              item.priority_score >= 90 ? 'text-red-600 font-semibold' :
                              item.priority_score >= 70 ? 'text-orange-600 font-medium' :
                              'text-amber-600'
                            }`}>
                              {item.priority_reason}
                            </span>
                          </TableCell>
                          <TableCell className="font-medium">{item.estimate_number}</TableCell>
                          <TableCell>{item.customer_name || '—'}</TableCell>
                          <TableCell>{item.insurance_company || '—'}</TableCell>
                          <TableCell>
                            <Badge
                              className={
                                item.insurer_status === 'needs_revision'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-blue-100 text-blue-800'
                              }
                            >
                              {item.insurer_status.replace('_', ' ')}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <span className={item.days_waiting > 7 ? 'text-red-600 font-medium' : ''}>
                              {item.days_waiting} days
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {formatCurrency(item.total_price)}
                          </TableCell>
                          <TableCell>
                            <Button variant="ghost" size="sm">
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            {/* Supplements Queue */}
            <Card className="border-purple-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="h-5 w-5 text-purple-500" />
                  Supplements Queue
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-12 w-full" />
                    ))}
                  </div>
                ) : !data?.supplements_queue?.length ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <CheckCircle className="h-10 w-10 mx-auto mb-2 text-green-500" />
                    <p>No pending supplements</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[100px]">Priority</TableHead>
                        <TableHead>Estimate</TableHead>
                        <TableHead>Supplement #</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Age</TableHead>
                        <TableHead className="text-right">Delta</TableHead>
                        <TableHead></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.supplements_queue.map((item) => (
                        <TableRow
                          key={`${item.estimate_id}-${item.supplement_id}`}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => navigate(`/estimates/${item.estimate_id}/review`)}
                        >
                          <TableCell>
                            <span className={`text-xs ${
                              item.priority_score >= 85 ? 'text-purple-600 font-semibold' :
                              item.priority_score >= 65 ? 'text-orange-600 font-medium' :
                              'text-muted-foreground'
                            }`}>
                              {item.priority_reason}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{item.estimate_number}</p>
                              <p className="text-xs text-muted-foreground">{item.customer_name}</p>
                            </div>
                          </TableCell>
                          <TableCell className="font-medium">#{item.supplement_number}</TableCell>
                          <TableCell className="text-sm">{item.discovery_type.replace('_', ' ')}</TableCell>
                          <TableCell>
                            <Badge
                              className={
                                item.status === 'draft'
                                  ? 'bg-purple-100 text-purple-800'
                                  : 'bg-blue-100 text-blue-800'
                              }
                            >
                              {item.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{item.days_open} days</TableCell>
                          <TableCell className="text-right font-medium text-green-600">
                            +{formatCurrency(item.delta_amount)}
                          </TableCell>
                          <TableCell>
                            <Button variant="ghost" size="sm">
                              <ChevronRight className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 4. MONEY TAB */}
        <TabsContent value="money">
          <div className="grid md:grid-cols-2 gap-4">
            {/* Invoice Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Invoice Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Draft</p>
                    <p className="text-xl font-bold">{data?.invoice_stats.draft || 0}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-medium">{formatCurrency(data?.invoice_stats.draft_total)}</p>
                    <p className="text-xs text-muted-foreground">ready to issue</p>
                  </div>
                </div>

                <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Issued</p>
                    <p className="text-xl font-bold">{data?.invoice_stats.issued || 0}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-medium">{formatCurrency(data?.invoice_stats.issued_balance)}</p>
                    <p className="text-xs text-muted-foreground">outstanding</p>
                  </div>
                </div>

                {data?.invoice_stats.overdue ? (
                  <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg border border-red-200">
                    <div>
                      <p className="text-sm text-red-600">Overdue</p>
                      <p className="text-xl font-bold text-red-600">{data.invoice_stats.overdue}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-medium text-red-600">
                        {formatCurrency(data.invoice_stats.overdue_total)}
                      </p>
                      <p className="text-xs text-red-600">needs collection</p>
                    </div>
                  </div>
                ) : null}

                <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Paid</p>
                    <p className="text-xl font-bold text-green-600">{data?.invoice_stats.paid || 0}</p>
                  </div>
                </div>

                <Button className="w-full" asChild>
                  <Link to="/invoices">View All Invoices</Link>
                </Button>
              </CardContent>
            </Card>

            {/* Draft Invoices to Issue */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Ready to Issue</CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <Skeleton className="h-40 w-full" />
                ) : (
                  <div className="space-y-2">
                    {data?.needs_attention
                      .filter((item) => item.type === 'invoice' && item.status === 'draft')
                      .slice(0, 5)
                      .map((inv) => (
                        <div
                          key={inv.id}
                          className="flex justify-between items-center p-3 border rounded-lg hover:bg-muted/50"
                        >
                          <div>
                            <p className="font-medium">{inv.identifier}</p>
                            <p className="text-sm text-muted-foreground">{inv.payer_name}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{formatCurrency(inv.total)}</span>
                            <Button
                              size="sm"
                              onClick={() => issueInvoice.mutate(inv.id)}
                              disabled={issueInvoice.isPending}
                            >
                              <Send className="h-3 w-3 mr-1" />
                              Issue
                            </Button>
                          </div>
                        </div>
                      ))}
                    {!data?.needs_attention.filter((i) => i.type === 'invoice' && i.status === 'draft').length && (
                      <p className="text-center text-muted-foreground py-4">No draft invoices</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 5. FOLLOW-UP TAB */}
        <TabsContent value="followup">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Leads Needing Follow-up</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : !data?.leads_needing_followup?.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
                  <p>All leads have been contacted recently!</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Business</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.leads_needing_followup.map((lead) => (
                      <TableRow
                        key={lead.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => navigate(`/leads/${lead.id}`)}
                      >
                        <TableCell className="font-medium">{lead.business_name || '—'}</TableCell>
                        <TableCell>{lead.contact_name || '—'}</TableCell>
                        <TableCell>
                          {lead.phone ? (
                            <a
                              href={`tel:${lead.phone}`}
                              className="text-blue-600 hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {lead.phone}
                            </a>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={
                              lead.status === 'new'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-blue-100 text-blue-800'
                            }
                          >
                            {lead.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{lead.source || '—'}</TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" asChild>
                            <Link to={`/leads/${lead.id}`}>
                              <Phone className="h-4 w-4 mr-1" />
                              Call
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Stage 5P/5Q: PARTS CONTROL TOWER TAB */}
        <TabsContent value="parts">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Package className="h-5 w-5 text-amber-500" />
                  Parts Control Tower
                </CardTitle>
                {/* Stage 5S: Parts exposure summary */}
                {data?.parts_exposure && data.parts_exposure.total_typical > 0 && (
                  <div
                    className="flex items-center gap-2 px-3 py-1 bg-amber-50 rounded-lg border border-amber-200"
                    title="Estimates only. Final pricing may vary."
                  >
                    <span className="text-sm text-amber-700">
                      Estimated exposure: <strong>~{formatCurrency(data.parts_exposure.total_typical)}</strong>
                    </span>
                    {data.parts_exposure.count_unknown > 0 && (
                      <span className="text-xs text-amber-500">
                        ({data.parts_exposure.count_unknown} unpriced)
                      </span>
                    )}
                  </div>
                )}
              </div>
              {/* Stage 5Q: Toggle between Blockers and Requests */}
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={partsViewMode === 'blockers' ? 'default' : 'outline'}
                  onClick={() => setPartsViewMode('blockers')}
                >
                  Blockers
                  {data?.dispatch_inbox?.filter(j => j.is_blocked && j.blocker_info?.issue_type === 'waiting_on_parts').length ? (
                    <Badge variant="secondary" className="ml-1">
                      {data.dispatch_inbox.filter(j => j.is_blocked && j.blocker_info?.issue_type === 'waiting_on_parts').length}
                    </Badge>
                  ) : null}
                </Button>
                <Button
                  size="sm"
                  variant={partsViewMode === 'requests' ? 'default' : 'outline'}
                  onClick={() => setPartsViewMode('requests')}
                >
                  Requests
                  {data?.parts_requests?.length ? (
                    <Badge variant="secondary" className="ml-1">{data.parts_requests.length}</Badge>
                  ) : null}
                </Button>
                {/* Stage 5V: Attention toggle with severity badges */}
                {partsViewMode === 'requests' && (data?.parts_requests_stats?.total_attention ?? 0) > 0 && (
                  <div className="flex items-center gap-2 ml-2 pl-2 border-l">
                    <Button
                      size="sm"
                      variant={showPartsAttention ? 'default' : 'outline'}
                      className={showPartsAttention ? 'bg-red-600 hover:bg-red-700' : ''}
                      onClick={() => setShowPartsAttention(!showPartsAttention)}
                    >
                      <AlertTriangle className="h-3.5 w-3.5 mr-1" />
                      Attention
                      <Badge variant="secondary" className="ml-1">
                        {data?.parts_requests_stats?.total_attention ?? 0}
                      </Badge>
                    </Button>
                    {/* Severity breakdown badges */}
                    {showPartsAttention && data?.parts_requests_stats?.counts_by_severity && (
                      <div className="flex items-center gap-1">
                        {(data.parts_requests_stats.counts_by_severity.critical ?? 0) > 0 && (
                          <Badge className="bg-red-100 text-red-800 text-xs">
                            {data.parts_requests_stats.counts_by_severity.critical} critical
                          </Badge>
                        )}
                        {(data.parts_requests_stats.counts_by_severity.high ?? 0) > 0 && (
                          <Badge className="bg-orange-100 text-orange-800 text-xs">
                            {data.parts_requests_stats.counts_by_severity.high} high
                          </Badge>
                        )}
                        {(data.parts_requests_stats.counts_by_severity.warn ?? 0) > 0 && (
                          <Badge className="bg-yellow-100 text-yellow-800 text-xs">
                            {data.parts_requests_stats.counts_by_severity.warn} warn
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {partsViewMode === 'blockers' ? (
                // BLOCKERS VIEW (existing)
                (() => {
                  const partsBlockedJobs = data?.dispatch_inbox?.filter(
                    j => j.is_blocked && j.blocker_info?.issue_type === 'waiting_on_parts'
                  ) || []
                  const canDispatch = ['owner', 'manager', 'desk', 'admin'].includes(user?.role || '')

                  if (partsBlockedJobs.length === 0) {
                    return (
                      <div className="text-center py-8 text-muted-foreground">
                        <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                        <p>No jobs blocked on parts</p>
                      </div>
                    )
                  }

                  return (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[140px]">Priority</TableHead>
                          <TableHead>Job #</TableHead>
                          <TableHead>Customer / Vehicle</TableHead>
                          <TableHead>Tech</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Vendor</TableHead>
                          <TableHead>PO #</TableHead>
                          <TableHead>ETA</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {partsBlockedJobs.map((job) => {
                          const parts = job.blocker_info?.parts
                          const partsStatus = parts?.parts_status || 'needed'
                          const isEtaOverdue = parts?.eta && new Date(parts.eta) < new Date()

                          return (
                            <TableRow key={job.id} className="hover:bg-muted/50">
                              <TableCell>
                                <span className={`text-xs ${
                                  job.priority_score >= 90 ? 'text-red-600 font-semibold' :
                                  job.priority_score >= 75 ? 'text-orange-600' :
                                  job.priority_score >= 60 ? 'text-amber-600' :
                                  'text-muted-foreground'
                                }`}>
                                  {job.priority_reason}
                                </span>
                              </TableCell>
                              <TableCell>
                                <button
                                  className="font-medium text-blue-600 hover:underline"
                                  onClick={() => navigate(`/jobs/${job.id}`)}
                                >
                                  {job.job_number}
                                </button>
                              </TableCell>
                              <TableCell>
                                <div>
                                  <p className="font-medium">{job.customer_name || '—'}</p>
                                  <p className="text-sm text-muted-foreground">{job.vehicle_display}</p>
                                </div>
                              </TableCell>
                              <TableCell className="text-sm">{job.tech_name || '—'}</TableCell>
                              <TableCell>
                                <PartsStatusBadge status={partsStatus} />
                                {parts?.approved_amount && (
                                  <span className="text-xs text-muted-foreground block">
                                    ${parts.approved_amount.toFixed(0)} approved
                                  </span>
                                )}
                              </TableCell>
                              <TableCell className="text-sm">{parts?.vendor || '—'}</TableCell>
                              <TableCell className="text-sm">{parts?.po_number || '—'}</TableCell>
                              <TableCell>
                                {parts?.eta ? (
                                  <span className={`text-sm flex items-center gap-1 ${isEtaOverdue ? 'text-red-600 font-medium' : ''}`}>
                                    {isEtaOverdue && <ClockAlert className="h-3.5 w-3.5" />}
                                    {parts.eta.split('T')[0]}
                                  </span>
                                ) : (
                                  <span className="text-sm text-muted-foreground">—</span>
                                )}
                              </TableCell>
                              <TableCell className="text-right">
                                <div className="flex items-center justify-end gap-1">
                                  {canDispatch && (
                                    <>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => openEtaModal(job.id, parts)}
                                        disabled={updateJobBlocker.isPending}
                                      >
                                        Update
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        className="text-green-600 hover:text-green-700"
                                        onClick={() => clearJobBlocker.mutate({ id: job.id })}
                                        disabled={clearJobBlocker.isPending}
                                      >
                                        <CheckCircle className="h-4 w-4" />
                                      </Button>
                                    </>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  )
                })()
              ) : (
                // REQUESTS VIEW (Stage 5Q, enhanced Stage 5T, 5V attention filter)
                (() => {
                  // Stage 5V: Filter by attention if toggle is on
                  const allPartsRequests = data?.parts_requests || []
                  const attentionRequests = data?.parts_requests_attention || []
                  const partsRequests = showPartsAttention ? attentionRequests : allPartsRequests
                  const canDispatch = ['owner', 'manager', 'desk', 'admin'].includes(user?.role || '')
                  const pendingApprovalCount = allPartsRequests.filter(r => !r.approved_to_order).length
                  const approvedCount = allPartsRequests.filter(r => r.approved_to_order).length

                  if (partsRequests.length === 0) {
                    return (
                      <div className="text-center py-8 text-muted-foreground">
                        <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                        <p>{showPartsAttention ? 'No parts requests needing attention' : 'No part requests'}</p>
                      </div>
                    )
                  }

                  return (
                    <>
                      {/* Stage 5T: Bulk approve controls */}
                      {canDispatch && selectedPartRequests.size > 0 && (
                        <div className="flex items-center justify-between p-3 mb-2 bg-amber-50 border border-amber-200 rounded-lg">
                          <span className="text-sm text-amber-800">
                            {selectedPartRequests.size} request{selectedPartRequests.size !== 1 ? 's' : ''} selected
                          </span>
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setSelectedPartRequests(new Set())}
                            >
                              Clear
                            </Button>
                            <Button
                              size="sm"
                              className="bg-amber-600 hover:bg-amber-700"
                              onClick={() => {
                                bulkApprovePartRequests.mutate({
                                  requestIds: Array.from(selectedPartRequests),
                                })
                                setSelectedPartRequests(new Set())
                              }}
                              disabled={bulkApprovePartRequests.isPending}
                            >
                              {bulkApprovePartRequests.isPending ? (
                                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                              ) : (
                                <CheckCircle className="h-4 w-4 mr-1" />
                              )}
                              Approve Selected
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Stage 5T: Summary badges */}
                      <div className="flex items-center gap-3 mb-3">
                        <Badge variant="outline" className="text-xs">
                          {pendingApprovalCount} pending approval
                        </Badge>
                        <Badge className="bg-green-100 text-green-700 text-xs">
                          {approvedCount} approved
                        </Badge>
                      </div>

                      <Table>
                        <TableHeader>
                          <TableRow>
                            {canDispatch && (
                              <TableHead className="w-[40px]">
                                <input
                                  type="checkbox"
                                  checked={selectedPartRequests.size === partsRequests.filter(r => !r.approved_to_order).length && pendingApprovalCount > 0}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedPartRequests(new Set(partsRequests.filter(r => !r.approved_to_order).map(r => r.id)))
                                    } else {
                                      setSelectedPartRequests(new Set())
                                    }
                                  }}
                                  className="rounded border-gray-300"
                                />
                              </TableHead>
                            )}
                            <TableHead className="w-[100px]">Priority</TableHead>
                            <TableHead>Job #</TableHead>
                            <TableHead>Customer / Vehicle</TableHead>
                          <TableHead>Tech</TableHead>
                          <TableHead className="w-[180px]">Part</TableHead>
                          <TableHead>Qty</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Est. Cost</TableHead>
                          <TableHead>Vendor / PO</TableHead>
                          <TableHead>ETA</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {partsRequests.map((req) => {
                          // Stage 5V: Cast to attention item if showing attention view
                          const attentionReq = req as PartsRequestAttentionItem
                          const severity = showPartsAttention ? attentionReq.severity : undefined
                          const rowBgClass = severity === 'critical' ? 'bg-red-50/50' :
                            severity === 'high' ? 'bg-orange-50/50' :
                            severity === 'warn' ? 'bg-yellow-50/30' :
                            req.approved_to_order ? 'bg-green-50/30' : ''

                          return (
                          <TableRow key={req.id} className={`hover:bg-muted/50 ${rowBgClass}`}>
                            {/* Stage 5T: Checkbox for bulk selection */}
                            {canDispatch && (
                              <TableCell>
                                <input
                                  type="checkbox"
                                  checked={selectedPartRequests.has(req.id)}
                                  onChange={(e) => {
                                    const newSet = new Set(selectedPartRequests)
                                    if (e.target.checked) {
                                      newSet.add(req.id)
                                    } else {
                                      newSet.delete(req.id)
                                    }
                                    setSelectedPartRequests(newSet)
                                  }}
                                  disabled={req.approved_to_order}
                                  className="rounded border-gray-300"
                                />
                              </TableCell>
                            )}
                            <TableCell>
                              <div className="flex flex-col gap-0.5">
                                {/* Stage 5V: Severity badge */}
                                {severity && (
                                  <Badge className={`text-[10px] w-fit ${
                                    severity === 'critical' ? 'bg-red-100 text-red-800' :
                                    severity === 'high' ? 'bg-orange-100 text-orange-800' :
                                    'bg-yellow-100 text-yellow-800'
                                  }`}>
                                    {severity}
                                  </Badge>
                                )}
                                <span className={`text-xs ${
                                  req.is_overdue ? 'text-red-600 font-semibold' :
                                  req.priority >= 75 ? 'text-orange-600' :
                                  req.priority >= 60 ? 'text-amber-600' :
                                  'text-muted-foreground'
                                }`}>
                                  {req.priority_reason || (req.is_overdue ? 'ETA Overdue' :
                                    req.parts_status === 'exception' ? 'Exception' :
                                    req.parts_status === 'needed' && !req.approved_to_order ? 'Needs Approval' :
                                    req.parts_status.replace('_', ' '))}
                                </span>
                              </div>
                            </TableCell>
                            <TableCell>
                              {req.job_number ? (
                                <button
                                  className="font-medium text-blue-600 hover:underline"
                                  onClick={() => navigate(`/jobs/${req.job_id}`)}
                                >
                                  {req.job_number}
                                </button>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell>
                              <div>
                                <p className="font-medium">{req.customer_name || '—'}</p>
                                <p className="text-sm text-muted-foreground">{req.vehicle_display || ''}</p>
                              </div>
                            </TableCell>
                            <TableCell className="text-sm">{req.tech_name || '—'}</TableCell>
                            <TableCell>
                              <div>
                                <p className="font-medium text-sm truncate max-w-[180px]" title={req.description}>
                                  {req.description}
                                </p>
                                {req.part_number && (
                                  <p className="text-xs text-muted-foreground">#{req.part_number}</p>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="text-sm">{req.qty}</TableCell>
                            <TableCell>
                              <div className="flex flex-col gap-1">
                                <PartsStatusBadge status={req.parts_status} />
                                {/* Stage 5T: Approval badge */}
                                {req.approved_to_order && (
                                  <Badge className="bg-green-100 text-green-700 text-xs w-fit" title={req.approval_notes || 'Approved to order'}>
                                    <CheckCircle className="h-3 w-3 mr-1" />
                                    Approved
                                  </Badge>
                                )}
                                {req.approved_amount && (
                                  <span className="text-xs text-muted-foreground">
                                    ${req.approved_amount.toFixed(0)} approved
                                  </span>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              {req.pricing_preview ? (
                                <div title={`${req.pricing_preview.source}: ${req.pricing_preview.notes || ''}`}>
                                  <span className="text-sm font-medium">
                                    {formatPriceRange(req.pricing_preview)}
                                  </span>
                                  <div className="flex items-center gap-1 mt-0.5">
                                    <PricingConfidenceBadge confidence={req.pricing_preview.confidence} />
                                    <span className="text-xs text-muted-foreground">
                                      {req.pricing_preview.source === 'historical' ? 'hist.' :
                                       req.pricing_preview.source === 'vendor_table' ? 'ref.' :
                                       req.pricing_preview.source === 'manual' ? 'set' : ''}
                                    </span>
                                  </div>
                                </div>
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-sm">
                              <div>
                                {req.vendor && <p>{req.vendor}</p>}
                                {req.po_number && <p className="text-xs text-muted-foreground">{req.po_number}</p>}
                                {!req.vendor && !req.po_number && '—'}
                              </div>
                            </TableCell>
                            <TableCell>
                              {req.eta ? (
                                <span className={`text-sm flex items-center gap-1 ${req.is_overdue ? 'text-red-600 font-medium' : ''}`}>
                                  {req.is_overdue && <ClockAlert className="h-3.5 w-3.5" />}
                                  {req.eta.split('T')[0]}
                                </span>
                              ) : (
                                <span className="text-sm text-muted-foreground">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              {canDispatch && (
                                <div className="flex items-center justify-end gap-1">
                                  {/* Stage 5U: Quick Mark buttons */}
                                  {req.approved_to_order && req.parts_status === 'approved_to_order' && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="text-yellow-700 border-yellow-300 hover:bg-yellow-50"
                                      onClick={() => updatePartRequestStatus.mutate({
                                        id: req.id,
                                        partsStatus: 'ordered',
                                      })}
                                      disabled={updatePartRequestStatus.isPending}
                                      title="Mark as ordered"
                                    >
                                      <Truck className="h-3.5 w-3.5 mr-1" />
                                      Ordered
                                    </Button>
                                  )}
                                  {req.parts_status === 'shipped' && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="text-green-700 border-green-300 hover:bg-green-50"
                                      onClick={() => updatePartRequestStatus.mutate({
                                        id: req.id,
                                        partsStatus: 'received',
                                      })}
                                      disabled={updatePartRequestStatus.isPending}
                                      title="Mark as received"
                                    >
                                      <Package className="h-3.5 w-3.5 mr-1" />
                                      Received
                                    </Button>
                                  )}

                                  {/* Stage 5U: Inline status dropdown */}
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <div className="inline-block">
                                          <Select
                                            value={req.parts_status}
                                            onValueChange={(newStatus) => {
                                              if (newStatus !== req.parts_status) {
                                                updatePartRequestStatus.mutate({
                                                  id: req.id,
                                                  partsStatus: newStatus,
                                                })
                                              }
                                            }}
                                            disabled={updatePartRequestStatus.isPending}
                                          >
                                            <SelectTrigger className="h-8 w-[110px] text-xs">
                                              <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                              {(req.allowed_transitions || []).map((status) => {
                                                const opt = PARTS_STATUS_OPTIONS.find(o => o.value === status)
                                                return (
                                                  <SelectItem key={status} value={status}>
                                                    {opt?.label || status}
                                                  </SelectItem>
                                                )
                                              })}
                                              {/* Always show current status */}
                                              <SelectItem value={req.parts_status} disabled>
                                                {PARTS_STATUS_OPTIONS.find(o => o.value === req.parts_status)?.label || req.parts_status} (current)
                                              </SelectItem>
                                            </SelectContent>
                                          </Select>
                                        </div>
                                      </TooltipTrigger>
                                      <TooltipContent side="left" className="max-w-xs">
                                        <div className="text-xs space-y-0.5">
                                          <p className="font-medium mb-1">Timeline</p>
                                          {formatPartRequestTimeline(req).length > 0 ? (
                                            formatPartRequestTimeline(req).map((line, i) => (
                                              <p key={i} className="text-muted-foreground">{line}</p>
                                            ))
                                          ) : (
                                            <p className="text-muted-foreground">No timeline data</p>
                                          )}
                                        </div>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>

                                  {/* Stage 5T: Approve/Unapprove button */}
                                  {req.approved_to_order ? (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                      onClick={() => unapprovePartRequest.mutate(req.id)}
                                      disabled={unapprovePartRequest.isPending}
                                      title="Revoke approval"
                                    >
                                      <XCircle className="h-4 w-4" />
                                    </Button>
                                  ) : (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="text-green-600 hover:text-green-700 hover:bg-green-50"
                                      onClick={() => approvePartRequest.mutate({ id: req.id })}
                                      disabled={approvePartRequest.isPending}
                                      title="Approve to order"
                                    >
                                      <CheckCircle className="h-4 w-4" />
                                    </Button>
                                  )}
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => openPartRequestModal(req)}
                                    disabled={updatePartRequest.isPending}
                                  >
                                    Update
                                  </Button>
                                </div>
                              )}
                            </TableCell>
                          </TableRow>
                        )})}
                      </TableBody>
                    </Table>
                    </>
                  )
                })()
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Update ETA Modal (Stage 5O, extended 5P) */}
      <Dialog open={etaModalOpen} onOpenChange={setEtaModalOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-amber-500" />
              Update Parts Blocker
            </DialogTitle>
            <DialogDescription>
              Update the parts order status and expected arrival time.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Stage 5P: Parts Status dropdown */}
            <div className="space-y-1">
              <Label htmlFor="eta-status" className="text-sm">Parts Status</Label>
              <Select value={etaPartsStatus} onValueChange={setEtaPartsStatus}>
                <SelectTrigger id="eta-status">
                  <SelectValue placeholder="Select status..." />
                </SelectTrigger>
                <SelectContent>
                  {PARTS_STATUS_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="eta-vendor" className="text-sm">Vendor</Label>
                <Input
                  id="eta-vendor"
                  placeholder="e.g., AutoZone"
                  value={etaVendor}
                  onChange={(e) => setEtaVendor(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="eta-po" className="text-sm">PO #</Label>
                <Input
                  id="eta-po"
                  placeholder="e.g., PO-12345"
                  value={etaPoNumber}
                  onChange={(e) => setEtaPoNumber(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="eta-date" className="text-sm">Expected Arrival Date</Label>
                <Input
                  id="eta-date"
                  type="date"
                  value={etaValue}
                  onChange={(e) => setEtaValue(e.target.value)}
                />
              </div>
              {/* Stage 5P: Approved amount */}
              <div className="space-y-1">
                <Label htmlFor="eta-amount" className="text-sm">Approved Amount ($)</Label>
                <Input
                  id="eta-amount"
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={etaApprovedAmount}
                  onChange={(e) => setEtaApprovedAmount(e.target.value)}
                />
              </div>
            </div>

            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={etaPartsOrdered}
                  onChange={(e) => setEtaPartsOrdered(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Parts ordered</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={etaApprovedToOrder}
                  onChange={(e) => setEtaApprovedToOrder(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Approved to order</span>
              </label>
            </div>

            <div className="space-y-1">
              <Label htmlFor="eta-notes" className="text-sm">Notes (optional)</Label>
              <Textarea
                id="eta-notes"
                placeholder="Any additional notes..."
                value={etaNotes}
                onChange={(e) => setEtaNotes(e.target.value)}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEtaModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleUpdateEta}
              disabled={updateJobBlocker.isPending}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {updateJobBlocker.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Package className="h-4 w-4 mr-2" />
              )}
              Update Blocker
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stage 5Q: Part Request Edit Modal */}
      <Dialog open={partRequestModalOpen} onOpenChange={setPartRequestModalOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-amber-500" />
              Update Part Request
            </DialogTitle>
            <DialogDescription>
              Update the part request details and status.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1">
              <Label htmlFor="pr-description" className="text-sm">Description</Label>
              <Input
                id="pr-description"
                placeholder="Part description..."
                value={prDescription}
                onChange={(e) => setPrDescription(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label htmlFor="pr-partnum" className="text-sm">Part #</Label>
                <Input
                  id="pr-partnum"
                  placeholder="Part number"
                  value={prPartNumber}
                  onChange={(e) => setPrPartNumber(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pr-qty" className="text-sm">Qty</Label>
                <Input
                  id="pr-qty"
                  type="number"
                  min="1"
                  value={prQty}
                  onChange={(e) => setPrQty(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pr-status" className="text-sm">Status</Label>
                <Select value={prStatus} onValueChange={setPrStatus}>
                  <SelectTrigger id="pr-status">
                    <SelectValue placeholder="Status..." />
                  </SelectTrigger>
                  <SelectContent>
                    {PARTS_STATUS_OPTIONS.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="pr-vendor" className="text-sm">Vendor</Label>
                <Input
                  id="pr-vendor"
                  placeholder="e.g., AutoZone"
                  value={prVendor}
                  onChange={(e) => setPrVendor(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pr-po" className="text-sm">PO #</Label>
                <Input
                  id="pr-po"
                  placeholder="e.g., PO-12345"
                  value={prPoNumber}
                  onChange={(e) => setPrPoNumber(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="pr-eta" className="text-sm">Expected Arrival Date</Label>
                <Input
                  id="pr-eta"
                  type="date"
                  value={prEta}
                  onChange={(e) => setPrEta(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pr-amount" className="text-sm">Approved Amount ($)</Label>
                <Input
                  id="pr-amount"
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={prApprovedAmount}
                  onChange={(e) => setPrApprovedAmount(e.target.value)}
                />
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={prApprovedToOrder}
                onChange={(e) => setPrApprovedToOrder(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Approved to order</span>
            </label>

            <div className="space-y-1">
              <Label htmlFor="pr-notes" className="text-sm">Notes (optional)</Label>
              <Textarea
                id="pr-notes"
                placeholder="Any additional notes..."
                value={prNotes}
                onChange={(e) => setPrNotes(e.target.value)}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPartRequestModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleUpdatePartRequest}
              disabled={updatePartRequest.isPending || !prDescription.trim()}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {updatePartRequest.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Package className="h-4 w-4 mr-2" />
              )}
              Update Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ============================================================================
// DISPATCH ROW COMPONENT
// ============================================================================
interface DispatchRowProps {
  job: NeedsAttentionItem
  team: { id: number; name: string; role: string }[]
  onAssign: (techId: number) => void
  onSchedule: (date: string) => void
  onStart: () => void
  onComplete: () => void
  onCancel: () => void
  isUpdating: boolean
  userRole?: string
  navigate: (path: string) => void
}

function DispatchRow({
  job,
  team,
  onAssign,
  onSchedule,
  onStart,
  onComplete,
  onCancel,
  isUpdating,
  userRole,
  navigate,
}: DispatchRowProps) {
  // Filter team to just technicians (role is 'tech' in the system)
  const technicians = team.filter((t) => t.role === 'tech')

  // Permission checks
  const canDispatch = userRole && ['owner', 'manager', 'desk', 'admin'].includes(userRole)
  const canCancel = userRole && ['owner', 'manager', 'admin'].includes(userRole)

  // Status badge colors
  const statusColors: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-gray-100 text-gray-800',
  }

  return (
    <TableRow className="hover:bg-muted/50">
      <TableCell>
        <button
          className="font-medium text-blue-600 hover:underline text-left"
          onClick={() => navigate(`/jobs/${job.id}`)}
        >
          {job.identifier}
        </button>
      </TableCell>
      <TableCell>
        <div>
          <p className="font-medium">{job.customer_name || '—'}</p>
          <p className="text-sm text-muted-foreground">{job.vehicle_display}</p>
        </div>
      </TableCell>
      <TableCell>
        {canDispatch ? (
          <Select
            value={job.assigned_tech?.toString() || ''}
            onValueChange={(value) => onAssign(parseInt(value))}
            disabled={isUpdating}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Assign..." />
            </SelectTrigger>
            <SelectContent>
              {technicians.length === 0 ? (
                <SelectItem value="none" disabled>No technicians</SelectItem>
              ) : (
                technicians.map((tech) => (
                  <SelectItem key={tech.id} value={tech.id.toString()}>
                    {tech.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        ) : (
          <span className="text-sm text-muted-foreground">
            {job.tech_name || 'Unassigned'}
          </span>
        )}
      </TableCell>
      <TableCell>
        {canDispatch ? (
          <Input
            type="date"
            className="h-8 text-xs w-[130px]"
            value={job.scheduled_date ? job.scheduled_date.split('T')[0] : ''}
            onChange={(e) => onSchedule(e.target.value)}
            disabled={isUpdating}
          />
        ) : (
          <span className="text-sm text-muted-foreground flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {job.scheduled_date
              ? new Date(job.scheduled_date).toLocaleDateString()
              : 'Not scheduled'}
          </span>
        )}
      </TableCell>
      <TableCell>
        <Badge className={statusColors[job.status || ''] || 'bg-gray-100'}>
          {job.status?.replace('_', ' ')}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          {job.status === 'scheduled' && canDispatch && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs"
              onClick={onStart}
              disabled={isUpdating}
            >
              <PlayCircle className="h-3 w-3 mr-1" />
              Start
            </Button>
          )}
          {job.status === 'in_progress' && canDispatch && (
            <Button
              size="sm"
              variant="default"
              className="h-7 px-2 text-xs"
              onClick={onComplete}
              disabled={isUpdating}
            >
              <CheckCircle className="h-3 w-3 mr-1" />
              Complete
            </Button>
          )}
          {(job.status === 'scheduled' || job.status === 'in_progress') && canCancel && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
              onClick={onCancel}
              disabled={isUpdating}
            >
              <XCircle className="h-3 w-3" />
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2"
            onClick={() => navigate(`/jobs/${job.id}`)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

// ============================================================================
// DISPATCH INBOX ROW COMPONENT (Stage 5H + 5M suggestions + 5O parts)
// ============================================================================
interface DispatchInboxRowProps {
  item: DispatchInboxItem
  suggestion?: DispatchSuggestion
  team: { id: number; name: string; role: string }[]
  onAssign: (techId: number) => void
  onApplySuggestion: () => void
  onSchedule: (date: string) => void
  onStart: () => void
  onComplete: () => void
  onClearBlocker: () => void
  onUpdateEta: () => void
  isUpdating: boolean
  userRole?: string
  navigate: (path: string) => void
}

function DispatchInboxRow({
  item,
  suggestion,
  team,
  onAssign,
  onApplySuggestion,
  onSchedule,
  onStart,
  onComplete,
  onClearBlocker,
  onUpdateEta,
  isUpdating,
  userRole,
  navigate,
}: DispatchInboxRowProps) {
  // Filter team to just technicians
  const technicians = team.filter((t) => t.role === 'tech')

  // Permission checks
  const canDispatch = userRole && ['owner', 'manager', 'desk', 'admin'].includes(userRole)

  // Priority color based on score
  const getPriorityColor = (score: number) => {
    if (score >= 80) return 'text-red-600 font-semibold'
    if (score >= 70) return 'text-orange-600 font-medium'
    if (score >= 60) return 'text-amber-600'
    return 'text-muted-foreground'
  }

  // Status badge with parts info (using shared helper - Stage 5O.1)
  const getStatusBadge = () => {
    if (item.is_blocked) {
      return (
        <div className="space-y-1">
          <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Blocked
          </Badge>
          {/* Parts info using shared renderer */}
          {renderBlockerPartsSummary(item.blocker_info)}
        </div>
      )
    }
    const colors: Record<string, string> = {
      scheduled: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
    }
    return (
      <Badge className={colors[item.status] || 'bg-gray-100'}>
        {item.status.replace('_', ' ')}
        {item.age_hours && ` (${item.age_hours}h)`}
      </Badge>
    )
  }

  return (
    <TableRow className="hover:bg-muted/50">
      {/* Priority */}
      <TableCell>
        <span className={`text-xs ${getPriorityColor(item.priority_score)}`}>
          {item.priority_reason}
        </span>
      </TableCell>

      {/* Job # */}
      <TableCell>
        <button
          className="font-medium text-blue-600 hover:underline text-left"
          onClick={() => navigate(`/jobs/${item.id}`)}
        >
          {item.job_number}
        </button>
      </TableCell>

      {/* Customer / Vehicle */}
      <TableCell>
        <div>
          <p className="font-medium">{item.customer_name || '—'}</p>
          <p className="text-sm text-muted-foreground">{item.vehicle_display}</p>
        </div>
      </TableCell>

      {/* Tech Assignment */}
      <TableCell>
        {canDispatch ? (
          <Select
            value={item.assigned_tech?.toString() || ''}
            onValueChange={(value) => onAssign(parseInt(value))}
            disabled={isUpdating}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Assign..." />
            </SelectTrigger>
            <SelectContent>
              {technicians.length === 0 ? (
                <SelectItem value="none" disabled>No technicians</SelectItem>
              ) : (
                technicians.map((tech) => (
                  <SelectItem key={tech.id} value={tech.id.toString()}>
                    {tech.name}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        ) : (
          <span className="text-sm text-muted-foreground">
            {item.tech_name || 'Unassigned'}
          </span>
        )}
      </TableCell>

      {/* Suggested Tech (Stage 5M) */}
      <TableCell>
        {suggestion?.suggested_tech_id && !item.assigned_tech ? (
          <div className="flex items-center gap-1">
            <div
              className="flex-1 cursor-help"
              title={suggestion.reasons.join('\n')}
            >
              <div className="flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-amber-500" />
                <span className="text-xs font-medium truncate max-w-[80px]">
                  {suggestion.suggested_tech_name}
                </span>
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <div
                  className={`h-1.5 flex-1 rounded-full ${
                    suggestion.confidence >= 70 ? 'bg-green-400' :
                    suggestion.confidence >= 50 ? 'bg-amber-400' :
                    'bg-gray-300'
                  }`}
                  style={{ width: `${Math.min(suggestion.confidence, 100)}%` }}
                />
                <span className="text-[10px] text-muted-foreground">
                  {suggestion.confidence}%
                </span>
              </div>
            </div>
            {canDispatch && (
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-1.5 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                onClick={onApplySuggestion}
                disabled={isUpdating}
                title="Apply suggestion"
              >
                <CheckCircle className="h-3 w-3" />
              </Button>
            )}
          </div>
        ) : item.assigned_tech ? (
          <span className="text-xs text-muted-foreground">Assigned</span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </TableCell>

      {/* Schedule */}
      <TableCell>
        {canDispatch ? (
          <Input
            type="date"
            className="h-8 text-xs w-[120px]"
            value={item.scheduled_date ? item.scheduled_date.split('T')[0] : ''}
            onChange={(e) => onSchedule(e.target.value)}
            disabled={isUpdating}
          />
        ) : (
          <span className="text-sm text-muted-foreground">
            {item.scheduled_date
              ? new Date(item.scheduled_date).toLocaleDateString()
              : 'Not set'}
          </span>
        )}
      </TableCell>

      {/* Status */}
      <TableCell>{getStatusBadge()}</TableCell>

      {/* Actions */}
      <TableCell>
        <div className="flex items-center gap-1">
          {/* Blocked: Update ETA + Clear Blocker */}
          {item.is_blocked && item.blocker_info?.issue_type === 'waiting_on_parts' && canDispatch && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs border-amber-300 text-amber-600 hover:bg-amber-50"
              onClick={onUpdateEta}
              disabled={isUpdating}
            >
              <Package className="h-3 w-3 mr-1" />
              ETA
            </Button>
          )}
          {item.is_blocked && canDispatch && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs border-red-300 text-red-600 hover:bg-red-50"
              onClick={onClearBlocker}
              disabled={isUpdating}
            >
              <XCircle className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}

          {/* Scheduled: Start */}
          {item.status === 'scheduled' && !item.is_blocked && canDispatch && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs"
              onClick={onStart}
              disabled={isUpdating}
            >
              <PlayCircle className="h-3 w-3 mr-1" />
              Start
            </Button>
          )}

          {/* In Progress (stale): Complete */}
          {item.status === 'in_progress' && item.age_hours && canDispatch && (
            <Button
              size="sm"
              variant="default"
              className="h-7 px-2 text-xs"
              onClick={onComplete}
              disabled={isUpdating}
            >
              <CheckCircle className="h-3 w-3 mr-1" />
              Complete
            </Button>
          )}

          {/* View button */}
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2"
            onClick={() => navigate(`/jobs/${item.id}`)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}
