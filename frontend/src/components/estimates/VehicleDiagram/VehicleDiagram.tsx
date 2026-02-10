/**
 * Vehicle Diagram Component
 * Renders the appropriate vehicle SVG based on vehicle type
 * Handles panel selection and long-press for conventional repair marking
 * Supports quick entry mode with click anchor positions
 */

import { useRef, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Car, Truck } from 'lucide-react'
import { CarSvg } from './CarSvg'
import { TruckSvg } from './TruckSvg'
import { SuvSvg } from './SuvSvg'
import { cn } from '@/lib/utils'
import { getSeverityFillColor, getSeverityLabel, type SeverityLevel } from './severity'

export type VehicleType = 'car' | 'truck' | 'suv'

export interface PanelState {
  selected: boolean      // Primary panel being edited
  damaged: boolean       // Has damage data
  conventional: boolean  // Marked for conventional repair
  batchSelected?: boolean // Part of batch selection set
  severityLevel?: 0 | 1 | 2 | 3 | 4  // Heat map intensity
  badgeText?: string     // Optional badge (e.g., count range)
}

export interface PanelClickEvent {
  panelId: string
  anchor: { x: number; y: number }
}

export interface PanelClickWithModifiers {
  panelId: string
  anchor: { x: number; y: number }
  ctrlKey: boolean
  metaKey: boolean
  shiftKey: boolean
}

interface VehicleDiagramProps {
  vehicleType: VehicleType
  onVehicleTypeChange: (type: VehicleType) => void
  panels: Record<string, PanelState>
  onPanelClick: (panelId: string) => void
  onPanelClickWithAnchor?: (event: PanelClickEvent) => void
  onPanelClickWithModifiers?: (event: PanelClickWithModifiers) => void
  onPanelLongPress: (panelId: string) => void
  onClearAll: () => void
  onClearSelection?: () => void
  onExitSelectionMode?: () => void
  onOpenPrimaryOverlay?: () => void  // Open overlay for primary panel while in selection mode
  selectionMode?: boolean
  selectedCount?: number
  primaryPanelName?: string  // Name of primary panel for display
  className?: string
}

// Detect if device is mobile (touch-based)
const isTouchDevice = () => {
  if (typeof window === 'undefined') return false
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0
}

// Panel labels for each vehicle type
export const VEHICLE_PANELS: Record<VehicleType, Record<string, string>> = {
  car: {
    hood: 'Hood',
    lff: 'Left Front Fender',
    rff: 'Right Front Fender',
    lfd: 'Left Front Door',
    rfd: 'Right Front Door',
    lrd: 'Left Rear Door',
    rrd: 'Right Rear Door',
    lrail: 'Left Roof Rail',
    rrail: 'Right Roof Rail',
    roof: 'Roof',
    lq: 'Left Quarter',
    rq: 'Right Quarter',
    deck: 'Deck Lid',
  },
  truck: {
    hood: 'Hood',
    lff: 'Left Front Fender',
    rff: 'Right Front Fender',
    lfd: 'Left Front Door',
    rfd: 'Right Front Door',
    lrd: 'Left Rear Door',
    rrd: 'Right Rear Door',
    lrail: 'Left Roof Rail',
    rrail: 'Right Roof Rail',
    roof: 'Roof',
    lbs: 'Left Bed Side',
    rbs: 'Right Bed Side',
    tailgate: 'Tailgate',
  },
  suv: {
    hood: 'Hood',
    lff: 'Left Front Fender',
    rff: 'Right Front Fender',
    lfd: 'Left Front Door',
    rfd: 'Right Front Door',
    lrd: 'Left Rear Door',
    rrd: 'Right Rear Door',
    lrail: 'Left Roof Rail',
    rrail: 'Right Roof Rail',
    roof: 'Roof',
    lq: 'Left Quarter',
    rq: 'Right Quarter',
    hatch: 'Hatch/Liftgate',
  },
}

export function VehicleDiagram({
  vehicleType,
  onVehicleTypeChange,
  panels,
  onPanelClick,
  onPanelClickWithAnchor,
  onPanelClickWithModifiers,
  onPanelLongPress,
  onClearAll,
  onClearSelection,
  onExitSelectionMode,
  onOpenPrimaryOverlay,
  selectionMode = false,
  selectedCount: propSelectedCount,
  primaryPanelName,
  className
}: VehicleDiagramProps) {
  const isMobile = isTouchDevice()

  // Check if we have any damaged panels (to show legend)
  const hasDamagedPanels = useMemo(() => {
    return Object.values(panels).some(p => p.damaged)
  }, [panels])

  // Track last click position and modifiers for popover anchoring
  const lastClickPosition = useRef<{ x: number; y: number }>({ x: 0, y: 0 })
  const lastClickModifiers = useRef<{ ctrlKey: boolean; metaKey: boolean; shiftKey: boolean }>({
    ctrlKey: false, metaKey: false, shiftKey: false
  })

  // Count panels with damage
  const damagedCount = Object.values(panels).filter(p => p.damaged).length
  const conventionalCount = Object.values(panels).filter(p => p.conventional).length
  const batchSelectedCount = propSelectedCount ?? Object.values(panels).filter(p => p.batchSelected).length

  // Handle panel click with position and modifier tracking
  const handlePanelClick = useCallback((panelId: string) => {
    const modifiers = lastClickModifiers.current

    // If ctrl/cmd is held or in selection mode, use modifier handler
    if (onPanelClickWithModifiers && (modifiers.ctrlKey || modifiers.metaKey || selectionMode)) {
      onPanelClickWithModifiers({
        panelId,
        anchor: lastClickPosition.current,
        ...modifiers
      })
    } else if (onPanelClickWithAnchor) {
      onPanelClickWithAnchor({
        panelId,
        anchor: lastClickPosition.current
      })
    } else {
      onPanelClick(panelId)
    }
  }, [onPanelClick, onPanelClickWithAnchor, onPanelClickWithModifiers, selectionMode])

  // Capture click position and modifiers at container level
  const handleContainerClick = useCallback((e: React.MouseEvent) => {
    lastClickPosition.current = { x: e.clientX, y: e.clientY }
    lastClickModifiers.current = {
      ctrlKey: e.ctrlKey,
      metaKey: e.metaKey,
      shiftKey: e.shiftKey
    }
  }, [])

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Vehicle Type Toggle */}
      <div className="flex justify-center gap-1 mb-4">
        <Button
          variant={vehicleType === 'car' ? 'default' : 'outline'}
          size="sm"
          onClick={() => onVehicleTypeChange('car')}
          className="min-w-[80px]"
        >
          <Car className="h-4 w-4 mr-1" />
          Car
        </Button>
        <Button
          variant={vehicleType === 'truck' ? 'default' : 'outline'}
          size="sm"
          onClick={() => onVehicleTypeChange('truck')}
          className="min-w-[80px]"
        >
          <Truck className="h-4 w-4 mr-1" />
          Truck
        </Button>
        <Button
          variant={vehicleType === 'suv' ? 'default' : 'outline'}
          size="sm"
          onClick={() => onVehicleTypeChange('suv')}
          className="min-w-[80px]"
        >
          <Car className="h-4 w-4 mr-1" />
          SUV
        </Button>
      </div>

      {/* Vehicle Diagram */}
      <div
        className="flex-1 flex items-center justify-center p-2"
        onClick={handleContainerClick}
      >
        {vehicleType === 'car' && (
          <CarSvg
            panels={panels}
            onPanelClick={handlePanelClick}
            onPanelLongPress={onPanelLongPress}
          />
        )}
        {vehicleType === 'truck' && (
          <TruckSvg
            panels={panels}
            onPanelClick={handlePanelClick}
            onPanelLongPress={onPanelLongPress}
          />
        )}
        {vehicleType === 'suv' && (
          <SuvSvg
            panels={panels}
            onPanelClick={handlePanelClick}
            onPanelLongPress={onPanelLongPress}
          />
        )}
      </div>

      {/* Instructions and Clear */}
      <div className="text-center mt-2 space-y-2">
        {/* Selection mode banner */}
        {selectionMode && (
          <div className="flex flex-col gap-2 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2">
            <div className="flex items-center justify-center gap-3">
              <span className="text-sm text-purple-700 font-medium">
                Selection Mode
              </span>
              <span className="text-xs text-purple-600">
                {batchSelectedCount > 0
                  ? `${batchSelectedCount} panel${batchSelectedCount !== 1 ? 's' : ''} selected`
                  : 'Tap panels to select'}
              </span>
            </div>
            <div className="flex items-center justify-center gap-2">
              {primaryPanelName && onOpenPrimaryOverlay && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={onOpenPrimaryOverlay}
                  className="h-7 text-xs bg-purple-600 hover:bg-purple-700"
                >
                  Edit {primaryPanelName}
                </Button>
              )}
              {onExitSelectionMode && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onExitSelectionMode}
                  className="h-7 text-xs border-purple-300 text-purple-700 hover:bg-purple-100"
                >
                  Done
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Instructions */}
        {!selectionMode && (
          <p className="text-xs text-muted-foreground">
            {isMobile
              ? 'Tap to edit. Long-press to multi-select.'
              : 'Tap to edit. Ctrl/Cmd+click for multi-select. Right-click for conventional.'}
          </p>
        )}

        {/* Counts and actions */}
        {(damagedCount > 0 || batchSelectedCount > 0) && (
          <div className="flex items-center justify-center gap-4 flex-wrap">
            {damagedCount > 0 && (
              <span className="text-sm">
                <span className="font-medium text-blue-600">{damagedCount}</span> panel{damagedCount !== 1 ? 's' : ''} with damage
                {conventionalCount > 0 && (
                  <span className="text-red-600 ml-2">({conventionalCount} conventional)</span>
                )}
              </span>
            )}
            {batchSelectedCount > 1 && !selectionMode && (
              <span className="text-sm">
                <span className="font-medium text-purple-600">{batchSelectedCount}</span> selected for batch
              </span>
            )}
            <div className="flex gap-2">
              {batchSelectedCount > 1 && onClearSelection && !selectionMode && (
                <button
                  onClick={onClearSelection}
                  className="text-sm text-purple-600 hover:text-purple-800 underline"
                >
                  Clear Selection
                </button>
              )}
              {damagedCount > 0 && (
                <button
                  onClick={onClearAll}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>
        )}

        {/* Severity Legend (only show when there are damaged panels) */}
        {hasDamagedPanels && (
          <div className="flex items-center justify-center gap-3 mt-2 pt-2 border-t border-gray-100">
            <span className="text-xs text-muted-foreground">Severity:</span>
            {([1, 2, 3, 4] as SeverityLevel[]).map(level => (
              <div key={level} className="flex items-center gap-1">
                <div
                  className="w-3 h-3 rounded-sm border border-gray-300"
                  style={{ backgroundColor: getSeverityFillColor(level) }}
                />
                <span className="text-xs text-muted-foreground">
                  {getSeverityLabel(level)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default VehicleDiagram
