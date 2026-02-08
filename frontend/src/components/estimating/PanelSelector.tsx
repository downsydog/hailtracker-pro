/**
 * Panel Selector Component
 * Visual grid of vehicle panels with dent count badges
 * Mobile-optimized for one-tap panel selection
 */

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface PanelInfo {
  id: string
  name: string
  displayName: string
  dentCount: number
  riCount: number
  total: number
  material?: 'steel' | 'aluminum' | 'high_strength_steel'
  isAluminum?: boolean
}

const DEFAULT_PANELS: Omit<PanelInfo, 'dentCount' | 'riCount' | 'total'>[] = [
  { id: 'hood', name: 'hood', displayName: 'Hood' },
  { id: 'roof', name: 'roof', displayName: 'Roof' },
  { id: 'driver_fender', name: 'driver_fender', displayName: 'Dr Fender' },
  { id: 'passenger_fender', name: 'passenger_fender', displayName: 'Pass Fender' },
  { id: 'driver_door', name: 'driver_door', displayName: 'Dr Door' },
  { id: 'passenger_door', name: 'passenger_door', displayName: 'Pass Door' },
  { id: 'driver_rear_door', name: 'driver_rear_door', displayName: 'Dr Rear Door' },
  { id: 'passenger_rear_door', name: 'passenger_rear_door', displayName: 'Pass Rear Door' },
  { id: 'driver_quarter', name: 'driver_quarter', displayName: 'Dr Quarter' },
  { id: 'passenger_quarter', name: 'passenger_quarter', displayName: 'Pass Quarter' },
  { id: 'trunk', name: 'trunk', displayName: 'Trunk' },
  { id: 'tailgate', name: 'tailgate', displayName: 'Tailgate' },
]

interface PanelSelectorProps {
  panels: PanelInfo[]
  selectedPanelId: string | null
  onSelectPanel: (panelId: string) => void
  aluminumPanels?: string[]
  className?: string
}

export function PanelSelector({
  panels,
  selectedPanelId,
  onSelectPanel,
  aluminumPanels = [],
  className
}: PanelSelectorProps) {
  // Merge default panels with data from props
  const panelData = DEFAULT_PANELS.map(defaultPanel => {
    const existing = panels.find(p => p.id === defaultPanel.id || p.name === defaultPanel.name)
    return {
      ...defaultPanel,
      dentCount: existing?.dentCount || 0,
      riCount: existing?.riCount || 0,
      total: existing?.total || 0,
      material: existing?.material || 'steel',
      isAluminum: aluminumPanels.includes(defaultPanel.name) || existing?.material === 'aluminum'
    } as PanelInfo
  })

  return (
    <div className={cn('grid grid-cols-2 md:grid-cols-3 gap-2', className)}>
      {panelData.map(panel => {
        const isSelected = selectedPanelId === panel.id
        const hasDents = panel.dentCount > 0

        return (
          <button
            key={panel.id}
            type="button"
            onClick={() => onSelectPanel(panel.id)}
            className={cn(
              'relative p-3 rounded-lg border-2 text-left transition-all',
              'hover:border-primary/50 hover:bg-accent/50',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
              isSelected && 'border-primary bg-primary/5',
              !isSelected && hasDents && 'border-green-300 bg-green-50/50',
              !isSelected && !hasDents && 'border-border',
              panel.isAluminum && 'ring-1 ring-orange-300'
            )}
          >
            {/* Panel name */}
            <p className="font-medium text-sm truncate">{panel.displayName}</p>

            {/* Dent count badge */}
            {panel.dentCount > 0 && (
              <Badge
                variant="secondary"
                className="absolute top-1 right-1 h-5 min-w-5 flex items-center justify-center text-xs bg-green-100 text-green-700"
              >
                {panel.dentCount}
              </Badge>
            )}

            {/* Material indicator */}
            {panel.isAluminum && (
              <span className="text-[10px] text-orange-600 font-medium">ALU</span>
            )}

            {/* Total price if has dents */}
            {panel.total > 0 && (
              <p className="text-xs text-green-600 font-medium mt-1">
                ${panel.total.toFixed(0)}
              </p>
            )}

            {/* Selection indicator */}
            <div
              className={cn(
                'absolute bottom-0 left-0 right-0 h-1 rounded-b-md transition-all',
                isSelected ? 'bg-primary' : 'bg-transparent'
              )}
            />
          </button>
        )
      })}
    </div>
  )
}

// Car diagram SVG version (optional visual alternative)
export function PanelDiagram({
  panels,
  selectedPanelId,
  onSelectPanel,
  className
}: PanelSelectorProps) {
  const getPanelCount = (panelName: string) => {
    const panel = panels.find(p => p.name === panelName)
    return panel?.dentCount || 0
  }

  const isSelected = (panelName: string) => selectedPanelId === panelName

  return (
    <svg viewBox="0 0 400 200" className={cn('w-full max-w-md mx-auto', className)}>
      {/* Top view of car */}
      <g>
        {/* Hood */}
        <rect
          x="150" y="10" width="100" height="50"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('hood') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('hood') > 0 && !isSelected('hood') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('hood')}
        />
        <text x="200" y="40" textAnchor="middle" className="text-xs font-medium fill-slate-700 pointer-events-none">
          Hood {getPanelCount('hood') > 0 && `(${getPanelCount('hood')})`}
        </text>

        {/* Roof */}
        <rect
          x="150" y="65" width="100" height="70"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('roof') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('roof') > 0 && !isSelected('roof') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('roof')}
        />
        <text x="200" y="105" textAnchor="middle" className="text-xs font-medium fill-slate-700 pointer-events-none">
          Roof {getPanelCount('roof') > 0 && `(${getPanelCount('roof')})`}
        </text>

        {/* Trunk */}
        <rect
          x="150" y="140" width="100" height="50"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('trunk') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('trunk') > 0 && !isSelected('trunk') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('trunk')}
        />
        <text x="200" y="170" textAnchor="middle" className="text-xs font-medium fill-slate-700 pointer-events-none">
          Trunk {getPanelCount('trunk') > 0 && `(${getPanelCount('trunk')})`}
        </text>

        {/* Driver fender */}
        <rect
          x="90" y="10" width="55" height="50"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('driver_fender') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('driver_fender') > 0 && !isSelected('driver_fender') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('driver_fender')}
        />
        <text x="117" y="40" textAnchor="middle" className="text-[9px] font-medium fill-slate-700 pointer-events-none">
          Dr F
        </text>

        {/* Passenger fender */}
        <rect
          x="255" y="10" width="55" height="50"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('passenger_fender') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('passenger_fender') > 0 && !isSelected('passenger_fender') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('passenger_fender')}
        />
        <text x="282" y="40" textAnchor="middle" className="text-[9px] font-medium fill-slate-700 pointer-events-none">
          Pass F
        </text>

        {/* Driver doors */}
        <rect
          x="90" y="65" width="55" height="35"
          rx="3"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('driver_door') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('driver_door') > 0 && !isSelected('driver_door') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('driver_door')}
        />
        <rect
          x="90" y="102" width="55" height="35"
          rx="3"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('driver_rear_door') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('driver_rear_door') > 0 && !isSelected('driver_rear_door') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('driver_rear_door')}
        />

        {/* Passenger doors */}
        <rect
          x="255" y="65" width="55" height="35"
          rx="3"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('passenger_door') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('passenger_door') > 0 && !isSelected('passenger_door') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('passenger_door')}
        />
        <rect
          x="255" y="102" width="55" height="35"
          rx="3"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('passenger_rear_door') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('passenger_rear_door') > 0 && !isSelected('passenger_rear_door') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('passenger_rear_door')}
        />

        {/* Quarter panels */}
        <rect
          x="90" y="140" width="55" height="50"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('driver_quarter') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('driver_quarter') > 0 && !isSelected('driver_quarter') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('driver_quarter')}
        />
        <rect
          x="255" y="140" width="55" height="50"
          rx="5"
          className={cn(
            'cursor-pointer transition-colors',
            isSelected('passenger_quarter') ? 'fill-primary/30 stroke-primary' : 'fill-slate-100 stroke-slate-300',
            getPanelCount('passenger_quarter') > 0 && !isSelected('passenger_quarter') && 'fill-green-100 stroke-green-400'
          )}
          strokeWidth="2"
          onClick={() => onSelectPanel('passenger_quarter')}
        />
      </g>
    </svg>
  )
}

export { DEFAULT_PANELS }
