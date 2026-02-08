/**
 * PDR Invoice & Supplement Generator
 *
 * Final invoice screen after work is complete.
 * Two tabs: INVOICE (payment details) | SUPPLEMENT (if discoveries exist)
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
  CheckCircle2,
  AlertCircle,
  Clock,
  DollarSign,
  Car,
  Camera,
  Copy,
  Loader2
} from 'lucide-react'

import { DiscoveryItem } from '@/components/estimating/DiscoveryForm'
import { SIZE_LABELS } from '@/components/estimating/DentEntry'

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
  const { data: supplementData, isLoading: isLoadingSupplement } = useSupplement(id ? parseInt(id) : null)

  // Calculate totals
  const totals = useMemo(() => {
    if (!estimate) return { dentTotal: 0, riTotal: 0, originalTotal: 0, supplementTotal: 0, grandTotal: 0 }

    const dentTotal = estimate.dent_total || 0
    const riTotal = estimate.ri_total || 0
    const originalTotal = dentTotal + riTotal
    const supplementTotal = supplementData?.supplement_total || 0
    const grandTotal = supplementData?.grand_total || originalTotal

    return { dentTotal, riTotal, originalTotal, supplementTotal, grandTotal }
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

  // Group dents by panel
  const dentsByPanel = useMemo(() => {
    if (!estimate?.panels) return {}

    const grouped: Record<string, typeof estimate.panels[0]> = {}
    estimate.panels.forEach(panel => {
      grouped[panel.panel_name] = panel
    })
    return grouped
  }, [estimate])

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

            {/* Work Summary */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Work Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Dents</span>
                  <span className="font-medium">
                    {estimate.panels?.reduce((sum, p) => sum + (p.dents?.length || 0), 0) || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">R&I Items</span>
                  <span className="font-medium">
                    {estimate.panels?.reduce((sum, p) => sum + (p.ri_items?.length || 0), 0) || 0}
                  </span>
                </div>
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
                  <span className="text-muted-foreground">Dent Repair</span>
                  <span>${totals.dentTotal.toFixed(2)}</span>
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

            {/* Insurance */}
            {estimate.insurance_profile && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Insurance</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-medium">{estimate.insurance_profile.carrier_name}</p>
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
            )}
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

              {/* Invoice Tab */}
              <TabsContent value="invoice" className="space-y-4">
                {estimate.panels?.map(panel => {
                  const panelDentTotal = panel.dents?.reduce((sum, d) => sum + (d.final_price || 0), 0) || 0
                  const panelRITotal = panel.ri_items?.reduce((sum, r) => sum + (r.price || 0), 0) || 0

                  return (
                    <Card key={panel.id}>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base flex items-center justify-between">
                          <span>{panel.display_name || panel.panel_name}</span>
                          <span className="text-green-600">
                            ${(panel.panel_total || panelDentTotal + panelRITotal).toFixed(0)}
                          </span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        {/* Dents table */}
                        {panel.dents && panel.dents.length > 0 && (
                          <table className="w-full text-sm mb-4">
                            <thead>
                              <tr className="border-b text-left">
                                <th className="py-2 text-muted-foreground font-medium">#</th>
                                <th className="py-2 text-muted-foreground font-medium">Size</th>
                                <th className="py-2 text-muted-foreground font-medium">Zone</th>
                                <th className="py-2 text-muted-foreground font-medium">Depth</th>
                                <th className="py-2 text-right text-muted-foreground font-medium">Price</th>
                              </tr>
                            </thead>
                            <tbody>
                              {panel.dents.map((dent, idx) => (
                                <tr key={dent.id} className="border-b border-dashed">
                                  <td className="py-2">{idx + 1}</td>
                                  <td className="py-2 capitalize">
                                    {SIZE_LABELS[dent.size as keyof typeof SIZE_LABELS] || dent.size}
                                  </td>
                                  <td className="py-2 capitalize">{dent.zone}</td>
                                  <td className="py-2 capitalize">{(dent as any).depth || 'medium'}</td>
                                  <td className="py-2 text-right font-medium">
                                    ${(dent.final_price || 0).toFixed(0)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                            <tfoot>
                              <tr>
                                <td colSpan={4} className="py-2 font-medium">Dent Subtotal</td>
                                <td className="py-2 text-right font-medium">
                                  ${panelDentTotal.toFixed(0)}
                                </td>
                              </tr>
                            </tfoot>
                          </table>
                        )}

                        {/* R&I items */}
                        {panel.ri_items && panel.ri_items.length > 0 && (
                          <div className="bg-muted/50 p-3 rounded-lg">
                            <p className="text-sm font-medium mb-2">R&I Items</p>
                            {panel.ri_items.map(item => (
                              <div key={item.id} className="flex justify-between text-sm py-1">
                                <span>{item.operation_name}</span>
                                <span>${(item.price || 0).toFixed(0)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
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
                                <p className="text-sm text-muted-foreground">{discovery.panel_name}</p>
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
