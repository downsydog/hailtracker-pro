/**
 * R&I Access Heuristics (Stage 8E)
 *
 * Smart selection rules for suggesting R&I operations based on:
 * - Panel type (roof, hood, door, etc.)
 * - Damage severity (dent count, size)
 * - Common PDR access patterns
 *
 * Uses only the 12 seeded operations from the backend catalog.
 */

// ============================================================================
// CONSTANTS
// ============================================================================

// Threshold for "heavy" damage requiring extended access
const HEAVY_DAMAGE_THRESHOLD = 20 // dent count

// ============================================================================
// TYPES
// ============================================================================

export interface PanelDamageContext {
  panelName: string
  dentCount: number       // Derived from countRange
  dentSize?: string       // 'dime' | 'nickel' | 'quarter' | 'half'
  oversizedCount?: number
  hasSunroof?: boolean    // Optional vehicle feature flag
}

export interface SuggestedRiOp {
  code: string
  label: string
  description?: string
  reason: string          // Why this op is suggested
  priority: number        // Lower = more important (for sorting)
}

// ============================================================================
// REASON STRINGS
// ============================================================================

const REASONS = {
  // Roof
  ROOF_DENTS: 'Roof dents require headliner access',
  HEAVY_ROOF: 'Heavy roof damage requires pillar trim removal',
  SUNROOF_PRESENT: 'Sunroof must be removed for full roof access',
  SEATBELT_HEAVY: 'Seatbelt anchors must be released for heavy roof work',

  // Hood
  HOOD_DENTS: 'Hood dents require liner removal',

  // Trunk/Rear
  TRUNK_DENTS: 'Trunk/decklid damage requires interior trim removal',
  REAR_AREA: 'Rear panel access commonly requires taillight removal',
  REAR_PACKAGE: 'Rear package tray removal for quarter/trunk access',

  // Door
  DOOR_DENTS: 'Door dents require interior panel removal',

  // Quarter
  QUARTER_ACCESS: 'Quarter panel access requires trim removal',
  QUARTER_TAILLIGHT: 'Quarter panel proximity requires taillight removal',

  // Generic
  PILLAR_ACCESS: 'Pillar trim removal for extended access',
} as const

// ============================================================================
// HEURISTIC FUNCTIONS
// ============================================================================

/**
 * Check if panel name matches a keyword (case-insensitive).
 */
function panelMatches(panelName: string, ...keywords: string[]): boolean {
  const normalized = panelName.toLowerCase()
  return keywords.some(k => normalized.includes(k))
}

/**
 * Determine if this is "heavy" damage requiring extended access.
 */
function isHeavyDamage(ctx: PanelDamageContext): boolean {
  return ctx.dentCount >= HEAVY_DAMAGE_THRESHOLD || (ctx.oversizedCount ?? 0) > 0
}

/**
 * Get smart suggestions for a panel based on damage context.
 * Returns prioritized list with reasons.
 */
export function getSuggestedRiOpsForPanel(
  ctx: PanelDamageContext,
  alreadyAddedCodes: Set<string>
): SuggestedRiOp[] {
  const suggestions: SuggestedRiOp[] = []
  const addedCodes = new Set<string>()

  // Helper to add suggestion if not already added to estimate
  const addSuggestion = (
    code: string,
    label: string,
    reason: string,
    priority: number,
    description?: string
  ) => {
    if (!alreadyAddedCodes.has(code) && !addedCodes.has(code)) {
      suggestions.push({ code, label, reason, priority, description })
      addedCodes.add(code)
    }
  }

  // No dents = no suggestions (except for explicit user request)
  if (ctx.dentCount === 0) {
    return []
  }

  const panelName = ctx.panelName.toLowerCase()
  const isHeavy = isHeavyDamage(ctx)

  // =========================================================================
  // ROOF HEURISTICS
  // =========================================================================
  if (panelMatches(panelName, 'roof', 'cab')) {
    // Always suggest headliner for roof dents
    addSuggestion(
      'RI_HEADLINER_REMOVAL',
      'Headliner Removal',
      REASONS.ROOF_DENTS,
      1,
      'Remove headliner for roof access'
    )

    // Heavy damage = pillars + seatbelt
    if (isHeavy) {
      addSuggestion('RI_A_PILLAR_TRIM', 'A-Pillar Trim', REASONS.HEAVY_ROOF, 2)
      addSuggestion('RI_B_PILLAR_TRIM', 'B-Pillar Trim', REASONS.HEAVY_ROOF, 2)
      addSuggestion('RI_C_PILLAR_TRIM', 'C-Pillar Trim', REASONS.HEAVY_ROOF, 2)
      addSuggestion('RI_SEATBELT_ANCHOR', 'Seatbelt Anchor', REASONS.SEATBELT_HEAVY, 3)
    }

    // Sunroof if flagged
    if (ctx.hasSunroof) {
      addSuggestion('RI_SUNROOF_ASSEMBLY', 'Sunroof Assembly', REASONS.SUNROOF_PRESENT, 2)
    }
  }

  // =========================================================================
  // HOOD HEURISTICS
  // =========================================================================
  if (panelMatches(panelName, 'hood')) {
    addSuggestion(
      'RI_HOOD_LINER',
      'Hood Liner',
      REASONS.HOOD_DENTS,
      1,
      'Remove hood insulation liner'
    )
  }

  // =========================================================================
  // TRUNK / DECKLID HEURISTICS
  // =========================================================================
  if (panelMatches(panelName, 'trunk', 'decklid', 'deck', 'lid')) {
    addSuggestion(
      'RI_TRUNK_TRIM',
      'Trunk Trim',
      REASONS.TRUNK_DENTS,
      1,
      'Remove trunk interior trim'
    )
    addSuggestion(
      'RI_TAILLIGHT_ASSEMBLY',
      'Taillight Assembly',
      REASONS.REAR_AREA,
      2,
      'Remove taillight for access'
    )
  }

  // =========================================================================
  // DOOR HEURISTICS
  // =========================================================================
  if (panelMatches(panelName, 'door')) {
    addSuggestion(
      'RI_DOOR_PANEL',
      'Door Panel',
      REASONS.DOOR_DENTS,
      1,
      'Remove door interior panel'
    )
  }

  // =========================================================================
  // QUARTER PANEL HEURISTICS
  // =========================================================================
  if (panelMatches(panelName, 'quarter', 'qtr')) {
    addSuggestion(
      'RI_C_PILLAR_TRIM',
      'C-Pillar Trim',
      REASONS.QUARTER_ACCESS,
      1,
      'Remove C-pillar trim panels'
    )
    addSuggestion(
      'RI_TAILLIGHT_ASSEMBLY',
      'Taillight Assembly',
      REASONS.QUARTER_TAILLIGHT,
      2,
      'Remove taillight for access'
    )
    addSuggestion(
      'RI_TRUNK_TRIM',
      'Trunk Trim',
      REASONS.REAR_PACKAGE,
      2,
      'Remove trunk interior trim'
    )

    // Heavy quarter = rear package tray
    if (isHeavy) {
      addSuggestion(
        'RI_REAR_PACKAGE_TRAY',
        'Rear Package Tray',
        REASONS.REAR_PACKAGE,
        3,
        'Remove rear package shelf'
      )
    }
  }

  // =========================================================================
  // PILLAR HEURISTICS (explicit pillar selection)
  // =========================================================================
  if (panelMatches(panelName, 'pillar')) {
    if (panelMatches(panelName, 'a-pillar', 'a_pillar', 'a pillar')) {
      addSuggestion('RI_A_PILLAR_TRIM', 'A-Pillar Trim', REASONS.PILLAR_ACCESS, 1)
    }
    if (panelMatches(panelName, 'b-pillar', 'b_pillar', 'b pillar')) {
      addSuggestion('RI_B_PILLAR_TRIM', 'B-Pillar Trim', REASONS.PILLAR_ACCESS, 1)
    }
    if (panelMatches(panelName, 'c-pillar', 'c_pillar', 'c pillar')) {
      addSuggestion('RI_C_PILLAR_TRIM', 'C-Pillar Trim', REASONS.PILLAR_ACCESS, 1)
    }
    // Generic pillar = all trims
    if (!panelMatches(panelName, 'a-', 'b-', 'c-', 'a_', 'b_', 'c_')) {
      addSuggestion('RI_A_PILLAR_TRIM', 'A-Pillar Trim', REASONS.PILLAR_ACCESS, 1)
      addSuggestion('RI_B_PILLAR_TRIM', 'B-Pillar Trim', REASONS.PILLAR_ACCESS, 1)
      addSuggestion('RI_C_PILLAR_TRIM', 'C-Pillar Trim', REASONS.PILLAR_ACCESS, 1)
    }
    addSuggestion('RI_SEATBELT_ANCHOR', 'Seatbelt Anchor', REASONS.SEATBELT_HEAVY, 2)
  }

  // Sort by priority
  suggestions.sort((a, b) => a.priority - b.priority)

  return suggestions
}

/**
 * Get total hours for suggested operations from catalog.
 */
export function getSuggestedTotalHours(
  suggestions: SuggestedRiOp[],
  catalogOps: Array<{ code: string; steps?: Array<{ base_time_hours: number }> }> | undefined
): number {
  if (!catalogOps) return 0

  let total = 0
  for (const suggestion of suggestions) {
    const catalogOp = catalogOps.find(op => op.code === suggestion.code)
    if (catalogOp?.steps) {
      total += catalogOp.steps.reduce((sum, step) => sum + (step.base_time_hours || 0), 0)
    }
  }
  return total
}

/**
 * Convert count range string to number (middleware).
 */
export function countRangeToNumber(countRange: string | null): number {
  if (!countRange) return 0
  const ranges: Record<string, number> = {
    '1-5': 3,
    '6-15': 10,
    '16-30': 23,
    '31-50': 40,
    '51-75': 63,
    '76-100': 88,
    '101+': 120
  }
  return ranges[countRange] || 0
}
