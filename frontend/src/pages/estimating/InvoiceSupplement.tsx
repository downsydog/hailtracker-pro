/**
 * PDR Invoice & Supplement Generator - Matrix Based
 *
 * Final invoice screen after work is complete.
 * Two tabs: INVOICE (payment details) | SUPPLEMENT (if discoveries exist)
 * Shows matrix-based pricing per panel with modifiers.
 * Auto-generates supplement narrative from discoveries.
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  ArrowLeft,
  FileText,
  Download,
  Send,
  Printer,
  AlertCircle,
  AlertTriangle,
  Clock,
  DollarSign,
  Car,
  Camera,
  Copy,
  Loader2,
  Layers,
  Droplets,
  ArrowUp
} from 'lucide-react'

import { SIZE_LABELS, PANEL_NAMES } from '@/hooks/use-pdr-estimates'

import {
  usePDREstimate,
  useSupplement,
} from '@/hooks/use-pdr-estimates'
import { cn } from '@/lib/utils'

export function InvoiceSupplement() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState('invoice')
  const [narrativeCopied, setNarrativeCopied] = useState(false)

  // API hooks
  const { data: estimate, isLoading: isLoadingEstimate } = usePDREstimate(id ? parseInt(id) : null)
  const { data: supplementData } = useSupplement(id ? parseInt(id) : null)

  // Calculate totals - matrix based
  const totals = useMemo(() => {
    if (!estimate) return {
      panelTotal: 0,
      riTotal: 0,
      originalTotal: 0,
      supplementTotal: 0,
      grandTotal: 0,
      totalDents: 0,
      crPanels: 0
    }

    // Sum panel totals from matrix pricing
    let panelTotal = 0
    let riTotal = 0
    let totalDents = 0
    let crPanels = 0

    estimate.panels?.forEach(panel => {
      panelTotal += panel.panel_total || 0
      totalDents += panel.total_dent_count || 0
      if (panel.is_conventional_repair) crPanels++

      panel.ri_items?.forEach(ri => {
        riTotal += ri.price || 0
      })
    })

    const originalTotal = panelTotal + riTotal
    const supplementTotal = supplementData?.supplement_total || 0
    const grandTotal = supplementData?.grand_total || originalTotal

    return { panelTotal, riTotal, originalTotal, supplementTotal, grandTotal, totalDents, crPanels }
  }, [estimate, supplementData])

  // Check if has supplements
  const hasSupplements = supplementData && supplementData.discoveries && supplementData.discoveries.length > 0

  // Copy narrative
  const copyNarrative = () => {
    if (supplementData?.narrative) {
      navigator.clipboard.writeText(supplementData.narrative)
      setNarrativeCopied(true)
      setTimeout(() => setNarrativeCopied(false), 2000)
    }
  }

  // Get display name for panel
  const getPanelDisplayName = (panelName: string) => {
    return PANEL_NAMES[panelName] || panelName
  }

  // Get majority size label
  const getMajoritySizeLabel = (size: string) => {
    return SIZE_LABELS[size as keyof typeof SIZE_LABELS] || size
  }

  if (isLoadingEstimate) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!estimate) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Estimate not found</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-background border-b">
        <div className="flex items-center justify-between p-4 max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-bold flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Invoice #{estimate.id}
              </h1>
              <div className="flex items-center gap-2">
                {hasSupplements && (
                  <Badge className="bg-orange-100 text-orange-700">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    Supplement Required
                  </Badge>
                )}
                {totals.crPanels > 0 && (
                  <Badge variant="destructive">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    {totals.crPanels} CR Panel{totals.crPanels > 1 ? 's' : ''}
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Printer className="h-4 w-4 mr-1" />
              Print
            </Button>
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" />
              PDF
            </Button>
            <Button size="sm">
              <Send className="h-4 w-4 mr-1" />
              Send Invoice
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Customer & Summary */}
          <div className="space-y-4">
            {/* Customer */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Customer</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">{estimate.customer_name || 'No customer info'}</p>
                {estimate.customer_email && (
                  <p className="text-sm text-muted-foreground">{estimate.customer_email}</p>
                )}
                {estimate.customer_phone && (
                  <p className="text-sm text-muted-foreground">{estimate.customer_phone}</p>
                )}
              </CardContent>
            </Card>

            {/* Vehicle */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Car className="h-4 w-4" />
                  Vehicle
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">
                  {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                </p>
                {estimate.vehicle_vin && (
                  <p className="text-xs text-muted-foreground mt-1">
                    VIN: {estimate.vehicle_vin}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Work Summary - Matrix Based */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Work Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Panels</span>
                  <span className="font-medium">
                    {estimate.panels?.length || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Dents</span>
                  <span className="font-medium">
                    {totals.totalDents}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">R&I Items</span>
                  <span className="font-medium">
                    {estimate.panels?.reduce((sum, p) => sum + (p.ri_items?.length || 0), 0) || 0}
                  </span>
                </div>
                {totals.crPanels > 0 && (
                  <div className="flex justify-between text-red-600">
                    <span>CR Panels</span>
                    <span className="font-medium">{totals.crPanels}</span>
                  </div>
                )}
                {hasSupplements && (
                  <div className="flex justify-between text-orange-600">
                    <span>Discoveries</span>
                    <span className="font-medium">{supplementData?.discoveries?.length || 0}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Totals */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Totals
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Panel Repairs</span>
                  <span>${totals.panelTotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">R&I Items</span>
                  <span>${totals.riTotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="font-medium">Original Estimate</span>
                  <span className="font-medium">${totals.originalTotal.toFixed(2)}</span>
                </div>
                {hasSupplements && (
                  <div className="flex justify-between text-orange-600">
                    <span className="font-medium">Supplement</span>
                    <span className="font-medium">+${totals.supplementTotal.toFixed(2)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t pt-2 text-lg">
                  <span className="font-bold">Grand Total</span>
                  <span className="font-bold text-green-600">
                    ${totals.grandTotal.toFixed(2)}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Insurance / Matrix Profile */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Insurance Matrix</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">{estimate.matrix_profile || estimate.insurance_profile?.carrier_name || 'Standard Matrix'}</p>
                {estimate.claim_number && (
                  <p className="text-sm text-muted-foreground">
                    Claim: {estimate.claim_number}
                  </p>
                )}
                <Button variant="outline" size="sm" className="w-full mt-3">
                  <Send className="h-4 w-4 mr-2" />
                  Send to Insurance
                </Button>
              </CardContent>
            </Card>

            {/* Legend */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground">Legend</CardTitle>
              </CardHeader>
              <CardContent className="text-xs space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">AL</span>
                  <span>Aluminum (+25%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">HSS</span>
                  <span>High Strength Steel (+25%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">GP</span>
                  <span>Glue Pull (+25%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded">TR</span>
                  <span>Tall Roof (+25%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded">O/S</span>
                  <span>Oversized ($50 ea)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded">CR</span>
                  <span>Conventional Repair</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right: Details */}
          <div className="lg:col-span-2">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-4">
                <TabsTrigger value="invoice">Invoice Details</TabsTrigger>
                {hasSupplements && (
                  <TabsTrigger value="supplement" className="flex items-center gap-1">
                    <AlertCircle className="h-4 w-4" />
                    Supplement
                  </TabsTrigger>
                )}
              </TabsList>

              {/* Invoice Tab - Matrix Based */}
              <TabsContent value="invoice" className="space-y-4">
                {estimate.panels?.map(panel => {
                  const panelRITotal = panel.ri_items?.reduce((sum, r) => sum + (r.price || 0), 0) || 0
                  const isCR = panel.is_conventional_repair

                  return (
                    <Card key={panel.id} className={cn(isCR && 'border-red-300')}>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span>{getPanelDisplayName(panel.panel_name)}</span>
                            {isCR && (
                              <Badge variant="destructive" className="text-xs">CR</Badge>
                            )}
                          </div>
                          <span className={cn(
                            "font-bold",
                            isCR ? "text-red-600" : "text-green-600"
                          )}>
                            ${(panel.panel_total || 0).toFixed(2)}
                          </span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        {/* CR Warning */}
                        {isCR && (
                          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                            <div className="flex items-start gap-2">
                              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                              <div>
                                <p className="font-medium text-red-700">Conventional Repair Required</p>
                                <p className="text-sm text-red-600">
                                  Panel exceeds PDR limits - routed for conventional repair
                                </p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Matrix Info Grid */}
                        <div className="grid grid-cols-4 gap-3 mb-4 p-3 bg-muted/50 rounded-lg">
                          <div className="text-center">
                            <p className="text-lg font-bold">{panel.total_dent_count || 0}</p>
                            <p className="text-xs text-muted-foreground">Dents</p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-bold capitalize">
                              {getMajoritySizeLabel(panel.majority_size || 'dime')}
                            </p>
                            <p className="text-xs text-muted-foreground">Majority</p>
                          </div>
                          <div className="text-center">
                            <p className="text-lg font-bold text-orange-600">
                              {panel.oversized_count || 0}
                            </p>
                            <p className="text-xs text-muted-foreground">Oversized</p>
                          </div>
                          <div className="text-center">
                            <p className="text-lg font-bold text-primary">
                              ${(panel.matrix_base_price || 0).toFixed(0)}
                            </p>
                            <p className="text-xs text-muted-foreground">Base</p>
                          </div>
                        </div>

                        {/* Modifier Badges */}
                        {(panel.is_aluminum || panel.is_hss || panel.requires_glue_pull || panel.is_tall_roof) && (
                          <div className="flex flex-wrap gap-2 mb-4">
                            {panel.is_aluminum && (
                              <Badge className="bg-amber-100 text-amber-700 border-amber-300">
                                <Layers className="h-3 w-3 mr-1" />
                                Aluminum +25%
                              </Badge>
                            )}
                            {panel.is_hss && (
                              <Badge className="bg-purple-100 text-purple-700 border-purple-300">
                                <Layers className="h-3 w-3 mr-1" />
                                HSS +25%
                              </Badge>
                            )}
                            {panel.requires_glue_pull && (
                              <Badge className="bg-blue-100 text-blue-700 border-blue-300">
                                <Droplets className="h-3 w-3 mr-1" />
                                Glue Pull +25%
                              </Badge>
                            )}
                            {panel.is_tall_roof && (
                              <Badge className="bg-slate-100 text-slate-700 border-slate-300">
                                <ArrowUp className="h-3 w-3 mr-1" />
                                Tall Roof +25%
                              </Badge>
                            )}
                          </div>
                        )}

                        {/* Price Breakdown Table */}
                        <table className="w-full text-sm mb-4">
                          <thead>
                            <tr className="border-b text-left">
                              <th className="py-2 text-muted-foreground font-medium">Item</th>
                              <th className="py-2 text-right text-muted-foreground font-medium">Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr className="border-b border-dashed">
                              <td className="py-2">
                                Matrix Base ({panel.total_dent_count} dents, {getMajoritySizeLabel(panel.majority_size || 'dime')})
                              </td>
                              <td className="py-2 text-right">
                                ${(panel.matrix_base_price || 0).toFixed(2)}
                              </td>
                            </tr>
                            {panel.is_aluminum && (
                              <tr className="border-b border-dashed text-amber-700">
                                <td className="py-2">Aluminum Upcharge (+25%)</td>
                                <td className="py-2 text-right">
                                  +${((panel.matrix_base_price || 0) * 0.25).toFixed(2)}
                                </td>
                              </tr>
                            )}
                            {panel.is_hss && (
                              <tr className="border-b border-dashed text-purple-700">
                                <td className="py-2">HSS Upcharge (+25%)</td>
                                <td className="py-2 text-right">
                                  +${((panel.matrix_base_price || 0) * 0.25).toFixed(2)}
                                </td>
                              </tr>
                            )}
                            {panel.requires_glue_pull && (
                              <tr className="border-b border-dashed text-blue-700">
                                <td className="py-2">Glue Pull Upcharge (+25%)</td>
                                <td className="py-2 text-right">
                                  +${((panel.matrix_base_price || 0) * 0.25).toFixed(2)}
                                </td>
                              </tr>
                            )}
                            {panel.is_tall_roof && (
                              <tr className="border-b border-dashed text-slate-700">
                                <td className="py-2">Tall Roof Upcharge (+25%)</td>
                                <td className="py-2 text-right">
                                  +${((panel.matrix_base_price || 0) * 0.25).toFixed(2)}
                                </td>
                              </tr>
                            )}
                            {(panel.oversized_count || 0) > 0 && (
                              <tr className="border-b border-dashed text-orange-700">
                                <td className="py-2">Oversized Dents ({panel.oversized_count} x $50)</td>
                                <td className="py-2 text-right">
                                  +${((panel.oversized_count || 0) * 50).toFixed(2)}
                                </td>
                              </tr>
                            )}
                          </tbody>
                          <tfoot>
                            <tr className="font-bold">
                              <td className="py-2">Panel Total</td>
                              <td className="py-2 text-right">
                                ${(panel.panel_total || 0).toFixed(2)}
                              </td>
                            </tr>
                          </tfoot>
                        </table>

                        {/* R&I items */}
                        {panel.ri_items && panel.ri_items.length > 0 && (
                          <div className="bg-muted/50 p-3 rounded-lg">
                            <p className="text-sm font-medium mb-2">R&I Items</p>
                            {panel.ri_items.map(item => (
                              <div key={item.id} className="flex justify-between text-sm py-1">
                                <span>{item.operation_name}</span>
                                <span>${(item.price || 0).toFixed(2)}</span>
                              </div>
                            ))}
                            <div className="flex justify-between text-sm font-medium border-t mt-2 pt-2">
                              <span>R&I Subtotal</span>
                              <span>${panelRITotal.toFixed(2)}</span>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}

                {/* Grand Total Card */}
                <Card className="bg-green-50 border-green-200">
                  <CardContent className="pt-6 pb-6">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="text-sm text-muted-foreground">Invoice Total</p>
                        <p className="text-3xl font-bold text-green-600">
                          ${totals.originalTotal.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-right text-sm text-muted-foreground">
                        <p>{estimate.panels?.length} panels</p>
                        <p>{totals.totalDents} total dents</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Supplement Tab */}
              {hasSupplements && (
                <TabsContent value="supplement" className="space-y-4">
                  {/* Narrative */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center justify-between">
                        <span>Insurance Narrative</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={copyNarrative}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          {narrativeCopied ? 'Copied!' : 'Copy'}
                        </Button>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <pre className="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded-lg">
                        {supplementData?.narrative || 'Generating narrative...'}
                      </pre>
                    </CardContent>
                  </Card>

                  {/* Discovery Details */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Discovery Details</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {supplementData?.discoveries?.map((discovery, idx) => (
                        <div key={discovery.id} className="p-4 border rounded-lg">
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <h4 className="font-medium flex items-center gap-2">
                                <span className="bg-orange-100 text-orange-700 text-xs px-2 py-0.5 rounded">
                                  #{idx + 1}
                                </span>
                                {discovery.discovery_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                              </h4>
                              {discovery.panel_name && (
                                <p className="text-sm text-muted-foreground">
                                  {getPanelDisplayName(discovery.panel_name)}
                                </p>
                              )}
                            </div>
                            <Badge className="bg-orange-100 text-orange-700">
                              +${(discovery.additional_cost || 0).toFixed(0)}
                            </Badge>
                          </div>

                          {discovery.description && (
                            <p className="text-sm mb-3">{discovery.description}</p>
                          )}

                          {discovery.narrative && (
                            <p className="text-sm text-muted-foreground italic">
                              {discovery.narrative}
                            </p>
                          )}

                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-3">
                            <span className="flex items-center gap-1">
                              <Clock className="h-4 w-4" />
                              {discovery.additional_time_hours || 0} hours
                            </span>
                            {discovery.photo_url && (
                              <span className="flex items-center gap-1">
                                <Camera className="h-4 w-4" />
                                Photo attached
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  {/* Evidence Chain */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Evidence Chain</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {supplementData?.discoveries?.map((discovery, idx) => (
                          <div
                            key={discovery.id}
                            className="flex items-center gap-3 p-2 bg-muted/50 rounded"
                          >
                            <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-700 font-bold text-sm shrink-0">
                              {idx + 1}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">
                                {discovery.discovery_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {new Date(discovery.created_at).toLocaleString()}
                              </p>
                            </div>
                            <span className="text-sm font-medium text-orange-600 shrink-0">
                              +${(discovery.additional_cost || 0).toFixed(0)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Supplement Total */}
                  <Card className="bg-orange-50 border-orange-200">
                    <CardContent className="pt-6 pb-6">
                      <div className="text-center">
                        <p className="text-orange-600 mb-1">Total Supplement Amount</p>
                        <p className="text-4xl font-bold text-orange-600">
                          +${totals.supplementTotal.toFixed(2)}
                        </p>
                      </div>
                      <div className="flex gap-2 mt-4">
                        <Button variant="outline" className="flex-1">
                          <Download className="h-4 w-4 mr-2" />
                          Generate PDF
                        </Button>
                        <Button className="flex-1">
                          <Send className="h-4 w-4 mr-2" />
                          Send to Insurance
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              )}
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  )
}

export default InvoiceSupplement
