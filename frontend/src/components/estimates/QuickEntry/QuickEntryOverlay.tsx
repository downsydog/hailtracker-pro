/**
 * Quick Entry Overlay
 * Fast inline panel damage entry without modal
 * Appears as popover on desktop, bottom sheet on mobile
 */

import { useEffect, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { X, ChevronRight, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { COUNT_RANGES, DENT_SIZES, type CountRange, type DentSize, type PanelDamage } from '../PanelEntry/PanelEntryModal'

// Depth options
const DEPTH_OPTIONS = [
  { id: 'shallow', label: 'Shallow', multiplier: 1.0 },
  { id: 'medium', label: 'Medium', multiplier: 1.15 },
  { id: 'deep', label: 'Deep', multiplier: 1.35 },
  { id: 'severe', label: 'Severe', multiplier: 1.6 },
] as const

// Zone options
const ZONE_OPTIONS = [
  { id: 'center', label: 'Center', multiplier: 1.0 },
  { id: 'edge', label: 'Edge', multiplier: 1.1 },
  { id: 'crease', label: 'Crease', multiplier: 1.25 },
  { id: 'body_line', label: 'Body Line', multiplier: 1.35 },
] as const

export type Depth = typeof DEPTH_OPTIONS[number]['id']
export type Zone = typeof ZONE_OPTIONS[number]['id']

export interface QuickEntryValue extends PanelDamage {
  depth?: Depth
  zone?: Zone
}

interface QuickEntryOverlayProps {
  open: boolean
  panelKey: string
  panelName: string
  value: QuickEntryValue
  onChange: (updates: Partial<QuickEntryValue>) => void
  onClose: () => void
  onOpenDetails: () => void
  onRepeatLast?: () => void
  hasLastUsed?: boolean
  anchorPoint?: { x: number; y: number }
  panelPrice: number
  className?: string
  // Batch selection props
  selectedCount?: number
  onApplyToSelected?: () => void
  onClearSelection?: () => void
}

export function QuickEntryOverlay({
  open,
  panelKey: _panelKey,
  panelName,
  value,
  onChange,
  onClose,
  onOpenDetails,
  onRepeatLast,
  hasLastUsed,
  anchorPoint,
  panelPrice,
  className,
  selectedCount = 0,
  onApplyToSelected,
  onClearSelection,
}: QuickEntryOverlayProps) {
  // panelKey available as _panelKey for future use (e.g., caching, keying)
  const overlayRef = useRef<HTMLDivElement>(null)
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768

  // Close on Escape key
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  // Close on outside click
  useEffect(() => {
    if (!open) return

    const handleClick = (e: MouseEvent) => {
      if (overlayRef.current && !overlayRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    // Delay to avoid immediate close from the triggering click
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClick)
    }, 100)

    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [open, onClose])

  // Calculate position for popover mode
  const getPopoverStyle = useCallback((): React.CSSProperties => {
    if (isMobile || !anchorPoint) return {}

    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const overlayWidth = 320
    const overlayHeight = 480

    let left = anchorPoint.x + 16
    let top = anchorPoint.y - 100

    // Keep within viewport
    if (left + overlayWidth > viewportWidth - 16) {
      left = anchorPoint.x - overlayWidth - 16
    }
    if (left < 16) left = 16

    if (top + overlayHeight > viewportHeight - 16) {
      top = viewportHeight - overlayHeight - 16
    }
    if (top < 80) top = 80 // Account for header

    return {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
      width: `${overlayWidth}px`,
      maxHeight: `${overlayHeight}px`,
    }
  }, [anchorPoint, isMobile])

  if (!open) return null

  const handleCountChange = (countRange: CountRange) => {
    onChange({ countRange })
  }

  const handleSizeChange = (dentSize: DentSize) => {
    onChange({ dentSize })
  }

  const handleDepthChange = (depth: Depth) => {
    onChange({ depth } as Partial<QuickEntryValue>)
  }

  const handleZoneChange = (zone: Zone) => {
    onChange({ zone } as Partial<QuickEntryValue>)
  }

  const handleAddonToggle = (addon: keyof Pick<QuickEntryValue, 'gluePull' | 'aluminum' | 'hss' | 'doubleMetal'>) => {
    onChange({ [addon]: !value[addon] })
  }

  return (
    <>
      {/* Backdrop for mobile */}
      {isMobile && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Overlay */}
      <div
        ref={overlayRef}
        className={cn(
          'bg-white rounded-lg shadow-xl border z-50 overflow-hidden flex flex-col',
          isMobile
            ? 'fixed inset-x-0 bottom-0 rounded-b-none max-h-[80vh] animate-in slide-in-from-bottom duration-200'
            : 'animate-in fade-in zoom-in-95 duration-150',
          className
        )}
        style={!isMobile ? getPopoverStyle() : undefined}
        role="dialog"
        aria-label={`Quick entry for ${panelName}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900">{panelName}</span>
              {value.countRange && value.dentSize && (
                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                  {value.countRange} • {value.dentSize}
                </span>
              )}
            </div>
            {selectedCount > 1 && (
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-purple-600 font-medium">
                  {selectedCount} panels selected
                </span>
                {onClearSelection && (
                  <button
                    onClick={onClearSelection}
                    className="text-xs text-purple-600 hover:text-purple-800 underline"
                  >
                    Clear
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-lg font-bold text-green-600 mr-2">
              ${panelPrice.toFixed(0)}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Dent Count */}
          <div>
            <Label className="text-xs font-semibold text-gray-500 mb-2 block">DENT COUNT</Label>
            <div className="grid grid-cols-4 gap-1.5">
              {COUNT_RANGES.slice(0, 4).map((range) => (
                <Button
                  key={range.id}
                  variant={value.countRange === range.id ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'h-9 text-xs font-medium',
                    value.countRange === range.id && 'bg-blue-600 hover:bg-blue-700'
                  )}
                  onClick={() => handleCountChange(range.id)}
                >
                  {range.label}
                </Button>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-1.5 mt-1.5">
              {COUNT_RANGES.slice(4).map((range) => (
                <Button
                  key={range.id}
                  variant={value.countRange === range.id ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'h-9 text-xs font-medium',
                    value.countRange === range.id && 'bg-blue-600 hover:bg-blue-700'
                  )}
                  onClick={() => handleCountChange(range.id)}
                >
                  {range.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Dent Size */}
          <div>
            <Label className="text-xs font-semibold text-gray-500 mb-2 block">SIZE</Label>
            <div className="grid grid-cols-4 gap-1.5">
              {DENT_SIZES.map((size) => (
                <Button
                  key={size.id}
                  variant={value.dentSize === size.id ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'h-9 text-xs font-medium',
                    value.dentSize === size.id && 'bg-blue-600 hover:bg-blue-700'
                  )}
                  onClick={() => handleSizeChange(size.id)}
                >
                  {size.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Depth (optional quick select) */}
          <div>
            <Label className="text-xs font-semibold text-gray-500 mb-2 block">DEPTH</Label>
            <div className="grid grid-cols-4 gap-1.5">
              {DEPTH_OPTIONS.map((depth) => (
                <Button
                  key={depth.id}
                  variant={value.depth === depth.id ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'h-8 text-xs',
                    value.depth === depth.id && 'bg-purple-600 hover:bg-purple-700'
                  )}
                  onClick={() => handleDepthChange(depth.id)}
                >
                  {depth.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Zone (optional quick select) */}
          <div>
            <Label className="text-xs font-semibold text-gray-500 mb-2 block">ZONE</Label>
            <div className="grid grid-cols-4 gap-1.5">
              {ZONE_OPTIONS.map((zone) => (
                <Button
                  key={zone.id}
                  variant={value.zone === zone.id ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'h-8 text-xs',
                    value.zone === zone.id && 'bg-amber-600 hover:bg-amber-700 text-white'
                  )}
                  onClick={() => handleZoneChange(zone.id)}
                >
                  {zone.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Quick Add-ons */}
          <div>
            <Label className="text-xs font-semibold text-gray-500 mb-2 block">ADD-ONS</Label>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 p-2 rounded bg-gray-50 cursor-pointer hover:bg-gray-100">
                <Checkbox
                  checked={value.gluePull}
                  onCheckedChange={() => handleAddonToggle('gluePull')}
                />
                <span className="text-xs">Glue Pull</span>
                <span className="text-xs text-blue-600 ml-auto">+25%</span>
              </label>
              <label className="flex items-center gap-2 p-2 rounded bg-gray-50 cursor-pointer hover:bg-gray-100">
                <Checkbox
                  checked={value.aluminum}
                  onCheckedChange={() => handleAddonToggle('aluminum')}
                />
                <span className="text-xs">Aluminum</span>
                <span className="text-xs text-amber-600 ml-auto">+25%</span>
              </label>
              <label className="flex items-center gap-2 p-2 rounded bg-gray-50 cursor-pointer hover:bg-gray-100">
                <Checkbox
                  checked={value.hss}
                  onCheckedChange={() => handleAddonToggle('hss')}
                />
                <span className="text-xs">HSS</span>
                <span className="text-xs text-purple-600 ml-auto">+25%</span>
              </label>
              <label className="flex items-center gap-2 p-2 rounded bg-gray-50 cursor-pointer hover:bg-gray-100">
                <Checkbox
                  checked={value.doubleMetal}
                  onCheckedChange={() => handleAddonToggle('doubleMetal')}
                />
                <span className="text-xs">Double Metal</span>
                <span className="text-xs text-red-600 ml-auto">+50%</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
          <div className="flex gap-2">
            {hasLastUsed && onRepeatLast && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRepeatLast}
                className="text-xs"
                title="Apply last used settings"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Repeat
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenDetails}
              className="text-xs"
            >
              More
              <ChevronRight className="h-3 w-3 ml-1" />
            </Button>
          </div>
          <div className="flex gap-2">
            {selectedCount > 1 && onApplyToSelected && value.countRange && value.dentSize && (
              <Button
                size="sm"
                variant="secondary"
                onClick={onApplyToSelected}
                className="bg-purple-600 hover:bg-purple-700 text-white"
              >
                Apply to {selectedCount}
              </Button>
            )}
            <Button
              size="sm"
              onClick={onClose}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Done • ${panelPrice.toFixed(0)}
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}

export default QuickEntryOverlay
