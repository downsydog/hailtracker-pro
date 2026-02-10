/**
 * Panel Entry Modal
 * Opens when a panel is tapped on the vehicle diagram
 * Contains tabs: COUNT, CP (Conventional Parts), SUPP (Supplement), NOTES
 */

import { useState, useMemo, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  ArrowLeft,
  Camera,
  Wrench,
  Package,
  DollarSign
} from 'lucide-react'
import { cn } from '@/lib/utils'

// Count range options
export const COUNT_RANGES = [
  { id: '1-5', label: '1-5', min: 1, max: 5 },
  { id: '6-15', label: '6-15', min: 6, max: 15 },
  { id: '16-30', label: '16-30', min: 16, max: 30 },
  { id: '31-50', label: '31-50', min: 31, max: 50 },
  { id: '51-75', label: '51-75', min: 51, max: 75 },
  { id: '76-100', label: '76-100', min: 76, max: 100 },
  { id: '101+', label: '101+', min: 101, max: 999 },
] as const

export type CountRange = typeof COUNT_RANGES[number]['id']

// Dent size options
export const DENT_SIZES = [
  { id: 'dime', label: 'DIME', description: 'Up to 0.5"' },
  { id: 'nickel', label: 'NICKEL', description: '0.5" - 0.75"' },
  { id: 'quarter', label: 'QUARTER', description: '0.75" - 1"' },
  { id: 'half', label: 'HALF $', description: '1" - 1.5"' },
] as const

export type DentSize = typeof DENT_SIZES[number]['id']

export interface PanelDamage {
  panelId: string
  countRange: CountRange | null
  dentSize: DentSize | null
  oversizedCount: number
  gluePull: boolean
  aluminum: boolean
  hss: boolean
  doubleMetal: boolean
  conventional: boolean
  notes: string
  basePrice: number
  totalPrice: number
}

interface PanelEntryModalProps {
  open: boolean
  onClose: () => void
  panelId: string
  panelName: string
  damage: PanelDamage
  onDamageChange: (damage: PanelDamage) => void
  matrixLookup: (panelId: string, countRange: CountRange, size: DentSize) => number
}

export function PanelEntryModal({
  open,
  onClose,
  panelId,
  panelName,
  damage,
  onDamageChange,
  matrixLookup
}: PanelEntryModalProps) {
  const [activeTab, setActiveTab] = useState('count')
  const [localDamage, setLocalDamage] = useState<PanelDamage>(damage)

  // Sync local state with prop
  useEffect(() => {
    setLocalDamage(damage)
  }, [damage])

  // Calculate price whenever damage changes
  const calculatedPrice = useMemo(() => {
    if (!localDamage.countRange || !localDamage.dentSize) return 0

    // Get base price from matrix
    let basePrice = matrixLookup(panelId, localDamage.countRange, localDamage.dentSize)

    // Apply modifiers
    let multiplier = 1.0
    if (localDamage.gluePull) multiplier += 0.25
    if (localDamage.aluminum) multiplier += 0.25
    if (localDamage.hss) multiplier += 0.25
    if (localDamage.doubleMetal) multiplier += 0.50

    let total = basePrice * multiplier

    // Add oversized dents ($50 each typically)
    total += localDamage.oversizedCount * 50

    return total
  }, [localDamage, panelId, matrixLookup])

  // Update damage and propagate
  const updateDamage = (updates: Partial<PanelDamage>) => {
    const newDamage = { ...localDamage, ...updates }

    // Recalculate prices
    if (newDamage.countRange && newDamage.dentSize) {
      const basePrice = matrixLookup(panelId, newDamage.countRange, newDamage.dentSize)
      let multiplier = 1.0
      if (newDamage.gluePull) multiplier += 0.25
      if (newDamage.aluminum) multiplier += 0.25
      if (newDamage.hss) multiplier += 0.25
      if (newDamage.doubleMetal) multiplier += 0.50

      newDamage.basePrice = basePrice
      newDamage.totalPrice = (basePrice * multiplier) + (newDamage.oversizedCount * 50)
    }

    setLocalDamage(newDamage)
    onDamageChange(newDamage)
  }

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-lg p-0 flex flex-col">
        {/* Header */}
        <SheetHeader className="p-4 border-b bg-white sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={onClose}>
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <SheetTitle className="text-xl">{panelName}</SheetTitle>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-green-600">
                ${calculatedPrice.toFixed(2)}
              </p>
              <p className="text-xs text-muted-foreground">Panel Total</p>
            </div>
          </div>
        </SheetHeader>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="w-full justify-start rounded-none border-b bg-white h-12 px-4">
            <TabsTrigger value="count" className="flex-1">COUNT</TabsTrigger>
            <TabsTrigger value="cp" className="flex-1">CP</TabsTrigger>
            <TabsTrigger value="supp" className="flex-1">SUPP</TabsTrigger>
            <TabsTrigger value="notes" className="flex-1">NOTES</TabsTrigger>
          </TabsList>

          {/* COUNT Tab */}
          <TabsContent value="count" className="flex-1 overflow-auto p-4 m-0 space-y-6">
            {/* Dent Count Range */}
            <div>
              <Label className="text-sm font-semibold text-gray-700 mb-3 block">
                DENT COUNT:
              </Label>
              <div className="grid grid-cols-4 gap-2">
                {COUNT_RANGES.slice(0, 4).map((range) => (
                  <Button
                    key={range.id}
                    variant={localDamage.countRange === range.id ? 'default' : 'outline'}
                    className={cn(
                      'h-12 text-sm font-semibold',
                      localDamage.countRange === range.id && 'bg-blue-600 hover:bg-blue-700'
                    )}
                    onClick={() => updateDamage({ countRange: range.id })}
                  >
                    {range.label}
                  </Button>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-2 mt-2">
                {COUNT_RANGES.slice(4).map((range) => (
                  <Button
                    key={range.id}
                    variant={localDamage.countRange === range.id ? 'default' : 'outline'}
                    className={cn(
                      'h-12 text-sm font-semibold',
                      localDamage.countRange === range.id && 'bg-blue-600 hover:bg-blue-700'
                    )}
                    onClick={() => updateDamage({ countRange: range.id })}
                  >
                    {range.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* Dent Size */}
            <div>
              <Label className="text-sm font-semibold text-gray-700 mb-3 block">
                DENT SIZE:
              </Label>
              <div className="grid grid-cols-4 gap-2">
                {DENT_SIZES.map((size) => (
                  <Button
                    key={size.id}
                    variant={localDamage.dentSize === size.id ? 'default' : 'outline'}
                    className={cn(
                      'h-12 text-sm font-semibold flex flex-col py-1',
                      localDamage.dentSize === size.id && 'bg-blue-600 hover:bg-blue-700'
                    )}
                    onClick={() => updateDamage({ dentSize: size.id })}
                  >
                    <span>{size.label}</span>
                  </Button>
                ))}
              </div>
            </div>

            {/* Calculated Base Price */}
            {localDamage.countRange && localDamage.dentSize && (
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex justify-between items-center">
                  <span className="font-medium text-blue-900">DENT COUNT TOTAL:</span>
                  <span className="text-xl font-bold text-blue-600">
                    ${localDamage.basePrice?.toFixed(2) || '0.00'}
                  </span>
                </div>
              </div>
            )}

            {/* Add-ons */}
            <div>
              <Label className="text-sm font-semibold text-gray-700 mb-3 block">
                ADD ONS:
              </Label>
              <div className="space-y-3">
                {/* Oversized Dents */}
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Checkbox
                      id="oversized"
                      checked={localDamage.oversizedCount > 0}
                      onCheckedChange={(checked) => {
                        updateDamage({ oversizedCount: checked ? 1 : 0 })
                      }}
                    />
                    <Label htmlFor="oversized" className="font-medium">
                      Oversized Dents
                    </Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      min={0}
                      value={localDamage.oversizedCount}
                      onChange={(e) => updateDamage({ oversizedCount: parseInt(e.target.value) || 0 })}
                      className="w-16 h-8 text-center"
                    />
                    <span className="text-sm text-muted-foreground">@ $50 ea</span>
                  </div>
                </div>

                {/* Glue Pull */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Checkbox
                    id="gluePull"
                    checked={localDamage.gluePull}
                    onCheckedChange={(checked) => updateDamage({ gluePull: !!checked })}
                  />
                  <Label htmlFor="gluePull" className="font-medium flex-1">
                    Glue Pull Required
                  </Label>
                  <span className="text-sm text-blue-600 font-medium">+25%</span>
                </div>

                {/* Aluminum */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Checkbox
                    id="aluminum"
                    checked={localDamage.aluminum}
                    onCheckedChange={(checked) => updateDamage({ aluminum: !!checked })}
                  />
                  <Label htmlFor="aluminum" className="font-medium flex-1">
                    Aluminum Panel
                  </Label>
                  <span className="text-sm text-amber-600 font-medium">+25%</span>
                </div>

                {/* HSS */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Checkbox
                    id="hss"
                    checked={localDamage.hss}
                    onCheckedChange={(checked) => updateDamage({ hss: !!checked })}
                  />
                  <Label htmlFor="hss" className="font-medium flex-1">
                    High Strength Steel
                  </Label>
                  <span className="text-sm text-purple-600 font-medium">+25%</span>
                </div>

                {/* Double Metal */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <Checkbox
                    id="doubleMetal"
                    checked={localDamage.doubleMetal}
                    onCheckedChange={(checked) => updateDamage({ doubleMetal: !!checked })}
                  />
                  <Label htmlFor="doubleMetal" className="font-medium flex-1">
                    Double Metal
                  </Label>
                  <span className="text-sm text-red-600 font-medium">+50%</span>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* CP (Conventional Parts) Tab */}
          <TabsContent value="cp" className="flex-1 overflow-auto p-4 m-0">
            <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg border border-red-200 mb-4">
              <Checkbox
                id="conventional"
                checked={localDamage.conventional}
                onCheckedChange={(checked) => updateDamage({ conventional: !!checked })}
              />
              <div>
                <Label htmlFor="conventional" className="font-medium text-red-700">
                  Mark as Conventional Repair
                </Label>
                <p className="text-sm text-red-600">
                  Panel exceeds PDR limits - requires body shop repair
                </p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground text-center py-8">
              Conventional parts and labor can be added here when conventional repair is selected.
            </p>
          </TabsContent>

          {/* SUPP (Supplement) Tab */}
          <TabsContent value="supp" className="flex-1 overflow-auto p-4 m-0">
            <p className="text-sm text-muted-foreground text-center py-8">
              Additional supplemental charges for this panel can be added here.
            </p>
          </TabsContent>

          {/* NOTES Tab */}
          <TabsContent value="notes" className="flex-1 overflow-auto p-4 m-0">
            <Textarea
              placeholder="Add notes about this panel..."
              value={localDamage.notes}
              onChange={(e) => updateDamage({ notes: e.target.value })}
              className="min-h-[200px]"
            />
          </TabsContent>
        </Tabs>

        {/* Bottom Actions */}
        <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
          <div className="flex gap-2">
            <Button variant="outline" size="icon">
              <Wrench className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon">
              <Package className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon">
              <Camera className="h-4 w-4" />
            </Button>
          </div>
          <Button onClick={onClose} className="bg-blue-600 hover:bg-blue-700">
            <DollarSign className="h-4 w-4 mr-1" />
            Done - ${calculatedPrice.toFixed(2)}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

export default PanelEntryModal
