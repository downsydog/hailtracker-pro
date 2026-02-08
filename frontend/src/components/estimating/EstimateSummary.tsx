/**
 * Estimate Summary Component
 * Reusable summary view for estimates
 * Used in Review, Invoice, and Supplement screens
 */

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Car, Calculator, Clock, AlertCircle, DollarSign, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DentSummary {
  size: string
  zone: string
  depth: string
  count: number
  total: number
}

interface RISummary {
  operation_name: string
  time_hours: number
  price: number
}

interface PanelSummary {
  panel_name: string
  display_name: string
  dent_count: number
  dent_total: number
  ri_count: number
  ri_total: number
  panel_total: number
  dents?: DentSummary[]
  ri_items?: RISummary[]
}

interface EstimateSummaryData {
  id: number
  estimate_number?: string
  status: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_vin?: string
  vehicle_tier?: string
  customer_name?: string
  panels: PanelSummary[]
  dent_total: number
  ri_total: number
  supplement_total?: number
  grand_total: number
}

interface EstimateSummaryProps {
  estimate: EstimateSummaryData
  view?: 'customer' | 'detail' | 'compact'
  showPrices?: boolean
  className?: string
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  completed: 'bg-blue-100 text-blue-700'
}

const TIER_LABELS: Record<string, string> = {
  economy: 'Economy',
  standard: 'Standard',
  premium: 'Premium',
  luxury: 'Luxury',
  ev_adas: 'EV/ADAS'
}

export function EstimateSummary({
  estimate,
  view = 'detail',
  showPrices = true,
  className
}: EstimateSummaryProps) {
  // Calculate stats
  const stats = useMemo(() => {
    let totalDents = 0
    let totalRITime = 0

    estimate.panels.forEach(panel => {
      totalDents += panel.dent_count
      if (panel.ri_items) {
        totalRITime += panel.ri_items.reduce((sum, ri) => sum + ri.time_hours, 0)
      }
    })

    return {
      totalDents,
      panelCount: estimate.panels.length,
      totalRITime
    }
  }, [estimate])

  // Customer view - simplified, no per-dent pricing
  if (view === 'customer') {
    return (
      <div className={cn('space-y-4', className)}>
        {/* Vehicle */}
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3">
              <Car className="h-8 w-8 text-primary" />
              <div>
                <p className="font-bold text-lg">
                  {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                </p>
                {estimate.vehicle_vin && (
                  <p className="text-sm text-muted-foreground">VIN: {estimate.vehicle_vin}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Panel summary (no prices per dent) */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Damage Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {estimate.panels.map(panel => (
              <div key={panel.panel_name} className="flex justify-between items-center">
                <span>{panel.display_name}</span>
                <Badge variant="secondary">{panel.dent_count} dent{panel.dent_count !== 1 ? 's' : ''}</Badge>
              </div>
            ))}
            <Separator className="my-2" />
            <div className="flex justify-between items-center font-medium">
              <span>Total Dents</span>
              <span>{stats.totalDents}</span>
            </div>
          </CardContent>
        </Card>

        {/* Grand total */}
        {showPrices && (
          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="pt-4">
              <div className="text-center">
                <p className="text-muted-foreground mb-1">Estimate Total</p>
                <p className="text-4xl font-bold text-primary">
                  ${estimate.grand_total.toFixed(2)}
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  // Compact view - for lists and cards
  if (view === 'compact') {
    return (
      <div className={cn('flex items-center justify-between', className)}>
        <div>
          <p className="font-medium">
            {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
          </p>
          <p className="text-sm text-muted-foreground">
            {stats.totalDents} dents • {stats.panelCount} panels
          </p>
        </div>
        <div className="text-right">
          <Badge className={STATUS_STYLES[estimate.status]}>
            {estimate.status}
          </Badge>
          {showPrices && (
            <p className="font-bold text-green-600 mt-1">
              ${estimate.grand_total.toFixed(0)}
            </p>
          )}
        </div>
      </div>
    )
  }

  // Detail view - full breakdown with all pricing
  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Car className="h-6 w-6 text-muted-foreground" />
              <div>
                <p className="font-bold">
                  {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                </p>
                {estimate.vehicle_vin && (
                  <p className="text-xs text-muted-foreground">VIN: {estimate.vehicle_vin}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {estimate.vehicle_tier && (
                <Badge variant="outline">{TIER_LABELS[estimate.vehicle_tier] || estimate.vehicle_tier}</Badge>
              )}
              <Badge className={STATUS_STYLES[estimate.status]}>
                {estimate.status}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{stats.totalDents}</p>
            <p className="text-xs text-muted-foreground">Total Dents</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{stats.panelCount}</p>
            <p className="text-xs text-muted-foreground">Panels</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">{stats.totalRITime.toFixed(1)}</p>
            <p className="text-xs text-muted-foreground">R&I Hours</p>
          </CardContent>
        </Card>
      </div>

      {/* Panel breakdown */}
      {estimate.panels.map(panel => (
        <Card key={panel.panel_name}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center justify-between">
              <span>{panel.display_name}</span>
              {showPrices && (
                <span className="text-green-600">${panel.panel_total.toFixed(0)}</span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {/* Dent breakdown */}
            {panel.dents && panel.dents.length > 0 && (
              <div className="space-y-1">
                {panel.dents.map((dent, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-sm bg-muted/30 p-2 rounded"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{dent.count}×</span>
                      <span className="capitalize">{dent.size}</span>
                      <Badge variant="outline" className="text-xs">{dent.zone}</Badge>
                      <span className="text-xs text-muted-foreground">({dent.depth})</span>
                    </div>
                    {showPrices && (
                      <span className="font-medium">${dent.total.toFixed(0)}</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* R&I items */}
            {panel.ri_items && panel.ri_items.length > 0 && (
              <div className="border-t pt-2 space-y-1">
                <p className="text-xs font-medium text-muted-foreground">R&I Items</p>
                {panel.ri_items.map((ri, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span>{ri.operation_name}</span>
                      <span className="text-xs text-muted-foreground">
                        ({ri.time_hours}h)
                      </span>
                    </div>
                    {showPrices && (
                      <span>${ri.price.toFixed(0)}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}

      {/* Totals */}
      {showPrices && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calculator className="h-4 w-4" />
              Totals
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Dent Repair</span>
              <span className="font-medium">${estimate.dent_total.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">R&I Items</span>
              <span className="font-medium">${estimate.ri_total.toFixed(2)}</span>
            </div>
            {estimate.supplement_total && estimate.supplement_total > 0 && (
              <div className="flex justify-between text-orange-600">
                <span className="flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  Supplement
                </span>
                <span className="font-medium">+${estimate.supplement_total.toFixed(2)}</span>
              </div>
            )}
            <Separator />
            <div className="flex justify-between text-lg">
              <span className="font-bold">Grand Total</span>
              <span className="font-bold text-green-600">
                ${estimate.grand_total.toFixed(2)}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Running totals footer component
interface RunningTotalsProps {
  dentTotal: number
  riTotal: number
  grandTotal: number
  onCalculate?: () => void
  onReview?: () => void
  isCalculating?: boolean
}

export function RunningTotals({
  dentTotal,
  riTotal,
  grandTotal,
  onCalculate,
  onReview,
  isCalculating = false
}: RunningTotalsProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-background border-t shadow-lg p-4 z-50">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between gap-4">
          {/* Totals */}
          <div className="flex items-center gap-6">
            <div>
              <p className="text-xs text-muted-foreground">Dents</p>
              <p className="font-bold">${dentTotal.toFixed(0)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">R&I</p>
              <p className="font-bold">${riTotal.toFixed(0)}</p>
            </div>
            <div className="border-l pl-6">
              <p className="text-xs text-muted-foreground">Total</p>
              <p className="text-xl font-bold text-green-600">${grandTotal.toFixed(0)}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {onCalculate && (
              <button
                onClick={onCalculate}
                disabled={isCalculating}
                className={cn(
                  'px-4 py-2 rounded-lg border font-medium transition-colors',
                  'hover:bg-accent',
                  isCalculating && 'opacity-50'
                )}
              >
                <Calculator className="h-4 w-4 inline mr-1" />
                {isCalculating ? 'Calculating...' : 'Calculate'}
              </button>
            )}
            {onReview && (
              <button
                onClick={onReview}
                className="px-6 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90"
              >
                <CheckCircle2 className="h-4 w-4 inline mr-1" />
                Review & Approve
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
