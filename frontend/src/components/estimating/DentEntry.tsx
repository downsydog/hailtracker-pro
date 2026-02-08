/**
 * Dent Entry Component
 * Fast one-tap dent entry with zone, size, depth selection
 * Goal: Add 20 dents in < 45 seconds
 */

import { useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Minus, Plus } from 'lucide-react'

export type DentSize = 'dime' | 'nickel' | 'quarter' | 'half_dollar' | 'silver_dollar' | 'oversized'
export type DentZone = 'center' | 'edge' | 'crease' | 'body_line'
export type DentDepth = 'shallow' | 'medium' | 'deep' | 'severe'

interface DentEntryProps {
  panelName: string
  onAddDent: (size: DentSize, zone: DentZone, depth: DentDepth) => void
  onAddBatch: (size: DentSize, zone: DentZone, depth: DentDepth, count: number) => void
  disabled?: boolean
  vehicleTier?: string
}

// Pricing reference (matches backend)
const SIZE_PRICES: Record<DentSize, number> = {
  dime: 45,
  nickel: 55,
  quarter: 70,
  half_dollar: 95,
  silver_dollar: 125,
  oversized: 175
}

const SIZE_LABELS: Record<DentSize, string> = {
  dime: 'Dime',
  nickel: 'Nickel',
  quarter: 'Quarter',
  half_dollar: 'Half $',
  silver_dollar: 'Silver $',
  oversized: 'Oversized'
}

const ZONE_MULTIPLIERS: Record<DentZone, number> = {
  center: 1.0,
  edge: 1.35,
  crease: 1.5,
  body_line: 1.8
}

const ZONE_LABELS: Record<DentZone, { label: string; color: string }> = {
  center: { label: 'Center', color: 'bg-green-500 hover:bg-green-600' },
  edge: { label: 'Edge', color: 'bg-yellow-500 hover:bg-yellow-600' },
  crease: { label: 'Crease', color: 'bg-orange-500 hover:bg-orange-600' },
  body_line: { label: 'Body Line', color: 'bg-red-500 hover:bg-red-600' }
}

const DEPTH_MULTIPLIERS: Record<DentDepth, number> = {
  shallow: 1.0,
  medium: 1.25,
  deep: 1.6,
  severe: 2.0
}

const DEPTH_LABELS: Record<DentDepth, { label: string; short: string }> = {
  shallow: { label: 'Shallow', short: 'S' },
  medium: { label: 'Medium', short: 'M' },
  deep: { label: 'Deep', short: 'D' },
  severe: { label: 'Severe', short: 'X' }
}

export function DentEntry({
  panelName,
  onAddDent,
  onAddBatch,
  disabled = false,
  vehicleTier = 'standard'
}: DentEntryProps) {
  const [selectedSize, setSelectedSize] = useState<DentSize>('quarter')
  const [selectedDepth, setSelectedDepth] = useState<DentDepth>('medium')

  // Calculate preview price
  const calculatePrice = useCallback((zone: DentZone) => {
    const basePrice = SIZE_PRICES[selectedSize]
    const zoneMult = ZONE_MULTIPLIERS[zone]
    const depthMult = DEPTH_MULTIPLIERS[selectedDepth]
    return Math.round(basePrice * zoneMult * depthMult)
  }, [selectedSize, selectedDepth])

  // Handle zone tap - adds dent immediately
  const handleZoneTap = useCallback((zone: DentZone) => {
    if (disabled) return
    onAddDent(selectedSize, zone, selectedDepth)
  }, [selectedSize, selectedDepth, disabled, onAddDent])

  // Handle quick add
  const handleQuickAdd = useCallback((count: number) => {
    if (disabled) return
    onAddBatch(selectedSize, 'center', selectedDepth, count)
  }, [selectedSize, selectedDepth, disabled, onAddBatch])

  return (
    <div className="space-y-4">
      {/* Size selector */}
      <div>
        <p className="text-xs text-muted-foreground mb-2 font-medium">DENT SIZE</p>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-1.5">
          {(Object.keys(SIZE_PRICES) as DentSize[]).map(size => (
            <button
              key={size}
              type="button"
              disabled={disabled}
              onClick={() => setSelectedSize(size)}
              className={cn(
                'p-2 rounded-lg border-2 text-center transition-all',
                'focus:outline-none focus:ring-2 focus:ring-primary',
                selectedSize === size
                  ? 'border-primary bg-primary/10 text-primary font-bold'
                  : 'border-border hover:border-primary/50'
              )}
            >
              <span className="text-xs font-medium block">{SIZE_LABELS[size]}</span>
              <span className="text-[10px] text-muted-foreground">${SIZE_PRICES[size]}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Depth selector */}
      <div>
        <p className="text-xs text-muted-foreground mb-2 font-medium">DEPTH</p>
        <div className="flex gap-2">
          {(Object.keys(DEPTH_MULTIPLIERS) as DentDepth[]).map(depth => (
            <button
              key={depth}
              type="button"
              disabled={disabled}
              onClick={() => setSelectedDepth(depth)}
              className={cn(
                'flex-1 p-2 rounded-lg border-2 text-center transition-all',
                'focus:outline-none focus:ring-2 focus:ring-primary',
                selectedDepth === depth
                  ? 'border-primary bg-primary/10'
                  : 'border-border hover:border-primary/50',
                depth === 'severe' && 'border-red-300'
              )}
            >
              <span className="text-xs font-medium">{DEPTH_LABELS[depth].label}</span>
              <span className="text-[10px] text-muted-foreground block">
                {DEPTH_MULTIPLIERS[depth]}x
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Zone selector - TAP TO ADD */}
      <div>
        <p className="text-xs text-muted-foreground mb-2 font-medium">
          TAP ZONE TO ADD DENT
        </p>
        <div className="grid grid-cols-2 gap-2">
          {(Object.keys(ZONE_LABELS) as DentZone[]).map(zone => {
            const price = calculatePrice(zone)
            const { label, color } = ZONE_LABELS[zone]

            return (
              <button
                key={zone}
                type="button"
                disabled={disabled}
                onClick={() => handleZoneTap(zone)}
                className={cn(
                  'relative p-4 rounded-xl text-white font-bold text-lg transition-all transform',
                  'focus:outline-none focus:ring-4 focus:ring-white/50',
                  'active:scale-95',
                  color,
                  disabled && 'opacity-50 cursor-not-allowed'
                )}
              >
                <span className="block">{label}</span>
                <span className="text-white/90 text-sm font-normal">
                  ${price}
                </span>
                <Badge
                  variant="secondary"
                  className="absolute top-1 right-1 bg-white/20 text-white text-[10px]"
                >
                  {ZONE_MULTIPLIERS[zone]}x
                </Badge>
              </button>
            )
          })}
        </div>
      </div>

      {/* Quick add buttons */}
      <div>
        <p className="text-xs text-muted-foreground mb-2 font-medium">QUICK ADD (CENTER ZONE)</p>
        <div className="flex gap-2">
          {[5, 10, 20].map(count => (
            <Button
              key={count}
              variant="outline"
              size="lg"
              disabled={disabled}
              onClick={() => handleQuickAdd(count)}
              className="flex-1 font-bold"
            >
              <Plus className="h-4 w-4 mr-1" />
              {count}
            </Button>
          ))}
        </div>
      </div>

      {/* Current selection summary */}
      <div className="bg-muted/50 rounded-lg p-3 text-center">
        <p className="text-xs text-muted-foreground">Currently adding:</p>
        <p className="font-bold text-lg">
          {SIZE_LABELS[selectedSize]} • {DEPTH_LABELS[selectedDepth].label}
        </p>
        <p className="text-sm text-muted-foreground">
          Base: ${SIZE_PRICES[selectedSize]} × {DEPTH_MULTIPLIERS[selectedDepth]}x depth
        </p>
      </div>
    </div>
  )
}

// Dent list component for showing added dents
interface DentListProps {
  dents: Array<{
    id: number
    size: DentSize
    zone: DentZone
    depth: DentDepth
    final_price: number
  }>
  onRemove: (dentId: number) => void
  groupByZone?: boolean
}

export function DentList({ dents, onRemove, groupByZone = true }: DentListProps) {
  if (dents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No dents added yet. Tap a zone above to add.
      </p>
    )
  }

  if (groupByZone) {
    // Group dents by zone and size
    const grouped: Record<string, typeof dents> = {}
    dents.forEach(dent => {
      const key = `${dent.zone}-${dent.size}-${dent.depth}`
      if (!grouped[key]) grouped[key] = []
      grouped[key].push(dent)
    })

    return (
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {Object.entries(grouped).map(([key, groupDents]) => {
          const first = groupDents[0]
          const totalPrice = groupDents.reduce((sum, d) => sum + d.final_price, 0)

          return (
            <div
              key={key}
              className="flex items-center justify-between p-2 bg-muted/50 rounded-lg"
            >
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs',
                    first.zone === 'center' && 'border-green-500 text-green-700',
                    first.zone === 'edge' && 'border-yellow-500 text-yellow-700',
                    first.zone === 'crease' && 'border-orange-500 text-orange-700',
                    first.zone === 'body_line' && 'border-red-500 text-red-700'
                  )}
                >
                  {first.zone}
                </Badge>
                <span className="text-sm font-medium">
                  {groupDents.length}× {SIZE_LABELS[first.size]}
                </span>
                <span className="text-xs text-muted-foreground">
                  ({DEPTH_LABELS[first.depth].label})
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-green-600">
                  ${totalPrice.toFixed(0)}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => onRemove(groupDents[groupDents.length - 1].id)}
                >
                  <Minus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  // Individual list view
  return (
    <div className="space-y-1 max-h-[300px] overflow-y-auto">
      {dents.map(dent => (
        <div
          key={dent.id}
          className="flex items-center justify-between p-2 bg-muted/30 rounded"
        >
          <div className="flex items-center gap-2">
            <span className="text-sm">{SIZE_LABELS[dent.size]}</span>
            <Badge variant="outline" className="text-xs">{dent.zone}</Badge>
            <span className="text-xs text-muted-foreground">
              {DEPTH_LABELS[dent.depth].short}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">${dent.final_price.toFixed(0)}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => onRemove(dent.id)}
            >
              <Minus className="h-3 w-3" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}

export { SIZE_PRICES, SIZE_LABELS, ZONE_MULTIPLIERS, ZONE_LABELS, DEPTH_MULTIPLIERS, DEPTH_LABELS }
