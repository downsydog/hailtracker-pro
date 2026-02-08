/**
 * PDR Invoice & Supplement Generator
 *
 * Final invoice screen that auto-generates supplement narrative
 * when discoveries exist. Shows complete breakdown with evidence chain.
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
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
  Copy
} from 'lucide-react'

// Types
interface Dent {
  id: number
  size: string
  zone: string
  final_price: number
  panel_name: string
}

interface RinItem {
  id: number
  item_name: string
  display_name: string
  price: number
  time_hours: number
  panel_name: string
}

interface Discovery {
  id: number
  type: string
  display_name: string
  description: string
  additional_time_hours: number
  additional_cost: number
  photo_url?: string
  panel_name: string
  dent_id?: number
  created_at: string
}

interface Invoice {
  id: number
  work_order_id: number
  estimate_id: number
  customer_name: string
  customer_email?: string
  customer_phone?: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_vin?: string
  original_total: number
  supplement_total: number
  grand_total: number
  dents: Dent[]
  rin_items: RinItem[]
  discoveries: Discovery[]
  work_time_hours: number
  created_at: string
}

// Mock invoice data
const mockInvoice: Invoice = {
  id: 1,
  work_order_id: 1,
  estimate_id: 1,
  customer_name: 'John Smith',
  customer_email: 'john.smith@email.com',
  customer_phone: '(555) 123-4567',
  vehicle_year: 2022,
  vehicle_make: 'Toyota',
  vehicle_model: 'Camry',
  vehicle_vin: '1HGCG5655WA123456',
  original_total: 1001,
  supplement_total: 250,
  grand_total: 1251,
  dents: [
    { id: 1, size: 'medium', zone: 'center', final_price: 75, panel_name: 'Hood' },
    { id: 2, size: 'medium', zone: 'center', final_price: 75, panel_name: 'Hood' },
    { id: 3, size: 'small', zone: 'edge', final_price: 70, panel_name: 'Hood' },
    { id: 4, size: 'large', zone: 'crease', final_price: 160, panel_name: 'Hood' },
    { id: 5, size: 'medium', zone: 'center', final_price: 90, panel_name: 'Roof' },
    { id: 6, size: 'medium', zone: 'center', final_price: 90, panel_name: 'Roof' },
    { id: 7, size: 'medium', zone: 'edge', final_price: 126, panel_name: 'Roof' },
    { id: 8, size: 'small', zone: 'center', final_price: 50, panel_name: 'Driver Door' },
    { id: 9, size: 'medium', zone: 'edge', final_price: 105, panel_name: 'Driver Door' }
  ],
  rin_items: [
    { id: 1, item_name: 'cowl_panel', display_name: 'Cowl Panel', price: 25, time_hours: 0.25, panel_name: 'Hood' },
    { id: 2, item_name: 'headliner_partial', display_name: 'Headliner Partial', price: 75, time_hours: 0.75, panel_name: 'Roof' },
    { id: 3, item_name: 'door_handle_removal', display_name: 'Door Handle Removal', price: 25, time_hours: 0.25, panel_name: 'Driver Door' },
    { id: 4, item_name: 'door_trim_panel', display_name: 'Door Trim Panel', price: 35, time_hours: 0.33, panel_name: 'Driver Door' }
  ],
  discoveries: [
    {
      id: 1,
      type: 'hidden_damage',
      display_name: 'Hidden Damage',
      description: 'Additional dents discovered under hood liner, not visible during initial inspection',
      additional_time_hours: 0.5,
      additional_cost: 75,
      panel_name: 'Hood',
      dent_id: 4,
      created_at: new Date().toISOString()
    },
    {
      id: 2,
      type: 'headliner_drop',
      display_name: 'Headliner Drop',
      description: 'Full headliner drop required for access to rear section of roof panel',
      additional_time_hours: 1.5,
      additional_cost: 150,
      panel_name: 'Roof',
      created_at: new Date().toISOString()
    },
    {
      id: 3,
      type: 'access_difficulty',
      display_name: 'Access Difficulty',
      description: 'Reinforcement bar requiring additional tool manipulation time',
      additional_time_hours: 0.25,
      additional_cost: 25,
      panel_name: 'Driver Door',
      created_at: new Date().toISOString()
    }
  ],
  work_time_hours: 3.5,
  created_at: new Date().toISOString()
}

// Generate supplement narrative
function generateSupplementNarrative(invoice: Invoice): string {
  const vehicle = `${invoice.vehicle_year} ${invoice.vehicle_make} ${invoice.vehicle_model}`
  const count = invoice.discoveries.length

  let narrative = `SUPPLEMENT REQUEST\n\n`
  narrative += `During the paintless dent repair process on the ${vehicle}, `
  narrative += `${count} additional item${count !== 1 ? 's were' : ' was'} `
  narrative += `discovered that were not visible or accessible during the initial inspection.\n\n`

  // Group discoveries by type
  const types: Record<string, number> = {}
  invoice.discoveries.forEach(d => {
    types[d.type] = (types[d.type] || 0) + 1
  })

  narrative += `DISCOVERIES:\n`
  Object.entries(types).forEach(([type, typeCount]) => {
    narrative += `  - ${type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}: ${typeCount}\n`
  })

  const totalTime = invoice.discoveries.reduce((sum, d) => sum + d.additional_time_hours, 0)
  const totalCost = invoice.discoveries.reduce((sum, d) => sum + d.additional_cost, 0)

  narrative += `\nTOTAL ADDITIONAL TIME: ${totalTime.toFixed(2)} hours\n`
  narrative += `TOTAL ADDITIONAL COST: $${totalCost.toFixed(2)}\n\n`

  narrative += `All additional items were documented at the time of discovery `
  narrative += `with photographs where applicable. These items are necessary `
  narrative += `for proper and complete repair of the hail damage.\n\n`

  narrative += `Please review and approve this supplement to proceed with complete repair.`

  return narrative
}

// Generate individual discovery narratives
function generateDiscoveryNarrative(discovery: Discovery): string {
  const type = discovery.type.replace(/_/g, ' ')

  let narrative = `During repair of the ${discovery.panel_name}, technician discovered that ${type}`

  if (discovery.description) {
    narrative += ` (${discovery.description})`
  }

  narrative += ` was required for proper tool access. `
  narrative += `This condition was not visible during the initial estimate.`

  if (discovery.additional_time_hours > 0) {
    narrative += ` Additional time: ${discovery.additional_time_hours} hours.`
  }
  if (discovery.additional_cost > 0) {
    narrative += ` Additional cost: $${discovery.additional_cost.toFixed(2)}.`
  }

  return narrative
}

export function InvoiceSupplement() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const invoice = mockInvoice
  const hasSupplements = invoice.discoveries.length > 0

  // Group dents by panel
  const dentsByPanel = useMemo(() => {
    const grouped: Record<string, typeof invoice.dents> = {}
    invoice.dents.forEach(dent => {
      if (!grouped[dent.panel_name]) grouped[dent.panel_name] = []
      grouped[dent.panel_name].push(dent)
    })
    return grouped
  }, [invoice.dents])

  // Group R&I by panel
  const rinByPanel = useMemo(() => {
    const grouped: Record<string, typeof invoice.rin_items> = {}
    invoice.rin_items.forEach(item => {
      if (!grouped[item.panel_name]) grouped[item.panel_name] = []
      grouped[item.panel_name].push(item)
    })
    return grouped
  }, [invoice.rin_items])

  // Calculate totals
  const totals = useMemo(() => {
    const dentTotal = invoice.dents.reduce((sum, d) => sum + d.final_price, 0)
    const rinTotal = invoice.rin_items.reduce((sum, r) => sum + r.price, 0)
    const supplementTotal = invoice.discoveries.reduce((sum, d) => sum + d.additional_cost, 0)

    return {
      dentTotal,
      rinTotal,
      originalTotal: dentTotal + rinTotal,
      supplementTotal,
      grandTotal: dentTotal + rinTotal + supplementTotal
    }
  }, [invoice])

  const supplementNarrative = useMemo(() => {
    if (!hasSupplements) return ''
    return generateSupplementNarrative(invoice)
  }, [invoice, hasSupplements])

  const copyNarrative = () => {
    navigator.clipboard.writeText(supplementNarrative)
  }

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <FileText className="h-6 w-6" />
              Invoice #{invoice.id}
            </h1>
            {hasSupplements && (
              <Badge className="bg-orange-100 text-orange-700">
                <AlertCircle className="h-3 w-3 mr-1" />
                Supplement Required
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            Work Order #{invoice.work_order_id} - {new Date(invoice.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Printer className="h-4 w-4 mr-2" />
            Print
          </Button>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Download PDF
          </Button>
          <Button>
            <Send className="h-4 w-4 mr-2" />
            Send to Insurance
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Customer & Vehicle info */}
        <div className="space-y-4">
          {/* Customer */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Customer</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="font-medium">{invoice.customer_name}</p>
              {invoice.customer_email && (
                <p className="text-sm text-muted-foreground">{invoice.customer_email}</p>
              )}
              {invoice.customer_phone && (
                <p className="text-sm text-muted-foreground">{invoice.customer_phone}</p>
              )}
            </CardContent>
          </Card>

          {/* Vehicle */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Car className="h-5 w-5" />
                Vehicle
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-medium">
                {invoice.vehicle_year} {invoice.vehicle_make} {invoice.vehicle_model}
              </p>
              {invoice.vehicle_vin && (
                <p className="text-sm text-muted-foreground mt-1">VIN: {invoice.vehicle_vin}</p>
              )}
            </CardContent>
          </Card>

          {/* Work Summary */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Work Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Dents</span>
                <span className="font-medium">{invoice.dents.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">R&I Items</span>
                <span className="font-medium">{invoice.rin_items.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Discoveries</span>
                <span className="font-medium">{invoice.discoveries.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Work Time</span>
                <span className="font-medium">{invoice.work_time_hours} hours</span>
              </div>
            </CardContent>
          </Card>

          {/* Totals */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Totals
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Dent Repair</span>
                <span className="font-medium">${totals.dentTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">R&I Items</span>
                <span className="font-medium">${totals.rinTotal.toFixed(2)}</span>
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
                <span className="font-bold text-green-600">${totals.grandTotal.toFixed(2)}</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: Details */}
        <div className="lg:col-span-2">
          <Tabs defaultValue={hasSupplements ? 'supplement' : 'invoice'}>
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
              {/* Panel breakdown */}
              {Object.entries(dentsByPanel).map(([panelName, dents]) => {
                const panelDentTotal = dents.reduce((sum, d) => sum + d.final_price, 0)
                const panelRin = rinByPanel[panelName] || []
                const panelRinTotal = panelRin.reduce((sum, r) => sum + r.price, 0)

                return (
                  <Card key={panelName}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center justify-between">
                        <span>{panelName}</span>
                        <span className="text-green-600">${(panelDentTotal + panelRinTotal).toFixed(0)}</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {/* Dents table */}
                      <table className="w-full text-sm mb-4">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2">Dent</th>
                            <th className="text-left py-2">Size</th>
                            <th className="text-left py-2">Zone</th>
                            <th className="text-right py-2">Price</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dents.map((dent, idx) => (
                            <tr key={dent.id} className="border-b border-dashed">
                              <td className="py-2">#{idx + 1}</td>
                              <td className="py-2 capitalize">{dent.size}</td>
                              <td className="py-2 capitalize">{dent.zone}</td>
                              <td className="py-2 text-right">${dent.final_price.toFixed(0)}</td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr>
                            <td colSpan={3} className="py-2 font-medium">Dent Subtotal</td>
                            <td className="py-2 text-right font-medium">${panelDentTotal.toFixed(0)}</td>
                          </tr>
                        </tfoot>
                      </table>

                      {/* R&I items */}
                      {panelRin.length > 0 && (
                        <div className="bg-muted/50 p-3 rounded-lg">
                          <p className="text-sm font-medium mb-2">R&I Items</p>
                          {panelRin.map(item => (
                            <div key={item.id} className="flex justify-between text-sm">
                              <span>{item.display_name}</span>
                              <span>${item.price.toFixed(0)}</span>
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
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center justify-between">
                      <span>Insurance Narrative</span>
                      <Button variant="outline" size="sm" onClick={copyNarrative}>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="whitespace-pre-wrap text-sm font-mono bg-muted p-4 rounded-lg">
                      {supplementNarrative}
                    </pre>
                  </CardContent>
                </Card>

                {/* Individual discoveries */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Discovery Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {invoice.discoveries.map((discovery, idx) => (
                      <div key={discovery.id} className="p-4 border rounded-lg">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h4 className="font-medium">
                              #{idx + 1} - {discovery.display_name}
                            </h4>
                            <p className="text-sm text-muted-foreground">{discovery.panel_name}</p>
                          </div>
                          <Badge className="bg-orange-100 text-orange-700">
                            +${discovery.additional_cost.toFixed(0)}
                          </Badge>
                        </div>

                        <p className="text-sm mb-3">{generateDiscoveryNarrative(discovery)}</p>

                        <div className="flex gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            {discovery.additional_time_hours} hours
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

                {/* Evidence chain */}
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Evidence Chain</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {invoice.discoveries.map((discovery, idx) => (
                        <div
                          key={discovery.id}
                          className="flex items-center gap-3 p-2 bg-muted/50 rounded"
                        >
                          <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-700 font-bold text-sm">
                            {idx + 1}
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-medium">{discovery.display_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(discovery.created_at).toLocaleString()}
                            </p>
                          </div>
                          <span className="text-sm font-medium text-orange-600">
                            +${discovery.additional_cost.toFixed(0)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>
        </div>
      </div>
    </div>
  )
}

export default InvoiceSupplement
