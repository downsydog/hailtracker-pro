/**
 * Severity Computation for Panel Damage
 *
 * Computes a severity score and level based on:
 * - Count range (primary driver)
 * - Dent size
 * - Depth
 * - Zone
 *
 * Returns severity level 0-4 for heat map visualization.
 */

import type { CountRange, DentSize } from '../PanelEntry/PanelEntryModal'

export type Depth = 'shallow' | 'medium' | 'deep' | 'severe'
export type Zone = 'center' | 'edge' | 'crease' | 'body_line'

export type SeverityLevel = 0 | 1 | 2 | 3 | 4

export interface SeverityResult {
  score: number
  level: SeverityLevel
  badgeText: string
}

// Count range weights (primary driver, doubled in score)
const COUNT_WEIGHTS: Record<CountRange, number> = {
  '1-5': 1,
  '6-15': 2,
  '16-30': 3,
  '31-50': 4,
  '51-75': 5,
  '76-100': 6,
  '101+': 7
}

// Size weights
const SIZE_WEIGHTS: Record<DentSize, number> = {
  'dime': 0,
  'nickel': 1,
  'quarter': 2,
  'half': 3
}

// Depth weights
const DEPTH_WEIGHTS: Record<Depth, number> = {
  'shallow': 0,
  'medium': 1,
  'deep': 2,
  'severe': 3
}

// Zone weights
const ZONE_WEIGHTS: Record<Zone, number> = {
  'center': 0,
  'edge': 1,
  'crease': 2,
  'body_line': 3
}

// Badge text shorthand for count ranges
const COUNT_BADGE: Record<CountRange, string> = {
  '1-5': '1-5',
  '6-15': '6-15',
  '16-30': '16-30',
  '31-50': '31-50',
  '51-75': '51-75',
  '76-100': '76+',
  '101+': '100+'
}

/**
 * Compute severity for a panel based on damage data
 */
export function computeSeverity(data: {
  countRange: CountRange | null
  dentSize: DentSize | null
  depth?: Depth | null
  zone?: Zone | null
}): SeverityResult {
  // No damage = level 0
  if (!data.countRange || !data.dentSize) {
    return { score: 0, level: 0, badgeText: '' }
  }

  // Compute weighted score
  const countWeight = COUNT_WEIGHTS[data.countRange] || 0
  const sizeWeight = SIZE_WEIGHTS[data.dentSize] || 0
  const depthWeight = data.depth ? (DEPTH_WEIGHTS[data.depth] || 0) : 1 // default medium
  const zoneWeight = data.zone ? (ZONE_WEIGHTS[data.zone] || 0) : 0 // default center

  // Score formula: count*2 + size + depth + zone
  const score = (countWeight * 2) + sizeWeight + depthWeight + zoneWeight

  // Map score to severity level
  let level: SeverityLevel
  if (score === 0) {
    level = 0
  } else if (score <= 5) {
    level = 1 // light
  } else if (score <= 10) {
    level = 2 // medium
  } else if (score <= 15) {
    level = 3 // heavy
  } else {
    level = 4 // severe
  }

  // Badge text (count range shorthand)
  const badgeText = COUNT_BADGE[data.countRange] || ''

  return { score, level, badgeText }
}

/**
 * Get severity color for heat map fill
 * Returns semi-transparent colors that work with selection outlines
 */
export function getSeverityFillColor(level: SeverityLevel): string {
  switch (level) {
    case 0:
      return '#f3f4f6' // gray-100, no damage
    case 1:
      return '#dbeafe' // blue-100, light
    case 2:
      return '#93c5fd' // blue-300, medium
    case 3:
      return '#f59e0b' // amber-500, heavy
    case 4:
      return '#ef4444' // red-500, severe
    default:
      return '#f3f4f6'
  }
}

/**
 * Get severity label for legend
 */
export function getSeverityLabel(level: SeverityLevel): string {
  switch (level) {
    case 0:
      return 'None'
    case 1:
      return 'Light'
    case 2:
      return 'Medium'
    case 3:
      return 'Heavy'
    case 4:
      return 'Severe'
    default:
      return 'None'
  }
}

export default computeSeverity
