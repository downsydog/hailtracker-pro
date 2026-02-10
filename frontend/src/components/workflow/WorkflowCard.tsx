/**
 * WorkflowCard Component
 *
 * Displays the current workflow state and available next actions.
 * Used on EstimateReview and JobDetail pages to guide users through
 * the PDR workflow process.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  CheckCircle2,
  Circle,
  ArrowRight,
  AlertCircle,
  Loader2,
  FileText,
  Briefcase,
  DollarSign,
  Send,
  User,
  Shield,
  Clock,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Types matching backend WorkflowService output
export interface WorkflowAction {
  key: string
  label: string
  description: string
  enabled: boolean
  reason_disabled?: string | null
  endpoint_hint?: string | null
  priority: number
}

export interface WorkflowState {
  estimate_status: string
  customer_status: string
  insurer_status: string
  job_status: string | null
  job_id: number | null
  invoices_count: number
  invoices_total: number
  invoices_paid: number
  invoices_balance: number
  has_insurer_invoice: boolean
  has_customer_invoice: boolean
  all_invoices_paid: boolean
  deductible: number
  customer_oop: number
}

export interface WorkflowData {
  state: WorkflowState
  next_actions: WorkflowAction[]
  primary_action: WorkflowAction | null
  estimate_id: number
  estimate_number: string
  job_id?: number
  job_number?: string
}

interface WorkflowCardProps {
  workflow: WorkflowData
  isLoading?: boolean
  onAction?: (actionKey: string) => void
  actionLoadingKey?: string | null
  className?: string
  /** Compact mode for embedding in lists - shows only primary action and condensed status */
  variant?: 'default' | 'compact'
}

// Status display helpers
const customerStatusLabels: Record<string, string> = {
  draft: "Draft",
  pending: "Pending Signature",
  authorized: "Authorized",
}

const customerStatusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  pending: "bg-yellow-100 text-yellow-700",
  authorized: "bg-green-100 text-green-700",
}

const insurerStatusLabels: Record<string, string> = {
  not_submitted: "Not Submitted",
  submitted: "Submitted",
  approved: "Approved",
  needs_revision: "Needs Revision",
  declined: "Declined",
}

const insurerStatusColors: Record<string, string> = {
  not_submitted: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  needs_revision: "bg-amber-100 text-amber-700",
  declined: "bg-red-100 text-red-700",
}

const jobStatusLabels: Record<string, string> = {
  scheduled: "Scheduled",
  SCHEDULED: "Scheduled",
  in_progress: "In Progress",
  IN_PROGRESS: "In Progress",
  completed: "Completed",
  COMPLETED: "Completed",
  cancelled: "Cancelled",
  CANCELLED: "Cancelled",
}

const jobStatusColors: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-700",
  SCHEDULED: "bg-blue-100 text-blue-700",
  in_progress: "bg-amber-100 text-amber-700",
  IN_PROGRESS: "bg-amber-100 text-amber-700",
  completed: "bg-green-100 text-green-700",
  COMPLETED: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-700",
  CANCELLED: "bg-gray-100 text-gray-700",
}

// Action icon mapping
const actionIcons: Record<string, typeof Circle> = {
  request_customer_auth: User,
  awaiting_signature: Clock,
  submit_to_insurer: Send,
  mark_insurer_approved: Shield,
  mark_needs_revision: AlertCircle,
  resubmit_to_insurer: Send,
  create_job: Briefcase,
  start_job: Briefcase,
  complete_job: CheckCircle2,
  create_insurer_invoice: FileText,
  create_customer_invoice: FileText,
  collect_payment: DollarSign,
  close_claim: CheckCircle2,
  claim_closed: CheckCircle2,
}

export function WorkflowCard({
  workflow,
  isLoading = false,
  onAction,
  actionLoadingKey,
  className,
  variant = 'default',
}: WorkflowCardProps) {
  const { state, next_actions, primary_action } = workflow

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  // Check if a stage is complete
  const isCustomerComplete = state.customer_status === "authorized"
  const isInsurerComplete = state.insurer_status === "approved"
  const isJobComplete = state.job_status
    ? ["completed", "COMPLETED"].includes(state.job_status)
    : true
  const isPaid = state.all_invoices_paid && state.invoices_count > 0

  // Compact variant - for embedding in lists
  if (variant === 'compact') {
    return (
      <div className={cn("flex items-center gap-3", className)}>
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : (
          <>
            {/* Condensed status badges */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <Badge
                variant="secondary"
                className={cn("text-xs", customerStatusColors[state.customer_status])}
              >
                {customerStatusLabels[state.customer_status] || state.customer_status}
              </Badge>
              <Badge
                variant="secondary"
                className={cn("text-xs", insurerStatusColors[state.insurer_status])}
              >
                {insurerStatusLabels[state.insurer_status] || state.insurer_status}
              </Badge>
              {state.job_status && (
                <Badge
                  variant="secondary"
                  className={cn("text-xs", jobStatusColors[state.job_status])}
                >
                  {jobStatusLabels[state.job_status] || state.job_status}
                </Badge>
              )}
            </div>

            {/* Primary action only */}
            {primary_action && primary_action.enabled && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="default"
                      size="sm"
                      disabled={actionLoadingKey === primary_action.key}
                      onClick={(e) => {
                        e.stopPropagation()
                        onAction?.(primary_action.key)
                      }}
                    >
                      {actionLoadingKey === primary_action.key ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <>
                          {(() => {
                            const Icon = actionIcons[primary_action.key] || Circle
                            return <Icon className="h-3 w-3 mr-1" />
                          })()}
                          {primary_action.label}
                        </>
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">{primary_action.description}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </>
        )}
      </div>
    )
  }

  // Default full variant
  return (
    <Card className={cn("border-primary/20", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <ArrowRight className="h-4 w-4 text-primary" />
          Workflow Progress
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Status Progress */}
            <div className="flex items-center gap-2 text-sm flex-wrap">
              {/* Customer Status */}
              <div className="flex items-center gap-1.5">
                {isCustomerComplete ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="text-muted-foreground">Customer:</span>
                <Badge
                  variant="secondary"
                  className={cn(
                    "text-xs",
                    customerStatusColors[state.customer_status]
                  )}
                >
                  {customerStatusLabels[state.customer_status] ||
                    state.customer_status}
                </Badge>
              </div>

              <span className="text-muted-foreground hidden sm:inline">
                |
              </span>

              {/* Insurer Status */}
              <div className="flex items-center gap-1.5">
                {isInsurerComplete ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="text-muted-foreground">Insurer:</span>
                <Badge
                  variant="secondary"
                  className={cn(
                    "text-xs",
                    insurerStatusColors[state.insurer_status]
                  )}
                >
                  {insurerStatusLabels[state.insurer_status] ||
                    state.insurer_status}
                </Badge>
              </div>

              {/* Job Status (if exists) */}
              {state.job_id && state.job_status && (
                <>
                  <span className="text-muted-foreground hidden sm:inline">
                    |
                  </span>
                  <div className="flex items-center gap-1.5">
                    {isJobComplete ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <Circle className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span className="text-muted-foreground">Job:</span>
                    <Badge
                      variant="secondary"
                      className={cn(
                        "text-xs",
                        jobStatusColors[state.job_status]
                      )}
                    >
                      {jobStatusLabels[state.job_status] || state.job_status}
                    </Badge>
                  </div>
                </>
              )}
            </div>

            {/* Invoice Summary */}
            {state.invoices_count > 0 && (
              <div className="flex items-center gap-4 text-sm bg-slate-50 rounded-lg p-2">
                <div className="flex items-center gap-1.5">
                  {isPaid ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="font-medium">
                    {state.invoices_count} Invoice
                    {state.invoices_count !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="flex items-center gap-3 ml-auto">
                  <span className="text-muted-foreground">
                    Total: {formatCurrency(state.invoices_total)}
                  </span>
                  <span className="text-green-600">
                    Paid: {formatCurrency(state.invoices_paid)}
                  </span>
                  {state.invoices_balance > 0 && (
                    <span className="text-red-600 font-medium">
                      Due: {formatCurrency(state.invoices_balance)}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Next Actions */}
            {next_actions.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Next Steps
                </p>
                <div className="flex flex-wrap gap-2">
                  <TooltipProvider>
                    {next_actions.map((action) => {
                      const Icon = actionIcons[action.key] || Circle
                      const isLoading = actionLoadingKey === action.key
                      const isPrimary =
                        primary_action?.key === action.key && action.enabled

                      return (
                        <Tooltip key={action.key}>
                          <TooltipTrigger asChild>
                            <div>
                              <Button
                                variant={isPrimary ? "default" : "outline"}
                                size="sm"
                                disabled={!action.enabled || isLoading}
                                onClick={() =>
                                  action.enabled && onAction?.(action.key)
                                }
                                className={cn(
                                  !action.enabled &&
                                    "opacity-50 cursor-not-allowed"
                                )}
                              >
                                {isLoading ? (
                                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                                ) : (
                                  <Icon className="h-4 w-4 mr-1.5" />
                                )}
                                {action.label}
                              </Button>
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="max-w-xs">
                              {action.enabled
                                ? action.description
                                : action.reason_disabled || action.description}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      )
                    })}
                  </TooltipProvider>
                </div>
              </div>
            )}

            {/* All complete message */}
            {next_actions.length === 0 && (
              <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 rounded-lg p-3">
                <CheckCircle2 className="h-5 w-5" />
                <span>
                  All workflow steps complete. Claim is closed.
                </span>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default WorkflowCard
