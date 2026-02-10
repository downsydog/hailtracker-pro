/**
 * R&I Suggestions Component
 * Shows suggested R&I items with scope bullets for the selected panel
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Check, ChevronDown, Clock, Plus, Wrench } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface RILibraryItem {
  operation_code: string
  operation_name: string
  category: string
  base_time_hours: number
  scope_bullets?: {
    min: string
    typical: string
    max: string
  }
}

export interface RIItemAdded {
  id: number
  operation_code: string
  operation_name: string
  calculated_time_hours: number
  price: number
}

interface RISuggestionsProps {
  suggestions: RILibraryItem[]
  addedItems: RIItemAdded[]
  vehicleTier?: string
  laborRate?: number
  onAdd: (operationCode: string) => void
  onRemove?: (itemId: number) => void
  onViewLibrary?: () => void
  isLoading?: boolean
}

// Tier multipliers for time calculation
const TIER_MULTIPLIERS: Record<string, number> = {
  economy: 0.85,
  standard: 1.0,
  premium: 1.15,
  luxury: 1.35,
  ev_adas: 1.25
}

export function RISuggestions({
  suggestions,
  addedItems,
  vehicleTier = 'standard',
  laborRate = 75,
  onAdd,
  onRemove: _onRemove,
  onViewLibrary,
  isLoading = false
}: RISuggestionsProps) {
  // _onRemove available for future use
  const [expandedItem, setExpandedItem] = useState<string | null>(null)

  const tierMult = TIER_MULTIPLIERS[vehicleTier] || 1.0

  // Calculate estimated price
  const calculatePrice = (baseTime: number) => {
    const adjustedTime = baseTime * tierMult
    return Math.round(adjustedTime * laborRate * 100) / 100
  }

  // Check if item is already added
  const isAdded = (operationCode: string) => {
    return addedItems.some(item => item.operation_code === operationCode)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            R&I Suggestions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            <div className="h-12 bg-muted rounded" />
            <div className="h-12 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (suggestions.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            R&I Suggestions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-2">
            No R&I suggestions for this panel
          </p>
          {onViewLibrary && (
            <Button
              variant="outline"
              size="sm"
              className="w-full mt-2"
              onClick={onViewLibrary}
            >
              View Full R&I Library
            </Button>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            R&I Suggestions
          </span>
          <Badge variant="outline" className="text-xs">
            {vehicleTier} tier
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {suggestions.map(item => {
          const added = isAdded(item.operation_code)
          const price = calculatePrice(item.base_time_hours)
          const adjustedTime = (item.base_time_hours * tierMult).toFixed(2)
          const isExpanded = expandedItem === item.operation_code

          return (
            <Collapsible
              key={item.operation_code}
              open={isExpanded}
              onOpenChange={(open) => setExpandedItem(open ? item.operation_code : null)}
            >
              <div
                className={cn(
                  'rounded-lg border transition-colors',
                  added ? 'bg-green-50 border-green-200' : 'bg-background'
                )}
              >
                <div className="flex items-center justify-between p-2">
                  <CollapsibleTrigger className="flex items-center gap-2 text-left flex-1">
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 text-muted-foreground transition-transform',
                        isExpanded && 'rotate-180'
                      )}
                    />
                    <div>
                      <p className="text-sm font-medium">{item.operation_name}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{adjustedTime} hrs</span>
                        <span>•</span>
                        <span className="font-medium text-green-600">${price}</span>
                      </div>
                    </div>
                  </CollapsibleTrigger>
                  <Button
                    variant={added ? 'ghost' : 'default'}
                    size="sm"
                    disabled={added}
                    onClick={(e) => {
                      e.stopPropagation()
                      if (!added) onAdd(item.operation_code)
                    }}
                    className={cn('ml-2', added && 'text-green-600')}
                  >
                    {added ? (
                      <>
                        <Check className="h-4 w-4" />
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>

                <CollapsibleContent>
                  {item.scope_bullets && (
                    <div className="px-3 pb-3 pt-1 border-t">
                      <p className="text-xs font-medium text-muted-foreground mb-2">
                        SCOPE BULLETS
                      </p>
                      <div className="space-y-1 text-xs">
                        <div className="flex gap-2">
                          <Badge variant="outline" className="text-[10px] shrink-0">MIN</Badge>
                          <span>{item.scope_bullets.min}</span>
                        </div>
                        <div className="flex gap-2">
                          <Badge className="text-[10px] shrink-0">TYP</Badge>
                          <span>{item.scope_bullets.typical}</span>
                        </div>
                        <div className="flex gap-2">
                          <Badge variant="secondary" className="text-[10px] shrink-0">MAX</Badge>
                          <span>{item.scope_bullets.max}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </CollapsibleContent>
              </div>
            </Collapsible>
          )
        })}

        {onViewLibrary && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={onViewLibrary}
          >
            View All R&I Items
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

// R&I Items List (for showing added items)
interface RIItemsListProps {
  items: RIItemAdded[]
  onRemove?: (itemId: number) => void
}

export function RIItemsList({ items, onRemove }: RIItemsListProps) {
  if (items.length === 0) return null

  const total = items.reduce((sum, item) => sum + item.price, 0)
  const totalTime = items.reduce((sum, item) => sum + item.calculated_time_hours, 0)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            R&I Items ({items.length})
          </span>
          <span className="text-green-600 font-bold">${total.toFixed(0)}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {items.map(item => (
          <div
            key={item.id}
            className="flex items-center justify-between p-2 bg-muted/50 rounded"
          >
            <div>
              <p className="text-sm font-medium">{item.operation_name}</p>
              <p className="text-xs text-muted-foreground">
                {item.calculated_time_hours.toFixed(2)} hrs
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">${item.price.toFixed(0)}</span>
              {onRemove && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-destructive"
                  onClick={() => onRemove(item.id)}
                >
                  ×
                </Button>
              )}
            </div>
          </div>
        ))}
        <div className="flex justify-between pt-2 border-t text-sm">
          <span className="text-muted-foreground">Total R&I Time:</span>
          <span className="font-medium">{totalTime.toFixed(2)} hrs</span>
        </div>
      </CardContent>
    </Card>
  )
}
