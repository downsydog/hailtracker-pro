/**
 * PDR Estimate Builder - Matrix-Based Pricing
 *
 * Panel-based pricing using insurance company matrices.
 * Price per panel based on dent count range + majority size.
 *
 * Features:
 * - Visual vehicle panel selector
 * - VIN decode with aluminum panel auto-detection
 * - Matrix profile selection (insurance company)
 * - Panel entry: count, majority size, modifiers
 * - Upcharges: aluminum +25%, HSS +25%, glue pull +25%, tall roof +25%
 * - Oversized dents: flat fee per dent
 * - CR (Conventional Repair) warnings
 * - Real-time pricing preview
 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
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
  DialogDescription,
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
  Search,
  AlertTriangle,
  Loader2,
  User,
  Building2,
  Plus,
  Trash2,
  DollarSign,
  Shield,
  Edit2,
  Check,
  AlertCircle,
  Zap,
  CircleDot,
  Bell
} from 'lucide-react'

// Import hooks
import {
  usePDREstimate,
  useCreatePDREstimate,
  useUpdatePDREstimate,
  useAddPanel,
  useUpdatePanel,
  useDeletePanel,
  useMatrixProfiles,
  useSetMatrixProfile,
  useMatrixLookup,
  useDecodeVIN,
  useSearchLeads,
  useCalculateTotals,
  useLinkToCRM,
  useCheckAluminum,
  Panel,
  MatrixPricing,
  PANEL_NAMES,
  SIZE_LABELS
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

// Dent sizes for majority size selection
const DENT_SIZES = [
  { value: 'dime', label: 'Dime', description: 'Up to 1/2"', color: 'bg-green-500' },
  { value: 'nickel', label: 'Nickel', description: '1/2" - 1"', color: 'bg-yellow-500' },
  { value: 'quarter', label: 'Quarter', description: '1" - 2"', color: 'bg-orange-500' },
  { value: 'half', label: 'Half Dollar', description: '2" - 3"', color: 'bg-red-500' }
] as const

// Quick panel buttons - most common hail panels
const QUICK_PANELS = [
  { id: 'hood', label: 'Hood', icon: '🚗' },
  { id: 'roof', label: 'Roof', icon: '⬛' },
  { id: 'deck_lid', label: 'Trunk', icon: '📦' },
  { id: 'lf_door', label: 'LF Door', icon: '🚪' },
  { id: 'rf_door', label: 'RF Door', icon: '🚪' },
  { id: 'l_fender', label: 'L Fender', icon: '◀' },
  { id: 'r_fender', label: 'R Fender', icon: '▶' },
]

// Visual vehicle layout - positioned panels
const VEHICLE_PANELS = [
  // Top row
  { id: 'hood', label: 'Hood', gridArea: '1 / 2 / 2 / 4', category: 'primary' },
  // Second row
  { id: 'l_fender', label: 'L Fender', gridArea: '2 / 1 / 3 / 2', category: 'primary' },
  { id: 'cowl_other', label: 'Cowl', gridArea: '2 / 2 / 3 / 4', category: 'secondary' },
  { id: 'r_fender', label: 'R Fender', gridArea: '2 / 4 / 3 / 5', category: 'primary' },
  // Third row - doors
  { id: 'lf_door', label: 'LF Door', gridArea: '3 / 1 / 4 / 2', category: 'primary' },
  { id: 'l_roof_rail', label: 'L Rail', gridArea: '3 / 2 / 4 / 3', category: 'secondary' },
  { id: 'r_roof_rail', label: 'R Rail', gridArea: '3 / 3 / 4 / 4', category: 'secondary' },
  { id: 'rf_door', label: 'RF Door', gridArea: '3 / 4 / 4 / 5', category: 'primary' },
  // Fourth row - roof
  { id: 'lr_door', label: 'LR Door', gridArea: '4 / 1 / 5 / 2', category: 'primary' },
  { id: 'roof', label: 'Roof', gridArea: '4 / 2 / 5 / 4', category: 'primary' },
  { id: 'rr_door', label: 'RR Door', gridArea: '4 / 4 / 5 / 5', category: 'primary' },
  // Fifth row - quarters
  { id: 'l_quarter', label: 'L Qtr', gridArea: '5 / 1 / 6 / 2', category: 'primary' },
  { id: 'metal_sunroof', label: 'Sunroof', gridArea: '5 / 2 / 6 / 4', category: 'secondary' },
  { id: 'r_quarter', label: 'R Qtr', gridArea: '5 / 4 / 6 / 5', category: 'primary' },
  // Bottom row
  { id: 'deck_lid', label: 'Deck Lid', gridArea: '6 / 2 / 7 / 4', category: 'primary' },
]

// Truck-specific panels
const TRUCK_PANELS = [
  { id: 'bedside_l', label: 'L Bed', gridArea: '5 / 1 / 7 / 2', category: 'truck' },
  { id: 'bedside_r', label: 'R Bed', gridArea: '5 / 4 / 7 / 5', category: 'truck' },
  { id: 'cab_corner_l', label: 'L Cab', gridArea: '4 / 1 / 5 / 2', category: 'truck' },
  { id: 'cab_corner_r', label: 'R Cab', gridArea: '4 / 4 / 5 / 5', category: 'truck' },
  { id: 'tailgate', label: 'Tailgate', gridArea: '7 / 2 / 8 / 4', category: 'truck' },
]

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-700 border-slate-300',
  in_progress: 'bg-amber-100 text-amber-700 border-amber-300',
  approved: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  completed: 'bg-blue-100 text-blue-700 border-blue-300'
}

// Panel entry form state
interface PanelFormData {
  panel_name: string
  total_dent_count: number
  majority_size: 'dime' | 'nickel' | 'quarter' | 'half'
  oversized_count: number
  is_aluminum: boolean
  is_hss: boolean
  requires_glue_pull: boolean
  is_tall_roof: boolean
}

const defaultPanelForm: PanelFormData = {
  panel_name: '',
  total_dent_count: 0,
  majority_size: 'quarter',
  oversized_count: 0,
  is_aluminum: false,
  is_hss: false,
  requires_glue_pull: false,
  is_tall_roof: false
}

export function EstimateBuilder() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isNew = !id || id === 'new'

  // Local state
  const [vehicleExpanded, setVehicleExpanded] = useState(true)
  const [customerExpanded, setCustomerExpanded] = useState(false)
  const [vinInput, setVinInput] = useState('')
  const [leadSearchOpen, setLeadSearchOpen] = useState(false)
  const [leadSearchQuery, setLeadSearchQuery] = useState('')
  const [panelFormOpen, setPanelFormOpen] = useState(false)
  const [panelForm, setPanelForm] = useState<PanelFormData>(defaultPanelForm)
  const [editingPanelId, setEditingPanelId] = useState<number | null>(null)
  const [pricingPreview, setPricingPreview] = useState<MatrixPricing | null>(null)
  const [showTruckPanels, setShowTruckPanels] = useState(false)
  const [aluminumNotification, setAluminumNotification] = useState<string | null>(null)

  // Form state for new estimate
  const [formData, setFormData] = useState({
    vehicle_year: '',
    vehicle_make: '',
    vehicle_model: '',
    vehicle_vin: '',
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    claim_number: '',
    matrix_profile_id: ''
  })

  // API hooks
  const { data: estimate, isLoading: isLoadingEstimate, refetch } = usePDREstimate(isNew ? null : parseInt(id!))
  const createEstimate = useCreatePDREstimate()
  const updateEstimate = useUpdatePDREstimate()
  const addPanel = useAddPanel()
  const updatePanel = useUpdatePanel()
  const deletePanel = useDeletePanel()
  const { data: matrixProfilesData } = useMatrixProfiles()
  const setMatrixProfile = useSetMatrixProfile()
  const matrixLookup = useMatrixLookup()
  const decodeVIN = useDecodeVIN()
  const checkAluminum = useCheckAluminum()
  const { data: leadSearchData } = useSearchLeads(leadSearchQuery)
  const calculateTotals = useCalculateTotals()
  const linkToCRM = useLinkToCRM()

  // Derived state
  const matrixProfiles = matrixProfilesData?.profiles || []
  const leadResults = leadSearchData?.leads || []

  // Aluminum panels from VIN decode
  const [aluminumPanels, setAluminumPanels] = useState<string[]>([])

  // Check if vehicle is a truck
  const isTruck = useMemo(() => {
    const model = formData.vehicle_model.toLowerCase()
    const make = formData.vehicle_make.toLowerCase()
    return (
      model.includes('f-150') || model.includes('f150') ||
      model.includes('silverado') || model.includes('sierra') ||
      model.includes('ram') || model.includes('tundra') ||
      model.includes('tacoma') || model.includes('titan') ||
      model.includes('colorado') || model.includes('canyon') ||
      model.includes('ranger') || model.includes('frontier') ||
      model.includes('ridgeline') || make === 'ram'
    )
  }, [formData.vehicle_make, formData.vehicle_model])

  // Auto-show truck panels
  useEffect(() => {
    setShowTruckPanels(isTruck)
  }, [isTruck])

  // Initialize form from existing estimate
  useEffect(() => {
    if (estimate) {
      setFormData({
        vehicle_year: estimate.vehicle_year?.toString() || '',
        vehicle_make: estimate.vehicle_make || '',
        vehicle_model: estimate.vehicle_model || '',
        vehicle_vin: estimate.vin || '',
        customer_name: estimate.customer_name || '',
        customer_email: estimate.customer_email || '',
        customer_phone: estimate.customer_phone || '',
        claim_number: estimate.claim_number || '',
        matrix_profile_id: estimate.matrix_profile_id?.toString() || ''
      })
      if (estimate.vin) {
        setVinInput(estimate.vin)
      }
      // Collapse vehicle section if already filled
      if (estimate.vehicle_year && estimate.vehicle_make) {
        setVehicleExpanded(false)
      }
    }
  }, [estimate])

  // Handle VIN decode with aluminum auto-detect
  const handleDecodeVIN = async () => {
    if (!vinInput || vinInput.length !== 17) return

    try {
      const result = await decodeVIN.mutateAsync(vinInput)
      setFormData(prev => ({
        ...prev,
        vehicle_year: result.year.toString(),
        vehicle_make: result.make,
        vehicle_model: result.model,
        vehicle_vin: vinInput
      }))

      // Check for aluminum panels
      if (result.aluminum_panels && result.aluminum_panels.length > 0) {
        setAluminumPanels(result.aluminum_panels)
        const panelNames = result.aluminum_panels.map(p => PANEL_NAMES[p] || p).slice(0, 3)
        const moreCount = result.aluminum_panels.length - 3
        const panelList = moreCount > 0
          ? `${panelNames.join(', ')} +${moreCount} more`
          : panelNames.join(', ')
        setAluminumNotification(
          `${result.year}+ ${result.make} ${result.model} detected - ${panelList} are aluminum`
        )
        // Auto-dismiss after 8 seconds
        setTimeout(() => setAluminumNotification(null), 8000)
      }

      setVehicleExpanded(false)
    } catch (error) {
      console.error('VIN decode failed:', error)
    }
  }

  // Check aluminum panels when make/model changes (manual entry)
  useEffect(() => {
    if (formData.vehicle_make && formData.vehicle_model && !formData.vehicle_vin) {
      checkAluminum.mutateAsync({
        make: formData.vehicle_make,
        model: formData.vehicle_model,
        year: formData.vehicle_year ? parseInt(formData.vehicle_year) : undefined
      }).then(result => {
        if (result.aluminum_panels?.length > 0) {
          setAluminumPanels(result.aluminum_panels)
        }
      }).catch(() => {})
    }
  }, [formData.vehicle_make, formData.vehicle_model, formData.vehicle_year])

  // Create or update estimate
  const handleSave = async () => {
    const data = {
      vehicle_year: parseInt(formData.vehicle_year),
      vehicle_make: formData.vehicle_make,
      vehicle_model: formData.vehicle_model,
      vin: formData.vehicle_vin || undefined,
      customer_name: formData.customer_name || undefined,
      customer_email: formData.customer_email || undefined,
      customer_phone: formData.customer_phone || undefined,
      claim_number: formData.claim_number || undefined,
      matrix_profile_id: formData.matrix_profile_id ? parseInt(formData.matrix_profile_id) : undefined
    }

    if (isNew) {
      const result = await createEstimate.mutateAsync(data)
      navigate(`/estimates/${result.estimate.id}`, { replace: true })
    } else {
      await updateEstimate.mutateAsync({ id: parseInt(id!), data })
      refetch()
    }
  }

  // Handle matrix profile change
  const handleMatrixProfileChange = async (profileId: string) => {
    setFormData(prev => ({ ...prev, matrix_profile_id: profileId }))

    if (estimate && profileId) {
      await setMatrixProfile.mutateAsync({
        id: estimate.id,
        data: { matrix_profile_id: parseInt(profileId) }
      })
      refetch()
    }
  }

  // Open panel form for specific panel
  const handlePanelClick = (panelId: string) => {
    // Check if panel already exists
    const existingPanel = estimate?.panels?.find(p => p.panel_name === panelId)
    if (existingPanel) {
      handleEditPanel(existingPanel)
    } else {
      // New panel
      const isAluminum = aluminumPanels.includes(panelId)
      setPanelForm({
        ...defaultPanelForm,
        panel_name: panelId,
        is_aluminum: isAluminum
      })
      setEditingPanelId(null)
      setPricingPreview(null)
      setPanelFormOpen(true)
    }
  }

  // Open panel form for editing
  const handleEditPanel = (panel: Panel) => {
    setPanelForm({
      panel_name: panel.panel_name,
      total_dent_count: panel.total_dent_count,
      majority_size: panel.majority_size,
      oversized_count: panel.oversized_count,
      is_aluminum: panel.is_aluminum,
      is_hss: panel.is_hss,
      requires_glue_pull: panel.requires_glue_pull,
      is_tall_roof: panel.is_tall_roof
    })
    setEditingPanelId(panel.id)
    setPanelFormOpen(true)
    // Get pricing preview
    handlePricingPreview({
      panel_name: panel.panel_name,
      total_dent_count: panel.total_dent_count,
      majority_size: panel.majority_size,
      oversized_count: panel.oversized_count,
      is_aluminum: panel.is_aluminum,
      is_hss: panel.is_hss,
      requires_glue_pull: panel.requires_glue_pull,
      is_tall_roof: panel.is_tall_roof
    })
  }

  // Get pricing preview when form changes
  const handlePricingPreview = useCallback(async (data: PanelFormData) => {
    if (!data.panel_name || data.total_dent_count <= 0) {
      setPricingPreview(null)
      return
    }

    try {
      const result = await matrixLookup.mutateAsync({
        matrix_profile_id: estimate?.matrix_profile_id || (formData.matrix_profile_id ? parseInt(formData.matrix_profile_id) : undefined),
        panel: data.panel_name,
        dent_count: data.total_dent_count,
        majority_size: data.majority_size,
        oversized_count: data.oversized_count,
        is_aluminum: data.is_aluminum,
        is_hss: data.is_hss,
        requires_glue_pull: data.requires_glue_pull,
        is_tall_roof: data.is_tall_roof
      })
      setPricingPreview(result)
    } catch (error) {
      console.error('Pricing lookup failed:', error)
      setPricingPreview(null)
    }
  }, [estimate?.matrix_profile_id, formData.matrix_profile_id, matrixLookup])

  // Update panel form and get preview
  const updatePanelForm = (updates: Partial<PanelFormData>) => {
    const newForm = { ...panelForm, ...updates }
    setPanelForm(newForm)

    // Auto-set aluminum if panel is known aluminum
    if (updates.panel_name && aluminumPanels.includes(updates.panel_name)) {
      newForm.is_aluminum = true
      setPanelForm(newForm)
    }

    // Debounce pricing preview
    if (newForm.panel_name && newForm.total_dent_count > 0) {
      handlePricingPreview(newForm)
    }
  }

  // Save panel
  const handleSavePanel = async () => {
    if (!estimate || !panelForm.panel_name || panelForm.total_dent_count <= 0) return

    const data = {
      panel_name: panelForm.panel_name,
      total_dent_count: panelForm.total_dent_count,
      majority_size: panelForm.majority_size,
      oversized_count: panelForm.oversized_count,
      is_aluminum: panelForm.is_aluminum,
      is_hss: panelForm.is_hss,
      requires_glue_pull: panelForm.requires_glue_pull,
      is_tall_roof: panelForm.is_tall_roof
    }

    if (editingPanelId) {
      await updatePanel.mutateAsync({
        estimateId: estimate.id,
        panelId: editingPanelId,
        data
      })
    } else {
      await addPanel.mutateAsync({
        estimateId: estimate.id,
        data
      })
    }

    setPanelFormOpen(false)
    setPanelForm(defaultPanelForm)
    setEditingPanelId(null)
    setPricingPreview(null)
    refetch()
  }

  // Delete panel
  const handleDeletePanel = async (panelId: number) => {
    if (!estimate) return
    await deletePanel.mutateAsync({
      estimateId: estimate.id,
      panelId
    })
    refetch()
  }

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
      navigate(`/estimates/${estimate.id}/review`)
    }
  }

  // Get panel status for visual display
  const getPanelStatus = (panelId: string) => {
    const panel = estimate?.panels?.find(p => p.panel_name === panelId)
    if (!panel) return null
    return {
      hasDamage: panel.total_dent_count > 0,
      isCR: panel.is_conventional_repair,
      isAluminum: panel.is_aluminum,
      dentCount: panel.total_dent_count,
      total: panel.panel_total
    }
  }

  // Calculate totals from panels
  const totals = useMemo(() => {
    if (!estimate?.panels) return { labor: 0, ri: 0, total: 0, crCount: 0, panelCount: 0, dentCount: 0 }
    const labor = estimate.panels.reduce((sum, p) => sum + (p.panel_total || 0), 0)
    const ri = estimate.panels.reduce((sum, p) =>
      sum + (p.ri_items?.reduce((s, ri) => s + ri.price, 0) || 0), 0)
    const crCount = estimate.panels.filter(p => p.is_conventional_repair).length
    const dentCount = estimate.panels.reduce((sum, p) => sum + p.total_dent_count, 0)
    return { labor, ri, total: labor + ri, crCount, panelCount: estimate.panels.length, dentCount }
  }, [estimate?.panels])

  // Loading state
  if (!isNew && isLoadingEstimate) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading estimate...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 pb-32">
      {/* Aluminum Detection Notification */}
      {aluminumNotification && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2 fade-in duration-300">
          <div className="bg-amber-50 border-2 border-amber-300 rounded-lg shadow-lg p-4 max-w-md">
            <div className="flex items-start gap-3">
              <Bell className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold text-amber-800">Aluminum Vehicle Detected</div>
                <p className="text-sm text-amber-700 mt-1">{aluminumNotification}</p>
                <p className="text-xs text-amber-600 mt-2 italic">+25% upcharge will auto-apply to these panels</p>
              </div>
              <button
                onClick={() => setAluminumNotification(null)}
                className="text-amber-400 hover:text-amber-600"
              >
                <span className="sr-only">Dismiss</span>
                &times;
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="sticky top-0 z-40 bg-white border-b shadow-sm">
        <div className="flex items-center justify-between p-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/estimates')}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                {isNew ? 'New PDR Estimate' : `Estimate #${estimate?.estimate_number || estimate?.id}`}
              </h1>
              <div className="flex items-center gap-2 mt-1">
                {estimate && (
                  <Badge className={cn('text-xs border', STATUS_STYLES[estimate.status])}>
                    {estimate.status.replace('_', ' ')}
                  </Badge>
                )}
                {formData.vehicle_year && formData.vehicle_make && (
                  <span className="text-sm text-muted-foreground">
                    {formData.vehicle_year} {formData.vehicle_make} {formData.vehicle_model}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSave}
              disabled={createEstimate.isPending || updateEstimate.isPending}
            >
              {(createEstimate.isPending || updateEstimate.isPending) && (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              )}
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>
            {estimate && (
              <Button size="sm" onClick={handleReview}>
                <DollarSign className="h-4 w-4 mr-1" />
                Review
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Vehicle & Insurance */}
          <div className="lg:col-span-3 space-y-4">
            {/* Vehicle Section */}
            <Collapsible open={vehicleExpanded} onOpenChange={setVehicleExpanded}>
              <Card className="shadow-sm">
                <CollapsibleTrigger asChild>
                  <CardHeader className="cursor-pointer hover:bg-slate-50 transition-colors py-3">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Car className="h-4 w-4 text-blue-600" />
                        Vehicle Info
                      </span>
                      <ChevronDown className={cn(
                        'h-4 w-4 transition-transform text-muted-foreground',
                        vehicleExpanded && 'rotate-180'
                      )} />
                    </CardTitle>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-3 pt-0">
                    {/* VIN Input */}
                    <div>
                      <Label className="text-xs text-muted-foreground">VIN Decode</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          placeholder="17-character VIN"
                          value={vinInput}
                          onChange={(e) => setVinInput(e.target.value.toUpperCase())}
                          maxLength={17}
                          className="font-mono text-sm"
                        />
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={handleDecodeVIN}
                          disabled={vinInput.length !== 17 || decodeVIN.isPending}
                        >
                          {decodeVIN.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Zap className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </div>

                    <Separator />

                    {/* Manual entry */}
                    <div className="space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <Label className="text-xs text-muted-foreground">Year</Label>
                          <Select
                            value={formData.vehicle_year}
                            onValueChange={(v) => setFormData(prev => ({ ...prev, vehicle_year: v }))}
                          >
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder="Year" />
                            </SelectTrigger>
                            <SelectContent>
                              {YEARS.map(y => (
                                <SelectItem key={y} value={y}>{y}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Make</Label>
                          <Select
                            value={formData.vehicle_make}
                            onValueChange={(v) => setFormData(prev => ({ ...prev, vehicle_make: v }))}
                          >
                            <SelectTrigger className="h-9">
                              <SelectValue placeholder="Make" />
                            </SelectTrigger>
                            <SelectContent>
                              {MAKES.map(m => (
                                <SelectItem key={m} value={m}>{m}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div>
                        <Label className="text-xs text-muted-foreground">Model</Label>
                        <Input
                          placeholder="Model"
                          value={formData.vehicle_model}
                          onChange={(e) => setFormData(prev => ({ ...prev, vehicle_model: e.target.value }))}
                          className="h-9"
                        />
                      </div>
                    </div>

                    {/* Aluminum indicator */}
                    {aluminumPanels.length > 0 && (
                      <div className="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                        <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        <div className="text-xs">
                          <span className="font-medium text-amber-800">Aluminum: </span>
                          <span className="text-amber-700">
                            {aluminumPanels.slice(0, 4).map(p => PANEL_NAMES[p] || p).join(', ')}
                            {aluminumPanels.length > 4 && ` +${aluminumPanels.length - 4}`}
                          </span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>

            {/* Insurance Matrix */}
            <Card className="shadow-sm">
              <CardHeader className="py-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="h-4 w-4 text-emerald-600" />
                  Insurance Matrix
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <Select
                  value={formData.matrix_profile_id}
                  onValueChange={handleMatrixProfileChange}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select insurance company" />
                  </SelectTrigger>
                  <SelectContent>
                    {matrixProfiles.map(p => (
                      <SelectItem key={p.id} value={p.id.toString()}>
                        <span className="flex items-center gap-2">
                          {p.name}
                          {p.is_default && (
                            <Badge variant="secondary" className="text-xs">Default</Badge>
                          )}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            {/* Customer Section */}
            <Collapsible open={customerExpanded} onOpenChange={setCustomerExpanded}>
              <Card className="shadow-sm">
                <CollapsibleTrigger asChild>
                  <CardHeader className="cursor-pointer hover:bg-slate-50 transition-colors py-3">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <User className="h-4 w-4 text-purple-600" />
                        Customer
                      </span>
                      <ChevronDown className={cn(
                        'h-4 w-4 transition-transform text-muted-foreground',
                        customerExpanded && 'rotate-180'
                      )} />
                    </CardTitle>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-3 pt-0">
                    <Input
                      placeholder="Customer Name"
                      value={formData.customer_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, customer_name: e.target.value }))}
                      className="h-9"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        placeholder="Phone"
                        value={formData.customer_phone}
                        onChange={(e) => setFormData(prev => ({ ...prev, customer_phone: e.target.value }))}
                        className="h-9"
                      />
                      <Input
                        placeholder="Claim #"
                        value={formData.claim_number}
                        onChange={(e) => setFormData(prev => ({ ...prev, claim_number: e.target.value }))}
                        className="h-9"
                      />
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          </div>

          {/* Center Column: Visual Panel Selector */}
          <div className="lg:col-span-6">
            <Card className="shadow-sm">
              <CardHeader className="py-3 border-b">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">Select Damaged Panels</CardTitle>
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-2 text-xs cursor-pointer">
                      <Checkbox
                        checked={showTruckPanels}
                        onCheckedChange={(checked) => setShowTruckPanels(!!checked)}
                      />
                      Show Truck Panels
                    </label>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4">
                {!estimate ? (
                  <div className="text-center py-12">
                    <Car className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                    <p className="text-muted-foreground mb-4">Save estimate first to add panels</p>
                    <Button onClick={handleSave} disabled={!formData.vehicle_year || !formData.vehicle_make}>
                      <Save className="h-4 w-4 mr-2" />
                      Save & Continue
                    </Button>
                  </div>
                ) : (
                  <>
                    {/* Quick Panel Buttons */}
                    <div className="flex flex-wrap gap-2 mb-4 pb-4 border-b">
                      <span className="text-xs text-muted-foreground mr-2 py-1">Quick Add:</span>
                      {QUICK_PANELS.map(panel => {
                        const status = getPanelStatus(panel.id)
                        return (
                          <Button
                            key={panel.id}
                            variant={status?.hasDamage ? "default" : "outline"}
                            size="sm"
                            className={cn(
                              "h-8 px-3",
                              status?.isCR && "bg-red-500 hover:bg-red-600",
                              status?.hasDamage && !status?.isCR && "bg-emerald-600 hover:bg-emerald-700"
                            )}
                            onClick={() => handlePanelClick(panel.id)}
                          >
                            <span className="mr-1">{panel.icon}</span>
                            {panel.label}
                            {status?.hasDamage && (
                              <Badge variant="secondary" className="ml-1 h-5 px-1 text-xs bg-white/20">
                                {status.dentCount}
                              </Badge>
                            )}
                          </Button>
                        )
                      })}
                    </div>

                    {/* Visual Vehicle Grid */}
                    <div
                      className="grid gap-2 mx-auto max-w-md"
                      style={{
                        gridTemplateColumns: 'repeat(4, 1fr)',
                        gridTemplateRows: showTruckPanels ? 'repeat(8, 48px)' : 'repeat(6, 48px)'
                      }}
                    >
                      {VEHICLE_PANELS.map(panel => {
                        const status = getPanelStatus(panel.id)
                        const isAluminum = aluminumPanels.includes(panel.id)

                        return (
                          <TooltipProvider key={panel.id}>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handlePanelClick(panel.id)}
                                  className={cn(
                                    "rounded-lg border-2 text-xs font-medium transition-all relative",
                                    "hover:scale-105 hover:shadow-md",
                                    !status?.hasDamage && "bg-slate-100 border-slate-300 text-slate-600 hover:border-blue-400",
                                    status?.hasDamage && !status?.isCR && "bg-emerald-100 border-emerald-500 text-emerald-800",
                                    status?.isCR && "bg-red-100 border-red-500 text-red-800",
                                    isAluminum && !status?.hasDamage && "border-amber-400 bg-amber-50"
                                  )}
                                  style={{ gridArea: panel.gridArea }}
                                >
                                  <div className="flex flex-col items-center justify-center h-full">
                                    <span>{panel.label}</span>
                                    {status?.hasDamage && (
                                      <span className="text-[10px] opacity-75">
                                        {status.dentCount} dents
                                      </span>
                                    )}
                                  </div>
                                  {/* Status indicators */}
                                  {status?.hasDamage && (
                                    <Check className="absolute top-1 right-1 h-3 w-3" />
                                  )}
                                  {isAluminum && (
                                    <span className="absolute bottom-1 left-1 text-[8px] text-amber-600 font-bold">AL</span>
                                  )}
                                  {status?.isCR && (
                                    <AlertCircle className="absolute top-1 left-1 h-3 w-3 text-red-600" />
                                  )}
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{PANEL_NAMES[panel.id]}</p>
                                {status?.hasDamage && <p className="text-emerald-400">${status.total.toFixed(0)}</p>}
                                {isAluminum && <p className="text-amber-400">Aluminum +25%</p>}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )
                      })}

                      {/* Truck-specific panels */}
                      {showTruckPanels && TRUCK_PANELS.map(panel => {
                        const status = getPanelStatus(panel.id)
                        const isAluminum = aluminumPanels.includes(panel.id)

                        return (
                          <TooltipProvider key={panel.id}>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handlePanelClick(panel.id)}
                                  className={cn(
                                    "rounded-lg border-2 text-xs font-medium transition-all relative",
                                    "hover:scale-105 hover:shadow-md",
                                    "bg-blue-50 border-blue-300 text-blue-700",
                                    status?.hasDamage && "bg-emerald-100 border-emerald-500 text-emerald-800",
                                    status?.isCR && "bg-red-100 border-red-500 text-red-800",
                                    isAluminum && !status?.hasDamage && "border-amber-400 bg-amber-50"
                                  )}
                                  style={{ gridArea: panel.gridArea }}
                                >
                                  <div className="flex flex-col items-center justify-center h-full">
                                    <span>{panel.label}</span>
                                    {status?.hasDamage && (
                                      <span className="text-[10px] opacity-75">{status.dentCount}</span>
                                    )}
                                  </div>
                                  {isAluminum && (
                                    <span className="absolute bottom-1 left-1 text-[8px] text-amber-600 font-bold">AL</span>
                                  )}
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{PANEL_NAMES[panel.id]}</p>
                                {status?.hasDamage && <p className="text-emerald-400">${status.total.toFixed(0)}</p>}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )
                      })}
                    </div>

                    {/* Legend */}
                    <div className="flex flex-wrap items-center justify-center gap-4 mt-4 pt-4 border-t text-xs">
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded bg-slate-200 border border-slate-400"></span>
                        No damage
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded bg-emerald-200 border border-emerald-500"></span>
                        Has damage
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded bg-red-200 border border-red-500"></span>
                        CR required
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-3 h-3 rounded bg-amber-100 border border-amber-400"></span>
                        Aluminum
                      </span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Panels List */}
            {estimate?.panels && estimate.panels.length > 0 && (
              <Card className="shadow-sm mt-4">
                <CardHeader className="py-3 border-b">
                  <CardTitle className="text-sm">Added Panels ({estimate.panels.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y">
                    {estimate.panels.map(panel => (
                      <div
                        key={panel.id}
                        className={cn(
                          "p-3 flex items-center justify-between hover:bg-slate-50 transition-colors",
                          panel.is_conventional_repair && "bg-red-50"
                        )}
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              {PANEL_NAMES[panel.panel_name] || panel.panel_name}
                            </span>
                            {panel.is_conventional_repair && (
                              <Badge variant="destructive" className="text-xs">CR</Badge>
                            )}
                            {panel.is_aluminum && (
                              <Badge variant="outline" className="text-xs text-amber-700 border-amber-300">AL</Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                            <span>{panel.total_dent_count} dents</span>
                            <span className="flex items-center gap-1">
                              <CircleDot className={cn("h-2 w-2", DENT_SIZES.find(s => s.value === panel.majority_size)?.color)} />
                              {SIZE_LABELS[panel.majority_size]}
                            </span>
                            {panel.oversized_count > 0 && (
                              <span>{panel.oversized_count} oversized</span>
                            )}
                            {(panel.is_hss || panel.requires_glue_pull || panel.is_tall_roof) && (
                              <span className="text-emerald-600">
                                +{[
                                  panel.is_hss && 'HSS',
                                  panel.requires_glue_pull && 'Glue',
                                  panel.is_tall_roof && 'Tall'
                                ].filter(Boolean).join(', ')}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-emerald-600">${panel.panel_total.toFixed(0)}</span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleEditPanel(panel)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50"
                            onClick={() => handleDeletePanel(panel.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column: Summary */}
          <div className="lg:col-span-3">
            <Card className="shadow-sm sticky top-20">
              <CardHeader className="py-3 border-b bg-slate-50">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Calculator className="h-4 w-4 text-blue-600" />
                  Estimate Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-4">
                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-blue-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-blue-700">{totals.dentCount}</p>
                    <p className="text-xs text-blue-600">Total Dents</p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-purple-700">{totals.panelCount}</p>
                    <p className="text-xs text-purple-600">Panels</p>
                  </div>
                </div>

                {/* CR Warning */}
                {totals.crCount > 0 && (
                  <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                    <div>
                      <p className="font-medium text-red-800 text-sm">CR Required</p>
                      <p className="text-xs text-red-700">
                        {totals.crCount} panel{totals.crCount > 1 ? 's' : ''} exceed PDR limits
                      </p>
                    </div>
                  </div>
                )}

                <Separator />

                {/* Totals */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">PDR Labor</span>
                    <span className="font-medium">${totals.labor.toFixed(0)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">R&I Operations</span>
                    <span className="font-medium">${totals.ri.toFixed(0)}</span>
                  </div>
                </div>

                <Separator />

                <div className="flex justify-between items-baseline">
                  <span className="text-lg font-bold">Grand Total</span>
                  <span className="text-2xl font-bold text-emerald-600">
                    ${totals.total.toFixed(0)}
                  </span>
                </div>

                {/* Actions */}
                <div className="space-y-2 pt-2">
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={handleCalculate}
                    disabled={!estimate || calculateTotals.isPending}
                  >
                    {calculateTotals.isPending && (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    )}
                    <Calculator className="h-4 w-4 mr-2" />
                    Recalculate Totals
                  </Button>

                  {estimate && (
                    <Button
                      className="w-full bg-emerald-600 hover:bg-emerald-700"
                      size="lg"
                      onClick={handleReview}
                    >
                      <DollarSign className="h-4 w-4 mr-2" />
                      Review & Finalize
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Panel Entry Dialog */}
      <Dialog open={panelFormOpen} onOpenChange={setPanelFormOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {editingPanelId ? 'Edit Panel' : 'Add Panel Damage'}
              {panelForm.panel_name && (
                <Badge variant="outline">{PANEL_NAMES[panelForm.panel_name]}</Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              Enter dent count and select the majority size for pricing
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5">
            {/* Panel Selection (if not pre-selected) */}
            {!panelForm.panel_name && (
              <div>
                <Label>Panel</Label>
                <Select
                  value={panelForm.panel_name}
                  onValueChange={(v) => updatePanelForm({ panel_name: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select panel" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(PANEL_NAMES)
                      .filter(([key]) => !estimate?.panels?.some(p => p.panel_name === key))
                      .map(([key, label]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                          {aluminumPanels.includes(key) && ' (Aluminum)'}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Dent Counts */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="flex items-center gap-1">
                  Total Dent Count
                  <span className="text-red-500">*</span>
                </Label>
                <Input
                  type="number"
                  min={1}
                  max={300}
                  value={panelForm.total_dent_count || ''}
                  onChange={(e) => updatePanelForm({ total_dent_count: parseInt(e.target.value) || 0 })}
                  placeholder="Enter count"
                  className="text-lg font-medium"
                />
              </div>
              <div>
                <Label>Oversized (3"+)</Label>
                <Input
                  type="number"
                  min={0}
                  max={panelForm.total_dent_count}
                  value={panelForm.oversized_count || ''}
                  onChange={(e) => updatePanelForm({ oversized_count: parseInt(e.target.value) || 0 })}
                  placeholder="0"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  +${pricingPreview?.oversized_charge_each || 50}/dent
                </p>
              </div>
            </div>

            {/* Majority Size - Visual Buttons */}
            <div>
              <Label>Majority Dent Size</Label>
              <div className="grid grid-cols-4 gap-2 mt-2">
                {DENT_SIZES.map(size => (
                  <button
                    key={size.value}
                    type="button"
                    onClick={() => updatePanelForm({ majority_size: size.value })}
                    className={cn(
                      "p-3 rounded-lg border-2 text-center transition-all",
                      panelForm.majority_size === size.value
                        ? "border-primary bg-primary/10 ring-2 ring-primary/20"
                        : "border-slate-200 hover:border-primary/50 hover:bg-slate-50"
                    )}
                  >
                    <div className={cn("w-4 h-4 rounded-full mx-auto mb-1", size.color)} />
                    <div className="font-medium text-sm">{size.label}</div>
                    <div className="text-xs text-muted-foreground">{size.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Modifiers */}
            <div>
              <Label>Panel Modifiers (+25% each)</Label>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <label className={cn(
                  "flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all",
                  panelForm.is_aluminum
                    ? "border-amber-400 bg-amber-50"
                    : "border-slate-200 hover:border-slate-300"
                )}>
                  <Checkbox
                    checked={panelForm.is_aluminum}
                    onCheckedChange={(checked) => updatePanelForm({ is_aluminum: !!checked })}
                  />
                  <div>
                    <span className="text-sm font-medium">Aluminum</span>
                    {aluminumPanels.includes(panelForm.panel_name) && (
                      <span className="text-xs text-amber-600 block">Auto-detected</span>
                    )}
                  </div>
                </label>
                <label className={cn(
                  "flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all",
                  panelForm.is_hss
                    ? "border-blue-400 bg-blue-50"
                    : "border-slate-200 hover:border-slate-300"
                )}>
                  <Checkbox
                    checked={panelForm.is_hss}
                    onCheckedChange={(checked) => updatePanelForm({ is_hss: !!checked })}
                  />
                  <span className="text-sm font-medium">High Strength Steel</span>
                </label>
                <label className={cn(
                  "flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all",
                  panelForm.requires_glue_pull
                    ? "border-purple-400 bg-purple-50"
                    : "border-slate-200 hover:border-slate-300"
                )}>
                  <Checkbox
                    checked={panelForm.requires_glue_pull}
                    onCheckedChange={(checked) => updatePanelForm({ requires_glue_pull: !!checked })}
                  />
                  <span className="text-sm font-medium">Glue Pull Only</span>
                </label>
                <label className={cn(
                  "flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all",
                  panelForm.is_tall_roof
                    ? "border-emerald-400 bg-emerald-50"
                    : "border-slate-200 hover:border-slate-300"
                )}>
                  <Checkbox
                    checked={panelForm.is_tall_roof}
                    onCheckedChange={(checked) => updatePanelForm({ is_tall_roof: !!checked })}
                  />
                  <span className="text-sm font-medium">Tall Roof Access</span>
                </label>
              </div>
            </div>

            {/* Pricing Preview */}
            {pricingPreview && (
              <div className={cn(
                "p-4 rounded-lg border-2",
                pricingPreview.is_cr
                  ? "border-red-300 bg-red-50"
                  : "border-emerald-300 bg-emerald-50"
              )}>
                {pricingPreview.is_cr ? (
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-6 w-6 text-red-600 flex-shrink-0" />
                    <div>
                      <div className="font-bold text-red-800">Conventional Repair Required</div>
                      <p className="text-sm text-red-700 mt-1">
                        {pricingPreview.dent_count} {pricingPreview.size_display} dents exceeds
                        PDR limits for this panel. Flag for body shop repair.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex justify-between items-center mb-3">
                      <div>
                        <span className="text-sm text-muted-foreground">
                          {pricingPreview.count_range} dents @ {pricingPreview.size_display}
                        </span>
                        <div className="text-xs text-muted-foreground">
                          {pricingPreview.matrix_profile_name} Matrix
                        </div>
                      </div>
                      <span className="text-2xl font-bold text-emerald-700">
                        ${pricingPreview.panel_total.toFixed(0)}
                      </span>
                    </div>
                    <div className="space-y-1 text-sm border-t border-emerald-200 pt-2">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Base Price</span>
                        <span>${pricingPreview.matrix_base_price.toFixed(0)}</span>
                      </div>
                      {pricingPreview.upcharges.map((upcharge, i) => (
                        <div key={i} className="flex justify-between text-emerald-700">
                          <span className="flex items-center gap-1">
                            <Plus className="h-3 w-3" />
                            {upcharge.label}
                          </span>
                          <span>${(upcharge.total || 0).toFixed(0)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button
                variant="outline"
                onClick={() => {
                  setPanelFormOpen(false)
                  setPanelForm(defaultPanelForm)
                  setEditingPanelId(null)
                  setPricingPreview(null)
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSavePanel}
                disabled={
                  !panelForm.panel_name ||
                  panelForm.total_dent_count <= 0 ||
                  addPanel.isPending ||
                  updatePanel.isPending
                }
                className="min-w-[120px]"
              >
                {(addPanel.isPending || updatePanel.isPending) ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-1" />
                    {editingPanelId ? 'Update' : 'Add Panel'}
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

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
                    {lead.contact_name} - {lead.phone}
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
