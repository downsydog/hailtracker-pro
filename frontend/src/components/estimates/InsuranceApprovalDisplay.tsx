/**
 * Insurance Approval Display Component
 *
 * Shows the insurance approval status with financial details.
 * Displays requested vs approved amounts and short-paid delta.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  CheckCircle,
  Clock,
  XCircle,
  AlertTriangle,
  FileEdit,
  Lock
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { InsurerStatus } from '@/hooks/use-pdr-estimates'

interface InsuranceApprovalDisplayProps {
  insurerStatus: InsurerStatus
  requestedTotal: number
  approvedTotal: number | null
  shortPaidAmount: number | null
  hasPartialApproval: boolean
  approvalNotes?: string | null
  approvalReference?: string | null
  approvedAt?: string | null
  isLocked?: boolean
  className?: string
}

const STATUS_CONFIG: Record<InsurerStatus, {
  icon: React.ElementType
  label: string
  color: string
  bgColor: string
  borderColor: string
}> = {
  not_submitted: {
    icon: Clock,
    label: 'Not Submitted',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200'
  },
  submitted: {
    icon: Clock,
    label: 'Submitted',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  },
  approved: {
    icon: CheckCircle,
    label: 'Approved',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  declined: {
    icon: XCircle,
    label: 'Declined',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200'
  },
  needs_revision: {
    icon: FileEdit,
    label: 'Needs Revision',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200'
  }
}

export function InsuranceApprovalDisplay({
  insurerStatus,
  requestedTotal,
  approvedTotal,
  shortPaidAmount,
  hasPartialApproval,
  approvalNotes,
  approvalReference,
  approvedAt,
  isLocked,
  className
}: InsuranceApprovalDisplayProps) {
  const config = STATUS_CONFIG[insurerStatus]
  const StatusIcon = config.icon

  // Only show financial details if approved
  const showFinancials = insurerStatus === 'approved' && approvedTotal !== null

  return (
    <Card className={cn(config.bgColor, config.borderColor, 'border', className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusIcon className={cn('h-5 w-5', config.color)} />
            <span>Insurer Status</span>
          </div>
          <Badge
            variant="outline"
            className={cn(
              config.color,
              config.borderColor,
              'border'
            )}
          >
            {config.label}
            {isLocked && insurerStatus === 'approved' && (
              <Lock className="h-3 w-3 ml-1" />
            )}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {showFinancials && (
          <>
            {/* Financial summary */}
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-wide">
                  Requested
                </div>
                <div className="text-lg font-semibold">
                  ${requestedTotal.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-wide">
                  Approved
                </div>
                <div className={cn(
                  'text-lg font-semibold',
                  hasPartialApproval ? 'text-amber-600' : 'text-green-600'
                )}>
                  ${approvedTotal.toFixed(2)}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-wide">
                  Delta
                </div>
                <div className={cn(
                  'text-lg font-semibold',
                  shortPaidAmount && shortPaidAmount > 0
                    ? 'text-red-600'
                    : 'text-green-600'
                )}>
                  {shortPaidAmount && shortPaidAmount > 0 ? (
                    <>-${shortPaidAmount.toFixed(2)}</>
                  ) : (
                    <>$0.00</>
                  )}
                </div>
              </div>
            </div>

            {/* Partial approval warning */}
            {hasPartialApproval && (
              <div className="flex items-center gap-2 p-2 bg-amber-100 rounded text-amber-800 text-sm">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span>
                  Partial approval - short paid by ${shortPaidAmount?.toFixed(2)}
                </span>
              </div>
            )}

            {/* Reference and notes */}
            {(approvalReference || approvalNotes) && (
              <div className="space-y-2 pt-2 border-t border-gray-200">
                {approvalReference && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Reference: </span>
                    <span className="font-medium">{approvalReference}</span>
                  </div>
                )}
                {approvalNotes && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Notes: </span>
                    <span>{approvalNotes}</span>
                  </div>
                )}
              </div>
            )}

            {/* Approved date */}
            {approvedAt && (
              <div className="text-xs text-muted-foreground pt-1">
                Approved on {new Date(approvedAt).toLocaleDateString()} at{' '}
                {new Date(approvedAt).toLocaleTimeString([], {
                  hour: 'numeric',
                  minute: '2-digit'
                })}
              </div>
            )}
          </>
        )}

        {/* Locked notice */}
        {isLocked && insurerStatus === 'approved' && (
          <div className="flex items-center gap-2 p-2 bg-gray-100 rounded text-gray-700 text-sm">
            <Lock className="h-4 w-4 flex-shrink-0" />
            <span>Estimate locked. Changes require supplements.</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Compact inline version for use in lists/headers
 */
export function InsuranceApprovalBadge({
  insurerStatus,
  hasPartialApproval,
  shortPaidAmount
}: {
  insurerStatus: InsurerStatus
  hasPartialApproval?: boolean
  shortPaidAmount?: number | null
}) {
  const config = STATUS_CONFIG[insurerStatus]
  const StatusIcon = config.icon

  return (
    <div className="flex items-center gap-2">
      <Badge
        variant="outline"
        className={cn(config.color, config.borderColor, 'border gap-1')}
      >
        <StatusIcon className="h-3 w-3" />
        {config.label}
      </Badge>
      {hasPartialApproval && shortPaidAmount && shortPaidAmount > 0 && (
        <Badge variant="outline" className="text-amber-600 border-amber-300">
          <AlertTriangle className="h-3 w-3 mr-1" />
          -${shortPaidAmount.toFixed(2)}
        </Badge>
      )}
    </div>
  )
}

export default InsuranceApprovalDisplay
