/**
 * SUV SVG - Top-down bird's eye view of an SUV
 * Similar to car but with hatch instead of deck
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

interface SuvSvgProps {
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

export function SuvSvg({ panels, onPanelClick, onPanelLongPress }: SuvSvgProps) {
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
      viewBox="0 0 320 520"
      className="w-full max-w-[320px] h-auto mx-auto"
      style={{ touchAction: 'manipulation' }}
    >
      {/* Vehicle outline - wider/boxier for SUV */}
      <path
        d="M55 80 Q55 40 100 30 L220 30 Q265 40 265 80 L265 440 Q265 480 220 490 L100 490 Q55 480 55 440 Z"
        fill="none"
        stroke="#d1d5db"
        strokeWidth="3"
      />

      {/* HOOD */}
      <Panel
        id="hood"
        label="HOOD"
        d="M65 50 Q65 35 100 30 L220 30 Q255 35 255 50 L255 120 L65 120 Z"
        labelX={160}
        labelY={75}
        {...getPanelState('hood')}
        onClick={() => onPanelClick('hood')}
        onLongPress={() => onPanelLongPress('hood')}
      />

      {/* LEFT FRONT FENDER */}
      <Panel
        id="lff"
        label="LFF"
        d="M55 50 L65 50 L65 140 L55 140 Q45 140 45 110 L45 80 Q45 50 55 50"
        labelX={55}
        labelY={95}
        {...getPanelState('lff')}
        onClick={() => onPanelClick('lff')}
        onLongPress={() => onPanelLongPress('lff')}
      />

      {/* RIGHT FRONT FENDER */}
      <Panel
        id="rff"
        label="RFF"
        d="M255 50 L265 50 Q275 50 275 80 L275 110 Q275 140 265 140 L255 140 L255 50"
        labelX={265}
        labelY={95}
        {...getPanelState('rff')}
        onClick={() => onPanelClick('rff')}
        onLongPress={() => onPanelLongPress('rff')}
      />

      {/* LEFT FRONT DOOR */}
      <Panel
        id="lfd"
        label="LFD"
        d="M55 145 L65 145 L65 240 L55 240 L55 145"
        labelX={60}
        labelY={192}
        {...getPanelState('lfd')}
        onClick={() => onPanelClick('lfd')}
        onLongPress={() => onPanelLongPress('lfd')}
      />

      {/* RIGHT FRONT DOOR */}
      <Panel
        id="rfd"
        label="RFD"
        d="M255 145 L265 145 L265 240 L255 240 L255 145"
        labelX={260}
        labelY={192}
        {...getPanelState('rfd')}
        onClick={() => onPanelClick('rfd')}
        onLongPress={() => onPanelLongPress('rfd')}
      />

      {/* LEFT REAR DOOR */}
      <Panel
        id="lrd"
        label="LRD"
        d="M55 245 L65 245 L65 340 L55 340 L55 245"
        labelX={60}
        labelY={292}
        {...getPanelState('lrd')}
        onClick={() => onPanelClick('lrd')}
        onLongPress={() => onPanelLongPress('lrd')}
      />

      {/* RIGHT REAR DOOR */}
      <Panel
        id="rrd"
        label="RRD"
        d="M255 245 L265 245 L265 340 L255 340 L255 245"
        labelX={260}
        labelY={292}
        {...getPanelState('rrd')}
        onClick={() => onPanelClick('rrd')}
        onLongPress={() => onPanelLongPress('rrd')}
      />

      {/* LEFT ROOF RAIL */}
      <Panel
        id="lrail"
        label="L RAIL"
        d="M65 125 L80 125 L80 365 L65 365 L65 125"
        labelX={72}
        labelY={245}
        {...getPanelState('lrail')}
        onClick={() => onPanelClick('lrail')}
        onLongPress={() => onPanelLongPress('lrail')}
      />

      {/* RIGHT ROOF RAIL */}
      <Panel
        id="rrail"
        label="R RAIL"
        d="M240 125 L255 125 L255 365 L240 365 L240 125"
        labelX={247}
        labelY={245}
        {...getPanelState('rrail')}
        onClick={() => onPanelClick('rrail')}
        onLongPress={() => onPanelLongPress('rrail')}
      />

      {/* ROOF */}
      <Panel
        id="roof"
        label="ROOF"
        d="M85 130 L235 130 L235 360 L85 360 Z"
        labelX={160}
        labelY={245}
        {...getPanelState('roof')}
        onClick={() => onPanelClick('roof')}
        onLongPress={() => onPanelLongPress('roof')}
      />

      {/* LEFT QUARTER */}
      <Panel
        id="lq"
        label="LQ"
        d="M55 345 L65 345 L65 440 Q65 460 55 460 L55 345"
        labelX={60}
        labelY={395}
        {...getPanelState('lq')}
        onClick={() => onPanelClick('lq')}
        onLongPress={() => onPanelLongPress('lq')}
      />

      {/* RIGHT QUARTER */}
      <Panel
        id="rq"
        label="RQ"
        d="M255 345 L265 345 L265 460 Q255 460 255 440 L255 345"
        labelX={260}
        labelY={395}
        {...getPanelState('rq')}
        onClick={() => onPanelClick('rq')}
        onLongPress={() => onPanelLongPress('rq')}
      />

      {/* HATCH / LIFTGATE */}
      <Panel
        id="hatch"
        label="HATCH"
        d="M65 370 L255 370 L255 470 Q255 485 220 490 L100 490 Q65 485 65 470 Z"
        labelX={160}
        labelY={430}
        {...getPanelState('hatch')}
        onClick={() => onPanelClick('hatch')}
        onLongPress={() => onPanelLongPress('hatch')}
      />

      {/* Windshield (non-interactive) */}
      <path
        d="M80 120 L240 120 L240 130 L80 130 Z"
        fill="#e5e7eb"
        stroke="#9ca3af"
        strokeWidth="1"
      />

      {/* Rear window (non-interactive) */}
      <path
        d="M80 360 L240 360 L240 370 L80 370 Z"
        fill="#e5e7eb"
        stroke="#9ca3af"
        strokeWidth="1"
      />

      {/* Direction indicator */}
      <polygon
        points="160,15 155,25 165,25"
        fill="#9ca3af"
      />
      <text x="160" y="10" textAnchor="middle" fontSize="8" fill="#6b7280">FRONT</text>
    </svg>
  )
}

export default SuvSvg
