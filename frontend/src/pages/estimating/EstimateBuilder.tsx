/**
 * PDR Estimate Builder - Mobile Tech RX Style
 *
 * Industry-standard hail estimating interface with FULL INTEGRATION:
 * - Tappable vehicle diagram (car/truck/SUV)
 * - Panel list sidebar with real-time pricing
 * - Customer picker with integration to customers table
 * - Vehicle picker with integration to vehicles table
 * - Lead conversion on estimate creation
 * - Invoice conversion for approved estimates
 * - Full data persistence for all relationships
 *
 * Phase 7A+: Single-line writer row for rapid keyboard-first entry
 * Phase 7B: Auto pricing engine with panel-level calculations
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { Button } from '@/components/ui/button'
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
  ArrowLeft,
  Save,
  Search,
  User,
  Loader2,
  UserPlus,
  Car,
  Receipt,
  CheckCircle,
  Clock,
  Send,
  FileText,
  AlertCircle,
  Download,
  Archive,
  PenLine,
  Lock,
  DollarSign,
  Wrench,
  Play,
  Keyboard,
  Repeat,
  Command,
  X,
  Plus,
  Zap,
  Info
} from 'lucide-react'

// Import estimate components
import {
  VehicleDiagram,
  VehicleType,
  PanelState,
  PanelClickEvent,
  PanelClickWithModifiers,
  VEHICLE_PANELS,
  PanelEntryModal,
  PanelDamage,
  CountRange,
  DentSize,
  PanelListSidebar,
  EstimateBottomNav,
  ServiceTab,
  CustomerPicker,
  VehiclePicker,
  QuickEntryOverlay,
  QuickEntryValue,
  EstimateStatusBar,
  SendToAdjusterModal,
  CreateSupplementModal,
  CreateShareLinkModal
} from '@/components/estimates'
import { computeSeverity } from '@/components/estimates/VehicleDiagram/severity'

// Import hooks
import {
  usePDREstimate,
  useCreatePDREstimate,
  useUpdatePDREstimate,
  useMatrixProfiles,
  useDecodeVIN,
  useLinkToCRM,
  useConvertToInvoice,
  useAddPanelMatrix,
  useUpdatePanelMatrix,
  countRangeToNumber,
  useDownloadEstimatePDF,
  useDownloadEstimatePhotoSheetPDF,
  useDownloadEstimateDisputePack,
  useEstimateActivities
} from '@/hooks/use-pdr-estimates'
import {
  useRiCatalog,
  useEstimateRI,
  useAddEstimateRI,
  useRemoveEstimateRI,
  useDenialCodes,
  useDenialSimulator,
  useSupplementWriter,
  RIOperation,
  DenialRebuttal,
  SupplementLetter
} from '@/hooks/use-ri'
import {
  useEstimateLaborRate,
  useSetLaborRateOverride,
} from '@/hooks/use-labor-rates'
import { useCustomer } from '@/hooks/use-customers'
import { useLead, useConvertLead } from '@/hooks/use-leads'
import { useCreateVehicle, useVehicle } from '@/hooks/use-vehicles'
import { Customer, Vehicle } from '@/types'
import { getRiSuggestionsForPanel, RISuggestion } from '@/lib/riPanelSuggestions'

// ============================================================================
// PHASE 7 FEATURE FLAGS
// ============================================================================
const ENABLE_WRITER_ROW = true      // 7A: Single-line panel entry mode
const ENABLE_PRICING_ENGINE = true  // 7B: Auto pricing with breakdown tooltips

// ============================================================================
// PHASE 7B: PRICING ENGINE TYPES & CONFIG
// ============================================================================
interface PricingContext {
  baseRatePerDent: number
  sizeMultipliers: Record<string, number>
  depthMultipliers: Record<string, number>
  zoneMultipliers: Record<string, number>
  materialMultipliers: Record<string, number>
  oversizedSurcharge: number
}

const DEFAULT_PRICING_CONTEXT: PricingContext = {
  baseRatePerDent: 15, // Base rate per dent
  sizeMultipliers: {
    dime: 1.0,
    nickel: 1.25,
    quarter: 1.5,
    half: 2.0,
  },
  depthMultipliers: {
    shallow: 1.0,
    medium: 1.15,
    deep: 1.35,
    severe: 1.6,
  },
  zoneMultipliers: {
    center: 1.0,
    edge: 1.1,
    crease: 1.25,
    body_line: 1.35,
  },
  materialMultipliers: {
    steel: 1.0,
    aluminum: 1.25,
    hss: 1.25,
  },
  oversizedSurcharge: 50,
}

/**
 * Phase 7B: Compute panel price with full breakdown
 */
function computePanelPrice(
  panel: {
    countRange?: string | null
    dentSize?: string | null
    depth?: string
    zone?: string
    gluePull?: boolean
    aluminum?: boolean
    hss?: boolean
    doubleMetal?: boolean
    oversizedCount?: number
  },
  ctx: PricingContext = DEFAULT_PRICING_CONTEXT
): { basePrice: number; totalPrice: number; breakdown: string[] } {
  if (!panel.countRange || !panel.dentSize) {
    return { basePrice: 0, totalPrice: 0, breakdown: [] }
  }

  const breakdown: string[] = []

  // Parse count range to get average dent count
  const countMap: Record<string, number> = {
    '1-5': 3, '6-15': 10, '16-30': 23, '31-50': 40,
    '51-75': 63, '76-100': 88, '101+': 120
  }
  const dentCount = countMap[panel.countRange] || 10
  breakdown.push(`${dentCount} dents @ $${ctx.baseRatePerDent}/dent`)

  // Base price from count
  let price = dentCount * ctx.baseRatePerDent

  // Size multiplier
  const sizeMult = ctx.sizeMultipliers[panel.dentSize] || 1.0
  if (sizeMult !== 1.0) {
    breakdown.push(`Size (${panel.dentSize}): ×${sizeMult}`)
  }
  price *= sizeMult

  // Depth multiplier
  const depthMult = ctx.depthMultipliers[panel.depth || 'medium'] || 1.0
  if (depthMult !== 1.0) {
    breakdown.push(`Depth (${panel.depth}): ×${depthMult}`)
  }
  price *= depthMult

  // Zone multiplier
  const zoneMult = ctx.zoneMultipliers[panel.zone || 'center'] || 1.0
  if (zoneMult !== 1.0) {
    breakdown.push(`Zone (${panel.zone}): ×${zoneMult}`)
  }
  price *= zoneMult

  const basePrice = price

  // Add-on multipliers (additive)
  let addonMult = 1.0
  if (panel.gluePull) { addonMult += 0.25; breakdown.push('Glue Pull: +25%') }
  if (panel.aluminum) { addonMult += 0.25; breakdown.push('Aluminum: +25%') }
  if (panel.hss) { addonMult += 0.25; breakdown.push('HSS: +25%') }
  if (panel.doubleMetal) { addonMult += 0.50; breakdown.push('Double Metal: +50%') }
  price *= addonMult

  // Oversized surcharge
  if (panel.oversizedCount && panel.oversizedCount > 0) {
    const osCharge = panel.oversizedCount * ctx.oversizedSurcharge
    price += osCharge
    breakdown.push(`${panel.oversizedCount} oversized @ $${ctx.oversizedSurcharge}: +$${osCharge}`)
  }

  return { basePrice, totalPrice: Math.round(price * 100) / 100, breakdown }
}

// ============================================================================
// PHASE 7A: WRITER ROW TYPES
// ============================================================================
interface WriterDraft {
  panelName: string
  countRange: CountRange | null
  dentSize: DentSize | null
  depth: string
  zone: string
  material: 'steel' | 'aluminum'
  notes: string
}

// Default empty panel damage
const createEmptyPanelDamage = (panelId: string): PanelDamage => ({
  panelId,
  countRange: null,
  dentSize: null,
  oversizedCount: 0,
  gluePull: false,
  aluminum: false,
  hss: false,
  doubleMetal: false,
  conventional: false,
  notes: '',
  basePrice: 0,
  totalPrice: 0
})

// Sample matrix data (State Farm default)
const SAMPLE_MATRIX: Record<string, Record<string, Record<string, number>>> = {
  hood: {
    '1-5': { dime: 75, nickel: 90, quarter: 110, half: 135 },
    '6-15': { dime: 125, nickel: 150, quarter: 180, half: 215 },
    '16-30': { dime: 200, nickel: 240, quarter: 290, half: 345 },
    '31-50': { dime: 275, nickel: 330, quarter: 400, half: 475 },
    '51-75': { dime: 350, nickel: 420, quarter: 510, half: 605 },
    '76-100': { dime: 425, nickel: 510, quarter: 620, half: 735 },
    '101+': { dime: 500, nickel: 600, quarter: 730, half: 865 }
  },
  roof: {
    '1-5': { dime: 85, nickel: 100, quarter: 120, half: 145 },
    '6-15': { dime: 140, nickel: 170, quarter: 200, half: 240 },
    '16-30': { dime: 225, nickel: 270, quarter: 325, half: 390 },
    '31-50': { dime: 310, nickel: 375, quarter: 450, half: 540 },
    '51-75': { dime: 395, nickel: 475, quarter: 575, half: 690 },
    '76-100': { dime: 480, nickel: 580, quarter: 700, half: 840 },
    '101+': { dime: 565, nickel: 680, quarter: 825, half: 990 }
  }
}

// Default matrix for panels not specifically defined
const DEFAULT_MATRIX: Record<string, Record<string, number>> = {
  '1-5': { dime: 70, nickel: 85, quarter: 100, half: 120 },
  '6-15': { dime: 115, nickel: 140, quarter: 165, half: 195 },
  '16-30': { dime: 185, nickel: 220, quarter: 265, half: 315 },
  '31-50': { dime: 255, nickel: 305, quarter: 365, half: 435 },
  '51-75': { dime: 325, nickel: 390, quarter: 465, half: 555 },
  '76-100': { dime: 395, nickel: 475, quarter: 565, half: 675 },
  '101+': { dime: 465, nickel: 555, quarter: 665, half: 795 }
}

export function EstimateBuilder() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id
  const estimateId = id ? parseInt(id) : null

  // Get user permissions from auth context
  const { permissions } = useAuth()

  // Get URL params for customer/lead integration
  const urlCustomerId = searchParams.get('customer_id')
  const urlLeadId = searchParams.get('lead_id')

  // API hooks
  const { data: existingEstimate, isLoading: isLoadingEstimate } = usePDREstimate(estimateId)
  const createEstimate = useCreatePDREstimate()
  const updateEstimate = useUpdatePDREstimate()
  const linkToCRM = useLinkToCRM()
  const convertToInvoice = useConvertToInvoice()
  useMatrixProfiles() // Load profiles
  const decodeVIN = useDecodeVIN()
  const convertLead = useConvertLead()
  const createVehicle = useCreateVehicle()
  const addPanelMatrix = useAddPanelMatrix()
  const downloadPDF = useDownloadEstimatePDF()
  const downloadPhotoSheet = useDownloadEstimatePhotoSheetPDF()
  const downloadDisputePack = useDownloadEstimateDisputePack()
  const { data: activitiesData } = useEstimateActivities(estimateId)
  const updatePanelMatrix = useUpdatePanelMatrix()

  // R&I hooks (Phase 6C)
  const { data: riCatalog } = useRiCatalog()
  const { data: estimateRiData, isLoading: isLoadingEstimateRi } = useEstimateRI(estimateId ?? 0)
  const addEstimateRI = useAddEstimateRI(estimateId ?? 0)
  const removeEstimateRI = useRemoveEstimateRI(estimateId ?? 0)

  // Labor Rate hooks (Stage 6E)
  const { data: laborRateData } = useEstimateLaborRate(estimateId)
  const setLaborRateOverride = useSetLaborRateOverride(estimateId ?? 0)

  // R&I state
  const [riSearchQuery, setRiSearchQuery] = useState('')
  const [riSearchOpen, setRiSearchOpen] = useState(false)
  const [expandedRiOperations, setExpandedRiOperations] = useState<Set<number>>(new Set())
  const [showRateOverride, setShowRateOverride] = useState(false)
  const [rateOverrideValue, setRateOverrideValue] = useState<string>('')

  // Stage 6H-A: Denial Simulator
  const { data: denialCodesData } = useDenialCodes(estimateId ?? 0)
  const denialSimulator = useDenialSimulator(estimateId ?? 0)
  const [selectedDenialCode, setSelectedDenialCode] = useState<string>('')
  const [denialRebuttal, setDenialRebuttal] = useState<DenialRebuttal | null>(null)

  // Stage 6H-B: Supplement Writer
  const supplementWriter = useSupplementWriter(estimateId ?? 0)
  const [supplementLetter, setSupplementLetter] = useState<SupplementLetter | null>(null)
  const [supplementDenialCode, setSupplementDenialCode] = useState<string>('')

  // Load customer/lead from URL params
  const { customer: urlCustomer, isLoading: isLoadingCustomer } = useCustomer(
    urlCustomerId ? parseInt(urlCustomerId) : null
  )
  const { data: urlLead, isLoading: isLoadingLead } = useLead(
    urlLeadId ? parseInt(urlLeadId) : 0
  )

  // Load linked customer/vehicle when editing existing estimate
  const { customer: linkedCustomer } = useCustomer(
    existingEstimate?.contact_id || null
  )
  const { vehicle: linkedVehicle } = useVehicle(
    (existingEstimate as any)?.vehicle_id || null
  )

  // State
  const [vehicleType, setVehicleType] = useState<VehicleType>('car')
  const [activeServiceTab, setActiveServiceTab] = useState<ServiceTab>('hail')
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null)
  const [panelModalOpen, setPanelModalOpen] = useState(false)
  const [panels, setPanels] = useState<Record<string, PanelDamage>>({})
  // Track backend panel IDs for updates (panelKey -> backend panel ID)
  const [panelDbIds, setPanelDbIds] = useState<Record<string, number>>({})
  const [matrixProfileId, setMatrixProfileId] = useState<string>('state_farm')
  const [showSidebar] = useState(true)
  const [vinDialogOpen, setVinDialogOpen] = useState(false)
  const [customerPickerOpen, setCustomerPickerOpen] = useState(false)
  const [vehiclePickerOpen, setVehiclePickerOpen] = useState(false)
  const [sendToAdjusterOpen, setSendToAdjusterOpen] = useState(false)
  const [createSupplementOpen, setCreateSupplementOpen] = useState(false)
  const [createShareLinkOpen, setCreateShareLinkOpen] = useState(false)

  // Quick Entry state
  const [quickEntryOpen, setQuickEntryOpen] = useState(false)
  const [quickEntryAnchor, setQuickEntryAnchor] = useState<{ x: number; y: number } | undefined>()
  const [lastUsedDamage, setLastUsedDamage] = useState<Partial<QuickEntryValue> | null>(null)

  // Batch selection state (for multi-panel apply)
  const [selectedPanelKeys, setSelectedPanelKeys] = useState<Set<string>>(new Set())
  const [selectionMode, setSelectionMode] = useState(false) // Mobile long-press mode

  // Stage 7A: Speed Bar state
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false)
  const [panelSearchOpen, setPanelSearchOpen] = useState(false)
  const [panelSearchQuery, setPanelSearchQuery] = useState('')
  const panelSearchInputRef = useRef<HTMLInputElement>(null)
  const handleSaveRef = useRef<() => void>(() => {})

  // Phase 7A+: Writer Row state (single-line rapid entry)
  const [writerDraft, setWriterDraft] = useState<WriterDraft>({
    panelName: '',
    countRange: null,
    dentSize: null,
    depth: 'medium',
    zone: 'center',
    material: 'steel',
    notes: ''
  })
  const [writerRapidMode, setWriterRapidMode] = useState(false) // Keep focus after adding
  const writerPanelInputRef = useRef<HTMLInputElement>(null)
  const [writerSearchOpen, setWriterSearchOpen] = useState(false)

  // Stage 7D: Panel-Driven R&I Quick Add state
  const [riAddingCode, setRiAddingCode] = useState<string | null>(null) // Currently adding
  const [riAddedCodes, setRiAddedCodes] = useState<Set<string>>(new Set()) // Already added this session

  // Debounced save state
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingChangesRef = useRef(false)

  // Vehicle info
  const [vehicleId, setVehicleId] = useState<number | null>(null)
  const [vehicleYear, setVehicleYear] = useState('')
  const [vehicleMake, setVehicleMake] = useState('')
  const [vehicleModel, setVehicleModel] = useState('')
  const [vehicleVin, setVehicleVin] = useState('')
  const [vehicleColor, setVehicleColor] = useState('')
  const [isNewVehicle, setIsNewVehicle] = useState(true)

  // Customer info
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [customerId, setCustomerId] = useState<number | null>(null)
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [leadId, setLeadId] = useState<number | null>(null)

  // Status
  const [estimateStatus, setEstimateStatus] = useState<string>('draft')
  const [isSaving, setIsSaving] = useState(false)
  const [isConverting, setIsConverting] = useState(false)

  // Load existing estimate data when editing
  useEffect(() => {
    if (existingEstimate && isEditing) {
      setVehicleYear(existingEstimate.vehicle_year?.toString() || '')
      setVehicleMake(existingEstimate.vehicle_make || '')
      setVehicleModel(existingEstimate.vehicle_model || '')
      setVehicleVin(existingEstimate.vin || existingEstimate.vehicle_vin || '')
      setCustomerName(existingEstimate.customer_name || '')
      setCustomerPhone(existingEstimate.customer_phone || '')
      setEstimateStatus(existingEstimate.status || 'draft')
      if (existingEstimate.contact_id) {
        setCustomerId(existingEstimate.contact_id)
      }
      if (existingEstimate.lead_id) {
        setLeadId(existingEstimate.lead_id)
      }
      if ((existingEstimate as any).vehicle_id) {
        setVehicleId((existingEstimate as any).vehicle_id)
        setIsNewVehicle(false)
      }
    }
  }, [existingEstimate, isEditing])

  // Load linked customer data when editing
  useEffect(() => {
    if (linkedCustomer && !selectedCustomer) {
      setSelectedCustomer(linkedCustomer)
      setCustomerId(linkedCustomer.id)
      setCustomerName(`${linkedCustomer.first_name} ${linkedCustomer.last_name}`)
      setCustomerPhone(linkedCustomer.phone || '')
    }
  }, [linkedCustomer, selectedCustomer])

  // Load linked vehicle data when editing
  useEffect(() => {
    if (linkedVehicle && !vehicleId) {
      setVehicleId(linkedVehicle.id)
      setVehicleYear(linkedVehicle.year?.toString() || '')
      setVehicleMake(linkedVehicle.make || '')
      setVehicleModel(linkedVehicle.model || '')
      setVehicleVin(linkedVehicle.vin || '')
      setVehicleColor(linkedVehicle.color || '')
      setIsNewVehicle(false)
    }
  }, [linkedVehicle, vehicleId])

  // Set customer from URL param
  useEffect(() => {
    if (urlCustomer && !selectedCustomer && !isEditing) {
      setSelectedCustomer(urlCustomer)
      setCustomerId(urlCustomer.id)
      setCustomerName(`${urlCustomer.first_name} ${urlCustomer.last_name}`)
      setCustomerPhone(urlCustomer.phone || '')
    }
  }, [urlCustomer, selectedCustomer, isEditing])

  // Set lead data from URL param
  useEffect(() => {
    if (urlLead && !leadId && !isEditing) {
      setLeadId(urlLead.id)
      // Pre-fill customer info from lead
      if (urlLead.first_name || urlLead.last_name) {
        setCustomerName(`${urlLead.first_name || ''} ${urlLead.last_name || ''}`.trim())
      }
      if (urlLead.phone) {
        setCustomerPhone(urlLead.phone)
      }
      // Pre-fill vehicle info from lead
      if (urlLead.vehicle_year) {
        setVehicleYear(urlLead.vehicle_year.toString())
      }
      if (urlLead.vehicle_make) {
        setVehicleMake(urlLead.vehicle_make)
      }
      if (urlLead.vehicle_model) {
        setVehicleModel(urlLead.vehicle_model)
      }
    }
  }, [urlLead, leadId, isEditing])

  // Handle customer selection from picker
  const handleSelectCustomer = (customer: Customer) => {
    setSelectedCustomer(customer)
    setCustomerId(customer.id)
    setCustomerName(`${customer.first_name} ${customer.last_name}`)
    setCustomerPhone(customer.phone || '')
    // Clear vehicle when customer changes (they may have different vehicles)
    setVehicleId(null)
    setIsNewVehicle(true)
  }

  // Handle vehicle selection from picker
  const handleSelectVehicle = (vehicle: Vehicle) => {
    setVehicleId(vehicle.id)
    setVehicleYear(vehicle.year?.toString() || '')
    setVehicleMake(vehicle.make || '')
    setVehicleModel(vehicle.model || '')
    setVehicleVin(vehicle.vin || '')
    setVehicleColor(vehicle.color || '')
    setIsNewVehicle(false)
  }

  // Handle add new vehicle
  const handleAddNewVehicle = () => {
    setVehicleId(null)
    setIsNewVehicle(true)
    setVinDialogOpen(true)
  }

  // Calculate panel states for diagram
  const panelStates = useMemo(() => {
    const states: Record<string, PanelState> = {}
    const vehiclePanels = VEHICLE_PANELS[vehicleType]

    Object.keys(vehiclePanels).forEach(panelId => {
      const damage = panels[panelId]
      const isDamaged = !!(damage?.countRange && damage?.dentSize)

      // Compute severity for heat map visualization
      const severity = isDamaged
        ? computeSeverity({
            countRange: damage.countRange,
            dentSize: damage.dentSize,
            depth: (damage as any).depth || null,
            zone: (damage as any).zone || null
          })
        : { score: 0, level: 0 as const, badgeText: '' }

      states[panelId] = {
        selected: selectedPanelId === panelId,
        damaged: isDamaged,
        conventional: damage?.conventional || false,
        batchSelected: selectedPanelKeys.has(panelId) && selectedPanelId !== panelId,
        severityLevel: severity.level,
        badgeText: severity.badgeText
      }
    })

    return states
  }, [panels, selectedPanelId, selectedPanelKeys, vehicleType])

  // Get resolved labor rate
  const resolvedLaborRate = laborRateData?.rate ?? estimateRiData?.ri_labor_rate ?? 85

  // Calculate totals
  const totals = useMemo(() => {
    let hailTotal = 0
    let partsTotal = 0
    let pdrTotal = 0

    Object.values(panels).forEach(panel => {
      if (panel.totalPrice > 0) {
        hailTotal += panel.totalPrice
      }
    })

    // R&I total from backend data with resolved labor rate
    const riTotal = estimateRiData?.total_ri_time_hours
      ? estimateRiData.total_ri_time_hours * resolvedLaborRate
      : 0

    return {
      pdr: pdrTotal,
      hail: hailTotal,
      ri: riTotal,
      parts: partsTotal,
      grand: pdrTotal + hailTotal + riTotal + partsTotal
    }
  }, [panels, estimateRiData, resolvedLaborRate])

  // Count damaged panels
  const damagedCount = useMemo(() => {
    return Object.values(panels).filter(p => p.countRange && p.dentSize).length
  }, [panels])

  // Vehicle info string for status bar
  const vehicleInfoString = useMemo(() => {
    const parts = [vehicleYear, vehicleMake, vehicleModel].filter(Boolean)
    return parts.join(' ') || 'New Estimate'
  }, [vehicleYear, vehicleMake, vehicleModel])

  // Current estimate data for supplement modal
  const currentEstimateData = useMemo(() => {
    return {
      panels: Object.entries(panels).reduce((acc, [key, damage]) => {
        if (damage.countRange && damage.dentSize) {
          acc[key] = {
            panel_name: key,
            count_range: damage.countRange,
            dent_size: damage.dentSize,
            oversized_count: damage.oversizedCount,
            glue_pull: damage.gluePull,
            aluminum: damage.aluminum,
            hss: damage.hss,
            double_metal: damage.doubleMetal,
            conventional: damage.conventional,
            base_price: damage.basePrice,
            total_price: damage.totalPrice,
            notes: damage.notes
          }
        }
        return acc
      }, {} as Record<string, unknown>),
      totals: {
        hail: totals.hail,
        pdr: totals.pdr,
        ri: totals.ri,
        parts: totals.parts,
        grand: totals.grand
      },
      vehicle: {
        year: vehicleYear,
        make: vehicleMake,
        model: vehicleModel,
        vin: vehicleVin,
        color: vehicleColor
      },
      matrix_profile_id: matrixProfileId
    }
  }, [panels, totals, vehicleYear, vehicleMake, vehicleModel, vehicleVin, vehicleColor, matrixProfileId])

  // Matrix lookup function
  const matrixLookup = useCallback((panelId: string, countRange: CountRange, size: DentSize): number => {
    const panelMatrix = SAMPLE_MATRIX[panelId]
    if (panelMatrix && panelMatrix[countRange] && panelMatrix[countRange][size] !== undefined) {
      return panelMatrix[countRange][size]
    }
    if (DEFAULT_MATRIX[countRange] && DEFAULT_MATRIX[countRange][size] !== undefined) {
      return DEFAULT_MATRIX[countRange][size]
    }
    return 0
  }, [])

  // Handle panel click on diagram
  const handlePanelClick = useCallback((panelId: string) => {
    setSelectedPanelId(panelId)
    if (!panels[panelId]) {
      setPanels(prev => ({
        ...prev,
        [panelId]: createEmptyPanelDamage(panelId)
      }))
    }
    setPanelModalOpen(true)
  }, [panels])

  // Detect if device is touch-based (mobile)
  const isTouchDevice = useCallback(() => {
    return 'ontouchstart' in window || navigator.maxTouchPoints > 0
  }, [])

  // Handle long press - mobile: toggle selection, desktop: mark conventional
  const handlePanelLongPress = useCallback((panelId: string) => {
    if (isTouchDevice()) {
      // Mobile: Enter selection mode and toggle this panel's selection
      setSelectionMode(true)
      setSelectedPanelKeys(prev => {
        const next = new Set(prev)
        if (next.has(panelId)) {
          next.delete(panelId)
        } else {
          next.add(panelId)
        }
        return next
      })

      // Set as primary if no primary selected
      if (!selectedPanelId) {
        setSelectedPanelId(panelId)
        if (!panels[panelId]) {
          setPanels(prev => ({
            ...prev,
            [panelId]: createEmptyPanelDamage(panelId)
          }))
        }
      }
    } else {
      // Desktop: Toggle conventional repair marking
      setPanels(prev => {
        const existing = prev[panelId] || createEmptyPanelDamage(panelId)
        return {
          ...prev,
          [panelId]: {
            ...existing,
            conventional: !existing.conventional
          }
        }
      })
    }
  }, [isTouchDevice, selectedPanelId, panels])

  // Exit selection mode (but preserve selection)
  const handleExitSelectionMode = useCallback(() => {
    setSelectionMode(false)
  }, [])

  // Open primary panel overlay while in selection mode (for mobile "Edit Primary" button)
  const handleOpenPrimaryOverlay = useCallback(() => {
    if (!selectedPanelId) return
    // Get anchor position from center of screen for mobile
    const anchor = {
      x: window.innerWidth / 2,
      y: window.innerHeight / 3
    }
    setQuickEntryAnchor(anchor)
    setQuickEntryOpen(true)
  }, [selectedPanelId])

  // Handle review/summary tap (scroll to summary or open modal)
  const handleReview = useCallback(() => {
    // For now, just scroll to top where totals are visible
    // Could be enhanced to open a summary modal
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  // Handle PDF download (uses GET - backend source of truth)
  const handleDownloadPDF = useCallback(() => {
    if (!estimateId) return
    downloadPDF.mutate(estimateId)
  }, [estimateId, downloadPDF])

  // Handle Photo Sheet download (uses GET - backend source of truth)
  const handleDownloadPhotoSheet = useCallback(() => {
    if (!estimateId) return
    downloadPhotoSheet.mutate(estimateId)
  }, [estimateId, downloadPhotoSheet])

  // Handle Dispute Pack download (uses GET - backend source of truth)
  const handleDownloadDisputePack = useCallback(() => {
    if (!estimateId) return
    downloadDisputePack.mutate(estimateId)
  }, [estimateId, downloadDisputePack])

  // Handle clear all panels
  const handleClearAll = useCallback(() => {
    setPanels({})
    setSelectedPanelId(null)
  }, [])

  // Handle quick entry panel click (with anchor position)
  const handleQuickEntryPanelClick = useCallback((event: PanelClickEvent) => {
    // In selection mode, tapping toggles selection instead of opening overlay
    if (selectionMode) {
      setSelectedPanelKeys(prev => {
        const next = new Set(prev)
        if (next.has(event.panelId)) {
          next.delete(event.panelId)
        } else {
          next.add(event.panelId)
        }
        return next
      })
      return
    }

    // Normal behavior: open quick entry overlay
    setSelectedPanelId(event.panelId)
    setQuickEntryAnchor(event.anchor)
    if (!panels[event.panelId]) {
      setPanels(prev => ({
        ...prev,
        [event.panelId]: createEmptyPanelDamage(event.panelId)
      }))
    }
    setQuickEntryOpen(true)
  }, [panels, selectionMode])

  // Convert frontend PanelDamage to backend format
  const toBackendPanelData = useCallback((panelKey: string, damage: PanelDamage & { depth?: string; zone?: string }) => {
    return {
      panel_name: panelKey,
      total_dent_count: countRangeToNumber(damage.countRange),
      majority_size: damage.dentSize || 'nickel',
      oversized_count: damage.oversizedCount || 0,
      is_aluminum: damage.aluminum || false,
      is_hss: damage.hss || false,
      requires_glue_pull: damage.gluePull || false,
      is_tall_roof: false, // TODO: detect from vehicle
      depth: damage.depth || 'medium',
      zone: damage.zone || 'center'
    }
  }, [])

  // Debounced save panel to backend
  const savePanelToBackend = useCallback(async (panelKey: string, damage: PanelDamage) => {
    if (!estimateId) return // Can't save panels without an estimate

    const backendData = toBackendPanelData(panelKey, damage)
    const existingPanelDbId = panelDbIds[panelKey]

    try {
      if (existingPanelDbId) {
        // Update existing panel
        const result = await updatePanelMatrix.mutateAsync({
          estimateId,
          panelId: existingPanelDbId,
          data: backendData
        })
        console.log('Panel updated:', result)
      } else {
        // Create new panel
        const result = await addPanelMatrix.mutateAsync({
          estimateId,
          data: backendData
        })
        // Store the backend panel ID
        if (result.panel?.id) {
          setPanelDbIds(prev => ({ ...prev, [panelKey]: result.panel.id }))
        }
        console.log('Panel created:', result)
      }
      setSaveStatus('saved')
      setLastSavedAt(new Date())
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (error) {
      console.error('Panel save failed:', error)
      setSaveStatus('error')
    }
  }, [estimateId, panelDbIds, toBackendPanelData, addPanelMatrix, updatePanelMatrix])

  // Retry save (for error state)
  const handleRetrySave = useCallback(() => {
    if (pendingPanelUpdateRef.current) {
      const { panelKey, damage } = pendingPanelUpdateRef.current
      if (damage.countRange && damage.dentSize) {
        setSaveStatus('saving')
        savePanelToBackend(panelKey, damage)
      }
    } else {
      // No pending panel update, reset to idle
      setSaveStatus('idle')
    }
  }, [savePanelToBackend])

  // Reference to store updated damage for debounced save
  const pendingPanelUpdateRef = useRef<{ panelKey: string; damage: PanelDamage } | null>(null)

  // Handle panel damage change (from modal) - with debounced backend save
  const handleDamageChange = useCallback((damage: PanelDamage) => {
    setPanels(prev => ({
      ...prev,
      [damage.panelId]: damage
    }))

    // Trigger debounced save to backend (same as quick entry)
    if (isEditing && estimateId && damage.countRange && damage.dentSize) {
      pendingPanelUpdateRef.current = { panelKey: damage.panelId, damage }
      pendingChangesRef.current = true

      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      saveTimeoutRef.current = setTimeout(() => {
        if (pendingChangesRef.current && pendingPanelUpdateRef.current) {
          const { panelKey, damage: pendingDamage } = pendingPanelUpdateRef.current
          if (pendingDamage.countRange && pendingDamage.dentSize) {
            setSaveStatus('saving')
            savePanelToBackend(panelKey, pendingDamage)
            pendingChangesRef.current = false
          }
        }
      }, 300)
    }
  }, [isEditing, estimateId, savePanelToBackend])

  // Handle quick entry changes with immediate update + debounced save
  const handleQuickEntryChange = useCallback((updates: Partial<QuickEntryValue>) => {
    if (!selectedPanelId) return

    setPanels(prev => {
      const current = prev[selectedPanelId] || createEmptyPanelDamage(selectedPanelId)
      const updated = { ...current, ...updates }

      // Recalculate price with depth/zone multipliers
      if (updated.countRange && updated.dentSize) {
        const basePrice = matrixLookup(selectedPanelId, updated.countRange, updated.dentSize)

        // Depth multipliers
        const depthMultipliers: Record<string, number> = {
          shallow: 1.0, medium: 1.15, deep: 1.35, severe: 1.6
        }
        const depthMult = depthMultipliers[(updated as any).depth || 'medium'] || 1.0

        // Zone multipliers
        const zoneMultipliers: Record<string, number> = {
          center: 1.0, edge: 1.1, crease: 1.25, body_line: 1.35
        }
        const zoneMult = zoneMultipliers[(updated as any).zone || 'center'] || 1.0

        // Add-on multipliers (additive percentages)
        let addonMult = 1.0
        if (updated.gluePull) addonMult += 0.25
        if (updated.aluminum) addonMult += 0.25
        if (updated.hss) addonMult += 0.25
        if (updated.doubleMetal) addonMult += 0.50

        // Total: base * depth * zone * addons + oversized
        updated.basePrice = basePrice
        updated.totalPrice = (basePrice * depthMult * zoneMult * addonMult) + (updated.oversizedCount * 50)
      }

      // Store for debounced save
      if (updated.countRange && updated.dentSize) {
        pendingPanelUpdateRef.current = { panelKey: selectedPanelId, damage: updated }
      }

      return { ...prev, [selectedPanelId]: updated }
    })

    // Debounced save to backend (only for existing estimates)
    if (isEditing && estimateId) {
      pendingChangesRef.current = true
      setSaveStatus('idle')

      // Debounced backend save
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      saveTimeoutRef.current = setTimeout(() => {
        if (pendingChangesRef.current && pendingPanelUpdateRef.current) {
          const { panelKey, damage } = pendingPanelUpdateRef.current
          if (damage.countRange && damage.dentSize) {
            setSaveStatus('saving')
            savePanelToBackend(panelKey, damage)
            pendingChangesRef.current = false
          }
        }
      }, 300)
    }
  }, [selectedPanelId, matrixLookup, isEditing, estimateId, savePanelToBackend])

  // Handle switching to full modal from quick entry
  const handleOpenDetails = useCallback(() => {
    setQuickEntryOpen(false)
    setPanelModalOpen(true)
  }, [])

  // Handle repeat last damage settings
  const handleRepeatLast = useCallback(() => {
    if (!selectedPanelId || !lastUsedDamage) return

    const updates: Partial<QuickEntryValue> = {
      countRange: lastUsedDamage.countRange,
      dentSize: lastUsedDamage.dentSize,
      gluePull: lastUsedDamage.gluePull,
      aluminum: lastUsedDamage.aluminum,
      hss: lastUsedDamage.hss,
      doubleMetal: lastUsedDamage.doubleMetal,
    }

    handleQuickEntryChange(updates)
  }, [selectedPanelId, lastUsedDamage, handleQuickEntryChange])

  // Save last used damage when closing quick entry with valid data
  const handleQuickEntryClose = useCallback(() => {
    if (selectedPanelId && panels[selectedPanelId]) {
      const damage = panels[selectedPanelId]
      if (damage.countRange && damage.dentSize) {
        setLastUsedDamage({
          countRange: damage.countRange,
          dentSize: damage.dentSize,
          gluePull: damage.gluePull,
          aluminum: damage.aluminum,
          hss: damage.hss,
          doubleMetal: damage.doubleMetal,
        })
      }
    }
    setQuickEntryOpen(false)
  }, [selectedPanelId, panels])

  // Calculate current panel price for quick entry display
  const currentPanelPrice = useMemo(() => {
    if (!selectedPanelId || !panels[selectedPanelId]) return 0
    return panels[selectedPanelId].totalPrice || 0
  }, [selectedPanelId, panels])

  // Handle multi-select panel click (ctrl/cmd+click or selection mode)
  const handlePanelClickWithModifiers = useCallback((event: PanelClickWithModifiers) => {
    const { panelId, anchor, ctrlKey, metaKey } = event

    if (ctrlKey || metaKey || selectionMode) {
      // Toggle panel in batch selection
      setSelectedPanelKeys(prev => {
        const next = new Set(prev)
        if (next.has(panelId)) {
          next.delete(panelId)
        } else {
          next.add(panelId)
        }
        return next
      })

      // If no primary panel selected, make this one primary and open overlay
      if (!selectedPanelId) {
        setSelectedPanelId(panelId)
        setQuickEntryAnchor(anchor)
        if (!panels[panelId]) {
          setPanels(prev => ({
            ...prev,
            [panelId]: createEmptyPanelDamage(panelId)
          }))
        }
        setQuickEntryOpen(true)
      }
    } else {
      // Normal click - set as primary and open quick entry
      setSelectedPanelId(panelId)
      setQuickEntryAnchor(anchor)
      if (!panels[panelId]) {
        setPanels(prev => ({
          ...prev,
          [panelId]: createEmptyPanelDamage(panelId)
        }))
      }
      setQuickEntryOpen(true)
    }
  }, [panels, selectedPanelId, selectionMode])

  // Clear batch selection
  const handleClearSelection = useCallback(() => {
    setSelectedPanelKeys(new Set())
    setSelectionMode(false)
  }, [])

  // Apply current primary panel values to all selected panels
  const handleApplyToSelected = useCallback(() => {
    if (!selectedPanelId || selectedPanelKeys.size < 2) return

    const primaryDamage = panels[selectedPanelId]
    if (!primaryDamage?.countRange || !primaryDamage?.dentSize) return

    // Values to copy (NOT notes - preserve those)
    const valuesToApply = {
      countRange: primaryDamage.countRange,
      dentSize: primaryDamage.dentSize,
      oversizedCount: primaryDamage.oversizedCount,
      gluePull: primaryDamage.gluePull,
      aluminum: primaryDamage.aluminum,
      hss: primaryDamage.hss,
      doubleMetal: primaryDamage.doubleMetal,
      // Copy depth/zone if available
      ...(('depth' in primaryDamage) && { depth: (primaryDamage as any).depth }),
      ...(('zone' in primaryDamage) && { zone: (primaryDamage as any).zone }),
    }

    // Store updated panels for backend save
    const updatedPanelsForSave: Array<{ panelKey: string; damage: PanelDamage }> = []

    // Apply to all selected panels (except primary)
    setPanels(prev => {
      const updated = { ...prev }

      selectedPanelKeys.forEach(panelKey => {
        if (panelKey === selectedPanelId) return // Skip primary

        const existing = updated[panelKey] || createEmptyPanelDamage(panelKey)

        // Calculate price for this panel
        const basePrice = matrixLookup(panelKey, valuesToApply.countRange!, valuesToApply.dentSize!)

        // Apply multipliers
        const depthMultipliers: Record<string, number> = {
          shallow: 1.0, medium: 1.15, deep: 1.35, severe: 1.6
        }
        const zoneMultipliers: Record<string, number> = {
          center: 1.0, edge: 1.1, crease: 1.25, body_line: 1.35
        }
        const depthMult = depthMultipliers[(valuesToApply as any).depth || 'medium'] || 1.0
        const zoneMult = zoneMultipliers[(valuesToApply as any).zone || 'center'] || 1.0

        let addonMult = 1.0
        if (valuesToApply.gluePull) addonMult += 0.25
        if (valuesToApply.aluminum) addonMult += 0.25
        if (valuesToApply.hss) addonMult += 0.25
        if (valuesToApply.doubleMetal) addonMult += 0.50

        const totalPrice = (basePrice * depthMult * zoneMult * addonMult) + ((valuesToApply.oversizedCount || 0) * 50)

        const updatedDamage: PanelDamage = {
          ...existing,
          ...valuesToApply,
          basePrice,
          totalPrice,
          // Preserve notes
          notes: existing.notes,
        }

        updated[panelKey] = updatedDamage
        updatedPanelsForSave.push({ panelKey, damage: updatedDamage })
      })

      return updated
    })

    // Trigger debounced save for all updated panels
    if (isEditing && estimateId && updatedPanelsForSave.length > 0) {
      pendingChangesRef.current = true

      // Clear existing timeout and set new one for batch save
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      saveTimeoutRef.current = setTimeout(() => {
        // Save all updated panels
        setSaveStatus('saving')
        updatedPanelsForSave.forEach(({ panelKey, damage }) => {
          if (damage.countRange && damage.dentSize) {
            savePanelToBackend(panelKey, damage)
          }
        })
        pendingChangesRef.current = false
      }, 300)
    }

    // Clear selection after applying
    setSelectedPanelKeys(new Set())
    setSelectionMode(false)
  }, [selectedPanelId, selectedPanelKeys, panels, matrixLookup, isEditing, estimateId, savePanelToBackend])

  // Stage 7D: R&I suggestions for selected panel
  const riSuggestions = useMemo(() => {
    if (!selectedPanelId) return []
    return getRiSuggestionsForPanel(selectedPanelId)
  }, [selectedPanelId])

  // Stage 7D: Track already-added R&I operation codes for this estimate
  const alreadyAddedRiCodes = useMemo(() => {
    if (!estimateRiData?.operations) return new Set<string>()
    return new Set(estimateRiData.operations.map((op: { code: string }) => op.code))
  }, [estimateRiData?.operations])

  // Stage 7D: Handle R&I quick add with auto-save
  const handleRiQuickAdd = useCallback(async (suggestion: RISuggestion) => {
    if (!estimateId) {
      // For new estimates, show toast to save first
      alert('Please save the estimate first to add R&I operations.')
      return
    }

    // If there are pending changes, trigger save and wait
    if (pendingChangesRef.current) {
      setSaveStatus('saving')
      // Trigger the actual save via ref
      handleSaveRef.current()
      // Wait for save to complete (isSaving will go true then false)
      await new Promise(resolve => setTimeout(resolve, 800))
    } else if (isSaving) {
      // Already saving, just wait for it
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    setRiAddingCode(suggestion.code)

    try {
      await addEstimateRI.mutateAsync({
        operationCode: suggestion.code,
        notes: `Added via panel suggestion for ${selectedPanelId}`
      })

      // Mark as added this session
      setRiAddedCodes(prev => new Set(prev).add(suggestion.code))

      // Success feedback - brief toast would go here
      console.log(`Added R&I: ${suggestion.label}`)
    } catch (error) {
      console.error('Failed to add R&I:', error)
      alert(`Failed to add ${suggestion.label}. It may already exist or the operation code may not be in the catalog.`)
    } finally {
      setRiAddingCode(null)
    }
  }, [estimateId, selectedPanelId, addEstimateRI, isSaving])

  // Stage 7A: Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      const target = e.target as HTMLElement
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable

      // ESC - clear selection or close modals
      if (e.key === 'Escape') {
        if (panelSearchOpen) {
          setPanelSearchOpen(false)
          setPanelSearchQuery('')
          return
        }
        if (shortcutsModalOpen) {
          setShortcutsModalOpen(false)
          return
        }
        if (selectedPanelKeys.size > 0 && !quickEntryOpen) {
          handleClearSelection()
          return
        }
      }

      // Skip other shortcuts if in input
      if (isInput && e.key !== 'Escape') return

      // "/" - Focus panel search
      if (e.key === '/' && !panelModalOpen && !quickEntryOpen) {
        e.preventDefault()
        setPanelSearchOpen(true)
        setTimeout(() => panelSearchInputRef.current?.focus(), 100)
        return
      }

      // "?" - Open shortcuts modal
      if (e.key === '?' && e.shiftKey) {
        e.preventDefault()
        setShortcutsModalOpen(true)
        return
      }

      // "r" - Repeat last (when panel selected)
      if (e.key === 'r' && selectedPanelId && lastUsedDamage && !panelModalOpen && !quickEntryOpen) {
        e.preventDefault()
        handleRepeatLast()
        return
      }

      // "a" - Apply to selected (when multiple panels selected)
      if (e.key === 'a' && selectedPanelKeys.size >= 2 && !panelModalOpen && !quickEntryOpen) {
        e.preventDefault()
        handleApplyToSelected()
        return
      }

      // "Ctrl+S" - Save
      if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        handleSaveRef.current()
        return
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  // Note: handleSave excluded from deps to avoid circular dependency - it's stable
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedPanelKeys.size, quickEntryOpen, handleClearSelection, panelSearchOpen,
    shortcutsModalOpen, panelModalOpen, selectedPanelId, lastUsedDamage,
    handleRepeatLast, handleApplyToSelected
  ])

  // Focus panel search input when opened
  useEffect(() => {
    if (panelSearchOpen && panelSearchInputRef.current) {
      panelSearchInputRef.current.focus()
    }
  }, [panelSearchOpen])

  // Filtered panels for search typeahead
  const filteredPanels = useMemo(() => {
    if (!panelSearchQuery.trim()) return []
    const query = panelSearchQuery.toLowerCase()
    const vehiclePanels = VEHICLE_PANELS[vehicleType]
    return Object.entries(vehiclePanels)
      .filter(([_, name]) => name.toLowerCase().includes(query))
      .slice(0, 8) // Limit results
  }, [panelSearchQuery, vehicleType])

  // Handle panel search selection
  const handlePanelSearchSelect = useCallback((panelId: string) => {
    setPanelSearchOpen(false)
    setPanelSearchQuery('')
    setSelectedPanelId(panelId)
    if (!panels[panelId]) {
      setPanels(prev => ({
        ...prev,
        [panelId]: createEmptyPanelDamage(panelId)
      }))
    }
    setPanelModalOpen(true)
  }, [panels])

  // Phase 7A+: Writer Row - filtered panels for typeahead
  const writerFilteredPanels = useMemo(() => {
    if (!writerDraft.panelName.trim()) return []
    const query = writerDraft.panelName.toLowerCase()
    const vehiclePanels = VEHICLE_PANELS[vehicleType]
    return Object.entries(vehiclePanels)
      .filter(([id, name]) => {
        // Don't show panels already added with damage
        const existing = panels[id]
        const hasDamage = existing?.countRange && existing?.dentSize
        if (hasDamage) return false
        return name.toLowerCase().includes(query) || id.toLowerCase().includes(query)
      })
      .slice(0, 6)
  }, [writerDraft.panelName, vehicleType, panels])

  // Phase 7A+: Writer Row - compute preview price
  const writerPreviewPrice = useMemo(() => {
    if (!writerDraft.countRange || !writerDraft.dentSize) return null
    return computePanelPrice({
      countRange: writerDraft.countRange,
      dentSize: writerDraft.dentSize,
      depth: writerDraft.depth,
      zone: writerDraft.zone,
      aluminum: writerDraft.material === 'aluminum',
    })
  }, [writerDraft])

  // Phase 7A+: Writer Row - reset draft
  const resetWriterDraft = useCallback(() => {
    setWriterDraft({
      panelName: '',
      countRange: null,
      dentSize: null,
      depth: 'medium',
      zone: 'center',
      material: 'steel',
      notes: ''
    })
    setWriterSearchOpen(false)
  }, [])

  // Phase 7A+: Writer Row - add panel from draft
  const handleWriterAddPanel = useCallback(() => {
    if (!writerDraft.panelName || !writerDraft.countRange || !writerDraft.dentSize) return

    // Find the panel ID from name
    const vehiclePanels = VEHICLE_PANELS[vehicleType]
    const entry = Object.entries(vehiclePanels).find(
      ([id, name]) => name.toLowerCase() === writerDraft.panelName.toLowerCase() ||
                      id.toLowerCase() === writerDraft.panelName.toLowerCase()
    )
    if (!entry) return
    const [panelId] = entry

    // Compute price using pricing engine
    const priceResult = computePanelPrice({
      countRange: writerDraft.countRange,
      dentSize: writerDraft.dentSize,
      depth: writerDraft.depth,
      zone: writerDraft.zone,
      aluminum: writerDraft.material === 'aluminum',
    })

    // Create panel damage
    const damage: PanelDamage = {
      panelId,
      countRange: writerDraft.countRange,
      dentSize: writerDraft.dentSize,
      oversizedCount: 0,
      gluePull: false,
      aluminum: writerDraft.material === 'aluminum',
      hss: false,
      doubleMetal: false,
      conventional: false,
      notes: writerDraft.notes,
      basePrice: priceResult.basePrice,
      totalPrice: priceResult.totalPrice
    }

    // Add to panels
    setPanels(prev => ({ ...prev, [panelId]: damage }))

    // Store as last used
    setLastUsedDamage({
      countRange: writerDraft.countRange,
      dentSize: writerDraft.dentSize,
      gluePull: false,
      aluminum: writerDraft.material === 'aluminum',
      hss: false,
      doubleMetal: false
    })

    // Select the panel
    setSelectedPanelId(panelId)

    // Trigger save if editing existing estimate
    if (isEditing && estimateId) {
      pendingChangesRef.current = true
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
      saveTimeoutRef.current = setTimeout(() => {
        if (pendingChangesRef.current) {
          setSaveStatus('saving')
          savePanelToBackend(panelId, damage)
          pendingChangesRef.current = false
        }
      }, 300)
    }

    // Handle rapid mode vs normal
    if (writerRapidMode) {
      // Keep panel fields, clear panel name only
      setWriterDraft(prev => ({ ...prev, panelName: '' }))
      setTimeout(() => writerPanelInputRef.current?.focus(), 50)
    } else {
      resetWriterDraft()
    }
  }, [writerDraft, vehicleType, isEditing, estimateId, savePanelToBackend, writerRapidMode, resetWriterDraft])

  // Phase 7A+: Writer Row - apply last settings and add
  const handleWriterApplyLastAndAdd = useCallback(() => {
    if (!writerDraft.panelName || !lastUsedDamage?.countRange || !lastUsedDamage?.dentSize) return

    setWriterDraft(prev => ({
      ...prev,
      countRange: lastUsedDamage.countRange || null,
      dentSize: lastUsedDamage.dentSize || null,
      ...(lastUsedDamage.aluminum && { material: 'aluminum' as const })
    }))

    // Auto-add after applying
    setTimeout(() => handleWriterAddPanel(), 50)
  }, [writerDraft.panelName, lastUsedDamage, handleWriterAddPanel])

  // Handle VIN decode
  const handleVinDecode = async () => {
    if (!vehicleVin || vehicleVin.length < 17) return

    try {
      const result = await decodeVIN.mutateAsync(vehicleVin)
      if (result.valid) {
        setVehicleYear(result.year.toString())
        setVehicleMake(result.make)
        setVehicleModel(result.model)

        // Check for aluminum panels
        if (result.aluminum_panels && result.aluminum_panels.length > 0) {
          const newPanels = { ...panels }
          result.aluminum_panels.forEach(alPanel => {
            const normalizedPanel = alPanel.toLowerCase().replace(/ /g, '_')
            if (newPanels[normalizedPanel]) {
              newPanels[normalizedPanel].aluminum = true
            } else {
              newPanels[normalizedPanel] = {
                ...createEmptyPanelDamage(normalizedPanel),
                aluminum: true
              }
            }
          })
          setPanels(newPanels)
        }

        setVinDialogOpen(false)
      }
    } catch (error) {
      console.error('VIN decode error:', error)
    }
  }

  // Handle vehicle type change
  const handleVehicleTypeChange = useCallback((type: VehicleType) => {
    setVehicleType(type)
    setPanels({})
    setSelectedPanelId(null)
  }, [])

  // Get selected panel name
  const selectedPanelName = useMemo(() => {
    if (!selectedPanelId) return ''
    return VEHICLE_PANELS[vehicleType][selectedPanelId] || selectedPanelId
  }, [selectedPanelId, vehicleType])

  // Handle save with full vehicle/customer persistence
  const handleSave = async () => {
    setIsSaving(true)
    try {
      let savedVehicleId = vehicleId

      // Create new vehicle if needed
      if (isNewVehicle && customerId && vehicleYear && vehicleMake) {
        try {
          const newVehicle = await createVehicle.mutateAsync({
            customer_id: customerId,
            year: parseInt(vehicleYear),
            make: vehicleMake,
            model: vehicleModel,
            vin: vehicleVin,
            color: vehicleColor,
            status: 'active'
          })
          savedVehicleId = newVehicle.id
          setVehicleId(newVehicle.id)
          setIsNewVehicle(false)
        } catch (e) {
          console.warn('Vehicle creation failed:', e)
        }
      }

      const estimateData = {
        vehicle_year: parseInt(vehicleYear) || new Date().getFullYear(),
        vehicle_make: vehicleMake || 'Unknown',
        vehicle_model: vehicleModel || 'Unknown',
        vin: vehicleVin,
        vehicle_id: savedVehicleId || undefined,
        customer_name: customerName,
        customer_phone: customerPhone,
        contact_id: customerId || undefined,
        lead_id: leadId || undefined,
        matrix_profile_id: 1, // State Farm default
        status: estimateStatus as 'draft' | 'in_progress' | 'approved' | 'completed'
      }

      if (isEditing && id) {
        await updateEstimate.mutateAsync({
          id: parseInt(id),
          data: estimateData
        })
      } else {
        const result = await createEstimate.mutateAsync(estimateData)
        if (result.estimate) {
          // Link to CRM if we have customer or lead
          if (customerId || leadId) {
            await linkToCRM.mutateAsync({
              id: result.estimate.id,
              data: {
                contact_id: customerId || undefined,
                lead_id: leadId || undefined
              }
            })
          }

          // Convert lead if creating from lead
          if (leadId) {
            try {
              await convertLead.mutateAsync({
                id: leadId,
                data: { create_job: false }
              })
            } catch (e) {
              console.warn('Lead conversion failed:', e)
            }
          }

          navigate(`/estimates/${result.estimate.id}`)
        }
      }
    } catch (error) {
      console.error('Save error:', error)
    } finally {
      setIsSaving(false)
    }
  }

  // Keep ref updated for keyboard shortcuts
  handleSaveRef.current = handleSave

  // Handle convert to invoice
  const handleConvertToInvoice = async () => {
    if (!estimateId || estimateStatus !== 'approved') return

    setIsConverting(true)
    try {
      const result = await convertToInvoice.mutateAsync(estimateId)
      if (result.invoice_id) {
        navigate(`/invoices/${result.invoice_id}`)
      } else {
        navigate('/invoices')
      }
    } catch (error) {
      console.error('Convert to invoice error:', error)
      // Still navigate to invoices list on error
      navigate('/invoices')
    } finally {
      setIsConverting(false)
    }
  }

  // Show loading state
  const isLoading = (isLoadingEstimate && isEditing) || isLoadingCustomer || isLoadingLead

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const canConvertToInvoice = isEditing && estimateStatus === 'approved'

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center justify-between z-40">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold">
                Hail Total: ${totals.hail.toFixed(2)}
              </h1>
              {saveStatus === 'saving' && (
                <span className="text-xs text-blue-600 animate-pulse flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Saving...
                </span>
              )}
              {saveStatus === 'saved' && (
                <span className="text-xs text-green-600 flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" />
                  Saved
                </span>
              )}
              {saveStatus === 'error' && (
                <button
                  onClick={() => setSaveStatus('idle')}
                  className="text-xs text-red-600 flex items-center gap-1 hover:underline"
                >
                  Save failed — Retry
                </button>
              )}
              {lastSavedAt && saveStatus === 'idle' && (
                <span className="text-xs text-muted-foreground">
                  Last saved {lastSavedAt.toLocaleTimeString()}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {vehicleYear} {vehicleMake} {vehicleModel || 'New Estimate'}
              {isEditing && existingEstimate?.estimate_number && (
                <span className="ml-2 text-xs">({existingEstimate.estimate_number})</span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Matrix Selector */}
          <Select value={matrixProfileId} onValueChange={setMatrixProfileId}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Matrix" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="state_farm">State Farm</SelectItem>
              <SelectItem value="farmers">Farmers</SelectItem>
              <SelectItem value="allstate">Allstate</SelectItem>
              <SelectItem value="progressive">Progressive</SelectItem>
              <SelectItem value="usaa">USAA</SelectItem>
              <SelectItem value="geico">Geico</SelectItem>
              <SelectItem value="liberty">Liberty Mutual</SelectItem>
              <SelectItem value="nationwide">Nationwide</SelectItem>
              <SelectItem value="retail">Retail/Cash</SelectItem>
            </SelectContent>
          </Select>

          {/* VIN Decode Button */}
          <Button variant="outline" size="icon" onClick={() => setVinDialogOpen(true)} title="Enter VIN">
            <Search className="h-4 w-4" />
          </Button>

          {/* Vehicle Picker Button */}
          <Button
            variant={vehicleId ? 'default' : 'outline'}
            size="icon"
            onClick={() => setVehiclePickerOpen(true)}
            title={vehicleId ? `${vehicleYear} ${vehicleMake} ${vehicleModel}` : 'Select Vehicle'}
            disabled={!customerId}
          >
            <Car className="h-4 w-4" />
          </Button>

          {/* Customer Button */}
          <Button
            variant={selectedCustomer ? 'default' : 'outline'}
            size="icon"
            onClick={() => setCustomerPickerOpen(true)}
            title={selectedCustomer ? customerName : 'Select Customer'}
          >
            {selectedCustomer ? (
              <User className="h-4 w-4" />
            ) : (
              <UserPlus className="h-4 w-4" />
            )}
          </Button>

          {/* Convert to Invoice Button (only for approved estimates) */}
          {canConvertToInvoice && (
            <Button
              variant="outline"
              onClick={handleConvertToInvoice}
              disabled={isConverting}
              className="text-green-600 border-green-600 hover:bg-green-50"
              title="Convert to Invoice"
            >
              {isConverting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Receipt className="h-4 w-4 mr-2" />
              )}
              Invoice
            </Button>
          )}

          {/* Save Button */}
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save
          </Button>
        </div>
      </header>

      {/* Status Badge */}
      {isEditing && (
        <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Status:</span>
            <select
              value={estimateStatus}
              onChange={(e) => setEstimateStatus(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="draft">Draft</option>
              <option value="in_progress">In Progress</option>
              <option value="approved">Approved</option>
              <option value="completed">Completed</option>
            </select>
            {estimateStatus === 'approved' && (
              <span className="flex items-center gap-1 text-green-600 text-sm">
                <CheckCircle className="h-4 w-4" />
                Ready for invoice
              </span>
            )}
          </div>

          {/* Timeline Toggle (Desktop only) */}
          <div className="hidden lg:flex items-center gap-2">
            {activitiesData?.activities && activitiesData.activities.length > 0 && (
              <details className="relative">
                <summary className="flex items-center gap-1 text-sm text-muted-foreground cursor-pointer hover:text-foreground">
                  <Clock className="h-4 w-4" />
                  Timeline ({activitiesData.activities.length})
                </summary>
                <div className="absolute right-0 top-full mt-1 w-80 bg-white border rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
                  <div className="p-3 border-b">
                    <h4 className="font-medium text-sm">Recent Activity</h4>
                  </div>
                  <div className="p-2 space-y-1">
                    {activitiesData.activities.slice(0, 10).map((activity) => {
                      // Activity icon and label based on type
                      const getActivityInfo = (type: string) => {
                        switch (type) {
                          case 'estimate_sent':
                            return { icon: Send, label: 'Estimate sent', color: 'text-blue-600' }
                          case 'estimate_failed':
                            return { icon: AlertCircle, label: 'Send failed', color: 'text-red-600' }
                          case 'supplement_created':
                            return { icon: FileText, label: 'Supplement created', color: 'text-green-600' }
                          case 'supplement_sent':
                            return { icon: Send, label: 'Supplement sent', color: 'text-blue-600' }
                          case 'supplement_failed':
                            return { icon: AlertCircle, label: 'Supplement failed', color: 'text-red-600' }
                          case 'pdf_downloaded':
                            return { icon: Download, label: 'PDF downloaded', color: 'text-gray-600' }
                          case 'dispute_pack_downloaded':
                            return { icon: Archive, label: 'Dispute pack downloaded', color: 'text-purple-600' }
                          case 'customer_authorized':
                            return { icon: PenLine, label: 'Customer authorized', color: 'text-green-600' }
                          case 'customer_declined':
                            return { icon: AlertCircle, label: 'Customer declined', color: 'text-red-600' }
                          case 'insurer_submitted':
                            return { icon: Send, label: 'Submitted to insurer', color: 'text-blue-600' }
                          case 'insurer_approved':
                            return { icon: Lock, label: 'Insurer approved', color: 'text-green-600' }
                          case 'insurer_declined':
                            return { icon: AlertCircle, label: 'Insurer declined', color: 'text-red-600' }
                          case 'insurer_needs_revision':
                            return { icon: FileText, label: 'Revision requested', color: 'text-amber-600' }
                          case 'job_created_from_estimate':
                            return { icon: Wrench, label: 'Job created', color: 'text-blue-600' }
                          case 'job_status_changed':
                            return { icon: Play, label: 'Job status changed', color: 'text-blue-600' }
                          default:
                            return { icon: Clock, label: type.replace(/_/g, ' '), color: 'text-gray-600' }
                        }
                      }

                      const info = getActivityInfo(activity.activity_type)
                      const Icon = info.icon
                      const metadata = activity.metadata as Record<string, unknown>
                      const createdAt = new Date(activity.created_at)
                      const timeStr = createdAt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
                      const dateStr = createdAt.toLocaleDateString([], { month: 'short', day: 'numeric' })

                      return (
                        <div key={activity.id} className="flex items-start gap-2 p-2 rounded hover:bg-muted/50">
                          <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${info.color}`} />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{info.label}</div>
                            {!!metadata?.recipient && (
                              <div className="text-xs text-muted-foreground truncate">
                                To: {String(metadata.recipient)}
                              </div>
                            )}
                            {!!metadata?.supplement_number && (
                              <div className="text-xs text-muted-foreground">
                                Supplement #{String(metadata.supplement_number)}
                              </div>
                            )}
                            {activity.activity_type === 'insurer_approved' && metadata?.approved_total !== undefined ? (
                              <div className="text-xs space-y-0.5 mt-1">
                                <div className="flex items-center gap-1 text-green-600">
                                  <DollarSign className="h-3 w-3" />
                                  <span>{'Approved: $' + Number(metadata.approved_total).toFixed(2)}</span>
                                </div>
                                {metadata?.short_paid && Number(metadata.short_paid) > 0 ? (
                                  <div className="text-amber-600">
                                    {'Short paid: $' + Number(metadata.short_paid).toFixed(2)}
                                  </div>
                                ) : null}
                                {metadata?.reference ? (
                                  <div className="text-muted-foreground truncate">
                                    {'Ref: ' + String(metadata.reference)}
                                  </div>
                                ) : null}
                              </div>
                            ) : null}
                            {activity.activity_type === 'customer_authorized' && metadata?.signed_by ? (
                              <div className="text-xs text-muted-foreground">
                                {'Signed by: ' + String(metadata.signed_by)}
                              </div>
                            ) : null}
                            {activity.activity_type === 'job_created_from_estimate' && metadata?.job_number ? (
                              <div className="text-xs text-muted-foreground">
                                {String(metadata.job_number)}
                              </div>
                            ) : null}
                            {activity.activity_type === 'job_status_changed' && metadata?.to_status ? (
                              <div className="text-xs text-muted-foreground">
                                {String(metadata.from_status).replace('_', ' ') + ' → ' + String(metadata.to_status).replace('_', ' ')}
                              </div>
                            ) : null}
                          </div>
                          <div className="text-xs text-muted-foreground text-right flex-shrink-0">
                            <div>{timeStr}</div>
                            <div>{dateStr}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </details>
            )}
          </div>
        </div>
      )}

      {/* Running Total Status Bar */}
      <EstimateStatusBar
        estimateNumber={isEditing && existingEstimate?.estimate_number ? existingEstimate.estimate_number : undefined}
        vehicleInfo={vehicleInfoString}
        total={totals.hail}
        damagedCount={damagedCount}
        selectedCount={selectedPanelKeys.size}
        selectionMode={selectionMode}
        saveStatus={saveStatus}
        lastSavedAt={lastSavedAt}
        onRetrySave={handleRetrySave}
        onReview={handleReview}
        isSaved={isEditing}
        onDownloadPDF={handleDownloadPDF}
        isDownloadingPDF={downloadPDF.isPending}
        onDownloadPhotoSheet={handleDownloadPhotoSheet}
        isDownloadingPhotoSheet={downloadPhotoSheet.isPending}
        onDownloadDisputePack={handleDownloadDisputePack}
        isDownloadingDisputePack={downloadDisputePack.isPending}
        onSendToAdjuster={isEditing ? () => setSendToAdjusterOpen(true) : undefined}
        onCreateSupplement={isEditing ? () => setCreateSupplementOpen(true) : undefined}
        onCreateShareLink={isEditing ? () => setCreateShareLinkOpen(true) : undefined}
        permissions={permissions}
        overlayOpen={quickEntryOpen}
      />

      {/* Stage 7A: Speed Bar - Quick Actions */}
      <div className="hidden lg:flex bg-muted/50 border-b px-4 py-2 items-center gap-4">
        {/* Panel Search */}
        <div className="relative flex-1 max-w-xs">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              ref={panelSearchInputRef}
              placeholder="Search panels... (press /)"
              value={panelSearchQuery}
              onChange={(e) => {
                setPanelSearchQuery(e.target.value)
                setPanelSearchOpen(true)
              }}
              onFocus={() => setPanelSearchOpen(true)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && filteredPanels.length > 0) {
                  handlePanelSearchSelect(filteredPanels[0][0])
                }
                if (e.key === 'Escape') {
                  setPanelSearchOpen(false)
                  setPanelSearchQuery('')
                  ;(e.target as HTMLInputElement).blur()
                }
              }}
              className="pl-8 h-8 text-sm"
            />
          </div>
          {/* Search Results Dropdown */}
          {panelSearchOpen && filteredPanels.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
              {filteredPanels.map(([panelId, panelName]) => {
                const damage = panels[panelId]
                const hasDamage = !!(damage?.countRange && damage?.dentSize)
                return (
                  <button
                    key={panelId}
                    onClick={() => handlePanelSearchSelect(panelId)}
                    className="w-full text-left px-3 py-2 hover:bg-muted/50 flex items-center justify-between text-sm"
                  >
                    <span>{panelName}</span>
                    {hasDamage && (
                      <span className="text-xs text-muted-foreground">
                        ${damage.totalPrice.toFixed(0)}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {/* Last Used Summary */}
        {lastUsedDamage?.countRange && lastUsedDamage?.dentSize && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground bg-white px-3 py-1 rounded border">
            <span className="font-medium">Last:</span>
            <span>{lastUsedDamage.countRange}</span>
            <span className="text-muted-foreground/60">•</span>
            <span className="capitalize">{lastUsedDamage.dentSize}</span>
            {lastUsedDamage.gluePull && <span className="text-xs bg-yellow-100 px-1 rounded">GP</span>}
            {lastUsedDamage.aluminum && <span className="text-xs bg-blue-100 px-1 rounded">AL</span>}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRepeatLast}
            disabled={!selectedPanelId || !lastUsedDamage}
            title="Repeat last settings (R)"
          >
            <Repeat className="h-3.5 w-3.5 mr-1" />
            Repeat
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleApplyToSelected}
            disabled={selectedPanelKeys.size < 2}
            title="Apply to selected panels (A)"
          >
            <Command className="h-3.5 w-3.5 mr-1" />
            Apply to {selectedPanelKeys.size > 0 ? selectedPanelKeys.size : 'Selected'}
          </Button>

          {selectedPanelKeys.size > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearSelection}
              title="Clear selection (Esc)"
            >
              <X className="h-3.5 w-3.5 mr-1" />
              Clear
            </Button>
          )}

          <div className="border-l pl-2 ml-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShortcutsModalOpen(true)}
              title="Keyboard shortcuts (?)"
            >
              <Keyboard className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Autosave Indicator */}
        <div className="ml-auto text-xs text-muted-foreground flex items-center gap-1">
          {saveStatus === 'saving' && (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Saving...</span>
            </>
          )}
          {saveStatus === 'saved' && (
            <>
              <CheckCircle className="h-3 w-3 text-green-600" />
              <span>Saved just now</span>
            </>
          )}
          {saveStatus === 'idle' && lastSavedAt && (
            <span>Saved {lastSavedAt.toLocaleTimeString()}</span>
          )}
        </div>
      </div>

      {/* Phase 7A+: Writer Row - Single-line rapid panel entry */}
      {ENABLE_WRITER_ROW && (
        <div className="hidden lg:flex bg-gradient-to-r from-blue-50 to-indigo-50 border-b px-4 py-2 items-center gap-3">
          <div className="flex items-center gap-1 text-blue-600">
            <Zap className="h-4 w-4" />
            <span className="text-xs font-medium">Quick Add</span>
          </div>

          {/* Panel Name Search */}
          <div className="relative w-48">
            <Input
              ref={writerPanelInputRef}
              placeholder="Panel name..."
              value={writerDraft.panelName}
              onChange={(e) => {
                setWriterDraft(prev => ({ ...prev, panelName: e.target.value }))
                setWriterSearchOpen(true)
              }}
              onFocus={() => setWriterSearchOpen(true)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey) {
                  if (writerFilteredPanels.length > 0 && !writerDraft.countRange) {
                    // Select first panel from dropdown
                    setWriterDraft(prev => ({ ...prev, panelName: writerFilteredPanels[0][1] }))
                    setWriterSearchOpen(false)
                  } else if (writerDraft.countRange && writerDraft.dentSize) {
                    handleWriterAddPanel()
                  }
                }
                if (e.key === 'Enter' && e.shiftKey) {
                  // Rapid mode: add and keep focus
                  setWriterRapidMode(true)
                  handleWriterAddPanel()
                }
                if (e.key === 'Enter' && e.ctrlKey && lastUsedDamage) {
                  // Apply last and add
                  handleWriterApplyLastAndAdd()
                }
                if (e.key === 'Escape') {
                  resetWriterDraft()
                }
              }}
              className="h-8 text-sm"
            />
            {/* Typeahead dropdown */}
            {writerSearchOpen && writerFilteredPanels.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                {writerFilteredPanels.map(([panelId, panelName]) => (
                  <button
                    key={panelId}
                    onClick={() => {
                      setWriterDraft(prev => ({ ...prev, panelName }))
                      setWriterSearchOpen(false)
                    }}
                    className="w-full text-left px-3 py-1.5 hover:bg-muted/50 text-sm"
                  >
                    {panelName}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Count Range */}
          <Select
            value={writerDraft.countRange || ''}
            onValueChange={(v) => setWriterDraft(prev => ({ ...prev, countRange: v as CountRange }))}
          >
            <SelectTrigger className="w-24 h-8 text-xs">
              <SelectValue placeholder="Count" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1-5">1-5</SelectItem>
              <SelectItem value="6-15">6-15</SelectItem>
              <SelectItem value="16-30">16-30</SelectItem>
              <SelectItem value="31-50">31-50</SelectItem>
              <SelectItem value="51-75">51-75</SelectItem>
              <SelectItem value="76-100">76-100</SelectItem>
              <SelectItem value="101+">101+</SelectItem>
            </SelectContent>
          </Select>

          {/* Dent Size */}
          <Select
            value={writerDraft.dentSize || ''}
            onValueChange={(v) => setWriterDraft(prev => ({ ...prev, dentSize: v as DentSize }))}
          >
            <SelectTrigger className="w-24 h-8 text-xs">
              <SelectValue placeholder="Size" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dime">Dime</SelectItem>
              <SelectItem value="nickel">Nickel</SelectItem>
              <SelectItem value="quarter">Quarter</SelectItem>
              <SelectItem value="half">Half $</SelectItem>
            </SelectContent>
          </Select>

          {/* Depth */}
          <Select
            value={writerDraft.depth}
            onValueChange={(v) => setWriterDraft(prev => ({ ...prev, depth: v }))}
          >
            <SelectTrigger className="w-24 h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="shallow">Shallow</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="deep">Deep</SelectItem>
              <SelectItem value="severe">Severe</SelectItem>
            </SelectContent>
          </Select>

          {/* Material Toggle */}
          <Button
            variant={writerDraft.material === 'aluminum' ? 'default' : 'outline'}
            size="sm"
            className="h-8 text-xs px-2"
            onClick={() => setWriterDraft(prev => ({
              ...prev,
              material: prev.material === 'steel' ? 'aluminum' : 'steel'
            }))}
          >
            {writerDraft.material === 'aluminum' ? 'AL' : 'Steel'}
          </Button>

          {/* Price Preview */}
          {ENABLE_PRICING_ENGINE && writerPreviewPrice && (
            <div className="flex items-center gap-1 text-sm font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
              <DollarSign className="h-3.5 w-3.5" />
              {writerPreviewPrice.totalPrice.toFixed(0)}
              <button
                className="ml-1 text-muted-foreground hover:text-foreground"
                title={writerPreviewPrice.breakdown.join('\n')}
              >
                <Info className="h-3 w-3" />
              </button>
            </div>
          )}

          {/* Add Button */}
          <Button
            size="sm"
            className="h-8"
            onClick={handleWriterAddPanel}
            disabled={!writerDraft.panelName || !writerDraft.countRange || !writerDraft.dentSize}
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            Add
          </Button>

          {/* Rapid Mode Indicator */}
          {writerRapidMode && (
            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded">
              Rapid Mode
            </span>
          )}

          {/* Keyboard hints */}
          <div className="ml-auto text-xs text-muted-foreground hidden xl:flex items-center gap-2">
            <span><kbd className="px-1 bg-muted rounded">Enter</kbd> Add</span>
            <span><kbd className="px-1 bg-muted rounded">Shift+Enter</kbd> Rapid</span>
            <span><kbd className="px-1 bg-muted rounded">Ctrl+Enter</kbd> Use Last</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      {/* pb-16 for bottom nav, pb-32 on mobile for floating status bar */}
      <div className="flex-1 flex overflow-hidden pb-32 lg:pb-16">
        {/* Panel List Sidebar (left on desktop) */}
        {showSidebar && (
          <div className="hidden lg:block w-64 flex-shrink-0">
            <PanelListSidebar
              vehicleType={vehicleType}
              panels={panels}
              selectedPanelId={selectedPanelId}
              onPanelSelect={handlePanelClick}
              onAddCustomPanel={() => {}}
              className="h-full"
            />
          </div>
        )}

        {/* Vehicle Diagram (center) - shown when NOT on R&I tab */}
        {activeServiceTab !== 'ri' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
              <VehicleDiagram
                vehicleType={vehicleType}
                onVehicleTypeChange={handleVehicleTypeChange}
                panels={panelStates}
                onPanelClick={handlePanelClick}
                onPanelClickWithAnchor={handleQuickEntryPanelClick}
                onPanelClickWithModifiers={handlePanelClickWithModifiers}
                onPanelLongPress={handlePanelLongPress}
                onClearAll={handleClearAll}
                onClearSelection={handleClearSelection}
                onExitSelectionMode={handleExitSelectionMode}
                onOpenPrimaryOverlay={handleOpenPrimaryOverlay}
                selectionMode={selectionMode}
                selectedCount={selectedPanelKeys.size}
                primaryPanelName={selectedPanelName}
                className="w-full max-w-md"
              />
            </div>

            {/* Stage 7D: R&I Suggestions Strip - shown when panel selected */}
            {selectedPanelId && riSuggestions.length > 0 && isEditing && (
              <div className="border-t bg-blue-50/50 px-4 py-2">
                <div className="flex items-center gap-2 mb-2">
                  <Wrench className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">
                    R&I for {selectedPanelId.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                  </span>
                  <button
                    onClick={() => setActiveServiceTab('ri')}
                    className="text-xs text-blue-600 hover:underline ml-auto"
                  >
                    View R&I Tab →
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {riSuggestions.slice(0, 6).map((suggestion) => {
                    const isAdded = alreadyAddedRiCodes.has(suggestion.code) || riAddedCodes.has(suggestion.code)
                    const isAdding = riAddingCode === suggestion.code

                    return (
                      <button
                        key={suggestion.code}
                        onClick={() => !isAdded && !isAdding && handleRiQuickAdd(suggestion)}
                        disabled={isAdded || isAdding}
                        className={`
                          inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm
                          transition-all duration-200
                          ${isAdded
                            ? 'bg-green-100 text-green-700 cursor-default'
                            : isAdding
                              ? 'bg-blue-100 text-blue-700 cursor-wait'
                              : 'bg-white border border-blue-200 text-blue-700 hover:bg-blue-100 hover:border-blue-300'
                          }
                        `}
                        title={suggestion.description}
                      >
                        {isAdding ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : isAdded ? (
                          <CheckCircle className="h-3 w-3" />
                        ) : (
                          <Plus className="h-3 w-3" />
                        )}
                        {suggestion.label}
                      </button>
                    )
                  })}
                </div>
                {estimateRiData && estimateRiData.total_ri_time_hours > 0 && (
                  <div className="mt-2 text-xs text-blue-700">
                    Current R&I: {estimateRiData.total_ri_time_hours.toFixed(1)} hrs
                    (${((estimateRiData.total_ri_time_hours) * resolvedLaborRate).toFixed(2)})
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* R&I Editor (Phase 6C) - shown when R&I tab is active */}
        {activeServiceTab === 'ri' && (
          <div className="flex-1 flex flex-col overflow-hidden bg-white">
            <div className="flex-1 overflow-auto p-4 space-y-4">
              {/* R&I Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    <Wrench className="h-5 w-5 text-blue-600" />
                    R&I Justification
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Add remove & install operations to justify labor time
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-blue-600">
                    {estimateRiData?.total_ri_time_hours?.toFixed(1) ?? '0.0'} hrs
                  </div>
                  <div className="text-sm text-muted-foreground">
                    ${((estimateRiData?.total_ri_time_hours ?? 0) * resolvedLaborRate).toFixed(2)} @ ${resolvedLaborRate.toFixed(2)}/hr
                  </div>
                </div>
              </div>

              {/* Labor Rate Card (Stage 6E) */}
              {isEditing && (
                <div className="bg-muted/30 rounded-lg p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <DollarSign className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <div className="text-sm font-medium">
                        R&I Rate: ${resolvedLaborRate.toFixed(2)}/hr
                        {laborRateData?.source === 'rule' && laborRateData.rule_name && (
                          <span className="ml-2 text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                            {laborRateData.rule_name}
                          </span>
                        )}
                        {laborRateData?.source === 'override' && (
                          <span className="ml-2 text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded">
                            Override
                          </span>
                        )}
                        {laborRateData?.source === 'default' && (
                          <span className="ml-2 text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                            Default
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {laborRateData?.reason || 'Resolved from tenant settings'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {showRateOverride ? (
                      <>
                        <div className="flex items-center gap-1">
                          <span>$</span>
                          <Input
                            type="number"
                            min="0"
                            max="500"
                            step="0.01"
                            value={rateOverrideValue}
                            onChange={(e) => setRateOverrideValue(e.target.value)}
                            className="w-24 h-8"
                            placeholder={resolvedLaborRate.toString()}
                          />
                          <span>/hr</span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const rate = parseFloat(rateOverrideValue)
                            if (!isNaN(rate) && rate >= 0 && rate <= 500) {
                              setLaborRateOverride.mutate({ ri_labor_rate: rate })
                            }
                            setShowRateOverride(false)
                            setRateOverrideValue('')
                          }}
                          disabled={setLaborRateOverride.isPending}
                        >
                          {setLaborRateOverride.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            'Apply'
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setShowRateOverride(false)
                            setRateOverrideValue('')
                          }}
                        >
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowRateOverride(true)}
                        >
                          Override Rate
                        </Button>
                        {laborRateData?.source === 'override' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setLaborRateOverride.mutate({ ri_labor_rate: null })}
                            disabled={setLaborRateOverride.isPending}
                            className="text-red-600 hover:text-red-700"
                          >
                            Clear Override
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Denial Pack Card (Stage 6F) */}
              {estimateRiData?.ri_denial_pack && estimateRiData.ri_denial_pack.overall_score > 0 && (
                <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-full ${
                        estimateRiData.ri_denial_pack.overall_rating === 'high'
                          ? 'bg-green-100'
                          : estimateRiData.ri_denial_pack.overall_rating === 'medium'
                          ? 'bg-amber-100'
                          : 'bg-red-100'
                      }`}>
                        <CheckCircle className={`h-5 w-5 ${
                          estimateRiData.ri_denial_pack.overall_rating === 'high'
                            ? 'text-green-600'
                            : estimateRiData.ri_denial_pack.overall_rating === 'medium'
                            ? 'text-amber-600'
                            : 'text-red-600'
                        }`} />
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">Denial Resistance Analysis</div>
                        <div className="text-sm text-gray-600">
                          Score: <span className={`font-bold ${
                            estimateRiData.ri_denial_pack.overall_rating === 'high'
                              ? 'text-green-600'
                              : estimateRiData.ri_denial_pack.overall_rating === 'medium'
                              ? 'text-amber-600'
                              : 'text-red-600'
                          }`}>{estimateRiData.ri_denial_pack.overall_score}/100</span>
                          {' '}({estimateRiData.ri_denial_pack.overall_rating.toUpperCase()})
                        </div>
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      <div className="flex gap-3 text-gray-600">
                        <span className="text-green-600">{estimateRiData.ri_denial_pack.resistance_counts.high} high</span>
                        <span className="text-amber-600">{estimateRiData.ri_denial_pack.resistance_counts.medium} med</span>
                        <span className="text-red-600">{estimateRiData.ri_denial_pack.resistance_counts.low} low</span>
                      </div>
                      <div className="text-gray-500 mt-1">
                        {estimateRiData.ri_denial_pack.required_steps_count} required, {estimateRiData.ri_denial_pack.optional_steps_count} optional
                      </div>
                    </div>
                  </div>

                  {/* Risk Tags */}
                  {estimateRiData.ri_denial_pack.risk_tags.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-green-200">
                      <div className="text-xs text-gray-500 mb-1">Risk Factors Addressed:</div>
                      <div className="flex flex-wrap gap-1">
                        {estimateRiData.ri_denial_pack.risk_tags.map((tag) => (
                          <span
                            key={tag}
                            className="text-xs px-2 py-0.5 bg-white border border-green-300 text-green-700 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Summary Text */}
                  <div className="mt-3 pt-3 border-t border-green-200">
                    <p className="text-sm text-gray-700 italic">
                      {estimateRiData.ri_denial_pack.summary_text}
                    </p>
                  </div>
                </div>
              )}

              {/* --- 6G: Denial Ammo (Adjuster-ready copy/paste) --- */}
              {estimateRiData?.ri_denial_pack?.copy_blocks && (
                <div className="rounded-lg border bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold">Denial Ammo</div>
                      <div className="text-xs text-muted-foreground">
                        Copy/paste bullets and cite-lines for adjuster conversations and supplements.
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="inline-flex items-center rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                        onClick={async () => {
                          const text = estimateRiData.ri_denial_pack?.copy_blocks?.short || ''
                          if (text) await navigator.clipboard.writeText(text)
                        }}
                      >
                        Copy Short
                      </button>
                      <button
                        type="button"
                        className="inline-flex items-center rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                        onClick={async () => {
                          const text = estimateRiData.ri_denial_pack?.copy_blocks?.full || ''
                          if (text) await navigator.clipboard.writeText(text)
                        }}
                      >
                        Copy Full
                      </button>
                    </div>
                  </div>

                  {/* Top defensible steps */}
                  {estimateRiData.ri_denial_pack?.top_defensible_steps?.length ? (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-muted-foreground">Top defensible sub-steps (cite lines)</div>
                      <ul className="mt-2 space-y-1 text-sm">
                        {estimateRiData.ri_denial_pack.top_defensible_steps.slice(0, 6).map((s, idx) => (
                          <li key={idx} className="rounded-md bg-muted/40 px-3 py-2">
                            <div className="text-sm">{s.cite_line}</div>
                            {s.risk_tags?.length ? (
                              <div className="mt-1 text-xs text-muted-foreground">
                                Risk tags: {s.risk_tags.join(', ')}
                              </div>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {/* Adjuster bullets */}
                  {estimateRiData.ri_denial_pack?.adjuster_bullets?.length ? (
                    <div className="mt-4">
                      <div className="text-xs font-medium text-muted-foreground">Adjuster bullets</div>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                        {estimateRiData.ri_denial_pack.adjuster_bullets.slice(0, 8).map((b, idx) => (
                          <li key={idx}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {/* Scope clarifier */}
                  {estimateRiData.ri_denial_pack?.scope_clarifier ? (
                    <div className="mt-4 rounded-md bg-muted/30 p-3">
                      <div className="text-xs font-medium text-muted-foreground">Scope clarifier</div>
                      <div className="mt-1 text-sm">{estimateRiData.ri_denial_pack.scope_clarifier}</div>
                    </div>
                  ) : null}
                </div>
              )}

              {/* --- 6H-A: Denial Simulator --- */}
              {(estimateRiData?.operations?.length ?? 0) > 0 && (
                <div className="rounded-lg border bg-white p-4">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div>
                      <div className="text-sm font-semibold flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-orange-500" />
                        Denial Simulator
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Select a common denial to generate an instant rebuttal.
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Select
                      value={selectedDenialCode}
                      onValueChange={setSelectedDenialCode}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select denial type..." />
                      </SelectTrigger>
                      <SelectContent>
                        {denialCodesData?.codes?.map((d) => (
                          <SelectItem key={d.code} value={d.code}>
                            {d.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!selectedDenialCode || denialSimulator.isPending}
                      onClick={async () => {
                        if (selectedDenialCode) {
                          const result = await denialSimulator.mutateAsync(selectedDenialCode)
                          if (result.success) {
                            setDenialRebuttal(result)
                          }
                        }
                      }}
                    >
                      {denialSimulator.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        'Generate'
                      )}
                    </Button>
                  </div>

                  {/* Rebuttal Output */}
                  {denialRebuttal?.success && (
                    <div className="mt-4 space-y-3">
                      <div className="p-3 bg-orange-50 border border-orange-200 rounded-md">
                        <div className="text-xs font-medium text-orange-700">Insurer Claim</div>
                        <div className="text-sm mt-1">{denialRebuttal.insurer_claim}</div>
                      </div>

                      <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                        <div className="text-xs font-medium text-green-700">Rebuttal Summary</div>
                        <div className="text-sm mt-1">{denialRebuttal.rebuttal_summary}</div>
                      </div>

                      {denialRebuttal.rebuttal_bullets?.length > 0 && (
                        <div>
                          <div className="text-xs font-medium text-muted-foreground mb-1">Key Points</div>
                          <ul className="list-disc pl-5 text-sm space-y-1">
                            {denialRebuttal.rebuttal_bullets.map((b, idx) => (
                              <li key={idx}>{b}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {denialRebuttal.cited_steps?.length > 0 && (
                        <div>
                          <div className="text-xs font-medium text-muted-foreground mb-1">Cited Steps</div>
                          <ul className="text-sm space-y-1">
                            {denialRebuttal.cited_steps.map((s, idx) => (
                              <li key={idx} className="p-2 bg-muted/30 rounded">
                                {s.cite_line}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="flex gap-2 pt-2">
                        <button
                          type="button"
                          className="inline-flex items-center rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                          onClick={async () => {
                            const text = denialRebuttal.copy_blocks?.short || ''
                            if (text) await navigator.clipboard.writeText(text)
                          }}
                        >
                          Copy Short
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                          onClick={async () => {
                            const text = denialRebuttal.copy_blocks?.full || ''
                            if (text) await navigator.clipboard.writeText(text)
                          }}
                        >
                          Copy Full
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* --- 6H-B: Supplement Writer --- */}
              {(estimateRiData?.operations?.length ?? 0) > 0 && (
                <div className="rounded-lg border bg-white p-4">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div>
                      <div className="text-sm font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-500" />
                        Supplement Writer
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Generate a complete insurer-ready supplement letter.
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Select
                      value={supplementDenialCode}
                      onValueChange={setSupplementDenialCode}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Optional: Include denial rebuttal..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">No denial rebuttal</SelectItem>
                        {denialCodesData?.codes?.map((d) => (
                          <SelectItem key={d.code} value={d.code}>
                            {d.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="default"
                      size="sm"
                      disabled={supplementWriter.isPending}
                      onClick={async () => {
                        const result = await supplementWriter.mutateAsync(supplementDenialCode || undefined)
                        if (result.success) {
                          setSupplementLetter(result)
                        }
                      }}
                    >
                      {supplementWriter.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        'Generate Supplement'
                      )}
                    </Button>
                  </div>

                  {/* Supplement Letter Output */}
                  {supplementLetter?.success && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs text-muted-foreground">
                          Est: {supplementLetter.estimate_number} | Claim: {supplementLetter.claim_number}
                        </div>
                        <div className="text-xs font-medium text-blue-600">
                          ${supplementLetter.total_ri_cost?.toFixed(2)} R&I Total
                        </div>
                      </div>

                      <div className="max-h-64 overflow-y-auto p-3 bg-gray-50 border rounded-md text-sm font-mono whitespace-pre-wrap">
                        {supplementLetter.letter_text}
                      </div>

                      <div className="flex gap-2 pt-3">
                        <button
                          type="button"
                          className="inline-flex items-center rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                          onClick={async () => {
                            const text = supplementLetter.letter_text || ''
                            if (text) await navigator.clipboard.writeText(text)
                          }}
                        >
                          Copy Text
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center rounded-md bg-blue-600 text-white px-3 py-1.5 text-xs hover:bg-blue-700"
                          onClick={() => {
                            // Download as text file
                            const blob = new Blob([supplementLetter.letter_text || ''], { type: 'text/plain' })
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement('a')
                            a.href = url
                            a.download = `supplement-${supplementLetter.estimate_number}.txt`
                            a.click()
                            URL.revokeObjectURL(url)
                          }}
                        >
                          <Download className="h-3 w-3 mr-1" />
                          Download
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Add Operation Search */}
              {isEditing && (
                <div className="relative">
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search operations to add..."
                        value={riSearchQuery}
                        onChange={(e) => {
                          setRiSearchQuery(e.target.value)
                          setRiSearchOpen(true)
                        }}
                        onFocus={() => setRiSearchOpen(true)}
                        className="pl-9"
                      />
                    </div>
                    {addEstimateRI.isPending && (
                      <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                    )}
                  </div>

                  {/* Search Results Dropdown */}
                  {riSearchOpen && riSearchQuery && riCatalog?.operations && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
                      {riCatalog.operations
                        .filter((op: RIOperation) =>
                          op.display_name.toLowerCase().includes(riSearchQuery.toLowerCase()) ||
                          op.code.toLowerCase().includes(riSearchQuery.toLowerCase())
                        )
                        .slice(0, 10)
                        .map((op: RIOperation) => {
                          const isAlreadyAdded = estimateRiData?.operations?.some(
                            (existingOp) => existingOp.operation_id === op.id
                          )
                          return (
                            <button
                              key={op.id}
                              className={`w-full text-left px-4 py-3 hover:bg-muted/50 border-b last:border-b-0 ${
                                isAlreadyAdded ? 'opacity-50 cursor-not-allowed' : ''
                              }`}
                              onClick={() => {
                                if (!isAlreadyAdded) {
                                  addEstimateRI.mutate({ operationCode: op.code })
                                  setRiSearchQuery('')
                                  setRiSearchOpen(false)
                                }
                              }}
                              disabled={isAlreadyAdded}
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="font-medium">{op.display_name}</div>
                                  <div className="text-xs text-muted-foreground">
                                    {op.category} • {op.risk_level} risk
                                  </div>
                                </div>
                                <div className="text-sm text-muted-foreground">
                                  {isAlreadyAdded ? (
                                    <span className="text-green-600 flex items-center gap-1">
                                      <CheckCircle className="h-4 w-4" /> Added
                                    </span>
                                  ) : (
                                    <span className="text-blue-600">+ Add</span>
                                  )}
                                </div>
                              </div>
                            </button>
                          )
                        })}
                      {riCatalog.operations.filter((op: RIOperation) =>
                        op.display_name.toLowerCase().includes(riSearchQuery.toLowerCase()) ||
                        op.code.toLowerCase().includes(riSearchQuery.toLowerCase())
                      ).length === 0 && (
                        <div className="px-4 py-3 text-sm text-muted-foreground">
                          No operations found
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Click outside to close search */}
              {riSearchOpen && (
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setRiSearchOpen(false)}
                />
              )}

              {/* Added Operations List */}
              <div className="space-y-3">
                {isLoadingEstimateRi ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : estimateRiData?.operations && estimateRiData.operations.length > 0 ? (
                  estimateRiData.operations.map((op) => {
                    const isExpanded = expandedRiOperations.has(op.estimate_ri_operation_id)
                    return (
                      <div
                        key={op.estimate_ri_operation_id}
                        className="border rounded-lg overflow-hidden"
                      >
                        {/* Operation Header */}
                        <div
                          className="flex items-center justify-between p-3 bg-muted/30 cursor-pointer hover:bg-muted/50"
                          onClick={() => {
                            setExpandedRiOperations((prev) => {
                              const next = new Set(prev)
                              if (next.has(op.estimate_ri_operation_id)) {
                                next.delete(op.estimate_ri_operation_id)
                              } else {
                                next.add(op.estimate_ri_operation_id)
                              }
                              return next
                            })
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                            >
                              <ArrowLeft className="h-4 w-4 rotate-180" />
                            </div>
                            <div>
                              <div className="font-medium">{op.display_name}</div>
                              <div className="text-xs text-muted-foreground">
                                {op.category} • {op.steps.length} steps • {op.modifiers.length} modifiers
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="text-right">
                              <div className="font-medium text-blue-600">
                                {op.totals.total_time.toFixed(2)} hrs
                              </div>
                              <div className="text-xs text-muted-foreground">
                                ${(op.totals.total_time * 50).toFixed(2)}
                              </div>
                            </div>
                            {isEditing && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  removeEstimateRI.mutate(op.estimate_ri_operation_id)
                                }}
                              >
                                <AlertCircle className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* Expanded Steps & Modifiers */}
                        {isExpanded && (
                          <div className="p-3 border-t bg-white space-y-3">
                            {/* Steps Table */}
                            <div>
                              <h4 className="text-sm font-medium mb-2">Steps</h4>
                              <div className="border rounded overflow-hidden">
                                <table className="w-full text-sm">
                                  <thead className="bg-muted/50">
                                    <tr>
                                      <th className="text-left px-3 py-2">Step</th>
                                      <th className="text-center px-3 py-2 w-20">Required</th>
                                      <th className="text-center px-3 py-2 w-24">Resistance</th>
                                      <th className="text-right px-3 py-2 w-20">Hours</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {op.steps.map((step) => (
                                      <tr key={step.step_id} className="border-t">
                                        <td className="px-3 py-2">
                                          <div className="font-medium">{step.label}</div>
                                          {step.description && (
                                            <div className="text-xs text-muted-foreground">
                                              {step.description}
                                            </div>
                                          )}
                                        </td>
                                        <td className="text-center px-3 py-2">
                                          {step.required ? (
                                            <CheckCircle className="h-4 w-4 text-green-600 mx-auto" />
                                          ) : (
                                            <span className="text-muted-foreground">-</span>
                                          )}
                                        </td>
                                        <td className="text-center px-3 py-2">
                                          <span
                                            className={`text-xs px-2 py-0.5 rounded ${
                                              step.denial_resistance === 'high'
                                                ? 'bg-green-100 text-green-700'
                                                : step.denial_resistance === 'medium'
                                                ? 'bg-amber-100 text-amber-700'
                                                : 'bg-red-100 text-red-700'
                                            }`}
                                          >
                                            {step.denial_resistance}
                                          </span>
                                        </td>
                                        <td className="text-right px-3 py-2 font-mono">
                                          {step.effective_time_hours.toFixed(2)}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>

                            {/* Modifiers */}
                            {op.modifiers.length > 0 && (
                              <div>
                                <h4 className="text-sm font-medium mb-2">Modifiers Applied</h4>
                                <div className="flex flex-wrap gap-2">
                                  {op.modifiers.map((mod) => (
                                    <span
                                      key={mod.modifier_id}
                                      className="inline-flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded"
                                    >
                                      {mod.label}
                                      <span className="font-mono">+{mod.adds_time_hours.toFixed(2)}h</span>
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Justification Text Preview */}
                            <div className="bg-muted/30 rounded p-3">
                              <h4 className="text-xs font-medium text-muted-foreground mb-1">
                                Justification for Insurer
                              </h4>
                              <p className="text-sm">{op.justification_text}</p>
                            </div>

                            {/* Totals Row */}
                            <div className="flex justify-between items-center pt-2 border-t">
                              <span className="text-sm text-muted-foreground">
                                Base: {op.totals.base_steps_time.toFixed(2)}h + Modifiers: {op.totals.modifiers_time.toFixed(2)}h
                              </span>
                              <span className="font-bold text-blue-600">
                                Total: {op.totals.total_time.toFixed(2)} hrs
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })
                ) : !isEditing ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Wrench className="h-12 w-12 mx-auto mb-2 opacity-30" />
                    <p>Save the estimate first to add R&I operations</p>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Wrench className="h-12 w-12 mx-auto mb-2 opacity-30" />
                    <p>No R&I operations added yet</p>
                    <p className="text-sm">Search above to add operations</p>
                  </div>
                )}
              </div>

              {/* Grand Total */}
              {estimateRiData?.operations && estimateRiData.operations.length > 0 && (
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-lg font-medium">
                      Total R&I Time ({estimateRiData.operation_count} operations)
                    </span>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-blue-600">
                        {estimateRiData.total_ri_time_hours.toFixed(2)} hours
                      </div>
                      <div className="text-muted-foreground">
                        ${(estimateRiData.total_ri_time_hours * resolvedLaborRate).toFixed(2)} @ ${resolvedLaborRate.toFixed(2)}/hr
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Navigation */}
      <EstimateBottomNav
        activeTab={activeServiceTab}
        onTabChange={setActiveServiceTab}
        totals={totals}
      />

      {/* Quick Entry Overlay */}
      <QuickEntryOverlay
        open={quickEntryOpen}
        panelKey={selectedPanelId || ''}
        panelName={selectedPanelName}
        value={(panels[selectedPanelId || ''] || createEmptyPanelDamage(selectedPanelId || '')) as QuickEntryValue}
        onChange={handleQuickEntryChange}
        onClose={handleQuickEntryClose}
        onOpenDetails={handleOpenDetails}
        onRepeatLast={handleRepeatLast}
        hasLastUsed={!!lastUsedDamage}
        anchorPoint={quickEntryAnchor}
        panelPrice={currentPanelPrice}
        selectedCount={selectedPanelKeys.size}
        onApplyToSelected={handleApplyToSelected}
        onClearSelection={handleClearSelection}
      />

      {/* Panel Entry Modal (full details) */}
      <PanelEntryModal
        open={panelModalOpen}
        onClose={() => setPanelModalOpen(false)}
        panelId={selectedPanelId || ''}
        panelName={selectedPanelName}
        damage={panels[selectedPanelId || ''] || createEmptyPanelDamage(selectedPanelId || '')}
        onDamageChange={handleDamageChange}
        matrixLookup={matrixLookup}
      />

      {/* VIN Decode Dialog */}
      <Dialog open={vinDialogOpen} onOpenChange={setVinDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Vehicle Information</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="vin">Vehicle Identification Number</Label>
              <Input
                id="vin"
                value={vehicleVin}
                onChange={(e) => setVehicleVin(e.target.value.toUpperCase())}
                placeholder="17-character VIN"
                maxLength={17}
                className="font-mono text-lg tracking-wider"
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <Label htmlFor="year">Year</Label>
                <Input
                  id="year"
                  value={vehicleYear}
                  onChange={(e) => setVehicleYear(e.target.value)}
                  placeholder="2024"
                />
              </div>
              <div>
                <Label htmlFor="make">Make</Label>
                <Input
                  id="make"
                  value={vehicleMake}
                  onChange={(e) => setVehicleMake(e.target.value)}
                  placeholder="Ford"
                />
              </div>
              <div>
                <Label htmlFor="model">Model</Label>
                <Input
                  id="model"
                  value={vehicleModel}
                  onChange={(e) => setVehicleModel(e.target.value)}
                  placeholder="F-150"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="color">Color (optional)</Label>
              <Input
                id="color"
                value={vehicleColor}
                onChange={(e) => setVehicleColor(e.target.value)}
                placeholder="Silver"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setVinDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleVinDecode}
                disabled={decodeVIN.isPending || vehicleVin.length < 17}
              >
                {decodeVIN.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Search className="h-4 w-4 mr-2" />
                )}
                Decode VIN
              </Button>
            </div>
            {vehicleYear && vehicleMake && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setVinDialogOpen(false)}
              >
                Use Manual Entry
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Customer Picker Dialog */}
      <CustomerPicker
        open={customerPickerOpen}
        onClose={() => setCustomerPickerOpen(false)}
        onSelectCustomer={handleSelectCustomer}
        selectedCustomerId={customerId}
        onCreateNew={() => {
          setCustomerPickerOpen(false)
          navigate('/customers/new?returnTo=' + encodeURIComponent(window.location.pathname + window.location.search))
        }}
      />

      {/* Vehicle Picker Dialog */}
      <VehiclePicker
        open={vehiclePickerOpen}
        onClose={() => setVehiclePickerOpen(false)}
        customerId={customerId}
        onSelectVehicle={handleSelectVehicle}
        onAddNew={handleAddNewVehicle}
        selectedVehicleId={vehicleId}
      />

      {/* Customer Info Banner (when customer is selected) */}
      {selectedCustomer && (
        <div className="fixed bottom-20 left-0 right-0 bg-blue-50 border-t border-blue-200 px-4 py-2 flex items-center justify-between z-30">
          <div className="flex items-center gap-2">
            <User className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-blue-900">{customerName}</span>
            {vehicleId && (
              <>
                <span className="text-blue-400 mx-1">|</span>
                <Car className="h-4 w-4 text-blue-600" />
                <span className="text-blue-700">{vehicleYear} {vehicleMake} {vehicleModel}</span>
              </>
            )}
            {customerPhone && !vehicleId && (
              <span className="text-blue-600 text-sm">({customerPhone})</span>
            )}
          </div>
          <div className="flex gap-2">
            {customerId && !vehicleId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setVehiclePickerOpen(true)}
                className="text-blue-600 hover:text-blue-800"
              >
                + Vehicle
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCustomerPickerOpen(true)}
              className="text-blue-600 hover:text-blue-800"
            >
              Change
            </Button>
          </div>
        </div>
      )}

      {/* Lead Banner (when creating from lead) */}
      {leadId && !selectedCustomer && urlLead && (
        <div className="fixed bottom-20 left-0 right-0 bg-amber-50 border-t border-amber-200 px-4 py-2 flex items-center justify-between z-30">
          <div className="flex items-center gap-2">
            <UserPlus className="h-4 w-4 text-amber-600" />
            <span className="font-medium text-amber-900">
              Lead: {urlLead.first_name} {urlLead.last_name}
            </span>
            <span className="text-amber-600 text-sm">(will convert on save)</span>
          </div>
        </div>
      )}

      {/* Send to Adjuster Modal */}
      {estimateId && (
        <SendToAdjusterModal
          open={sendToAdjusterOpen}
          onClose={() => setSendToAdjusterOpen(false)}
          estimateId={estimateId}
          estimateNumber={existingEstimate?.estimate_number}
          vehicleInfo={vehicleInfoString}
          customerName={customerName}
        />
      )}

      {/* Create Supplement Modal */}
      {estimateId && (
        <CreateSupplementModal
          open={createSupplementOpen}
          onClose={() => setCreateSupplementOpen(false)}
          estimateId={estimateId}
          currentEstimateData={currentEstimateData}
        />
      )}

      {/* Create Share Link Modal */}
      {estimateId && (
        <CreateShareLinkModal
          open={createShareLinkOpen}
          onClose={() => setCreateShareLinkOpen(false)}
          estimateId={estimateId}
          estimateNumber={existingEstimate?.estimate_number}
          vehicleInfo={vehicleInfoString}
        />
      )}

      {/* Stage 7A: Keyboard Shortcuts Modal */}
      <Dialog open={shortcutsModalOpen} onOpenChange={setShortcutsModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="h-5 w-5" />
              Keyboard Shortcuts
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">Navigation</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center justify-between">
                  <span>/</span>
                  <span className="text-muted-foreground">Search panels</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Enter</span>
                  <span className="text-muted-foreground">Confirm/select</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Tab</span>
                  <span className="text-muted-foreground">Next field</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Esc</span>
                  <span className="text-muted-foreground">Close/clear</span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">Actions</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center justify-between">
                  <span>R</span>
                  <span className="text-muted-foreground">Repeat last</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>A</span>
                  <span className="text-muted-foreground">Apply to selected</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Ctrl+S</span>
                  <span className="text-muted-foreground">Save</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>?</span>
                  <span className="text-muted-foreground">Show shortcuts</span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">Multi-Select</h4>
              <div className="text-sm text-muted-foreground">
                <p>Hold <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl</kbd> or <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Cmd</kbd> and click panels to select multiple, then press <kbd className="px-1 py-0.5 bg-muted rounded text-xs">A</kbd> to apply damage settings to all.</p>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default EstimateBuilder
