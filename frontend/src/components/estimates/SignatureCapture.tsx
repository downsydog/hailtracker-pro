/**
 * Signature Capture Component
 *
 * Canvas-based signature pad for capturing customer signatures.
 * Supports touch and mouse input. Returns PNG data URL.
 */

import { useRef, useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react'
import { Button } from '@/components/ui/button'
import { Eraser, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SignatureCaptureProps {
  /** Callback when signature changes */
  onChange?: (dataUrl: string | null) => void
  /** Width of the signature pad */
  width?: number
  /** Height of the signature pad */
  height?: number
  /** Line color */
  penColor?: string
  /** Line width */
  penWidth?: number
  /** Background color */
  backgroundColor?: string
  /** Class name for container */
  className?: string
  /** Placeholder text */
  placeholder?: string
  /** Whether the pad is disabled */
  disabled?: boolean
}

export interface SignatureCaptureRef {
  /** Clear the signature */
  clear: () => void
  /** Check if signature is empty */
  isEmpty: () => boolean
  /** Get signature as PNG data URL */
  toDataURL: () => string | null
}

export const SignatureCapture = forwardRef<SignatureCaptureRef, SignatureCaptureProps>(
  function SignatureCapture(
    {
      onChange,
      width = 400,
      height = 200,
      penColor = '#1a1a1a',
      penWidth = 2,
      backgroundColor = '#ffffff',
      className,
      placeholder = 'Sign here',
      disabled = false
    },
    ref
  ) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [isDrawing, setIsDrawing] = useState(false)
    const [isEmpty, setIsEmpty] = useState(true)
    const lastPoint = useRef<{ x: number; y: number } | null>(null)

    // Get canvas context
    const getContext = useCallback(() => {
      const canvas = canvasRef.current
      if (!canvas) return null
      return canvas.getContext('2d')
    }, [])

    // Initialize canvas
    useEffect(() => {
      const canvas = canvasRef.current
      if (!canvas) return

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      // Set canvas size (handle high DPI displays)
      const dpr = window.devicePixelRatio || 1
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.scale(dpr, dpr)

      // Set background
      ctx.fillStyle = backgroundColor
      ctx.fillRect(0, 0, width, height)
    }, [width, height, backgroundColor])

    // Get coordinates from event
    const getCoordinates = useCallback((e: React.TouchEvent | React.MouseEvent): { x: number; y: number } => {
      const canvas = canvasRef.current
      if (!canvas) return { x: 0, y: 0 }

      const rect = canvas.getBoundingClientRect()
      const scaleX = width / rect.width
      const scaleY = height / rect.height

      if ('touches' in e) {
        const touch = e.touches[0] || e.changedTouches[0]
        return {
          x: (touch.clientX - rect.left) * scaleX,
          y: (touch.clientY - rect.top) * scaleY
        }
      } else {
        return {
          x: (e.clientX - rect.left) * scaleX,
          y: (e.clientY - rect.top) * scaleY
        }
      }
    }, [width, height])

    // Start drawing
    const startDrawing = useCallback((e: React.TouchEvent | React.MouseEvent) => {
      if (disabled) return
      e.preventDefault()

      const point = getCoordinates(e)
      lastPoint.current = point
      setIsDrawing(true)
    }, [disabled, getCoordinates])

    // Draw line
    const draw = useCallback((e: React.TouchEvent | React.MouseEvent) => {
      if (!isDrawing || disabled) return
      e.preventDefault()

      const ctx = getContext()
      if (!ctx || !lastPoint.current) return

      const point = getCoordinates(e)

      ctx.beginPath()
      ctx.moveTo(lastPoint.current.x, lastPoint.current.y)
      ctx.lineTo(point.x, point.y)
      ctx.strokeStyle = penColor
      ctx.lineWidth = penWidth
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.stroke()

      lastPoint.current = point

      if (isEmpty) {
        setIsEmpty(false)
      }
    }, [isDrawing, disabled, getContext, getCoordinates, penColor, penWidth, isEmpty])

    // Stop drawing
    const stopDrawing = useCallback(() => {
      if (isDrawing) {
        setIsDrawing(false)
        lastPoint.current = null

        // Notify parent of change
        if (onChange && canvasRef.current) {
          const dataUrl = canvasRef.current.toDataURL('image/png')
          onChange(isEmpty ? null : dataUrl)
        }
      }
    }, [isDrawing, isEmpty, onChange])

    // Clear signature
    const clear = useCallback(() => {
      const canvas = canvasRef.current
      const ctx = getContext()
      if (!canvas || !ctx) return

      ctx.fillStyle = backgroundColor
      ctx.fillRect(0, 0, width, height)
      setIsEmpty(true)

      if (onChange) {
        onChange(null)
      }
    }, [getContext, backgroundColor, width, height, onChange])

    // Check if empty
    const checkIsEmpty = useCallback(() => {
      return isEmpty
    }, [isEmpty])

    // Get data URL
    const toDataURL = useCallback(() => {
      if (isEmpty || !canvasRef.current) return null
      return canvasRef.current.toDataURL('image/png')
    }, [isEmpty])

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      clear,
      isEmpty: checkIsEmpty,
      toDataURL
    }), [clear, checkIsEmpty, toDataURL])

    return (
      <div className={cn('relative', className)}>
        {/* Canvas */}
        <div
          className={cn(
            'relative border-2 border-dashed rounded-lg overflow-hidden',
            disabled ? 'border-gray-200 bg-gray-50' : 'border-gray-300 bg-white',
            'touch-none'
          )}
        >
          <canvas
            ref={canvasRef}
            className={cn(
              'cursor-crosshair',
              disabled && 'cursor-not-allowed opacity-50'
            )}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
          />

          {/* Placeholder */}
          {isEmpty && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <span className="text-gray-400 text-lg">{placeholder}</span>
            </div>
          )}

          {/* Signature line */}
          <div
            className="absolute bottom-8 left-8 right-8 border-b border-gray-300 pointer-events-none"
            style={{ borderStyle: 'dotted' }}
          />
          <span className="absolute bottom-2 left-8 text-xs text-gray-400 pointer-events-none">
            X
          </span>
        </div>

        {/* Controls */}
        <div className="flex justify-end gap-2 mt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={clear}
            disabled={disabled || isEmpty}
          >
            <Eraser className="h-4 w-4 mr-1" />
            Clear
          </Button>
        </div>
      </div>
    )
  }
)

// Signature display component (for showing signed signatures)
interface SignatureDisplayProps {
  /** Base64 signature image */
  signatureBase64?: string
  /** Signed by name */
  signedByName?: string
  /** Signed at timestamp */
  signedAt?: string
  /** Class name */
  className?: string
}

export function SignatureDisplay({
  signatureBase64,
  signedByName,
  signedAt,
  className
}: SignatureDisplayProps) {
  if (!signatureBase64) {
    return null
  }

  const signedDate = signedAt ? new Date(signedAt) : null

  return (
    <div className={cn('border rounded-lg p-4 bg-green-50 border-green-200', className)}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0">
          <Check className="h-5 w-5 text-green-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-green-800">
            Signed by {signedByName || 'Customer'}
          </p>
          {signedDate && (
            <p className="text-xs text-green-600 mt-0.5">
              {signedDate.toLocaleDateString()} at {signedDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
            </p>
          )}
          <div className="mt-2 bg-white rounded border p-2">
            <img
              src={signatureBase64.startsWith('data:') ? signatureBase64 : `data:image/png;base64,${signatureBase64}`}
              alt="Signature"
              className="max-h-20 max-w-full object-contain"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default SignatureCapture
