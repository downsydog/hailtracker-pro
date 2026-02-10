/**
 * Estimate Status Bar Component
 *
 * Desktop: Sticky header with running total, save status, and panel stats
 * Mobile: Floating bottom bar with compact total and status
 *
 * Provides always-visible feedback during panel entry.
 */

import { useCallback } from 'react'
import { Loader2, CheckCircle, AlertCircle, ChevronUp, ChevronDown, Download, Image, FileText, Send, Plus, Archive, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface EstimateStatusBarProps {
  // Estimate info
  estimateNumber?: string
  vehicleInfo?: string  // e.g., "2024 Ford F-150"

  // Totals
  total: number

  // Panel stats
  damagedCount: number
  selectedCount?: number
  selectionMode?: boolean

  // Save status
  saveStatus: SaveStatus
  lastSavedAt?: Date | null
  onRetrySave?: () => void

  // Export actions (only available when saved)
  isSaved?: boolean  // Whether the estimate has been saved to backend
  onDownloadPDF?: () => void
  isDownloadingPDF?: boolean
  onDownloadPhotoSheet?: () => void
  isDownloadingPhotoSheet?: boolean
  onDownloadDisputePack?: () => void
  isDownloadingDisputePack?: boolean
  onSendToAdjuster?: () => void
  onCreateSupplement?: () => void
  onCreateShareLink?: () => void

  // Permissions for UI gating (from auth context)
  permissions?: ExportMenuPermissions

  // Actions
  onReview?: () => void

  // Overlay visibility (to hide mobile bar when overlay is open)
  overlayOpen?: boolean

  className?: string
}

// Format currency
const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount)
}

// Format relative time
const formatRelativeTime = (date: Date) => {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

// Save status indicator component
function SaveStatusIndicator({
  status,
  lastSavedAt,
  onRetry,
  compact = false
}: {
  status: SaveStatus
  lastSavedAt?: Date | null
  onRetry?: () => void
  compact?: boolean
}) {
  if (status === 'saving') {
    return (
      <span className={cn(
        "flex items-center gap-1 text-blue-600",
        compact ? "text-xs" : "text-sm"
      )}>
        <Loader2 className={cn("animate-spin", compact ? "h-3 w-3" : "h-4 w-4")} />
        {!compact && <span>Saving...</span>}
      </span>
    )
  }

  if (status === 'saved') {
    return (
      <span className={cn(
        "flex items-center gap-1 text-green-600",
        compact ? "text-xs" : "text-sm"
      )}>
        <CheckCircle className={cn(compact ? "h-3 w-3" : "h-4 w-4")} />
        {!compact && <span>Saved</span>}
      </span>
    )
  }

  if (status === 'error') {
    return (
      <button
        onClick={onRetry}
        className={cn(
          "flex items-center gap-1 text-red-600 hover:text-red-700",
          compact ? "text-xs" : "text-sm"
        )}
      >
        <AlertCircle className={cn(compact ? "h-3 w-3" : "h-4 w-4")} />
        {!compact && <span>Retry</span>}
      </button>
    )
  }

  // Idle - show last saved time if available
  if (lastSavedAt) {
    return (
      <span className={cn(
        "text-muted-foreground",
        compact ? "text-xs" : "text-sm"
      )}>
        {compact ? formatRelativeTime(lastSavedAt) : `Saved ${formatRelativeTime(lastSavedAt)}`}
      </span>
    )
  }

  return null
}

// Permission props for UI gating
interface ExportMenuPermissions {
  canSendEmail?: boolean
  canCreateShareLink?: boolean
  canDownloadDisputePack?: boolean
  canCreateSupplement?: boolean
}

// Export dropdown menu component
function ExportMenu({
  isSaved,
  onDownloadPDF,
  isDownloadingPDF,
  onDownloadPhotoSheet,
  isDownloadingPhotoSheet,
  onDownloadDisputePack,
  isDownloadingDisputePack,
  onSendToAdjuster,
  onCreateSupplement,
  onCreateShareLink,
  permissions,
  compact = false
}: {
  isSaved: boolean
  onDownloadPDF?: () => void
  isDownloadingPDF?: boolean
  onDownloadPhotoSheet?: () => void
  isDownloadingPhotoSheet?: boolean
  onDownloadDisputePack?: () => void
  isDownloadingDisputePack?: boolean
  onSendToAdjuster?: () => void
  onCreateSupplement?: () => void
  onCreateShareLink?: () => void
  permissions?: ExportMenuPermissions
  compact?: boolean
}) {
  const isAnyDownloading = isDownloadingPDF || isDownloadingPhotoSheet || isDownloadingDisputePack

  // Default to all permissions if not provided (backwards compatibility)
  const perms = {
    canSendEmail: permissions?.canSendEmail ?? true,
    canCreateShareLink: permissions?.canCreateShareLink ?? true,
    canDownloadDisputePack: permissions?.canDownloadDisputePack ?? true,
    canCreateSupplement: permissions?.canCreateSupplement ?? true,
  }

  const noPermissionLabel = "Requires Admin/Estimator role"

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size={compact ? "icon" : "sm"}
          disabled={!isSaved}
          className={cn(compact ? "h-8 w-8" : "h-8")}
          title={!isSaved ? "Save estimate to enable exports" : "Export options"}
        >
          {isAnyDownloading ? (
            <Loader2 className={cn("animate-spin", compact ? "h-4 w-4" : "h-4 w-4 mr-1")} />
          ) : (
            <Download className={cn(compact ? "h-4 w-4" : "h-4 w-4 mr-1")} />
          )}
          {!compact && (
            <>
              Export
              <ChevronDown className="h-3 w-3 ml-1" />
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {/* Send to Adjuster - primary action (permission gated) */}
        {onSendToAdjuster && (
          <>
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                if (perms.canSendEmail) onSendToAdjuster()
              }}
              disabled={!perms.canSendEmail}
              className={cn("cursor-pointer", !perms.canSendEmail && "opacity-50")}
              title={!perms.canSendEmail ? noPermissionLabel : undefined}
            >
              <Send className="h-4 w-4 mr-2" />
              Send to Adjuster...
              {!perms.canSendEmail && (
                <span className="ml-auto text-xs text-muted-foreground">🔒</span>
              )}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem
          onClick={(e) => {
            e.stopPropagation()
            onDownloadPDF?.()
          }}
          disabled={isDownloadingPDF || !onDownloadPDF}
          className="cursor-pointer"
        >
          <FileText className="h-4 w-4 mr-2" />
          {isDownloadingPDF ? (
            <span className="flex items-center gap-1">
              Estimate PDF
              <Loader2 className="h-3 w-3 animate-spin ml-1" />
            </span>
          ) : (
            'Estimate PDF'
          )}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={(e) => {
            e.stopPropagation()
            onDownloadPhotoSheet?.()
          }}
          disabled={isDownloadingPhotoSheet || !onDownloadPhotoSheet}
          className="cursor-pointer"
        >
          <Image className="h-4 w-4 mr-2" />
          {isDownloadingPhotoSheet ? (
            <span className="flex items-center gap-1">
              Photo Sheet
              <Loader2 className="h-3 w-3 animate-spin ml-1" />
            </span>
          ) : (
            'Photo Sheet'
          )}
        </DropdownMenuItem>
        {/* Dispute Pack - permission gated */}
        <DropdownMenuItem
          onClick={(e) => {
            e.stopPropagation()
            if (perms.canDownloadDisputePack) onDownloadDisputePack?.()
          }}
          disabled={isDownloadingDisputePack || !onDownloadDisputePack || !perms.canDownloadDisputePack}
          className={cn("cursor-pointer", !perms.canDownloadDisputePack && "opacity-50")}
          title={!perms.canDownloadDisputePack ? noPermissionLabel : undefined}
        >
          <Archive className="h-4 w-4 mr-2" />
          {isDownloadingDisputePack ? (
            <span className="flex items-center gap-1">
              Dispute Pack (ZIP)
              <Loader2 className="h-3 w-3 animate-spin ml-1" />
            </span>
          ) : (
            <>
              Dispute Pack (ZIP)
              {!perms.canDownloadDisputePack && (
                <span className="ml-auto text-xs text-muted-foreground">🔒</span>
              )}
            </>
          )}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {/* Create Supplement - permission gated */}
        {onCreateSupplement ? (
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation()
              if (perms.canCreateSupplement) onCreateSupplement()
            }}
            disabled={!perms.canCreateSupplement}
            className={cn("cursor-pointer", !perms.canCreateSupplement && "opacity-50")}
            title={!perms.canCreateSupplement ? noPermissionLabel : undefined}
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Supplement...
            {!perms.canCreateSupplement && (
              <span className="ml-auto text-xs text-muted-foreground">🔒</span>
            )}
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem disabled className="cursor-not-allowed opacity-50">
            <FileText className="h-4 w-4 mr-2" />
            Supplement PDF
            <span className="ml-auto text-xs text-muted-foreground">Soon</span>
          </DropdownMenuItem>
        )}
        {/* Create Share Link - permission gated */}
        {onCreateShareLink && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                if (perms.canCreateShareLink) onCreateShareLink()
              }}
              disabled={!perms.canCreateShareLink}
              className={cn("cursor-pointer", !perms.canCreateShareLink && "opacity-50")}
              title={!perms.canCreateShareLink ? noPermissionLabel : undefined}
            >
              <Link2 className="h-4 w-4 mr-2" />
              Create Share Link...
              {!perms.canCreateShareLink && (
                <span className="ml-auto text-xs text-muted-foreground">🔒</span>
              )}
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function EstimateStatusBar({
  estimateNumber,
  vehicleInfo,
  total,
  damagedCount,
  selectedCount = 0,
  selectionMode = false,
  saveStatus,
  lastSavedAt,
  onRetrySave,
  isSaved = false,
  onDownloadPDF,
  isDownloadingPDF = false,
  onDownloadPhotoSheet,
  isDownloadingPhotoSheet = false,
  onDownloadDisputePack,
  isDownloadingDisputePack = false,
  onSendToAdjuster,
  onCreateSupplement,
  onCreateShareLink,
  permissions,
  onReview,
  overlayOpen = false,
  className
}: EstimateStatusBarProps) {

  const handleBarClick = useCallback(() => {
    if (onReview) {
      onReview()
    }
  }, [onReview])

  const hasExportOptions = onDownloadPDF || onDownloadPhotoSheet || onDownloadDisputePack || onSendToAdjuster || onCreateSupplement || onCreateShareLink

  return (
    <>
      {/* Desktop Sticky Header */}
      <div className={cn(
        "hidden lg:block sticky top-0 z-30 bg-white border-b shadow-sm",
        className
      )}>
        <div className="px-4 py-2">
          {/* Main row */}
          <div className="flex items-center justify-between">
            {/* Left: Estimate info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                {estimateNumber && (
                  <span className="text-sm font-medium text-muted-foreground">
                    {estimateNumber}
                  </span>
                )}
                {vehicleInfo && (
                  <span className="text-sm text-muted-foreground truncate">
                    {vehicleInfo}
                  </span>
                )}
              </div>
            </div>

            {/* Center: Running Total */}
            <div className="flex-shrink-0 px-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {formatCurrency(total)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Running Total
                </div>
              </div>
            </div>

            {/* Right: Save status + Export */}
            <div className="flex-1 min-w-0 flex justify-end items-center gap-3">
              <SaveStatusIndicator
                status={saveStatus}
                lastSavedAt={lastSavedAt}
                onRetry={onRetrySave}
              />
              {hasExportOptions && (
                <ExportMenu
                  isSaved={isSaved}
                  onDownloadPDF={onDownloadPDF}
                  isDownloadingPDF={isDownloadingPDF}
                  onDownloadPhotoSheet={onDownloadPhotoSheet}
                  isDownloadingPhotoSheet={isDownloadingPhotoSheet}
                  onDownloadDisputePack={onDownloadDisputePack}
                  isDownloadingDisputePack={isDownloadingDisputePack}
                  onSendToAdjuster={onSendToAdjuster}
                  onCreateSupplement={onCreateSupplement}
                  onCreateShareLink={onCreateShareLink}
                  permissions={permissions}
                />
              )}
            </div>
          </div>

          {/* Secondary row: Stats */}
          <div className="flex items-center justify-center gap-4 mt-1">
            <span className="text-xs text-muted-foreground">
              <span className="font-medium text-blue-600">{damagedCount}</span>
              {' '}panel{damagedCount !== 1 ? 's' : ''} with damage
            </span>
            {selectionMode && selectedCount > 0 && (
              <span className="text-xs text-muted-foreground">
                <span className="font-medium text-purple-600">{selectedCount}</span>
                {' '}selected
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Floating Bottom Bar */}
      {!overlayOpen && (
        <div
          className={cn(
            "lg:hidden fixed bottom-16 left-2 right-2 z-40",
            "bg-white border rounded-xl shadow-lg",
            "transition-all duration-200"
          )}
        >
          <div className="flex items-center justify-between px-4 py-3">
            {/* Left: Total */}
            <div
              className={cn(
                "flex-shrink-0",
                onReview && "cursor-pointer active:scale-[0.98]"
              )}
              onClick={handleBarClick}
            >
              <div className="text-xl font-bold text-primary">
                {formatCurrency(total)}
              </div>
            </div>

            {/* Middle: Stats */}
            <div
              className="flex items-center gap-3 text-xs text-muted-foreground flex-1 justify-center"
              onClick={handleBarClick}
            >
              <span>
                <span className="font-semibold text-blue-600">{damagedCount}</span> damaged
              </span>
              {selectionMode && selectedCount > 0 && (
                <span>
                  <span className="font-semibold text-purple-600">{selectedCount}</span> selected
                </span>
              )}
            </div>

            {/* Right: Save status + Export */}
            <div className="flex items-center gap-2">
              <SaveStatusIndicator
                status={saveStatus}
                lastSavedAt={lastSavedAt}
                onRetry={onRetrySave}
                compact
              />
              {hasExportOptions && (
                <ExportMenu
                  isSaved={isSaved}
                  onDownloadPDF={onDownloadPDF}
                  isDownloadingPDF={isDownloadingPDF}
                  onDownloadPhotoSheet={onDownloadPhotoSheet}
                  isDownloadingPhotoSheet={isDownloadingPhotoSheet}
                  onDownloadDisputePack={onDownloadDisputePack}
                  isDownloadingDisputePack={isDownloadingDisputePack}
                  onSendToAdjuster={onSendToAdjuster}
                  onCreateSupplement={onCreateSupplement}
                  onCreateShareLink={onCreateShareLink}
                  permissions={permissions}
                  compact
                />
              )}
              {onReview && (
                <ChevronUp
                  className="h-4 w-4 text-muted-foreground cursor-pointer"
                  onClick={handleBarClick}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Collapsed pill when overlay is open on mobile */}
      {overlayOpen && (
        <div
          className={cn(
            "lg:hidden fixed bottom-2 left-1/2 -translate-x-1/2 z-30",
            "bg-white/90 backdrop-blur border rounded-full shadow-md",
            "px-4 py-1.5",
            "transition-all duration-200"
          )}
        >
          <div className="flex items-center gap-2 text-sm">
            <span className="font-bold text-primary">
              {formatCurrency(total)}
            </span>
            <span className="text-muted-foreground">•</span>
            <span className="text-xs text-muted-foreground">
              {damagedCount} panels
            </span>
          </div>
        </div>
      )}
    </>
  )
}

export default EstimateStatusBar
