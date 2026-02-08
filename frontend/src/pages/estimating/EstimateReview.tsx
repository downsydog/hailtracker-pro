/**
 * PDR Estimate Review Screen
 *
 * Read-only view of the estimate. Shows panel → dent grid,
 * highlights complex dents, totals with R&I breakdown.
 * CTA: "Create Work Order"
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  FileText,
  Printer,
  Send,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  Car,
  DollarSign,
  Clock
} from 'lucide-react'

// Types
interface Dent {
  id: number
  size: 'small' | 'medium' | 'large' | 'xlarge'
  zone: 'center' | 'edge' | 'crease'
  base_price: number
  final_price: number
  complexity: 'low' | 'medium' | 'high'
}

interface RinItem {
  id: number
  item_name: string
  display_name: string
  price: number
  time_hours: number
}

interface Panel {
  id: number
  panel_name: string
  display_name: string
  dents: Dent[]
  rin_items: RinItem[]
  panel_total: number
}

interface Estimate {
  id: number
  customer_name: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
  vehicle_vin?: string
  status: 'draft' | 'pending' | 'approved' | 'converted'
  panels: Panel[]
  dent_total: number
  rin_total: number
  grand_total: number
  created_at: string
}

// Mock data for demo
const mockEstimate: Estimate = {
  id: 1,
  customer_name: 'John Smith',
  vehicle_year: 2022,
  vehicle_make: 'Toyota',
  vehicle_model: 'Camry',
  vehicle_vin: '1HGCG5655WA123456',
  status: 'pending',
  panels: [
    {
      id: 1,
      panel_name: 'hood',
      display_name: 'Hood',
      dents: [
        { id: 1, size: 'medium', zone: 'center', base_price: 75, final_price: 75, complexity: 'low' },
        { id: 2, size: 'medium', zone: 'center', base_price: 75, final_price: 75, complexity: 'low' },
        { id: 3, size: 'small', zone: 'edge', base_price: 50, final_price: 70, complexity: 'medium' },
        { id: 4, size: 'large', zone: 'crease', base_price: 100, final_price: 160, complexity: 'high' }
      ],
      rin_items: [
        { id: 1, item_name: 'cowl_panel', display_name: 'Cowl Panel', price: 25, time_hours: 0.25 }
      ],
      panel_total: 405
    },
    {
      id: 2,
      panel_name: 'roof',
      display_name: 'Roof',
      dents: [
        { id: 5, size: 'medium', zone: 'center', base_price: 75, final_price: 90, complexity: 'low' },
        { id: 6, size: 'medium', zone: 'center', base_price: 75, final_price: 90, complexity: 'low' },
        { id: 7, size: 'medium', zone: 'edge', base_price: 75, final_price: 126, complexity: 'medium' }
      ],
      rin_items: [
        { id: 2, item_name: 'headliner_partial', display_name: 'Headliner Partial', price: 75, time_hours: 0.75 }
      ],
      panel_total: 381
    },
    {
      id: 3,
      panel_name: 'driver_door',
      display_name: 'Driver Door',
      dents: [
        { id: 8, size: 'small', zone: 'center', base_price: 50, final_price: 50, complexity: 'low' },
        { id: 9, size: 'medium', zone: 'edge', base_price: 75, final_price: 105, complexity: 'medium' }
      ],
      rin_items: [
        { id: 3, item_name: 'door_handle_removal', display_name: 'Door Handle Removal', price: 25, time_hours: 0.25 },
        { id: 4, item_name: 'door_trim_panel', display_name: 'Door Trim Panel', price: 35, time_hours: 0.33 }
      ],
      panel_total: 215
    }
  ],
  dent_total: 841,
  rin_total: 160,
  grand_total: 1001,
  created_at: '2024-01-20T10:30:00Z'
}

const statusColors = {
  draft: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  converted: 'bg-blue-100 text-blue-700'
}

const complexityColors = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-700'
}

export function EstimateReview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // In real app, fetch estimate by id
  const estimate = mockEstimate

  // Calculate stats
  const stats = useMemo(() => {
    let totalDents = 0
    let highComplexity = 0
    let totalRinTime = 0

    estimate.panels.forEach(panel => {
      totalDents += panel.dents.length
      highComplexity += panel.dents.filter(d => d.complexity === 'high').length
      totalRinTime += panel.rin_items.reduce((sum, r) => sum + r.time_hours, 0)
    })

    return { totalDents, highComplexity, totalRinTime }
  }, [estimate])

  const handleCreateWorkOrder = () => {
    // API call to create work order from estimate
    console.log('Creating work order from estimate:', estimate.id)
    // navigate(`/estimating/work-order/${newWorkOrderId}`)
  }

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">Estimate #{estimate.id}</h1>
            <Badge className={statusColors[estimate.status]}>
              {estimate.status.charAt(0).toUpperCase() + estimate.status.slice(1)}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            Created {new Date(estimate.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline">
            <Printer className="h-4 w-4 mr-2" />
            Print
          </Button>
          <Button variant="outline">
            <Send className="h-4 w-4 mr-2" />
            Send to Customer
          </Button>
          <Button onClick={handleCreateWorkOrder}>
            <Wrench className="h-4 w-4 mr-2" />
            Create Work Order
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Vehicle & Customer Info */}
        <div className="space-y-4">
          {/* Customer */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Customer</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-medium">{estimate.customer_name}</p>
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
                {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
              </p>
              {estimate.vehicle_vin && (
                <p className="text-sm text-muted-foreground mt-1">VIN: {estimate.vehicle_vin}</p>
              )}
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Total Dents</span>
                <span className="font-medium">{stats.totalDents}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Panels</span>
                <span className="font-medium">{estimate.panels.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  High Complexity
                </span>
                <span className="font-medium text-red-600">{stats.highComplexity}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  Est. R&I Time
                </span>
                <span className="font-medium">{stats.totalRinTime.toFixed(2)} hrs</span>
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
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Dent Repair</span>
                <span className="font-medium">${estimate.dent_total.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">R&I Items</span>
                <span className="font-medium">${estimate.rin_total.toFixed(2)}</span>
              </div>
              <div className="border-t pt-3 flex items-center justify-between text-lg">
                <span className="font-bold">Grand Total</span>
                <span className="font-bold text-green-600">${estimate.grand_total.toFixed(2)}</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: Panel Details */}
        <div className="lg:col-span-2 space-y-4">
          {estimate.panels.map(panel => (
            <Card key={panel.id}>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center justify-between">
                  <span>{panel.display_name}</span>
                  <span className="text-green-600">${panel.panel_total.toFixed(0)}</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Dent Grid */}
                <div className="mb-4">
                  <p className="text-sm text-muted-foreground mb-2">
                    Dents ({panel.dents.length})
                  </p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {panel.dents.map(dent => (
                      <div
                        key={dent.id}
                        className={`p-2 rounded-lg border text-center ${
                          dent.complexity === 'high' ? 'border-red-300 bg-red-50' :
                          dent.complexity === 'medium' ? 'border-yellow-300 bg-yellow-50' :
                          'border-gray-200'
                        }`}
                      >
                        <p className="text-sm font-medium">{dent.size}</p>
                        <p className="text-xs text-muted-foreground">{dent.zone}</p>
                        <p className="text-sm font-bold mt-1">${dent.final_price.toFixed(0)}</p>
                        {dent.complexity !== 'low' && (
                          <Badge className={`mt-1 text-xs ${complexityColors[dent.complexity]}`}>
                            {dent.complexity}
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* R&I Items */}
                {panel.rin_items.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">
                      R&I Items ({panel.rin_items.length})
                    </p>
                    <div className="space-y-1">
                      {panel.rin_items.map(item => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between text-sm p-2 bg-muted/50 rounded"
                        >
                          <span>{item.display_name}</span>
                          <div className="flex items-center gap-4">
                            <span className="text-muted-foreground">{item.time_hours} hrs</span>
                            <span className="font-medium">${item.price.toFixed(0)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}

export default EstimateReview
