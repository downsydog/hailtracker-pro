/**
 * PDR Work Order Screen - Matrix Based
 *
 * Tech's working view for repairs using matrix-based pricing.
 * Features:
 * - Panel view with matrix pricing info (dent count, majority size, modifiers)
 * - Panel completion tracking (not per-dent)
 * - R&I checklist
 * - Discovery logging with photo capture
 * - Timer tracking
 * - Completion workflow
 * - CR (Conventional Repair) warnings
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
  AlertCircle,
  AlertTriangle,
  Loader2,
  CircleDot,
  Droplets,
  ArrowUp,
  Layers
} from 'lucide-react'

import { DiscoveryForm, DiscoveryItem } from '@/components/estimating/DiscoveryForm'
import { SIZE_LABELS, PANEL_NAMES } from '@/hooks/use-pdr-estimates'

import {
  useWorkOrder,
  useUpdateWorkOrder,
  useAddDiscovery,
} from '@/hooks/use-pdr-estimates'
import { cn } from '@/lib/utils'

// Status styles
const STATUS_STYLES: Record<string, string> = {
  assigned: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700'
}

// Modifier icons for visual display
const ModifierIcon = ({ type, active }: { type: string; active: boolean }) => {
  if (!active) return null

  const icons: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    aluminum: {
      icon: <Layers className="h-4 w-4" />,
      label: 'AL',
      color: 'bg-amber-100 text-amber-700 border-amber-300'
    },
    hss: {
      icon: <Layers className="h-4 w-4" />,
      label: 'HSS',
      color: 'bg-purple-100 text-purple-700 border-purple-300'
    },
    glue_pull: {
      icon: <Droplets className="h-4 w-4" />,
      label: 'GP',
      color: 'bg-blue-100 text-blue-700 border-blue-300'
    },
    tall_roof: {
      icon: <ArrowUp className="h-4 w-4" />,
      label: 'TR',
      color: 'bg-slate-100 text-slate-700 border-slate-300'
    }
  }

  const config = icons[type]
  if (!config) return null

  return (
    <div className={cn(
      'flex items-center gap-1 px-2 py-1 rounded border text-xs font-medium',
      config.color
    )}>
      {config.icon}
      <span>{config.label}</span>
    </div>
  )
}

export function WorkOrder() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [selectedPanelId, setSelectedPanelId] = useState<number | null>(null)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [discoveryDialogOpen, setDiscoveryDialogOpen] = useState(false)
  const [completedPanels, setCompletedPanels] = useState<Set<number>>(new Set())
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

  // Progress stats - panel based for matrix pricing
  const stats = useMemo(() => {
    if (!workOrder) return {
      totalPanels: 0,
      completedPanels: 0,
      totalDents: 0,
      progress: 0,
      discoveryTotal: 0,
      crPanels: 0
    }

    const panels = workOrder.panels || []
    const totalPanels = panels.length

    // Sum total dents across all panels
    let totalDents = 0
    let crPanels = 0
    panels.forEach(panel => {
      totalDents += panel.total_dent_count || 0
      if (panel.is_conventional_repair) crPanels++
    })

    const discoveryTotal = workOrder.discoveries?.reduce((sum, d) => sum + (d.additional_cost || 0), 0) || 0

    return {
      totalPanels,
      completedPanels: completedPanels.size,
      totalDents,
      progress: totalPanels > 0 ? Math.round((completedPanels.size / totalPanels) * 100) : 0,
      discoveryTotal,
      crPanels
    }
  }, [workOrder, completedPanels])

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

  // Toggle panel completion
  const togglePanel = useCallback((panelId: number) => {
    setCompletedPanels(prev => {
      const newSet = new Set(prev)
      if (newSet.has(panelId)) {
        newSet.delete(panelId)
      } else {
        newSet.add(panelId)
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

  // Get display name for panel
  const getPanelDisplayName = (panelName: string) => {
    return PANEL_NAMES[panelName] || panelName
  }

  // Get majority size label
  const getMajoritySizeLabel = (size: string) => {
    return SIZE_LABELS[size as keyof typeof SIZE_LABELS] || size
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
                {stats.crPanels > 0 && (
                  <Badge variant="destructive" className="text-xs">
                    {stats.crPanels} CR Panel{stats.crPanels > 1 ? 's' : ''}
                  </Badge>
                )}
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
              {stats.completedPanels} of {stats.totalPanels} panels completed
              <span className="text-xs ml-2">({stats.totalDents} total dents)</span>
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
                <CardTitle className="text-sm flex items-center justify-between">
                  <span>Panels</span>
                  <span className="text-xs font-normal text-muted-foreground">
                    {stats.completedPanels}/{stats.totalPanels}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {workOrder.panels?.map(panel => {
                  const isComplete = completedPanels.has(panel.id)
                  const isCR = panel.is_conventional_repair

                  return (
                    <button
                      key={panel.id}
                      onClick={() => setSelectedPanelId(panel.id)}
                      className={cn(
                        'w-full p-3 rounded-lg border text-left transition-colors',
                        selectedPanelId === panel.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:bg-accent/50',
                        isCR && 'border-red-300 bg-red-50'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isComplete ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                          ) : isCR ? (
                            <AlertTriangle className="h-5 w-5 text-red-500" />
                          ) : (
                            <Circle className="h-5 w-5 text-muted-foreground" />
                          )}
                          <div>
                            <span className="font-medium">
                              {getPanelDisplayName(panel.panel_name)}
                            </span>
                            {isCR && (
                              <span className="text-xs text-red-600 ml-2">CR</span>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant="secondary" className="text-xs">
                            {panel.total_dent_count || 0} dents
                          </Badge>
                          <p className="text-xs text-muted-foreground mt-1">
                            ${(panel.panel_total || 0).toFixed(0)}
                          </p>
                        </div>
                      </div>

                      {/* Modifier badges in panel list */}
                      {(panel.is_aluminum || panel.is_hss || panel.requires_glue_pull || panel.is_tall_roof) && (
                        <div className="flex gap-1 mt-2">
                          {panel.is_aluminum && (
                            <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">AL</span>
                          )}
                          {panel.is_hss && (
                            <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">HSS</span>
                          )}
                          {panel.requires_glue_pull && (
                            <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">GP</span>
                          )}
                          {panel.is_tall_roof && (
                            <span className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded">TR</span>
                          )}
                        </div>
                      )}
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
                {workOrder.matrix_profile && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Matrix: {workOrder.matrix_profile}
                  </p>
                )}
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
                  <span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded">CR</span>
                  <span>Conventional Repair</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Center & Right: Panel Detail and R&I */}
          <div className="lg:col-span-2 space-y-4">
            {selectedPanel ? (
              <>
                {/* Panel Header & Completion */}
                <Card className={cn(
                  selectedPanel.is_conventional_repair && 'border-red-300'
                )}>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span>{getPanelDisplayName(selectedPanel.panel_name)}</span>
                        {selectedPanel.is_conventional_repair && (
                          <Badge variant="destructive">CR - Conventional</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setDiscoveryDialogOpen(true)}
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          Add Discovery
                        </Button>
                        <Button
                          variant={completedPanels.has(selectedPanel.id) ? "default" : "outline"}
                          size="sm"
                          onClick={() => togglePanel(selectedPanel.id)}
                          className={cn(
                            completedPanels.has(selectedPanel.id) && 'bg-green-600 hover:bg-green-700'
                          )}
                        >
                          {completedPanels.has(selectedPanel.id) ? (
                            <>
                              <CheckCircle2 className="h-4 w-4 mr-1" />
                              Completed
                            </>
                          ) : (
                            <>
                              <Circle className="h-4 w-4 mr-1" />
                              Mark Complete
                            </>
                          )}
                        </Button>
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {/* CR Warning */}
                    {selectedPanel.is_conventional_repair && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                          <div>
                            <p className="font-medium text-red-700">Conventional Repair Required</p>
                            <p className="text-sm text-red-600">
                              This panel exceeds PDR limits. Route to body shop for conventional repair.
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Matrix Info Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div className="p-3 bg-muted/50 rounded-lg text-center">
                        <CircleDot className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
                        <p className="text-2xl font-bold">{selectedPanel.total_dent_count || 0}</p>
                        <p className="text-xs text-muted-foreground">Total Dents</p>
                      </div>
                      <div className="p-3 bg-muted/50 rounded-lg text-center">
                        <CircleDot className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
                        <p className="text-lg font-bold capitalize">
                          {getMajoritySizeLabel(selectedPanel.majority_size || 'dime')}
                        </p>
                        <p className="text-xs text-muted-foreground">Majority Size</p>
                      </div>
                      <div className="p-3 bg-muted/50 rounded-lg text-center">
                        <CircleDot className="h-5 w-5 mx-auto mb-1 text-orange-500" />
                        <p className="text-2xl font-bold text-orange-600">
                          {selectedPanel.oversized_count || 0}
                        </p>
                        <p className="text-xs text-muted-foreground">Oversized</p>
                      </div>
                      <div className="p-3 bg-primary/10 rounded-lg text-center">
                        <p className="text-xl font-bold text-primary">
                          ${(selectedPanel.matrix_base_price || 0).toFixed(0)}
                        </p>
                        <p className="text-xs text-muted-foreground">Base Price</p>
                      </div>
                    </div>

                    {/* Modifiers */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      <ModifierIcon type="aluminum" active={selectedPanel.is_aluminum || false} />
                      <ModifierIcon type="hss" active={selectedPanel.is_hss || false} />
                      <ModifierIcon type="glue_pull" active={selectedPanel.requires_glue_pull || false} />
                      <ModifierIcon type="tall_roof" active={selectedPanel.is_tall_roof || false} />
                    </div>

                    {/* Price Breakdown */}
                    <div className="border-t pt-4">
                      <h4 className="text-sm font-medium mb-2">Price Breakdown</h4>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span>Matrix Base ({selectedPanel.total_dent_count} dents, {getMajoritySizeLabel(selectedPanel.majority_size || 'dime')})</span>
                          <span>${(selectedPanel.matrix_base_price || 0).toFixed(2)}</span>
                        </div>
                        {selectedPanel.is_aluminum && (
                          <div className="flex justify-between text-amber-700">
                            <span>+ Aluminum (+25%)</span>
                            <span>+${((selectedPanel.matrix_base_price || 0) * 0.25).toFixed(2)}</span>
                          </div>
                        )}
                        {selectedPanel.is_hss && (
                          <div className="flex justify-between text-purple-700">
                            <span>+ HSS (+25%)</span>
                            <span>+${((selectedPanel.matrix_base_price || 0) * 0.25).toFixed(2)}</span>
                          </div>
                        )}
                        {selectedPanel.requires_glue_pull && (
                          <div className="flex justify-between text-blue-700">
                            <span>+ Glue Pull (+25%)</span>
                            <span>+${((selectedPanel.matrix_base_price || 0) * 0.25).toFixed(2)}</span>
                          </div>
                        )}
                        {selectedPanel.is_tall_roof && (
                          <div className="flex justify-between text-slate-700">
                            <span>+ Tall Roof (+25%)</span>
                            <span>+${((selectedPanel.matrix_base_price || 0) * 0.25).toFixed(2)}</span>
                          </div>
                        )}
                        {(selectedPanel.oversized_count || 0) > 0 && (
                          <div className="flex justify-between text-orange-700">
                            <span>+ Oversized ({selectedPanel.oversized_count} x $50)</span>
                            <span>+${((selectedPanel.oversized_count || 0) * 50).toFixed(2)}</span>
                          </div>
                        )}
                        <div className="flex justify-between font-bold text-lg border-t pt-2 mt-2">
                          <span>Panel Total</span>
                          <span>${(selectedPanel.panel_total || 0).toFixed(2)}</span>
                        </div>
                      </div>
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
                  <p className="text-muted-foreground">Select a panel to view details</p>
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
            <div>
              <p className="text-xs text-muted-foreground">Panels</p>
              <p className="font-bold">{stats.completedPanels}/{stats.totalPanels}</p>
            </div>
            {stats.discoveryTotal > 0 && (
              <div>
                <p className="text-xs text-orange-600">Supplement</p>
                <p className="font-bold text-orange-600">+${stats.discoveryTotal}</p>
              </div>
            )}
            {stats.crPanels > 0 && (
              <div>
                <p className="text-xs text-red-600">CR Panels</p>
                <p className="font-bold text-red-600">{stats.crPanels}</p>
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
