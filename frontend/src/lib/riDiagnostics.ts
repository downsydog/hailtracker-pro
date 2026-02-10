/**
 * R&I Mapping Diagnostics (DEV ONLY)
 *
 * Stage 8C: Developer-only diagnostics to catch mapping mismatches between:
 * - Frontend panel -> R&I operation mappings
 * - Backend R&I catalog seeded operations
 * - Estimate-attached R&I operations
 */

import { getAllMappedOperationCodes, getPanelRelevantOperationCodes } from './riPanelSuggestions'
import type { RIOperation, EstimateRIOperationSummary } from '@/hooks/use-ri'

// ============================================================================
// TYPES
// ============================================================================

export interface MappingVsCatalogResult {
  missing_in_catalog: string[]      // Mapped codes that don't exist in backend catalog
  catalog_unmapped: string[]        // Catalog ops never suggested by any panel mapping
  stats: {
    mapped_total: number
    catalog_total: number
  }
}

export interface EstimateOpsMappingResult {
  unmapped_estimate_ops: Array<{
    code: string
    display_name?: string
  }>
}

export interface PanelDiagnosticsResult {
  invalid_codes_for_panel: string[]  // Mapped to this panel but not in catalog
  valid_codes_for_panel: string[]    // Mapped to this panel and exists in catalog
  suggestions_count: number
}

// ============================================================================
// DIAGNOSTIC FUNCTIONS
// ============================================================================

/**
 * Validate panel mappings against the backend catalog.
 * Returns codes that are mapped but missing in catalog, and catalog ops that are never mapped.
 */
export function validatePanelMappingAgainstCatalog(
  catalogOps: RIOperation[] | undefined,
  mappedCodes?: Set<string>
): MappingVsCatalogResult {
  // Get all mapped codes from frontend
  const allMappedCodes = mappedCodes || getAllMappedOperationCodes()

  // Build set of catalog codes
  const catalogCodes = new Set<string>()
  if (catalogOps) {
    for (const op of catalogOps) {
      catalogCodes.add(op.code)
    }
  }

  // Find mapped codes missing in catalog
  const missing_in_catalog: string[] = []
  for (const code of allMappedCodes) {
    if (!catalogCodes.has(code)) {
      missing_in_catalog.push(code)
    }
  }

  // Find catalog ops never mapped to any panel
  const catalog_unmapped: string[] = []
  for (const code of catalogCodes) {
    if (!allMappedCodes.has(code)) {
      catalog_unmapped.push(code)
    }
  }

  return {
    missing_in_catalog,
    catalog_unmapped,
    stats: {
      mapped_total: allMappedCodes.size,
      catalog_total: catalogCodes.size
    }
  }
}

/**
 * Find estimate R&I operations that are not mapped to any panel.
 * These could have been added manually or from an expanded catalog.
 */
export function validateEstimateOpsMappedToPanels(
  estimateOps: EstimateRIOperationSummary[] | undefined
): EstimateOpsMappingResult {
  if (!estimateOps || estimateOps.length === 0) {
    return { unmapped_estimate_ops: [] }
  }

  const allMappedCodes = getAllMappedOperationCodes()
  const unmapped_estimate_ops: Array<{ code: string; display_name?: string }> = []

  for (const op of estimateOps) {
    if (!allMappedCodes.has(op.code)) {
      unmapped_estimate_ops.push({
        code: op.code,
        display_name: op.display_name
      })
    }
  }

  return { unmapped_estimate_ops }
}

/**
 * Get diagnostics for a specific panel's R&I suggestions.
 * Shows which suggested codes are valid (in catalog) vs invalid (missing).
 */
export function getPanelSuggestionsDiagnostics(
  panelKey: string,
  catalogOps: RIOperation[] | undefined
): PanelDiagnosticsResult {
  // Get codes mapped to this panel
  const panelCodes = getPanelRelevantOperationCodes(panelKey)

  // Build catalog code set
  const catalogCodes = new Set<string>()
  if (catalogOps) {
    for (const op of catalogOps) {
      catalogCodes.add(op.code)
    }
  }

  const invalid_codes_for_panel: string[] = []
  const valid_codes_for_panel: string[] = []

  for (const code of panelCodes) {
    if (catalogCodes.has(code)) {
      valid_codes_for_panel.push(code)
    } else {
      invalid_codes_for_panel.push(code)
    }
  }

  return {
    invalid_codes_for_panel,
    valid_codes_for_panel,
    suggestions_count: panelCodes.size
  }
}

// ============================================================================
// LOCALSTORAGE KEY
// ============================================================================

export const RI_DIAGNOSTICS_STORAGE_KEY = 'hailtracker.dev.riDiagnostics'

/**
 * Get saved diagnostics toggle state from localStorage.
 */
export function getDiagnosticsEnabled(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return localStorage.getItem(RI_DIAGNOSTICS_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

/**
 * Save diagnostics toggle state to localStorage.
 */
export function setDiagnosticsEnabled(enabled: boolean): void {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(RI_DIAGNOSTICS_STORAGE_KEY, enabled ? 'true' : 'false')
  } catch {
    // Ignore storage errors
  }
}
