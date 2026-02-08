/**
 * PDR Estimate Review Screen
 *
 * Two tabs: CUSTOMER VIEW (simplified) | DETAIL VIEW (full breakdown)
 * Customer view for signature approval
 * Detail view for internal/insurance use with matrix format
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  ArrowLeft,
  FileText,
  Printer,
  Send,
  Wrench,
  Car,
  DollarSign,
  Clock,
  CheckCircle2,
  Download,
  Table,
  Loader2,
  Eye,
  User
} from 'lucide-react'

import { SignaturePad } from '@/components/estimating/SignaturePad'
import { EstimateSummary } from '@/components/estimating/EstimateSummary'
import { SIZE_LABELS, ZONE_LABELS, DEPTH_LABELS } from '@/components/estimating/DentEntry'

import {
  usePDREstimate,
  useApprovePDREstimate,
  useCreateWorkOrder,
} from '@/hooks/use-pdr-estimates'
import { cn } from '@/lib/utils'

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  completed: 'bg-blue-100 text-blue-700'
}

export function EstimateReview() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState('customer')
  const [signature, setSignature] = useState<string | null>(null)
  const [showMatrixDialog, setShowMatrixDialog] = useState(false)
  const [isApproving, setIsApproving] = useState(false)

  // API hooks
  const { data: estimate, isLoading, refetch } = usePDREstimate(id ? parseInt(id) : null)
  const approveEstimate = useApprovePDREstimate()
  const createWorkOrder = useCreateWorkOrder()

  // Calculate stats
  const stats = useMemo(() => {
    if (!estimate) return { totalDents: 0, totalPanels: 0, totalRITime: 0 }

    let totalDents = 0
    let totalRITime = 0

    estimate.panels?.forEach(panel => {
      totalDents += panel.dents?.length || 0
      panel.ri_items?.forEach(ri => {
        totalRITime += ri.calculated_time_hours || 0
      })
    })

    return {
      totalDents,
      totalPanels: estimate.panels?.length || 0,
      totalRITime
    }
  }, [estimate])

  // Handle approve
  const handleApprove = async () => {
    if (!estimate || !signature) return

    setIsApproving(true)
    try {
      await approveEstimate.mutateAsync({ id: estimate.id, signature })
      refetch()
    } finally {
      setIsApproving(false)
    }
  }

  // Handle create work order
  const handleCreateWorkOrder = async () => {
    if (!estimate) return

    const workOrder = await createWorkOrder.mutateAsync({ estimateId: estimate.id })
    navigate(`/estimating/work-order/${workOrder.id}`)
  }

  // Generate matrix data
  const matrixData = useMemo(() => {
    if (!estimate?.panels) return []

    return estimate.panels.map(panel => {
      const dentsBySize: Record<string, number> = {}
      panel.dents?.forEach(dent => {
        const key = `${dent.size}`
        dentsBySize[key] = (dentsBySize[key] || 0) + 1
      })

      return {
        panel: panel.panel_name,
        displayName: panel.display_name || panel.panel_name,
        dents: dentsBySize,
        total: panel.panel_total || 0
      }
    })
  }, [estimate])

  if (isLoading) {
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
                Estimate #{estimate.estimate_number || estimate.id}
              </h1>
              <Badge className={cn('text-xs', STATUS_STYLES[estimate.status])}>
                {estimate.status}
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Printer className="h-4 w-4 mr-1" />
              Print
            </Button>
            {estimate.status === 'approved' && (
              <Button
                size="sm"
                onClick={handleCreateWorkOrder}
                disabled={createWorkOrder.isPending}
              >
                <Wrench className="h-4 w-4 mr-1" />
                Create Work Order
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full max-w-md mx-auto grid grid-cols-2 mb-6">
            <TabsTrigger value="customer" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Customer View
            </TabsTrigger>
            <TabsTrigger value="detail" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Detail View
            </TabsTrigger>
          </TabsList>

          {/* Customer View Tab */}
          <TabsContent value="customer">
            <div className="max-w-lg mx-auto space-y-4">
              {/* Vehicle Info */}
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <Car className="h-8 w-8 text-primary" />
                    <div>
                      <p className="font-bold text-lg">
                        {estimate.vehicle_year} {estimate.vehicle_make} {estimate.vehicle_model}
                      </p>
                      {estimate.vehicle_vin && (
                        <p className="text-sm text-muted-foreground">
                          VIN: {estimate.vehicle_vin}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Customer Info */}
              {estimate.customer_name && (
                <Card>
                  <CardContent className="pt-4">
                    <p className="font-medium">{estimate.customer_name}</p>
                    {estimate.customer_phone && (
                      <p className="text-sm text-muted-foreground">{estimate.customer_phone}</p>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Panel Summary (simplified) */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Repair Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {estimate.panels?.map(panel => (
                    <div key={panel.id} className="flex justify-between items-center">
                      <span>{panel.display_name || panel.panel_name}</span>
                      <Badge variant="secondary">
                        {panel.dents?.length || 0} dent{(panel.dents?.length || 0) !== 1 ? 's' : ''}
                      </Badge>
                    </div>
                  ))}
                  <div className="border-t pt-2 flex justify-between font-medium">
                    <span>Total Dents</span>
                    <span>{stats.totalDents}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Grand Total */}
              <Card className="bg-primary/5 border-primary/20">
                <CardContent className="pt-6 pb-6">
                  <div className="text-center">
                    <p className="text-muted-foreground mb-1">Estimate Total</p>
                    <p className="text-4xl font-bold text-primary">
                      ${estimate.grand_total?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Terms */}
              <Card>
                <CardContent className="pt-4">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    By signing below, I authorize the paintless dent repair work described
                    in this estimate. I understand that additional charges may apply if
                    hidden damage is discovered during the repair process. Any additional
                    work will be documented and communicated before proceeding.
                  </p>
                </CardContent>
              </Card>

              {/* Signature */}
              {estimate.status === 'draft' || estimate.status === 'pending' ? (
                <>
                  <SignaturePad
                    onSignatureChange={setSignature}
                    title="Customer Signature"
                  />

                  <Button
                    className="w-full"
                    size="lg"
                    onClick={handleApprove}
                    disabled={!signature || isApproving}
                  >
                    {isApproving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Approving...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        I Approve This Estimate
                      </>
                    )}
                  </Button>
                </>
              ) : (
                <Card className="bg-green-50 border-green-200">
                  <CardContent className="pt-4 text-center">
                    <CheckCircle2 className="h-8 w-8 text-green-600 mx-auto mb-2" />
                    <p className="font-medium text-green-700">Estimate Approved</p>
                    <p className="text-sm text-green-600">
                      Approved on {new Date(estimate.updated_at).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Detail View Tab */}
          <TabsContent value="detail">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left: Info & Stats */}
              <div className="space-y-4">
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
                    {estimate.vehicle_tier && (
                      <Badge variant="outline" className="mt-2">
                        {estimate.vehicle_tier} tier
                      </Badge>
                    )}
                  </CardContent>
                </Card>

                {/* Customer */}
                {estimate.customer_name && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Customer</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="font-medium">{estimate.customer_name}</p>
                      {estimate.customer_email && (
                        <p className="text-sm text-muted-foreground">{estimate.customer_email}</p>
                      )}
                      {estimate.customer_phone && (
                        <p className="text-sm text-muted-foreground">{estimate.customer_phone}</p>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Stats */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Dents</span>
                      <span className="font-medium">{stats.totalDents}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Panels</span>
                      <span className="font-medium">{stats.totalPanels}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">R&I Time</span>
                      <span className="font-medium">{stats.totalRITime.toFixed(2)} hrs</span>
                    </div>
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
                      <span>${(estimate.dent_total || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">R&I Items</span>
                      <span>${(estimate.ri_total || 0).toFixed(2)}</span>
                    </div>
                    <div className="border-t pt-2 flex justify-between text-lg">
                      <span className="font-bold">Grand Total</span>
                      <span className="font-bold text-green-600">
                        ${(estimate.grand_total || 0).toFixed(2)}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                {/* Actions */}
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => setShowMatrixDialog(true)}
                  >
                    <Table className="h-4 w-4 mr-2" />
                    View Matrix Format
                  </Button>
                  <Button variant="outline" className="w-full">
                    <Download className="h-4 w-4 mr-2" />
                    Export PDF
                  </Button>
                  <Button variant="outline" className="w-full">
                    <Send className="h-4 w-4 mr-2" />
                    Email to Customer
                  </Button>
                  {estimate.insurance_profile && (
                    <Button variant="outline" className="w-full">
                      <Send className="h-4 w-4 mr-2" />
                      Email to Insurance
                    </Button>
                  )}
                </div>
              </div>

              {/* Right: Panel Details */}
              <div className="lg:col-span-2 space-y-4">
                {estimate.panels?.map(panel => (
                  <Card key={panel.id}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base flex items-center justify-between">
                        <span>{panel.display_name || panel.panel_name}</span>
                        <span className="text-green-600">
                          ${(panel.panel_total || 0).toFixed(0)}
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {/* Dent Grid */}
                      {panel.dents && panel.dents.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs text-muted-foreground mb-2">
                            Dents ({panel.dents.length})
                          </p>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                            {panel.dents.map((dent, idx) => (
                              <div
                                key={dent.id || idx}
                                className="p-2 rounded-lg border text-center text-sm"
                              >
                                <p className="font-medium capitalize">
                                  {SIZE_LABELS[dent.size as keyof typeof SIZE_LABELS] || dent.size}
                                </p>
                                <p className="text-xs text-muted-foreground capitalize">
                                  {dent.zone} • {(dent as any).depth || 'medium'}
                                </p>
                                <p className="font-bold mt-1">
                                  ${(dent.final_price || 0).toFixed(0)}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* R&I Items */}
                      {panel.ri_items && panel.ri_items.length > 0 && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-2">
                            R&I Items ({panel.ri_items.length})
                          </p>
                          <div className="space-y-2">
                            {panel.ri_items.map((ri, idx) => (
                              <div
                                key={ri.id || idx}
                                className="p-2 bg-muted/50 rounded-lg"
                              >
                                <div className="flex justify-between">
                                  <span className="font-medium text-sm">
                                    {ri.operation_name}
                                  </span>
                                  <span className="font-medium">
                                    ${(ri.price || 0).toFixed(0)}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                                  <Clock className="h-3 w-3" />
                                  <span>{(ri.calculated_time_hours || 0).toFixed(2)} hrs</span>
                                </div>
                                {/* Scope bullets */}
                                {(ri.scope_min || ri.scope_typical) && (
                                  <div className="mt-2 text-xs space-y-1 border-t pt-2">
                                    {ri.scope_min && (
                                      <p><Badge variant="outline" className="text-[10px] mr-1">MIN</Badge>{ri.scope_min}</p>
                                    )}
                                    {ri.scope_typical && (
                                      <p><Badge className="text-[10px] mr-1">TYP</Badge>{ri.scope_typical}</p>
                                    )}
                                  </div>
                                )}
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
          </TabsContent>
        </Tabs>
      </div>

      {/* Matrix Dialog */}
      <Dialog open={showMatrixDialog} onOpenChange={setShowMatrixDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Insurance Matrix Format</DialogTitle>
          </DialogHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Panel</th>
                  <th className="text-center p-2">Dime</th>
                  <th className="text-center p-2">Nickel</th>
                  <th className="text-center p-2">Quarter</th>
                  <th className="text-center p-2">Half $</th>
                  <th className="text-center p-2">Silver $</th>
                  <th className="text-center p-2">Oversized</th>
                  <th className="text-right p-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {matrixData.map(row => (
                  <tr key={row.panel} className="border-b">
                    <td className="p-2 font-medium">{row.displayName}</td>
                    <td className="text-center p-2">{row.dents.dime || '-'}</td>
                    <td className="text-center p-2">{row.dents.nickel || '-'}</td>
                    <td className="text-center p-2">{row.dents.quarter || '-'}</td>
                    <td className="text-center p-2">{row.dents.half_dollar || '-'}</td>
                    <td className="text-center p-2">{row.dents.silver_dollar || '-'}</td>
                    <td className="text-center p-2">{row.dents.oversized || '-'}</td>
                    <td className="text-right p-2 font-medium">${row.total.toFixed(0)}</td>
                  </tr>
                ))}
                <tr className="font-bold">
                  <td className="p-2">TOTAL</td>
                  <td colSpan={6}></td>
                  <td className="text-right p-2 text-green-600">
                    ${(estimate.grand_total || 0).toFixed(0)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowMatrixDialog(false)}>
              Close
            </Button>
            <Button>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default EstimateReview
