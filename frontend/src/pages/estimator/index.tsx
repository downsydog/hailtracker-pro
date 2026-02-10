/**
 * Estimator Dashboard - Shows estimates needing action with workflow integration.
 *
 * Reuses ops/overview data to avoid duplicate queries.
 * All actions computed by backend WorkflowService.
 */
import { Link, useNavigate } from "react-router-dom"
import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  FileText,
  ChevronRight,
  Plus,
  User,
  Send,
  Shield,
  AlertCircle,
  Clock,
  RefreshCw,
} from "lucide-react"
import { useOpsOverview, NeedsAttentionItem } from '@/hooks/use-ops'
import { useAuth } from '@/contexts/auth-context'

// Status colors - matches WorkflowCard
const customerStatusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending_signature: 'bg-yellow-100 text-yellow-700',
  authorized: 'bg-green-100 text-green-700',
}

const insurerStatusColors: Record<string, string> = {
  not_submitted: 'bg-gray-100 text-gray-700',
  submitted: 'bg-blue-100 text-blue-700',
  approved: 'bg-green-100 text-green-700',
  needs_revision: 'bg-amber-100 text-amber-700',
  declined: 'bg-red-100 text-red-700',
}

// Action icons
const actionIcons: Record<string, typeof FileText> = {
  request_customer_auth: User,
  submit_to_insurer: Send,
  mark_insurer_approved: Shield,
  mark_needs_revision: AlertCircle,
  resubmit_to_insurer: Send,
}

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

export function EstimatorDashboardPage() {
  const navigate = useNavigate()
  const { permissions } = useAuth()
  const { data, isLoading, lastUpdated, isFetching } = useOpsOverview()

  // Force re-render every 10s to update relative time display
  const [, setTick] = useState(0)
  useEffect(() => {
    const interval = setInterval(() => setTick(t => t + 1), 10000)
    return () => clearInterval(interval)
  }, [])

  // Filter to just estimates from needs_attention
  const estimates = (data?.needs_attention || []).filter(
    (item): item is NeedsAttentionItem & { type: 'estimate' } => item.type === 'estimate'
  )

  // Compute stats
  const draftCount = estimates.filter(e => e.customer_status === 'draft').length
  const pendingSignature = estimates.filter(e => e.customer_status === 'pending_signature').length
  const submittedToInsurer = estimates.filter(e => e.insurer_status === 'submitted').length
  const needsRevision = estimates.filter(e => e.insurer_status === 'needs_revision').length

  const handleActionClick = (estimate: NeedsAttentionItem) => {
    // All estimate actions navigate to EstimateReview page
    navigate(`/estimates/${estimate.id}/review`)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Estimator Dashboard</h1>
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
          <p className="text-muted-foreground">Manage estimates and quotes</p>
        </div>
        <Button asChild>
          <Link to="/estimates/new">
            <Plus className="h-4 w-4 mr-2" />
            New Estimate
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Draft</CardTitle>
            <FileText className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold">{draftCount}</p>
                <p className="text-xs text-muted-foreground">Need authorization</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card className={pendingSignature > 0 ? 'border-yellow-200' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pending Signature</CardTitle>
            <User className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold">{pendingSignature}</p>
                <p className="text-xs text-muted-foreground">Awaiting customer</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card className={submittedToInsurer > 0 ? 'border-blue-200' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">With Insurer</CardTitle>
            <Send className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold">{submittedToInsurer}</p>
                <p className="text-xs text-muted-foreground">Awaiting approval</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card className={needsRevision > 0 ? 'border-amber-200' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Needs Revision</CardTitle>
            <AlertCircle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold text-amber-600">{needsRevision}</p>
                <p className="text-xs text-muted-foreground">Requires changes</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Needs Revision - Priority */}
      {needsRevision > 0 && (
        <Card className="border-amber-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-amber-500" />
              Needs Revision
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {estimates
              .filter(e => e.insurer_status === 'needs_revision')
              .map((estimate) => (
                <EstimateRow
                  key={estimate.id}
                  estimate={estimate}
                  onActionClick={handleActionClick}
                  permissions={permissions}
                />
              ))}
          </CardContent>
        </Card>
      )}

      {/* Estimates Needing Action */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-500" />
            Estimates Needing Action
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : estimates.filter(e => e.insurer_status !== 'needs_revision').length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No estimates needing attention</p>
              <Button asChild variant="link" className="mt-2">
                <Link to="/estimates/new">Create your first estimate</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {estimates
                .filter(e => e.insurer_status !== 'needs_revision')
                .map((estimate) => (
                  <EstimateRow
                    key={estimate.id}
                    estimate={estimate}
                    onActionClick={handleActionClick}
                    permissions={permissions}
                  />
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Links */}
      <div className="flex gap-4">
        <Button variant="outline" asChild>
          <Link to="/estimates">View All Estimates</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/estimates?status=completed">Completed Estimates</Link>
        </Button>
      </div>
    </div>
  )
}

interface EstimateRowProps {
  estimate: NeedsAttentionItem
  onActionClick: (estimate: NeedsAttentionItem) => void
  permissions: {
    canRequestSignature: boolean
    canSubmitToInsurer: boolean
    canInsurerApprove: boolean
  }
}

function EstimateRow({ estimate, onActionClick, permissions }: EstimateRowProps) {
  const navigate = useNavigate()
  const Icon = estimate.primary_action
    ? actionIcons[estimate.primary_action.key] || FileText
    : FileText

  // Check if action is permission-gated
  const isActionEnabled = () => {
    if (!estimate.primary_action) return false
    const key = estimate.primary_action.key
    if (key === 'request_customer_auth' && !permissions.canRequestSignature) return false
    if (key === 'submit_to_insurer' && !permissions.canSubmitToInsurer) return false
    if ((key === 'mark_insurer_approved' || key === 'mark_needs_revision') && !permissions.canInsurerApprove) return false
    return true
  }

  return (
    <div
      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 cursor-pointer"
      onClick={() => navigate(`/estimates/${estimate.id}/review`)}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold">{estimate.identifier}</span>
          <Badge className={customerStatusColors[estimate.customer_status || 'draft']}>
            {estimate.customer_status?.replace('_', ' ') || 'Draft'}
          </Badge>
          <Badge className={insurerStatusColors[estimate.insurer_status || 'not_submitted']}>
            {estimate.insurer_status?.replace('_', ' ') || 'Not Submitted'}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{estimate.customer_name || 'No customer'}</p>
        <p className="text-xs text-muted-foreground">{estimate.vehicle_display}</p>
        <div className="flex items-center gap-2 mt-1">
          <p className="text-sm font-medium">{formatCurrency(estimate.total_price)}</p>
          {estimate.priority_reason && (
            <span className={`text-xs ${(estimate.priority_score || 0) >= 70 ? 'text-red-600 font-medium' : (estimate.priority_score || 0) >= 55 ? 'text-amber-600' : 'text-muted-foreground'}`}>
              {estimate.priority_reason}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {estimate.primary_action && (
          <Button
            size="sm"
            variant={isActionEnabled() ? 'default' : 'outline'}
            disabled={!isActionEnabled()}
            onClick={(e) => {
              e.stopPropagation()
              onActionClick(estimate)
            }}
          >
            <Icon className="h-4 w-4 mr-1" />
            {estimate.primary_action.label}
            {!isActionEnabled() && ' 🔒'}
          </Button>
        )}
        <ChevronRight className="h-5 w-5 text-muted-foreground" />
      </div>
    </div>
  )
}
