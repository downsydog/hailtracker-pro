/**
 * Signature Pad Component
 * Canvas-based signature capture for estimate approval
 * Returns base64 image of signature
 */

import { useRef, useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Eraser, Check, Pen } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SignaturePadProps {
  onSignatureChange: (signature: string | null) => void
  width?: number
  height?: number
  className?: string
  title?: string
}

export function SignaturePad({
  onSignatureChange,
  width = 400,
  height = 150,
  className,
  title = 'Customer Signature'
}: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [hasSignature, setHasSignature] = useState(false)
  const lastPosRef = useRef<{ x: number; y: number } | null>(null)

  // Initialize canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size accounting for device pixel ratio
    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    ctx.scale(dpr, dpr)

    // Set drawing styles
    ctx.strokeStyle = '#000'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    // Fill with white background
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, width, height)
  }, [width, height])

  // Get position from event
  const getPos = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return null

    const rect = canvas.getBoundingClientRect()
    const scaleX = width / rect.width
    const scaleY = height / rect.height

    if ('touches' in e) {
      const touch = e.touches[0]
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

  // Drawing handlers
  const startDrawing = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    const pos = getPos(e)
    if (!pos) return

    setIsDrawing(true)
    lastPosRef.current = pos
  }, [getPos])

  const draw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    if (!isDrawing) return

    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx || !lastPosRef.current) return

    const pos = getPos(e)
    if (!pos) return

    ctx.beginPath()
    ctx.moveTo(lastPosRef.current.x, lastPosRef.current.y)
    ctx.lineTo(pos.x, pos.y)
    ctx.stroke()

    lastPosRef.current = pos
    setHasSignature(true)
  }, [isDrawing, getPos])

  const stopDrawing = useCallback(() => {
    if (isDrawing && hasSignature) {
      // Export signature as base64
      const canvas = canvasRef.current
      if (canvas) {
        const dataUrl = canvas.toDataURL('image/png')
        onSignatureChange(dataUrl)
      }
    }
    setIsDrawing(false)
    lastPosRef.current = null
  }, [isDrawing, hasSignature, onSignatureChange])

  // Clear signature
  const clearSignature = useCallback(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, width, height)
    setHasSignature(false)
    onSignatureChange(null)
  }, [width, height, onSignatureChange])

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Pen className="h-4 w-4" />
            {title}
          </span>
          {hasSignature && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearSignature}
            >
              <Eraser className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className={cn(
            'relative border-2 border-dashed rounded-lg overflow-hidden',
            hasSignature ? 'border-green-400' : 'border-muted-foreground/30'
          )}
        >
          <canvas
            ref={canvasRef}
            className="touch-none cursor-crosshair"
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
          />

          {/* Signature line */}
          <div
            className="absolute bottom-6 left-4 right-4 border-b border-muted-foreground/50"
            style={{ pointerEvents: 'none' }}
          />

          {/* Placeholder text */}
          {!hasSignature && (
            <div
              className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm pointer-events-none"
            >
              Sign here
            </div>
          )}

          {/* Signed indicator */}
          {hasSignature && (
            <div className="absolute top-2 right-2 flex items-center gap-1 text-green-600 bg-green-50 px-2 py-1 rounded text-xs">
              <Check className="h-3 w-3" />
              Signed
            </div>
          )}
        </div>

        <p className="text-xs text-muted-foreground text-center mt-2">
          By signing above, you authorize the repair work described in this estimate.
        </p>
      </CardContent>
    </Card>
  )
}

// Compact inline version
interface SignaturePadInlineProps {
  value: string | null
  onChange: (signature: string | null) => void
  error?: string
}

export function SignaturePadInline({ value, onChange, error }: SignaturePadInlineProps) {
  return (
    <div className="space-y-1">
      <SignaturePad
        onSignatureChange={onChange}
        width={350}
        height={120}
      />
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  )
}
