/**
 * Truck SVG - Top-down bird's eye view of a pickup truck
 * Includes bed side panels (LBS, RBS) and tailgate
 * Supports mobile long-press for batch selection
 * Supports severity heat map visualization
 */

import { useRef, useCallback } from 'react'
import { getSeverityFillColor, type SeverityLevel } from './severity'

// Long-press configuration
const LONG_PRESS_DURATION = 450 // ms
const MOVE_THRESHOLD = 10 // pixels

interface PanelProps {
  id: string
  label: string
  d: string
  labelX: number
  labelY: number
  selected: boolean
  damaged: boolean
  conventional: boolean
  batchSelected?: boolean
  severityLevel?: SeverityLevel
  badgeText?: string
  onClick: () => void
  onLongPress: () => void
}

const Panel = ({ id, label, d, labelX, labelY, selected, damaged, conventional, batchSelected, severityLevel = 0, badgeText, onClick, onLongPress }: PanelProps) => {
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const touchStartPosRef = useRef<{ x: number; y: number } | null>(null)
  const didLongPressRef = useRef(false)

  const clearLongPress = useCallback(() => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current)
      longPressTimerRef.current = null
    }
  }, [])

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0]
    touchStartPosRef.current = { x: touch.clientX, y: touch.clientY }
    didLongPressRef.current = false

    longPressTimerRef.current = setTimeout(() => {
      didLongPressRef.current = true
      onLongPress()
      if (navigator.vibrate) navigator.vibrate(50)
    }, LONG_PRESS_DURATION)
  }, [onLongPress])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartPosRef.current) return
    const touch = e.touches[0]
    const dx = touch.clientX - touchStartPosRef.current.x
    const dy = touch.clientY - touchStartPosRef.current.y
    if (Math.sqrt(dx * dx + dy * dy) > MOVE_THRESHOLD) {
      clearLongPress()
    }
  }, [clearLongPress])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    clearLongPress()
    if (didLongPressRef.current) {
      e.preventDefault()
      didLongPressRef.current = false
      return
    }
  }, [clearLongPress])

  const handleTouchCancel = useCallback(() => {
    clearLongPress()
    didLongPressRef.current = false
  }, [clearLongPress])

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
  let fillColor = '#f3f4f6'
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
        fontSize="10"
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
          y={labelY + 11}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="7"
          fontWeight="500"
          fill={
            conventional ? '#dc2626'
              : severityLevel >= 3 ? '#92400e'
                : '#1e40af'
          }
          className="pointer-events-none select-none"
        >
          {badgeText}
        </text>
      )}
    </g>
  )
}

interface TruckSvgProps {
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

export function TruckSvg({ panels, onPanelClick, onPanelLongPress }: TruckSvgProps) {
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
      viewBox="0 0 300 600"
      className="w-full max-w-[300px] h-auto mx-auto"
      style={{ touchAction: 'manipulation' }}
    >
      {/* Cab outline */}
      <path
        d="M60 80 Q60 40 100 30 L200 30 Q240 40 240 80 L240 280 L60 280 Z"
        fill="none"
        stroke="#d1d5db"
        strokeWidth="3"
      />

      {/* Bed outline */}
      <path
        d="M50 290 L250 290 L250 550 Q250 570 230 570 L70 570 Q50 570 50 550 Z"
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
        d="M60 145 L70 145 L70 220 L60 220 L60 145"
        labelX={65}
        labelY={182}
        {...getPanelState('lfd')}
        onClick={() => onPanelClick('lfd')}
        onLongPress={() => onPanelLongPress('lfd')}
      />

      {/* RIGHT FRONT DOOR */}
      <Panel
        id="rfd"
        label="RFD"
        d="M230 145 L240 145 L240 220 L230 220 L230 145"
        labelX={235}
        labelY={182}
        {...getPanelState('rfd')}
        onClick={() => onPanelClick('rfd')}
        onLongPress={() => onPanelLongPress('rfd')}
      />

      {/* LEFT REAR DOOR (Crew Cab) */}
      <Panel
        id="lrd"
        label="LRD"
        d="M60 225 L70 225 L70 280 L60 280 L60 225"
        labelX={65}
        labelY={252}
        {...getPanelState('lrd')}
        onClick={() => onPanelClick('lrd')}
        onLongPress={() => onPanelLongPress('lrd')}
      />

      {/* RIGHT REAR DOOR (Crew Cab) */}
      <Panel
        id="rrd"
        label="RRD"
        d="M230 225 L240 225 L240 280 L230 280 L230 225"
        labelX={235}
        labelY={252}
        {...getPanelState('rrd')}
        onClick={() => onPanelClick('rrd')}
        onLongPress={() => onPanelLongPress('rrd')}
      />

      {/* LEFT ROOF RAIL */}
      <Panel
        id="lrail"
        label="L RAIL"
        d="M70 125 L85 125 L85 265 L70 265 L70 125"
        labelX={77}
        labelY={195}
        {...getPanelState('lrail')}
        onClick={() => onPanelClick('lrail')}
        onLongPress={() => onPanelLongPress('lrail')}
      />

      {/* RIGHT ROOF RAIL */}
      <Panel
        id="rrail"
        label="R RAIL"
        d="M215 125 L230 125 L230 265 L215 265 L215 125"
        labelX={222}
        labelY={195}
        {...getPanelState('rrail')}
        onClick={() => onPanelClick('rrail')}
        onLongPress={() => onPanelLongPress('rrail')}
      />

      {/* ROOF (Cab) */}
      <Panel
        id="roof"
        label="ROOF"
        d="M90 130 L210 130 L210 260 L90 260 Z"
        labelX={150}
        labelY={195}
        {...getPanelState('roof')}
        onClick={() => onPanelClick('roof')}
        onLongPress={() => onPanelLongPress('roof')}
      />

      {/* LEFT BED SIDE */}
      <Panel
        id="lbs"
        label="L BEDSIDE"
        d="M50 295 L65 295 L65 545 Q65 555 55 555 L50 555 L50 295"
        labelX={57}
        labelY={425}
        {...getPanelState('lbs')}
        onClick={() => onPanelClick('lbs')}
        onLongPress={() => onPanelLongPress('lbs')}
      />

      {/* RIGHT BED SIDE */}
      <Panel
        id="rbs"
        label="R BEDSIDE"
        d="M235 295 L250 295 L250 555 L245 555 Q235 555 235 545 L235 295"
        labelX={242}
        labelY={425}
        {...getPanelState('rbs')}
        onClick={() => onPanelClick('rbs')}
        onLongPress={() => onPanelLongPress('rbs')}
      />

      {/* BED FLOOR (non-interactive reference) */}
      <rect
        x="70"
        y="295"
        width="160"
        height="250"
        fill="#e5e7eb"
        stroke="#d1d5db"
        strokeWidth="1"
      />
      <text x="150" y="420" textAnchor="middle" fontSize="10" fill="#9ca3af">BED</text>

      {/* TAILGATE */}
      <Panel
        id="tailgate"
        label="TAILGATE"
        d="M70 550 L230 550 L230 565 Q230 570 220 570 L80 570 Q70 570 70 565 Z"
        labelX={150}
        labelY={560}
        {...getPanelState('tailgate')}
        onClick={() => onPanelClick('tailgate')}
        onLongPress={() => onPanelLongPress('tailgate')}
      />

      {/* Windshield (non-interactive) */}
      <path
        d="M85 120 L215 120 L215 130 L85 130 Z"
        fill="#e5e7eb"
        stroke="#9ca3af"
        strokeWidth="1"
      />

      {/* Rear cab window (non-interactive) */}
      <path
        d="M85 260 L215 260 L215 270 L85 270 Z"
        fill="#e5e7eb"
        stroke="#9ca3af"
        strokeWidth="1"
      />

      {/* Direction indicator */}
      <polygon
        points="150,15 145,25 155,25"
        fill="#9ca3af"
      />
      <text x="150" y="10" textAnchor="middle" fontSize="8" fill="#6b7280">FRONT</text>
    </svg>
  )
}

export default TruckSvg
