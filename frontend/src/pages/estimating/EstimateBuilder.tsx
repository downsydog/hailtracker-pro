/**
 * PDR Estimate Builder - Fast Dent Entry Interface
 *
 * Tap zone to add dent instantly - no modals, no confirmations.
 * Goal: Add 10 dents to a panel in < 30 seconds.
 */

import { useState, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Plus,
  Minus,
  Car,
  Save,
  Trash2,
  ChevronRight,
  Calculator,
  Undo2
} from 'lucide-react'

// Types
interface Dent {
  id: string
  size: 'small' | 'medium' | 'large' | 'xlarge'
  zone: 'center' | 'edge' | 'crease'
  price?: number
}

interface Panel {
  id: string
  name: string
  displayName: string
  dents: Dent[]
  material: 'steel' | 'aluminum' | 'high_strength_steel'
}

interface VehicleInfo {
  year: string
  make: string
  model: string
  vin?: string
}

// Pricing config (mirrors backend)
const BASE_PRICES = {
  small: 50,
  medium: 75,
  large: 100,
  xlarge: 150
}

const ZONE_MULTIPLIERS = {
  center: 1.0,
  edge: 1.4,
  crease: 1.6
}

const PANEL_DIFFICULTY = {
  hood: 1.0,
  roof: 1.2,
  driver_door: 1.0,
  passenger_door: 1.0,
  driver_rear_door: 1.1,
  passenger_rear_door: 1.1,
  driver_fender: 1.1,
  passenger_fender: 1.1,
  driver_quarter: 1.3,
  passenger_quarter: 1.3,
  trunk: 1.0,
  tailgate: 1.1
}

const MATERIAL_MODIFIERS = {
  steel: 1.0,
  aluminum: 1.5,
  high_strength_steel: 1.3
}

// Available panels
const AVAILABLE_PANELS = [
  { id: 'hood', name: 'hood', displayName: 'Hood' },
  { id: 'roof', name: 'roof', displayName: 'Roof' },
  { id: 'driver_fender', name: 'driver_fender', displayName: 'Driver Fender' },
  { id: 'passenger_fender', name: 'passenger_fender', displayName: 'Passenger Fender' },
  { id: 'driver_door', name: 'driver_door', displayName: 'Driver Door' },
  { id: 'passenger_door', name: 'passenger_door', displayName: 'Passenger Door' },
  { id: 'driver_rear_door', name: 'driver_rear_door', displayName: 'Driver Rear Door' },
  { id: 'passenger_rear_door', name: 'passenger_rear_door', displayName: 'Passenger Rear Door' },
  { id: 'driver_quarter', name: 'driver_quarter', displayName: 'Driver Quarter' },
  { id: 'passenger_quarter', name: 'passenger_quarter', displayName: 'Passenger Quarter' },
  { id: 'trunk', name: 'trunk', displayName: 'Trunk' },
  { id: 'tailgate', name: 'tailgate', displayName: 'Tailgate' }
]

// Years for dropdown
const YEARS = Array.from({ length: 30 }, (_, i) => (new Date().getFullYear() - i).toString())

// Common makes
const MAKES = [
  'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler',
  'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jeep', 'Kia',
  'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'Nissan', 'Ram', 'Subaru',
  'Tesla', 'Toyota', 'Volkswagen', 'Volvo'
]

function generateId(): string {
  return Math.random().toString(36).substr(2, 9)
}

function calculateDentPrice(
  size: Dent['size'],
  zone: Dent['zone'],
  panelName: string,
  material: Panel['material']
): number {
  const basePrice = BASE_PRICES[size]
  const zoneMult = ZONE_MULTIPLIERS[zone]
  const panelMult = PANEL_DIFFICULTY[panelName as keyof typeof PANEL_DIFFICULTY] || 1.0
  const materialMult = MATERIAL_MODIFIERS[material]

  return Math.round(basePrice * zoneMult * panelMult * materialMult * 100) / 100
}

// Zone selector SVG component
function ZoneSelector({
  onZoneClick,
  currentSize,
  dentCounts
}: {
  onZoneClick: (zone: Dent['zone']) => void
  currentSize: Dent['size']
  dentCounts: { center: number; edge: number; crease: number }
}) {
  return (
    <svg viewBox="0 0 200 200" className="w-full max-w-[300px] mx-auto">
      {/* Crease zone (outermost ring) */}
      <circle
        cx="100"
        cy="100"
        r="95"
        fill="#fecaca"
        stroke="#dc2626"
        strokeWidth="2"
        className="cursor-pointer hover:fill-red-300 transition-colors"
        onClick={() => onZoneClick('crease')}
      />
      {/* Edge zone (middle ring) */}
      <circle
        cx="100"
        cy="100"
        r="70"
        fill="#fef08a"
        stroke="#ca8a04"
        strokeWidth="2"
        className="cursor-pointer hover:fill-yellow-300 transition-colors"
        onClick={() => onZoneClick('edge')}
      />
      {/* Center zone (inner circle) */}
      <circle
        cx="100"
        cy="100"
        r="40"
        fill="#bbf7d0"
        stroke="#16a34a"
        strokeWidth="2"
        className="cursor-pointer hover:fill-green-300 transition-colors"
        onClick={() => onZoneClick('center')}
      />

      {/* Zone labels with counts */}
      <text x="100" y="105" textAnchor="middle" className="text-sm font-bold fill-green-800 pointer-events-none">
        Center ({dentCounts.center})
      </text>
      <text x="100" y="155" textAnchor="middle" className="text-xs font-medium fill-yellow-800 pointer-events-none">
        Edge ({dentCounts.edge})
      </text>
      <text x="100" y="185" textAnchor="middle" className="text-xs font-medium fill-red-800 pointer-events-none">
        Crease ({dentCounts.crease})
      </text>

      {/* Current size indicator */}
      <text x="100" y="30" textAnchor="middle" className="text-xs font-bold fill-gray-600 pointer-events-none">
        TAP TO ADD: {currentSize.toUpperCase()}
      </text>
    </svg>
  )
}

// Size selector component
function SizeSelector({
  currentSize,
  onSizeChange
}: {
  currentSize: Dent['size']
  onSizeChange: (size: Dent['size']) => void
}) {
  const sizes: Dent['size'][] = ['small', 'medium', 'large', 'xlarge']

  return (
    <div className="flex gap-2">
      {sizes.map(size => (
        <Button
          key={size}
          variant={currentSize === size ? 'default' : 'outline'}
          size="sm"
          onClick={() => onSizeChange(size)}
          className="flex-1"
        >
          {size === 'xlarge' ? 'XL' : size.charAt(0).toUpperCase()}
          <span className="ml-1 text-xs opacity-70">${BASE_PRICES[size]}</span>
        </Button>
      ))}
    </div>
  )
}

// Quick add buttons
function QuickAddButtons({
  onQuickAdd,
  currentZone
}: {
  onQuickAdd: (size: Dent['size'], count: number) => void
  currentZone: Dent['zone']
}) {
  return (
    <div className="grid grid-cols-3 gap-2">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onQuickAdd('small', 5)}
        className="text-xs"
      >
        +5 Small
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onQuickAdd('medium', 3)}
        className="text-xs"
      >
        +3 Medium
      </Button>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onQuickAdd('large', 2)}
        className="text-xs"
      >
        +2 Large
      </Button>
    </div>
  )
}

// Panel list item
function PanelListItem({
  panel,
  isSelected,
  onClick,
  onRemove
}: {
  panel: Panel
  isSelected: boolean
  onClick: () => void
  onRemove: () => void
}) {
  const dentCount = panel.dents.length
  const panelTotal = panel.dents.reduce((sum, d) => sum + (d.price || 0), 0)

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
        isSelected ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/50'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${dentCount > 0 ? 'bg-green-500' : 'bg-gray-300'}`} />
        <span className="font-medium">{panel.displayName}</span>
        {dentCount > 0 && (
          <Badge variant="secondary" className="text-xs">
            {dentCount} dent{dentCount !== 1 ? 's' : ''}
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-2">
        {panelTotal > 0 && (
          <span className="text-sm font-medium text-green-600">${panelTotal.toFixed(0)}</span>
        )}
        <ChevronRight className="h-4 w-4 text-muted-foreground" />
      </div>
    </div>
  )
}

// Dent list for selected panel
function DentList({
  dents,
  onRemoveDent
}: {
  dents: Dent[]
  onRemoveDent: (dentId: string) => void
}) {
  const grouped = useMemo(() => {
    const groups: Record<string, Dent[]> = {}
    dents.forEach(d => {
      const key = `${d.size}-${d.zone}`
      if (!groups[key]) groups[key] = []
      groups[key].push(d)
    })
    return groups
  }, [dents])

  if (dents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        Tap a zone above to add dents
      </p>
    )
  }

  return (
    <div className="space-y-2 max-h-[200px] overflow-y-auto">
      {Object.entries(grouped).map(([key, groupDents]) => {
        const [size, zone] = key.split('-')
        const totalPrice = groupDents.reduce((sum, d) => sum + (d.price || 0), 0)

        return (
          <div
            key={key}
            className="flex items-center justify-between p-2 bg-muted/50 rounded-md"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">
                {groupDents.length}x {size} ({zone})
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">${totalPrice.toFixed(0)}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => {
                  // Remove last dent of this type
                  const lastDent = groupDents[groupDents.length - 1]
                  onRemoveDent(lastDent.id)
                }}
              >
                <Minus className="h-3 w-3" />
              </Button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function EstimateBuilder() {
  // Vehicle info
  const [vehicle, setVehicle] = useState<VehicleInfo>({
    year: '',
    make: '',
    model: ''
  })

  // Panels with dents
  const [panels, setPanels] = useState<Panel[]>([])

  // Selected panel
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null)

  // Current dent size for tap-to-add
  const [currentSize, setCurrentSize] = useState<Dent['size']>('medium')

  // Current zone for quick-add
  const [currentZone, setCurrentZone] = useState<Dent['zone']>('center')

  // Undo stack
  const [undoStack, setUndoStack] = useState<Dent[]>([])

  // Get or create panel
  const getOrCreatePanel = useCallback((panelInfo: typeof AVAILABLE_PANELS[0]): Panel => {
    const existing = panels.find(p => p.id === panelInfo.id)
    if (existing) return existing

    const newPanel: Panel = {
      id: panelInfo.id,
      name: panelInfo.name,
      displayName: panelInfo.displayName,
      dents: [],
      material: 'steel'
    }
    setPanels(prev => [...prev, newPanel])
    return newPanel
  }, [panels])

  // Selected panel object
  const selectedPanel = useMemo(() => {
    return panels.find(p => p.id === selectedPanelId) || null
  }, [panels, selectedPanelId])

  // Add dent to selected panel
  const addDent = useCallback((zone: Dent['zone'], size: Dent['size'] = currentSize) => {
    if (!selectedPanelId) return

    const panel = panels.find(p => p.id === selectedPanelId)
    if (!panel) return

    const price = calculateDentPrice(size, zone, panel.name, panel.material)

    const newDent: Dent = {
      id: generateId(),
      size,
      zone,
      price
    }

    setPanels(prev => prev.map(p => {
      if (p.id === selectedPanelId) {
        return { ...p, dents: [...p.dents, newDent] }
      }
      return p
    }))

    setCurrentZone(zone)
    setUndoStack(prev => [...prev, newDent])
  }, [selectedPanelId, currentSize, panels])

  // Quick add multiple dents
  const quickAddDents = useCallback((size: Dent['size'], count: number) => {
    if (!selectedPanelId) return

    const panel = panels.find(p => p.id === selectedPanelId)
    if (!panel) return

    const newDents: Dent[] = Array.from({ length: count }, () => ({
      id: generateId(),
      size,
      zone: currentZone,
      price: calculateDentPrice(size, currentZone, panel.name, panel.material)
    }))

    setPanels(prev => prev.map(p => {
      if (p.id === selectedPanelId) {
        return { ...p, dents: [...p.dents, ...newDents] }
      }
      return p
    }))

    setUndoStack(prev => [...prev, ...newDents])
  }, [selectedPanelId, currentZone, panels])

  // Remove dent
  const removeDent = useCallback((dentId: string) => {
    setPanels(prev => prev.map(p => ({
      ...p,
      dents: p.dents.filter(d => d.id !== dentId)
    })))
  }, [])

  // Undo last action
  const undo = useCallback(() => {
    if (undoStack.length === 0) return

    const lastDent = undoStack[undoStack.length - 1]
    removeDent(lastDent.id)
    setUndoStack(prev => prev.slice(0, -1))
  }, [undoStack, removeDent])

  // Select panel from available list
  const selectPanel = useCallback((panelInfo: typeof AVAILABLE_PANELS[0]) => {
    const panel = getOrCreatePanel(panelInfo)
    setSelectedPanelId(panel.id)
  }, [getOrCreatePanel])

  // Dent counts for selected panel
  const dentCounts = useMemo(() => {
    if (!selectedPanel) return { center: 0, edge: 0, crease: 0 }
    return {
      center: selectedPanel.dents.filter(d => d.zone === 'center').length,
      edge: selectedPanel.dents.filter(d => d.zone === 'edge').length,
      crease: selectedPanel.dents.filter(d => d.zone === 'crease').length
    }
  }, [selectedPanel])

  // Calculate totals
  const totals = useMemo(() => {
    let dentTotal = 0
    let dentCount = 0

    panels.forEach(p => {
      p.dents.forEach(d => {
        dentTotal += d.price || 0
        dentCount++
      })
    })

    return { dentTotal, dentCount, panelCount: panels.filter(p => p.dents.length > 0).length }
  }, [panels])

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Car className="h-6 w-6" />
            PDR Estimate Builder
          </h1>
          <p className="text-muted-foreground">Tap zones to add dents instantly</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={undo} disabled={undoStack.length === 0}>
            <Undo2 className="h-4 w-4 mr-2" />
            Undo
          </Button>
          <Button>
            <Save className="h-4 w-4 mr-2" />
            Save Estimate
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Vehicle Info + Panel List */}
        <div className="space-y-4">
          {/* Vehicle Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Vehicle</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                <select
                  className="px-3 py-2 border rounded-md bg-background text-sm"
                  value={vehicle.year}
                  onChange={(e) => setVehicle(v => ({ ...v, year: e.target.value }))}
                >
                  <option value="">Year</option>
                  {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <select
                  className="px-3 py-2 border rounded-md bg-background text-sm"
                  value={vehicle.make}
                  onChange={(e) => setVehicle(v => ({ ...v, make: e.target.value }))}
                >
                  <option value="">Make</option>
                  {MAKES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                <input
                  type="text"
                  placeholder="Model"
                  className="px-3 py-2 border rounded-md bg-background text-sm"
                  value={vehicle.model}
                  onChange={(e) => setVehicle(v => ({ ...v, model: e.target.value }))}
                />
              </div>
              <input
                type="text"
                placeholder="VIN (optional)"
                className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                value={vehicle.vin || ''}
                onChange={(e) => setVehicle(v => ({ ...v, vin: e.target.value }))}
              />
            </CardContent>
          </Card>

          {/* Panel List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Panels</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
              {AVAILABLE_PANELS.map(panelInfo => {
                const existingPanel = panels.find(p => p.id === panelInfo.id)
                const panel: Panel = existingPanel || {
                  id: panelInfo.id,
                  name: panelInfo.name,
                  displayName: panelInfo.displayName,
                  dents: [],
                  material: 'steel'
                }
                return (
                  <PanelListItem
                    key={panelInfo.id}
                    panel={panel}
                    isSelected={selectedPanelId === panelInfo.id}
                    onClick={() => selectPanel(panelInfo)}
                    onRemove={() => {
                      setPanels(prev => prev.filter(p => p.id !== panelInfo.id))
                      if (selectedPanelId === panelInfo.id) setSelectedPanelId(null)
                    }}
                  />
                )
              })}
            </CardContent>
          </Card>
        </div>

        {/* Center: Zone Selector */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">
                {selectedPanel ? selectedPanel.displayName : 'Select a Panel'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedPanel ? (
                <div className="space-y-4">
                  {/* Material selector */}
                  <div className="flex gap-2">
                    {(['steel', 'aluminum', 'high_strength_steel'] as const).map(mat => (
                      <Button
                        key={mat}
                        variant={selectedPanel.material === mat ? 'default' : 'outline'}
                        size="sm"
                        className="flex-1 text-xs"
                        onClick={() => {
                          setPanels(prev => prev.map(p => {
                            if (p.id === selectedPanelId) {
                              // Recalculate all dent prices
                              const newDents = p.dents.map(d => ({
                                ...d,
                                price: calculateDentPrice(d.size, d.zone, p.name, mat)
                              }))
                              return { ...p, material: mat, dents: newDents }
                            }
                            return p
                          }))
                        }}
                      >
                        {mat === 'high_strength_steel' ? 'HSS' : mat.charAt(0).toUpperCase() + mat.slice(1)}
                      </Button>
                    ))}
                  </div>

                  {/* Size selector */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">Dent Size</p>
                    <SizeSelector currentSize={currentSize} onSizeChange={setCurrentSize} />
                  </div>

                  {/* Zone selector */}
                  <ZoneSelector
                    onZoneClick={(zone) => addDent(zone)}
                    currentSize={currentSize}
                    dentCounts={dentCounts}
                  />

                  {/* Quick add */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">
                      Quick Add to {currentZone.toUpperCase()} zone
                    </p>
                    <QuickAddButtons onQuickAdd={quickAddDents} currentZone={currentZone} />
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Car className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Select a panel from the list to start adding dents</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Dent list for selected panel */}
          {selectedPanel && selectedPanel.dents.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center justify-between">
                  <span>Dents on {selectedPanel.displayName}</span>
                  <Badge variant="secondary">{selectedPanel.dents.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <DentList dents={selectedPanel.dents} onRemoveDent={removeDent} />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Summary */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Calculator className="h-5 w-5" />
                Estimate Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-muted/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold">{totals.dentCount}</p>
                  <p className="text-xs text-muted-foreground">Total Dents</p>
                </div>
                <div className="bg-muted/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold">{totals.panelCount}</p>
                  <p className="text-xs text-muted-foreground">Panels</p>
                </div>
              </div>

              {/* Panel breakdown */}
              {panels.filter(p => p.dents.length > 0).map(panel => {
                const panelTotal = panel.dents.reduce((sum, d) => sum + (d.price || 0), 0)
                return (
                  <div key={panel.id} className="flex items-center justify-between text-sm">
                    <span>{panel.displayName} ({panel.dents.length})</span>
                    <span className="font-medium">${panelTotal.toFixed(0)}</span>
                  </div>
                )
              })}

              {/* Divider */}
              {totals.dentCount > 0 && (
                <>
                  <div className="border-t pt-3">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Dent Subtotal</span>
                      <span className="font-medium">${totals.dentTotal.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between text-muted-foreground text-sm">
                      <span>R&I Items</span>
                      <span>$0.00</span>
                    </div>
                  </div>

                  <div className="border-t pt-3">
                    <div className="flex items-center justify-between text-lg font-bold">
                      <span>Total</span>
                      <span className="text-green-600">${totals.dentTotal.toFixed(2)}</span>
                    </div>
                  </div>
                </>
              )}

              {totals.dentCount === 0 && (
                <p className="text-center text-muted-foreground py-4">
                  No dents added yet
                </p>
              )}
            </CardContent>
          </Card>

          {/* Vehicle summary */}
          {(vehicle.year || vehicle.make || vehicle.model) && (
            <Card>
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground">Vehicle</p>
                <p className="font-medium">
                  {[vehicle.year, vehicle.make, vehicle.model].filter(Boolean).join(' ')}
                </p>
                {vehicle.vin && (
                  <p className="text-xs text-muted-foreground mt-1">VIN: {vehicle.vin}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Action buttons */}
          <div className="space-y-2">
            <Button className="w-full" size="lg">
              <Save className="h-4 w-4 mr-2" />
              Save Estimate
            </Button>
            <Button variant="outline" className="w-full">
              Continue to R&I Items
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EstimateBuilder
