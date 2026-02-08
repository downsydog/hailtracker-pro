/**
 * PDR Work Order Screen
 *
 * Tech's working view for repairs.
 * Features:
 * - Panel view with dent details
 * - R&I checklist
 * - Discovery logging with photo capture
 * - Timer tracking
 * - Completion workflow
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  Clock,
  Wrench,
  FileText,
  Plus,
  Play,
  Pause,
  Square,
  AlertCircle,
  Camera,
  Loader2
} from 'lucide-react'

import { DiscoveryForm, DiscoveryItem, DISCOVERY_TYPES } from '@/components/estimating/DiscoveryForm'
import { SIZE_LABELS, ZONE_LABELS, DEPTH_LABELS } from '@/components/estimating/DentEntry'

import {
  useWorkOrder,
  useUpdateWorkOrder,
  useAddDiscovery,
} from '@/hooks/use-pdr-estimates'
import { cn } from '@/lib/utils'

const STATUS_STYLES: Record<string, string> = {
  assigned: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700'
}

export function WorkOrder() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [selectedPanelId, setSelectedPanelId] = useState<number | null>(null)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [discoveryDialogOpen, setDiscoveryDialogOpen] = useState(false)
  const [completedDents, setCompletedDents] = useState<Set<number>>(new Set())
  const [completedRI, setCompletedRI] = useState<Set<number>>(new Set())

  // API hooks
  const { data: workOrder, isLoading, refetch } = useWorkOrder(id ? parseInt(id) : null)
  const updateWorkOrder = useUpdateWorkOrder()
  const addDiscovery = useAddDiscovery()

  // Initialize timer from work order
  useEffect(() => {
    if (workOrder?.total_time_minutes) {
      setElapsedSeconds(workOrder.total_time_minutes * 60)
    }
    if (workOrder?.status === 'in_progress' && workOrder.start_time) {
      setIsTimerRunning(true)
    }
  }, [workOrder])

  // Timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (isTimerRunning) {
      interval = setInterval(() => {
        setElapsedSeconds(prev => prev + 1)
      }, 1000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isTimerRunning])

  // Selected panel
  const selectedPanel = useMemo(() => {
    if (!workOrder || !selectedPanelId) return null
    return workOrder.panels?.find(p => p.id === selectedPanelId) || null
  }, [workOrder, selectedPanelId])

  // Auto-select first panel
  useEffect(() => {
    if (workOrder?.panels?.length && !selectedPanelId) {
      setSelectedPanelId(workOrder.panels[0].id)
    }
  }, [workOrder, selectedPanelId])

  // Progress stats
  const stats = useMemo(() => {
    if (!workOrder) return { totalDents: 0, completedDents: 0, progress: 0, discoveryTotal: 0 }

    let totalDents = 0
    workOrder.panels?.forEach(panel => {
      totalDents += panel.dents?.length || 0
    })

    const discoveryTotal = workOrder.discoveries?.reduce((sum, d) => sum + (d.additional_cost || 0), 0) || 0

    return {
      totalDents,
      completedDents: completedDents.size,
      progress: totalDents > 0 ? Math.round((completedDents.size / totalDents) * 100) : 0,
      discoveryTotal
    }
  }, [workOrder, completedDents])

  // Format time
  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Toggle dent completion
  const toggleDent = useCallback((dentId: number) => {
    setCompletedDents(prev => {
      const newSet = new Set(prev)
      if (newSet.has(dentId)) {
        newSet.delete(dentId)
      } else {
        newSet.add(dentId)
      }
      return newSet
    })
  }, [])

  // Toggle R&I completion
  const toggleRI = useCallback((riId: number) => {
    setCompletedRI(prev => {
      const newSet = new Set(prev)
      if (newSet.has(riId)) {
        newSet.delete(riId)
      } else {
        newSet.add(riId)
      }
      return newSet
    })
  }, [])

  // Handle timer toggle
  const handleTimerToggle = async () => {
    if (!workOrder) return

    if (!isTimerRunning && workOrder.status === 'assigned') {
      // Start work
      await updateWorkOrder.mutateAsync({
        id: workOrder.id,
        data: {
          status: 'in_progress',
          start_time: new Date().toISOString()
        }
      })
      refetch()
    }

    setIsTimerRunning(!isTimerRunning)
  }

  // Handle discovery submit
  const handleDiscoverySubmit = async (data: {
    discovery_type: string
    description: string
    additional_time_hours: number
    additional_cost: number
    photo_base64: string | null
    panel_name?: string
  }) => {
    if (!workOrder) return

    await addDiscovery.mutateAsync({
      workOrderId: workOrder.id,
      data: {
        discovery_type: data.discovery_type,
        description: data.description,
        additional_time_hours: data.additional_time_hours,
        additional_cost: data.additional_cost,
        photo_base64: data.photo_base64 || undefined,
        panel_name: selectedPanel?.panel_name || data.panel_name
      }
    })

    setDiscoveryDialogOpen(false)
    refetch()
  }

  // Handle complete
  const handleComplete = async () => {
    if (!workOrder) return

    await updateWorkOrder.mutateAsync({
      id: workOrder.id,
      data: {
        status: 'completed',
        end_time: new Date().toISOString(),
        total_time_minutes: Math.floor(elapsedSeconds / 60)
      }
    })

    setIsTimerRunning(false)
    navigate(`/estimating/invoice/${workOrder.estimate_id}`)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!workOrder) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Work order not found</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-background border-b">
        <div className="flex items-center justify-between p-4 max-w-6xl mx-auto">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-bold flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                Work Order #{workOrder.work_order_number || workOrder.id}
              </h1>
              <div className="flex items-center gap-2">
                <Badge className={cn('text-xs', STATUS_STYLES[workOrder.status])}>
                  {workOrder.status.replace('_', ' ').toUpperCase()}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {workOrder.customer_name}
                </span>
              </div>
            </div>
          </div>

          {/* Timer */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
              <Clock className="h-4 w-4" />
              <span className="font-mono font-bold text-lg">
                {formatTime(elapsedSeconds)}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handleTimerToggle}
              >
                {isTimerRunning ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="px-4 pb-4 max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">
              {stats.completedDents} of {stats.totalDents} dents completed
            </span>
            <span className="font-bold">{stats.progress}%</span>
          </div>
          <Progress value={stats.progress} className="h-3" />
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: Panel List */}
          <div className="space-y-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Panels</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {workOrder.panels?.map(panel => {
                  const panelDents = panel.dents?.length || 0
                  const panelCompleted = panel.dents?.filter(d => completedDents.has(d.id)).length || 0
                  const isComplete = panelCompleted === panelDents && panelDents > 0

                  return (
                    <button
                      key={panel.id}
                      onClick={() => setSelectedPanelId(panel.id)}
                      className={cn(
                        'w-full p-3 rounded-lg border text-left transition-colors',
                        selectedPanelId === panel.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:bg-accent/50'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isComplete ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                          ) : (
                            <Circle className="h-5 w-5 text-muted-foreground" />
                          )}
                          <span className="font-medium">
                            {panel.display_name || panel.panel_name}
                          </span>
                        </div>
                        <Badge variant="secondary">
                          {panelCompleted}/{panelDents}
                        </Badge>
                      </div>
                    </button>
                  )
                })}
              </CardContent>
            </Card>

            {/* Discoveries Summary */}
            {workOrder.discoveries && workOrder.discoveries.length > 0 && (
              <Card className="bg-orange-50 border-orange-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2 text-orange-700">
                    <AlertCircle className="h-4 w-4" />
                    Discoveries ({workOrder.discoveries.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-orange-600">
                    +${stats.discoveryTotal.toFixed(0)}
                  </p>
                  <p className="text-xs text-orange-600">
                    Supplement required
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Vehicle Info */}
            <Card>
              <CardContent className="pt-4">
                <p className="text-sm text-muted-foreground">Vehicle</p>
                <p className="font-medium">{workOrder.vehicle}</p>
              </CardContent>
            </Card>
          </div>

          {/* Center & Right: Dent List and R&I */}
          <div className="lg:col-span-2 space-y-4">
            {selectedPanel ? (
              <>
                {/* Panel Header */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center justify-between">
                      <span>{selectedPanel.display_name || selectedPanel.panel_name}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDiscoveryDialogOpen(true)}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Add Discovery
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {/* Dent Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {selectedPanel.dents?.map(dent => {
                        const isComplete = completedDents.has(dent.id)

                        return (
                          <button
                            key={dent.id}
                            onClick={() => toggleDent(dent.id)}
                            className={cn(
                              'p-4 rounded-lg border-2 text-left transition-all',
                              isComplete
                                ? 'border-green-500 bg-green-50'
                                : 'border-gray-200 hover:border-gray-400'
                            )}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium capitalize text-sm">
                                {SIZE_LABELS[dent.size as keyof typeof SIZE_LABELS] || dent.size}
                              </span>
                              {isComplete ? (
                                <CheckCircle2 className="h-5 w-5 text-green-500" />
                              ) : (
                                <Circle className="h-5 w-5 text-gray-300" />
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground capitalize">
                              {dent.zone} • {(dent as any).depth || 'medium'}
                            </p>
                            <p className="text-lg font-bold mt-2">
                              ${(dent.final_price || 0).toFixed(0)}
                            </p>
                          </button>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>

                {/* R&I Checklist */}
                {selectedPanel.ri_items && selectedPanel.ri_items.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">R&I Checklist</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {selectedPanel.ri_items.map(ri => {
                        const isComplete = completedRI.has(ri.id)

                        return (
                          <div
                            key={ri.id}
                            className={cn(
                              'p-3 rounded-lg border transition-colors',
                              isComplete && 'bg-green-50 border-green-200'
                            )}
                          >
                            <div className="flex items-start gap-3">
                              <Checkbox
                                checked={isComplete}
                                onCheckedChange={() => toggleRI(ri.id)}
                                className="mt-0.5"
                              />
                              <div className="flex-1">
                                <p className="font-medium text-sm">
                                  {ri.operation_name}
                                </p>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                                  <Clock className="h-3 w-3" />
                                  <span>{(ri.calculated_time_hours || 0).toFixed(2)} hrs</span>
                                  <span>•</span>
                                  <span>${(ri.price || 0).toFixed(0)}</span>
                                </div>
                                {/* Scope bullets */}
                                {ri.scope_typical && (
                                  <p className="text-xs text-muted-foreground mt-2 p-2 bg-muted/50 rounded">
                                    {ri.scope_typical}
                                  </p>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </CardContent>
                  </Card>
                )}

                {/* Panel Discoveries */}
                {workOrder.discoveries?.filter(d => d.panel_name === selectedPanel.panel_name).length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-orange-500" />
                        Discoveries on this panel
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      {workOrder.discoveries
                        ?.filter(d => d.panel_name === selectedPanel.panel_name)
                        .map(discovery => (
                          <DiscoveryItem key={discovery.id} discovery={discovery} />
                        ))}
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Wrench className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">Select a panel to view dents</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Progress</p>
              <p className="font-bold">{stats.progress}%</p>
            </div>
            {stats.discoveryTotal > 0 && (
              <div>
                <p className="text-xs text-orange-600">Supplement</p>
                <p className="font-bold text-orange-600">+${stats.discoveryTotal}</p>
              </div>
            )}
          </div>
          <Button
            size="lg"
            onClick={handleComplete}
            disabled={stats.progress < 100 || updateWorkOrder.isPending}
          >
            {updateWorkOrder.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <FileText className="h-4 w-4 mr-2" />
            )}
            Mark Complete & Generate Invoice
          </Button>
        </div>
      </div>

      {/* Discovery Dialog */}
      <Dialog open={discoveryDialogOpen} onOpenChange={setDiscoveryDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              Log Discovery
            </DialogTitle>
          </DialogHeader>
          <DiscoveryForm
            panelName={selectedPanel?.panel_name}
            onSubmit={handleDiscoverySubmit}
            onCancel={() => setDiscoveryDialogOpen(false)}
            isSubmitting={addDiscovery.isPending}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default WorkOrder
