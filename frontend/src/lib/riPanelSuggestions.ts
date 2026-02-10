/**
 * Panel-Driven R&I Suggestions
 *
 * Stage 7D: Maps vehicle panels to suggested R&I operations.
 * When the estimator is working a panel, these suggestions appear
 * so they can add R&I operations with one click.
 */

export interface RISuggestion {
  code: string
  label: string
  description?: string
}

// Panel name keywords to R&I operations mapping
// IMPORTANT: Only includes operations that are seeded in the backend catalog
const PANEL_RI_MAPPINGS: Record<string, RISuggestion[]> = {
  // Roof panels
  roof: [
    { code: 'RI_HEADLINER_REMOVAL', label: 'Headliner Removal', description: 'Remove headliner for roof access' },
    { code: 'RI_A_PILLAR_TRIM', label: 'A-Pillar Trim', description: 'Remove A-pillar trim panels' },
    { code: 'RI_B_PILLAR_TRIM', label: 'B-Pillar Trim', description: 'Remove B-pillar trim panels' },
    { code: 'RI_C_PILLAR_TRIM', label: 'C-Pillar Trim', description: 'Remove C-pillar trim panels' },
    { code: 'RI_SUNROOF_ASSEMBLY', label: 'Sunroof Assembly', description: 'R&I sunroof components' },
    { code: 'RI_SEATBELT_ANCHOR', label: 'Seatbelt Anchor', description: 'Seatbelt anchor point removal' },
  ],

  // Quarter panels
  quarter: [
    { code: 'RI_TAILLIGHT_ASSEMBLY', label: 'Taillight Assembly', description: 'Remove taillight for access' },
    { code: 'RI_TRUNK_TRIM', label: 'Trunk Trim', description: 'Remove trunk interior trim' },
    { code: 'RI_REAR_PACKAGE_TRAY', label: 'Rear Package Tray', description: 'Remove rear package shelf' },
    { code: 'RI_C_PILLAR_TRIM', label: 'C-Pillar Trim', description: 'Remove C-pillar trim panels' },
  ],

  // Door panels
  door: [
    { code: 'RI_DOOR_PANEL', label: 'Door Panel', description: 'Remove door interior panel' },
  ],

  // Trunk/Decklid
  trunk: [
    { code: 'RI_TRUNK_TRIM', label: 'Trunk Trim', description: 'Remove trunk interior trim' },
    { code: 'RI_TAILLIGHT_ASSEMBLY', label: 'Taillight Assembly', description: 'Remove taillight for access' },
  ],
  decklid: [
    { code: 'RI_TRUNK_TRIM', label: 'Trunk Trim', description: 'Remove trunk interior trim' },
  ],

  // Hood
  hood: [
    { code: 'RI_HOOD_LINER', label: 'Hood Liner', description: 'Remove hood insulation liner' },
  ],

  // Pillar-specific
  pillar: [
    { code: 'RI_A_PILLAR_TRIM', label: 'A-Pillar Trim', description: 'Remove A-pillar trim panels' },
    { code: 'RI_B_PILLAR_TRIM', label: 'B-Pillar Trim', description: 'Remove B-pillar trim panels' },
    { code: 'RI_C_PILLAR_TRIM', label: 'C-Pillar Trim', description: 'Remove C-pillar trim panels' },
    { code: 'RI_SEATBELT_ANCHOR', label: 'Seatbelt Anchor', description: 'Seatbelt anchor point removal' },
  ],

  // Cab (trucks) - uses headliner
  cab: [
    { code: 'RI_HEADLINER_REMOVAL', label: 'Headliner Removal', description: 'Remove headliner for roof access' },
  ],

  // Seat
  seat: [
    { code: 'RI_SEAT_REMOVAL', label: 'Seat Removal', description: 'Remove front or rear seat assembly' },
    { code: 'RI_SEATBELT_ANCHOR', label: 'Seatbelt Anchor', description: 'Seatbelt anchor point removal' },
  ],
}

/**
 * Get R&I suggestions for a given panel name or code.
 * Uses keyword matching to find relevant R&I operations.
 */
export function getRiSuggestionsForPanel(panelNameOrCode: string): RISuggestion[] {
  if (!panelNameOrCode) return []

  const normalized = panelNameOrCode.toLowerCase().trim()
  const suggestions: RISuggestion[] = []
  const seenCodes = new Set<string>()

  // Check each mapping key for matches
  for (const [keyword, ops] of Object.entries(PANEL_RI_MAPPINGS)) {
    if (normalized.includes(keyword) || keyword.includes(normalized)) {
      for (const op of ops) {
        if (!seenCodes.has(op.code)) {
          suggestions.push(op)
          seenCodes.add(op.code)
        }
      }
    }
  }

  // Special cases for compound panel names
  if (normalized.includes('front') && normalized.includes('door')) {
    // Already covered by 'door' keyword
  }
  if (normalized.includes('rear') && normalized.includes('door')) {
    // Already covered by 'door' keyword
  }
  if (normalized.includes('left') || normalized.includes('right')) {
    // Side doesn't change suggestions
  }

  return suggestions
}

/**
 * Get a short display label for a panel (for UI)
 */
export function getPanelDisplayName(panelId: string): string {
  // Convert panel ID to display name
  // e.g., 'left_front_door' -> 'Left Front Door'
  return panelId
    .split(/[_-]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export default getRiSuggestionsForPanel
