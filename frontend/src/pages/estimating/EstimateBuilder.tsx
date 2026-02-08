/**
 * PDR Estimate Builder - Fast Dent Entry Interface
 *
 * Mobile-first, one-tap dent entry for maximum speed.
 * Goal: Add 20 dents to a panel in < 45 seconds.
 *
 * Features:
 * - VIN decode with vehicle tier detection
 * - Coin-based dent sizes (dime → oversized)
 * - Depth multipliers (shallow → severe)
 * - Zone multipliers (center, edge, crease, body_line)
 * - R&I suggestions with scope bullets
 * - Customer/Lead linking
 * - Insurance profile selection
 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  ArrowLeft,
  Car,
  Save,
  Calculator,
  ChevronDown,
  ChevronRight,
  Search,
  Link,
  AlertTriangle,
  Loader2,
  Undo2,
  User,
  Building2
} from 'lucide-react'

// Import our new components
import { PanelSelector, PanelInfo, DEFAULT_PANELS } from '@/components/estimating/PanelSelector'
import { DentEntry, DentList, DentSize, DentZone, DentDepth } from '@/components/estimating/DentEntry'
import { RISuggestions, RIItemsList, RILibraryItem } from '@/components/estimating/RISuggestions'
import { RunningTotals } from '@/components/estimating/EstimateSummary'

// Import hooks
import {
  usePDREstimate,
  useCreatePDREstimate,
  useUpdatePDREstimate,
  useAddPanel,
  useAddDent,
  useAddDentsBatch,
  useDeleteDent,
  useRISuggestions,
  useAddRIFromLibrary,
  useDecodeVIN,
  useInsuranceProfiles,
  useSearchLeads,
  useCalculateTotals,
  useLinkToCRM,
  PDREstimate,
  Panel,
} from '@/hooks/use-pdr-estimates'
import { cn } from '@/lib/utils'

// Years dropdown
const YEARS = Array.from({ length: 35 }, (_, i) => (new Date().getFullYear() + 1 - i).toString())

// Common makes
const MAKES = [
  'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler',
  'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jeep', 'Kia',
  'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'Nissan', 'Ram', 'Subaru',
  'Tesla', 'Toyota', 'Volkswagen', 'Volvo'
]

// Vehicle tiers
const VEHICLE_TIERS = [
  { value: 'economy', label: 'Economy (0.85x)' },
  { value: 'standard', label: 'Standard (1.0x)' },
  { value: 'premium', label: 'Premium (1.15x)' },
  { value: 'luxury', label: 'Luxury (1.35x)' },
  { value: 'ev_adas', label: 'EV/ADAS (1.25x)' }
]

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  completed: 'bg-blue-100 text-blue-700'
}

export function EstimateBuilder() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const isNew = !id || id === 'new'

  // Local state
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null)
  const [vehicleExpanded, setVehicleExpanded] = useState(true)
  const [customerExpanded, setCustomerExpanded] = useState(false)
  const [vinInput, setVinInput] = useState('')
  const [leadSearchOpen, setLeadSearchOpen] = useState(false)
  const [leadSearchQuery, setLeadSearchQuery] = useState('')
  const [undoStack, setUndoStack] = useState<Array<{ type: string; id: number }>>([])

  // Form state for new estimate
  const [formData, setFormData] = useState({
    vehicle_year: '',
    vehicle_make: '',
    vehicle_model: '',
    vehicle_vin: '',
    vehicle_tier: 'standard',
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    claim_number: '',
    insurance_profile_id: ''
  })

  // API hooks
  const { data: estimate, isLoading: isLoadingEstimate, refetch } = usePDREstimate(isNew ? null : parseInt(id!))
  const createEstimate = useCreatePDREstimate()
  const updateEstimate = useUpdatePDREstimate()
  const addPanel = useAddPanel()
  const addDent = useAddDent()
  const addDentsBatch = useAddDentsBatch()
  const deleteDent = useDeleteDent()
  const decodeVIN = useDecodeVIN()
  const { data: insuranceProfilesData } = useInsuranceProfiles()
  const { data: leadSearchData } = useSearchLeads(leadSearchQuery)
  const calculateTotals = useCalculateTotals()
  const linkToCRM = useLinkToCRM()

  // R&I suggestions for selected panel
  const selectedPanel = useMemo(() => {
    if (!estimate || !selectedPanelId) return null
    return estimate.panels?.find(p => p.panel_name === selectedPanelId) || null
  }, [estimate, selectedPanelId])

  const { data: riSuggestionsData, isLoading: isLoadingRI } = useRISuggestions(
    estimate?.id || null,
    selectedPanel?.id || null
  )
  const addRIFromLibrary = useAddRIFromLibrary()

  // Derived state
  const insuranceProfiles = insuranceProfilesData?.profiles || []
  const riSuggestions = riSuggestionsData?.suggestions || []
  const leadResults = leadSearchData?.leads || []

  // Panel info for selector
  const panelInfo: PanelInfo[] = useMemo(() => {
    if (!estimate?.panels) return []
    return estimate.panels.map(p => ({
      id: p.panel_name,
      name: p.panel_name,
      displayName: DEFAULT_PANELS.find(dp => dp.name === p.panel_name)?.displayName || p.panel_name,
      dentCount: p.dents?.length || 0,
      riCount: p.ri_items?.length || 0,
      total: p.panel_total || 0,
      material: p.material
    }))
  }, [estimate?.panels])

  // Aluminum panels from VIN decode
  const [aluminumPanels, setAluminumPanels] = useState<string[]>([])

  // Initialize form from existing estimate
  useEffect(() => {
    if (estimate) {
      setFormData({
        vehicle_year: estimate.vehicle_year?.toString() || '',
        vehicle_make: estimate.vehicle_make || '',
        vehicle_model: estimate.vehicle_model || '',
        vehicle_vin: estimate.vehicle_vin || '',
        vehicle_tier: estimate.vehicle_tier || 'standard',
        customer_name: estimate.customer_name || '',
        customer_email: estimate.customer_email || '',
        customer_phone: estimate.customer_phone || '',
        claim_number: estimate.claim_number || '',
        insurance_profile_id: estimate.insurance_profile_id?.toString() || ''
      })
      if (estimate.vehicle_vin) {
        setVinInput(estimate.vehicle_vin)
      }
      // Collapse vehicle section if already filled
      if (estimate.vehicle_year && estimate.vehicle_make) {
        setVehicleExpanded(false)
      }
    }
  }, [estimate])

  // Handle VIN decode
  const handleDecodeVIN = async () => {
    if (!vinInput || vinInput.length !== 17) return

    try {
      const result = await decodeVIN.mutateAsync(vinInput)
      setFormData(prev => ({
        ...prev,
        vehicle_year: result.year.toString(),
        vehicle_make: result.make,
        vehicle_model: result.model,
        vehicle_vin: vinInput,
        vehicle_tier: result.vehicle_tier
      }))
      setAluminumPanels(result.aluminum_panels || [])
      setVehicleExpanded(false)
    } catch (error) {
      console.error('VIN decode failed:', error)
    }
  }

  // Create or update estimate
  const handleSave = async () => {
    const data = {
      vehicle_year: parseInt(formData.vehicle_year),
      vehicle_make: formData.vehicle_make,
      vehicle_model: formData.vehicle_model,
      vehicle_vin: formData.vehicle_vin || undefined,
      vehicle_tier: formData.vehicle_tier,
      customer_name: formData.customer_name || undefined,
      customer_email: formData.customer_email || undefined,
      customer_phone: formData.customer_phone || undefined,
      claim_number: formData.claim_number || undefined,
      insurance_profile_id: formData.insurance_profile_id ? parseInt(formData.insurance_profile_id) : undefined
    }

    if (isNew) {
      const newEstimate = await createEstimate.mutateAsync(data)
      navigate(`/estimating/${newEstimate.id}`, { replace: true })
    } else {
      await updateEstimate.mutateAsync({ id: parseInt(id!), data })
    }
  }

  // Handle panel selection
  const handleSelectPanel = useCallback(async (panelId: string) => {
    setSelectedPanelId(panelId)

    // Create panel if it doesn't exist
    if (estimate && !estimate.panels?.find(p => p.panel_name === panelId)) {
      const material = aluminumPanels.includes(panelId) ? 'aluminum' : 'steel'
      await addPanel.mutateAsync({
        estimateId: estimate.id,
        data: { panel_name: panelId, material }
      })
      refetch()
    }
  }, [estimate, aluminumPanels, addPanel, refetch])

  // Handle add dent
  const handleAddDent = useCallback(async (size: DentSize, zone: DentZone, depth: DentDepth) => {
    if (!estimate || !selectedPanel) return

    const result = await addDent.mutateAsync({
      estimateId: estimate.id,
      panelId: selectedPanel.id,
      data: { size, zone, depth }
    })

    setUndoStack(prev => [...prev, { type: 'dent', id: result.id }])
    refetch()
  }, [estimate, selectedPanel, addDent, refetch])

  // Handle batch add
  const handleAddBatch = useCallback(async (size: DentSize, zone: DentZone, depth: DentDepth, count: number) => {
    if (!estimate || !selectedPanel) return

    await addDentsBatch.mutateAsync({
      estimateId: estimate.id,
      panelId: selectedPanel.id,
      dents: [{ size, zone, depth, count }]
    })

    refetch()
  }, [estimate, selectedPanel, addDentsBatch, refetch])

  // Handle delete dent
  const handleDeleteDent = useCallback(async (dentId: number) => {
    if (!estimate) return

    await deleteDent.mutateAsync({
      estimateId: estimate.id,
      dentId
    })

    refetch()
  }, [estimate, deleteDent, refetch])

  // Handle undo
  const handleUndo = useCallback(async () => {
    if (undoStack.length === 0 || !estimate) return

    const lastAction = undoStack[undoStack.length - 1]
    if (lastAction.type === 'dent') {
      await deleteDent.mutateAsync({
        estimateId: estimate.id,
        dentId: lastAction.id
      })
      setUndoStack(prev => prev.slice(0, -1))
      refetch()
    }
  }, [undoStack, estimate, deleteDent, refetch])

  // Handle add R&I
  const handleAddRI = useCallback(async (operationCode: string) => {
    if (!estimate || !selectedPanel) return

    await addRIFromLibrary.mutateAsync({
      estimateId: estimate.id,
      panelId: selectedPanel.id,
      operationCode
    })

    refetch()
  }, [estimate, selectedPanel, addRIFromLibrary, refetch])

  // Handle calculate
  const handleCalculate = async () => {
    if (!estimate) return
    await calculateTotals.mutateAsync(estimate.id)
    refetch()
  }

  // Handle link to lead
  const handleLinkLead = async (leadId: number) => {
    if (!estimate) return
    await linkToCRM.mutateAsync({
      id: estimate.id,
      data: { lead_id: leadId }
    })
    setLeadSearchOpen(false)
    refetch()
  }

  // Navigate to review
  const handleReview = () => {
    if (estimate) {
      navigate(`/estimating/${estimate.id}/review`)
    }
  }

  // Loading state
  if (!isNew && isLoadingEstimate) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-background border-b">
        <div className="flex items-center justify-between p-4 max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/estimating')}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-bold flex items-center gap-2">
                {isNew ? 'New Estimate' : `Estimate #${estimate?.estimate_number || estimate?.id}`}
              </h1>
              {estimate && (
                <Badge className={cn('text-xs', STATUS_STYLES[estimate.status])}>
                  {estimate.status}
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleUndo}
              disabled={undoStack.length === 0}
            >
              <Undo2 className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={createEstimate.isPending || updateEstimate.isPending}
            >
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left Column: Vehicle, Customer, Panels */}
          <div className="space-y-4">
            {/* Vehicle Section */}
            <Collapsible open={vehicleExpanded} onOpenChange={setVehicleExpanded}>
              <Card>
                <CollapsibleTrigger asChild>
                  <CardHeader className="cursor-pointer hover:bg-accent/50 transition-colors">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Car className="h-4 w-4" />
                        Vehicle
                      </span>
                      <div className="flex items-center gap-2">
                        {formData.vehicle_year && formData.vehicle_make && (
                          <span className="text-xs text-muted-foreground font-normal">
                            {formData.vehicle_year} {formData.vehicle_make} {formData.vehicle_model}
                          </span>
                        )}
                        <ChevronDown className={cn(
                          'h-4 w-4 transition-transform',
                          vehicleExpanded && 'rotate-180'
                        )} />
                      </div>
                    </CardTitle>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-3">
                    {/* VIN Input */}
                    <div className="flex gap-2">
                      <Input
                        placeholder="Enter VIN (17 characters)"
                        value={vinInput}
                        onChange={(e) => setVinInput(e.target.value.toUpperCase())}
                        maxLength={17}
                        className="font-mono"
                      />
                      <Button
                        variant="secondary"
                        onClick={handleDecodeVIN}
                        disabled={vinInput.length !== 17 || decodeVIN.isPending}
                      >
                        {decodeVIN.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          'Decode'
                        )}
                      </Button>
                    </div>

                    {/* Aluminum warning */}
                    {aluminumPanels.length > 0 && (
                      <div className="flex items-center gap-2 p-2 bg-orange-50 border border-orange-200 rounded-lg text-sm text-orange-700">
                        <AlertTriangle className="h-4 w-4" />
                        <span>Aluminum panels: {aluminumPanels.join(', ')}</span>
                      </div>
                    )}

                    {/* Manual entry */}
                    <div className="grid grid-cols-3 gap-2">
                      <Select
                        value={formData.vehicle_year}
                        onValueChange={(v) => setFormData(prev => ({ ...prev, vehicle_year: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Year" />
                        </SelectTrigger>
                        <SelectContent>
                          {YEARS.map(y => (
                            <SelectItem key={y} value={y}>{y}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select
                        value={formData.vehicle_make}
                        onValueChange={(v) => setFormData(prev => ({ ...prev, vehicle_make: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Make" />
                        </SelectTrigger>
                        <SelectContent>
                          {MAKES.map(m => (
                            <SelectItem key={m} value={m}>{m}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        placeholder="Model"
                        value={formData.vehicle_model}
                        onChange={(e) => setFormData(prev => ({ ...prev, vehicle_model: e.target.value }))}
                      />
                    </div>

                    {/* Vehicle tier */}
                    <div>
                      <Label className="text-xs text-muted-foreground">Vehicle Tier</Label>
                      <Select
                        value={formData.vehicle_tier}
                        onValueChange={(v) => setFormData(prev => ({ ...prev, vehicle_tier: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {VEHICLE_TIERS.map(t => (
                            <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>

            {/* Customer Section */}
            <Collapsible open={customerExpanded} onOpenChange={setCustomerExpanded}>
              <Card>
                <CollapsibleTrigger asChild>
                  <CardHeader className="cursor-pointer hover:bg-accent/50 transition-colors">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <User className="h-4 w-4" />
                        Customer
                      </span>
                      <div className="flex items-center gap-2">
                        {formData.customer_name && (
                          <span className="text-xs text-muted-foreground font-normal">
                            {formData.customer_name}
                          </span>
                        )}
                        <ChevronDown className={cn(
                          'h-4 w-4 transition-transform',
                          customerExpanded && 'rotate-180'
                        )} />
                      </div>
                    </CardTitle>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-3">
                    {/* Link to Lead button */}
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => setLeadSearchOpen(true)}
                    >
                      <Link className="h-4 w-4 mr-2" />
                      Link to Lead
                    </Button>

                    {/* Manual customer entry */}
                    <Input
                      placeholder="Customer Name"
                      value={formData.customer_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, customer_name: e.target.value }))}
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        placeholder="Phone"
                        value={formData.customer_phone}
                        onChange={(e) => setFormData(prev => ({ ...prev, customer_phone: e.target.value }))}
                      />
                      <Input
                        placeholder="Email"
                        type="email"
                        value={formData.customer_email}
                        onChange={(e) => setFormData(prev => ({ ...prev, customer_email: e.target.value }))}
                      />
                    </div>

                    {/* Insurance */}
                    <div className="border-t pt-3">
                      <Label className="text-xs text-muted-foreground">Insurance</Label>
                      <Select
                        value={formData.insurance_profile_id}
                        onValueChange={(v) => setFormData(prev => ({ ...prev, insurance_profile_id: v }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select insurance carrier" />
                        </SelectTrigger>
                        <SelectContent>
                          {insuranceProfiles.map(p => (
                            <SelectItem key={p.id} value={p.id.toString()}>
                              {p.carrier_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        className="mt-2"
                        placeholder="Claim Number"
                        value={formData.claim_number}
                        onChange={(e) => setFormData(prev => ({ ...prev, claim_number: e.target.value }))}
                      />
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>

            {/* Panel Selector */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Select Panel</CardTitle>
              </CardHeader>
              <CardContent>
                <PanelSelector
                  panels={panelInfo}
                  selectedPanelId={selectedPanelId}
                  onSelectPanel={handleSelectPanel}
                  aluminumPanels={aluminumPanels}
                />
              </CardContent>
            </Card>
          </div>

          {/* Center Column: Dent Entry */}
          <div className="space-y-4">
            {selectedPanelId ? (
              <>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span>
                        {DEFAULT_PANELS.find(p => p.name === selectedPanelId)?.displayName || selectedPanelId}
                      </span>
                      {selectedPanel && selectedPanel.dents?.length > 0 && (
                        <Badge variant="secondary">
                          {selectedPanel.dents.length} dents
                        </Badge>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <DentEntry
                      panelName={selectedPanelId}
                      onAddDent={handleAddDent}
                      onAddBatch={handleAddBatch}
                      disabled={!estimate || addDent.isPending}
                      vehicleTier={formData.vehicle_tier}
                    />
                  </CardContent>
                </Card>

                {/* Dent list for selected panel */}
                {selectedPanel && selectedPanel.dents && selectedPanel.dents.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">
                        Dents ({selectedPanel.dents.length})
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <DentList
                        dents={selectedPanel.dents.map(d => ({
                          id: d.id,
                          size: d.size as DentSize,
                          zone: d.zone as DentZone,
                          depth: (d as any).depth || 'medium',
                          final_price: d.final_price
                        }))}
                        onRemove={handleDeleteDent}
                      />
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Car className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    Select a panel to start adding dents
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column: R&I and Summary */}
          <div className="space-y-4">
            {/* R&I Suggestions */}
            {selectedPanelId && (
              <RISuggestions
                suggestions={riSuggestions}
                addedItems={selectedPanel?.ri_items?.map(ri => ({
                  id: ri.id,
                  operation_code: ri.operation_code,
                  operation_name: ri.operation_name,
                  calculated_time_hours: ri.calculated_time_hours,
                  price: ri.price
                })) || []}
                vehicleTier={formData.vehicle_tier}
                laborRate={75}
                onAdd={handleAddRI}
                isLoading={isLoadingRI}
              />
            )}

            {/* R&I Items Added */}
            {selectedPanel?.ri_items && selectedPanel.ri_items.length > 0 && (
              <RIItemsList
                items={selectedPanel.ri_items.map(ri => ({
                  id: ri.id,
                  operation_code: ri.operation_code,
                  operation_name: ri.operation_name,
                  calculated_time_hours: ri.calculated_time_hours,
                  price: ri.price
                }))}
              />
            )}

            {/* Summary Card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Calculator className="h-4 w-4" />
                  Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-2xl font-bold">
                      {estimate?.panels?.reduce((sum, p) => sum + (p.dents?.length || 0), 0) || 0}
                    </p>
                    <p className="text-xs text-muted-foreground">Total Dents</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-2xl font-bold">
                      {panelInfo.filter(p => p.dentCount > 0).length}
                    </p>
                    <p className="text-xs text-muted-foreground">Panels</p>
                  </div>
                </div>

                {/* Panel totals */}
                {panelInfo.filter(p => p.dentCount > 0).map(panel => (
                  <div
                    key={panel.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span>{panel.displayName} ({panel.dentCount})</span>
                    <span className="font-medium">${panel.total.toFixed(0)}</span>
                  </div>
                ))}

                {estimate && (
                  <>
                    <div className="border-t pt-2 space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Dents</span>
                        <span>${(estimate.dent_total || 0).toFixed(0)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">R&I</span>
                        <span>${(estimate.ri_total || 0).toFixed(0)}</span>
                      </div>
                    </div>
                    <div className="flex justify-between text-lg border-t pt-2">
                      <span className="font-bold">Total</span>
                      <span className="font-bold text-green-600">
                        ${(estimate.grand_total || 0).toFixed(0)}
                      </span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Running Totals Footer */}
      {estimate && (
        <RunningTotals
          dentTotal={estimate.dent_total || 0}
          riTotal={estimate.ri_total || 0}
          grandTotal={estimate.grand_total || 0}
          onCalculate={handleCalculate}
          onReview={handleReview}
          isCalculating={calculateTotals.isPending}
        />
      )}

      {/* Lead Search Dialog */}
      <Dialog open={leadSearchOpen} onOpenChange={setLeadSearchOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link to Lead</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Search leads..."
                value={leadSearchQuery}
                onChange={(e) => setLeadSearchQuery(e.target.value)}
              />
              <Button variant="secondary">
                <Search className="h-4 w-4" />
              </Button>
            </div>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {leadResults.map(lead => (
                <button
                  key={lead.id}
                  onClick={() => handleLinkLead(lead.id)}
                  className="w-full p-3 text-left rounded-lg border hover:bg-accent transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{lead.business_name}</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {lead.contact_name} • {lead.phone}
                  </p>
                </button>
              ))}
              {leadSearchQuery.length >= 2 && leadResults.length === 0 && (
                <p className="text-center text-muted-foreground py-4">
                  No leads found
                </p>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default EstimateBuilder
