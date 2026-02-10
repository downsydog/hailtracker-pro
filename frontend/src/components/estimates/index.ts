/**
 * Estimates Components
 * Mobile Tech RX style PDR/Hail estimating components
 */

// Vehicle Diagram
export { VehicleDiagram, VEHICLE_PANELS } from './VehicleDiagram/VehicleDiagram'
export type { VehicleType, PanelState, PanelClickEvent, PanelClickWithModifiers } from './VehicleDiagram/VehicleDiagram'
export { CarSvg } from './VehicleDiagram/CarSvg'
export { TruckSvg } from './VehicleDiagram/TruckSvg'
export { SuvSvg } from './VehicleDiagram/SuvSvg'

// Panel Entry
export { PanelEntryModal, COUNT_RANGES, DENT_SIZES } from './PanelEntry/PanelEntryModal'
export type { PanelDamage, CountRange, DentSize } from './PanelEntry/PanelEntryModal'

// Panel List
export { PanelListSidebar } from './PanelList/PanelListSidebar'

// Bottom Nav
export { EstimateBottomNav } from './BottomNav/EstimateBottomNav'
export type { ServiceTab } from './BottomNav/EstimateBottomNav'

// Customer Picker
export { CustomerPicker } from './CustomerPicker/CustomerPicker'

// Vehicle Picker
export { VehiclePicker } from './VehiclePicker/VehiclePicker'

// Quick Entry
export { QuickEntryOverlay } from './QuickEntry/QuickEntryOverlay'
export type { QuickEntryValue, Depth, Zone } from './QuickEntry/QuickEntryOverlay'

// Status Bar
export { EstimateStatusBar } from './EstimateStatusBar'
export type { SaveStatus } from './EstimateStatusBar'

// Send to Adjuster Modal
export { SendToAdjusterModal } from './SendToAdjusterModal'

// Create Supplement Modal
export { CreateSupplementModal } from './CreateSupplementModal'

// Create Share Link Modal
export { CreateShareLinkModal } from './CreateShareLinkModal'

// Signature Capture
export { SignatureCapture, SignatureDisplay } from './SignatureCapture'
export type { SignatureCaptureRef } from './SignatureCapture'

// Insurer Approval
export { InsurerApprovalModal } from './InsurerApprovalModal'
export type { InsurerApprovalData } from './InsurerApprovalModal'
export { InsuranceApprovalDisplay, InsuranceApprovalBadge } from './InsuranceApprovalDisplay'
