/**
 * Panel List Sidebar
 * Shows all vehicle panels with their prices
 * Selected/damaged panels are highlighted
 */

import { Button } from '@/components/ui/button'
import { Plus, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { VehicleType, VEHICLE_PANELS } from '../VehicleDiagram/VehicleDiagram'
import type { PanelDamage } from '../PanelEntry/PanelEntryModal'

interface PanelListSidebarProps {
  vehicleType: VehicleType
  panels: Record<string, PanelDamage>
  selectedPanelId: string | null
  onPanelSelect: (panelId: string) => void
  onAddCustomPanel: () => void
  className?: string
}

export function PanelListSidebar({
  vehicleType,
  panels,
  selectedPanelId,
  onPanelSelect,
  onAddCustomPanel,
  className
}: PanelListSidebarProps) {
  const vehiclePanels = VEHICLE_PANELS[vehicleType]
  const panelIds = Object.keys(vehiclePanels)

  // Calculate totals
  const totalPrice = Object.values(panels).reduce((sum, p) => sum + (p.totalPrice || 0), 0)
  const damagedCount = Object.values(panels).filter(p => p.countRange && p.dentSize).length
  const conventionalCount = Object.values(panels).filter(p => p.conventional).length

  return (
    <div className={cn('flex flex-col bg-white border-r', className)}>
      {/* Header */}
      <div className="p-3 border-b bg-gray-50">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-sm uppercase tracking-wide text-gray-600">
              Panel
            </h3>
          </div>
          <div>
            <h3 className="font-semibold text-sm uppercase tracking-wide text-gray-600">
              Amount
            </h3>
          </div>
        </div>
      </div>

      {/* Panel List */}
      <div className="flex-1 overflow-auto">
        <div className="divide-y">
          {panelIds.map((panelId) => {
            const panel = panels[panelId]
            const hasDamage = panel?.countRange && panel?.dentSize
            const isConventional = panel?.conventional
            const isSelected = selectedPanelId === panelId
            const price = panel?.totalPrice || 0

            return (
              <button
                key={panelId}
                onClick={() => onPanelSelect(panelId)}
                className={cn(
                  'w-full p-3 flex justify-between items-center text-left transition-colors',
                  'hover:bg-gray-50',
                  isSelected && 'bg-blue-50 border-l-4 border-l-blue-600',
                  hasDamage && !isSelected && 'bg-blue-50/50',
                  isConventional && 'bg-red-50'
                )}
              >
                <div className="flex items-center gap-2">
                  {isConventional && (
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                  )}
                  <span className={cn(
                    'text-sm font-medium',
                    hasDamage ? 'text-blue-700' : 'text-gray-600',
                    isConventional && 'text-red-700'
                  )}>
                    {vehiclePanels[panelId]}
                  </span>
                </div>
                <span className={cn(
                  'text-sm font-semibold',
                  hasDamage ? 'text-blue-600' : 'text-gray-400',
                  isConventional && 'text-red-600'
                )}>
                  {hasDamage ? `$${price.toFixed(0)}` : '-'}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Add Custom Panel */}
      <div className="p-2 border-t">
        <Button
          variant="ghost"
          className="w-full justify-start text-blue-600 hover:text-blue-700 hover:bg-blue-50"
          onClick={onAddCustomPanel}
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Custom Panel
        </Button>
      </div>

      {/* Summary Footer */}
      <div className="p-3 border-t bg-gray-50">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-600">
            {damagedCount} panel{damagedCount !== 1 ? 's' : ''} with damage
          </span>
          {conventionalCount > 0 && (
            <span className="text-xs text-red-600">
              {conventionalCount} CR
            </span>
          )}
        </div>
        <div className="flex justify-between items-center">
          <span className="font-semibold">Hail Total:</span>
          <span className="text-xl font-bold text-green-600">
            ${totalPrice.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default PanelListSidebar
