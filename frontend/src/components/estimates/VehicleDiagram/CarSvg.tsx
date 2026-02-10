/**
 * Car SVG - Top-down bird's eye view of a sedan
 * Each panel is a clickable/tappable region
 * Supports mobile long-press for batch selection
 * Supports severity heat map visualization
 */

import { useRef, useCallback } from 'react'
import { getSeverityFillColor, type SeverityLevel } from './severity'

// Long-press configuration
const LONG_PRESS_DURATION = 450 // ms
const MOVE_THRESHOLD = 10 // pixels - movement beyond this cancels long-press

interface PanelProps {
  id: string
  label: string
  d: string
  labelX: number
  labelY: number
  selected: boolean      // Primary panel being edited
  damaged: boolean       // Has damage data
  conventional: boolean  // Conventional repair
  batchSelected?: boolean // Part of batch selection
  severityLevel?: SeverityLevel // Heat map intensity (0-4)
  badgeText?: string     // Optional badge text
  onClick: () => void
  onLongPress: () => void
}

const Panel = ({ id, label, d, labelX, labelY, selected, damaged, conventional, batchSelected, severityLevel = 0, badgeText, onClick, onLongPress }: PanelProps) => {
  // Long-press detection refs
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const touchStartPosRef = useRef<{ x: number; y: number } | null>(null)
  const didLongPressRef = useRef(false)

  // Clear long-press timer
  const clearLongPress = useCallback(() => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current)
      longPressTimerRef.current = null
    }
  }, [])

  // Handle touch start - begin long-press timer
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0]
    touchStartPosRef.current = { x: touch.clientX, y: touch.clientY }
    didLongPressRef.current = false

    longPressTimerRef.current = setTimeout(() => {
      didLongPressRef.current = true
      onLongPress()
      // Vibrate on mobile if available
      if (navigator.vibrate) {
        navigator.vibrate(50)
      }
    }, LONG_PRESS_DURATION)
  }, [onLongPress])

  // Handle touch move - cancel if moved beyond threshold
  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartPosRef.current) return

    const touch = e.touches[0]
    const dx = touch.clientX - touchStartPosRef.current.x
    const dy = touch.clientY - touchStartPosRef.current.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance > MOVE_THRESHOLD) {
      clearLongPress()
    }
  }, [clearLongPress])

  // Handle touch end - clear timer and handle tap if not long-pressed
  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    clearLongPress()

    // If we did a long-press, suppress the click
    if (didLongPressRef.current) {
      e.preventDefault()
      didLongPressRef.current = false
      return
    }

    // Short tap - trigger click
    // Note: We let the click event handle this naturally
  }, [clearLongPress])

  // Handle touch cancel
  const handleTouchCancel = useCallback(() => {
    clearLongPress()
    didLongPressRef.current = false
  }, [clearLongPress])

  // Handle click - suppress if long-press just occurred
  const handleClick = useCallback((e: React.MouseEvent) => {
    if (didLongPressRef.current) {
      e.preventDefault()
      e.stopPropagation()
      didLongPressRef.current = false
      return
    }
    onClick()
  }, [onClick])

  // Determine fill color based on severity heat map
  let fillColor = '#f3f4f6' // Default gray
  let strokeColor = '#9ca3af'
  let strokeWidth = 1
  let strokeDasharray = 'none'

  // Apply severity-based fill for damaged panels
  if (damaged && severityLevel > 0) {
    fillColor = getSeverityFillColor(severityLevel)
  }

  // Override styling for special states (but keep severity fill underneath)
  if (conventional) {
    fillColor = '#fecaca' // Red for conventional overrides severity
    strokeColor = '#dc2626'
    strokeWidth = 2
  } else if (selected) {
    // Primary panel - thicker outline, keep severity fill if damaged
    if (!damaged || severityLevel === 0) {
      fillColor = '#dbeafe'
    }
    strokeColor = '#1d4ed8'
    strokeWidth = 3
  } else if (batchSelected) {
    // Batch selected - purple dashed outline, keep severity fill
    if (!damaged || severityLevel === 0) {
      fillColor = '#f3e8ff'
    }
    strokeColor = '#7c3aed'
    strokeWidth = 2
    strokeDasharray = '4,2'
  } else if (damaged) {
    // Just damaged (not selected) - use severity fill, add border
    strokeColor = '#2563eb'
    strokeWidth = 2
  }

  return (
    <g
      id={id}
      onClick={handleClick}
      onContextMenu={(e) => {
        e.preventDefault()
        onLongPress()
      }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onTouchCancel={handleTouchCancel}
      style={{ cursor: 'pointer' }}
      className="transition-colors duration-150"
    >
      <path
        d={d}
        fill={fillColor}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeDasharray={strokeDasharray}
      />
      <text
        x={labelX}
        y={labelY}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="11"
        fontWeight="600"
        fill={
          conventional ? '#dc2626'
            : selected ? '#1d4ed8'
              : batchSelected ? '#7c3aed'
                : damaged ? '#2563eb'
                  : '#374151'
        }
        className="pointer-events-none select-none"
      >
        {label}
      </text>
      {/* Badge for count range (shown when damaged and has badge text) */}
      {damaged && badgeText && (
        <text
          x={labelX}
          y={labelY + 12}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="8"
          fontWeight="500"
          fill={
            conventional ? '#dc2626'
              : severityLevel >= 3 ? '#92400e' // amber-800 for heavy/severe
                : '#1e40af' // blue-800
          }
          className="pointer-events-none select-none"
        >
          {badgeText}
        </text>
      )}
    </g>
  )
}

interface CarSvgProps {
  panels: Record<string, {
    selected: boolean
    damaged: boolean
    conventional: boolean
    batchSelected?: boolean
    severityLevel?: SeverityLevel
    badgeText?: string
  }>
  onPanelClick: (panelId: string) => void
  onPanelLongPress: (panelId: string) => void
}

export function CarSvg({ panels, onPanelClick, onPanelLongPress }: CarSvgProps) {
  const getPanelState = (id: string) => panels[id] || {
    selected: false,
    damaged: false,
    conventional: false,
    batchSelected: false,
    severityLevel: 0 as SeverityLevel,
    badgeText: ''
  }

  return (
    <svg
      viewBox="0 0 300 500"
      className="w-full max-w-[300px] h-auto mx-auto"
      style={{ touchAction: 'manipulation' }}
    >
      {/* Vehicle outline */}
      <path
        d="M60 80 Q60 40 100 30 L200 30 Q240 40 240 80 L240 420 Q240 460 200 470 L100 470 Q60 460 60 420 Z"
        fill="none"
        stroke="#d1d5db"
        strokeWidth="3"
      />

      {/* HOOD */}
      <Panel
        id="hood"
        label="HOOD"
        d="M70 50 Q70 35 100 30 L200 30 Q230 35 230 50 L230 120 L70 120 Z"
        labelX={150}
        labelY={75}
        {...getPanelState('hood')}
        onClick={() => onPanelClick('hood')}
        onLongPress={() => onPanelLongPress('hood')}
      />

      {/* LEFT FRONT FENDER */}
      <Panel
        id="lff"
        label="LFF"
        d="M60 50 L70 50 L70 140 L60 140 Q50 140 50 110 L50 80 Q50 50 60 50"
        labelX={60}
        labelY={95}
        {...getPanelState('lff')}
        onClick={() => onPanelClick('lff')}
        onLongPress={() => onPanelLongPress('lff')}
      />

      {/* RIGHT FRONT FENDER */}
      <Panel
        id="rff"
        label="RFF"
        d="M230 50 L240 50 Q250 50 250 80 L250 110 Q250 140 240 140 L230 140 L230 50"
        labelX={240}
        labelY={95}
        {...getPanelState('rff')}
        onClick={() => onPanelClick('rff')}
        onLongPress={() => onPanelLongPress('rff')}
      />

      {/* LEFT FRONT DOOR */}
      <Panel
        id="lfd"
        label="LFD"
        d="M60 145 L70 145 L70 230 L60 230 L60 145"
        labelX={65}
        labelY={187}
        {...getPanelState('lfd')}
        onClick={() => onPanelClick('lfd')}
        onLongPress={() => onPanelLongPress('lfd')}
      />

      {/* RIGHT FRONT DOOR */}
      <Panel
        id="rfd"
        label="RFD"
        d="M230 145 L240 145 L240 230 L230 230 L230 145"
        labelX={235}
        labelY={187}
        {...getPanelState('rfd')}
        onClick={() => onPanelClick('rfd')}
        onLongPress={() => onPanelLongPress('rfd')}
      />

      {/* LEFT REAR DOOR */}
      <Panel
        id="lrd"
        label="LRD"
        d="M60 235 L70 235 L70 320 L60 320 L60 235"
        labelX={65}
        labelY={277}
        {...getPanelState('lrd')}
        onClick={() => onPanelClick('lrd')}
        onLongPress={() => onPanelLongPress('lrd')}
      />

      {/* RIGHT REAR DOOR */}
      <Panel
        id="rrd"
        label="RRD"
        d="M230 235 L240 235 L240 320 L230 320 L230 235"
        labelX={235}
        labelY={277}
        {...getPanelState('rrd')}
        onClick={() => onPanelClick('rrd')}
        onLongPress={() => onPanelLongPress('rrd')}
      />

      {/* LEFT ROOF RAIL */}
      <Panel
        id="lrail"
        label="L RAIL"
        d="M70 125 L85 125 L85 340 L70 340 L70 125"
        labelX={77}
        labelY={232}
        {...getPanelState('lrail')}
        onClick={() => onPanelClick('lrail')}
        onLongPress={() => onPanelLongPress('lrail')}
      />

      {/* RIGHT ROOF RAIL */}
      <Panel
        id="rrail"
        label="R RAIL"
        d="M215 125 L230 125 L230 340 L215 340 L215 125"
        labelX={222}
        labelY={232}
        {...getPanelState('rrail')}
        onClick={() => onPanelClick('rrail')}
        onLongPress={() => onPanelLongPress('rrail')}
      />

      {/* ROOF */}
      <Panel
        id="roof"
        label="ROOF"
        d="M90 130 L210 130 L210 335 L90 335 Z"
        labelX={150}
        labelY={232}
        {...getPanelState('roof')}
        onClick={() => onPanelClick('roof')}
        onLongPress={() => onPanelLongPress('roof')}
      />

      {/* LEFT QUARTER */}
      <Panel
        id="lq"
        label="LQ"
        d="M60 325 L70 325 L70 420 Q70 440 60 440 L60 325"
        labelX={65}
        labelY={375}
        {...getPanelState('lq')}
        onClick={() => onPanelClick('lq')}
        onLongPress={() => onPanelLongPress('lq')}
      />

      {/* RIGHT QUARTER */}
      <Panel
        id="rq"
        label="RQ"
        d="M230 325 L240 325 L240 440 Q230 440 230 420 L230 325"
        labelX={235}
        labelY={375}
        {...getPanelState('rq')}
        onClick={() => onPanelClick('rq')}
        onLongPress={() => onPanelLongPress('rq')}
      />

      {/* DECK LID / TRUNK */}
      <Panel
        id="deck"
        label="DECK"
        d="M70 345 L230 345 L230 450 Q230 465 200 470 L100 470 Q70 465 70 450 Z"
        labelX={150}
        labelY={410}
        {...getPanelState('deck')}
        onClick={() => onPanelClick('deck')}
        onLongPress={() => onPanelLongPress('deck')}
      />

      {/* Windshield (non-interactive) */}
      <path
        d="M85 120 L215 120 L215 130 L85 130 Z"
        fill="#e5e7eb"
        stroke="#9ca3af"
        strokeWidth="1"
      />

      {/* Rear window (non-interactive) */}
      <path
        d="M85 335 L215 335 L215 345 L85 345 Z"
        fill="#e5e7eb"
        stroke="#9ca3af"
        strokeWidth="1"
      />

      {/* Direction indicator (front) */}
      <polygon
        points="150,15 145,25 155,25"
        fill="#9ca3af"
      />
      <text x="150" y="10" textAnchor="middle" fontSize="8" fill="#6b7280">FRONT</text>
    </svg>
  )
}

export default CarSvg
