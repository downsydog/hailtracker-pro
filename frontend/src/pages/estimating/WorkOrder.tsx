/**
 * PDR Work Order Screen
 *
 * Tech's working view of the estimate. Shows panel-by-panel dent list.
 * One-tap discovery logging with template selection.
 * At completion: click "Generate Invoice" which creates supplement if discoveries exist.
 */

import { useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import {
  CheckCircle2,
  Circle,
  Clock,
  Camera,
  AlertCircle,
  Wrench,
  FileText,
  Plus,
  Play,
  Pause,
  Square
} from 'lucide-react'

// Types
interface Dent {
  id: number
  size: 'small' | 'medium' | 'large' | 'xlarge'
  zone: 'center' | 'edge' | 'crease'
  final_price: number
  status: 'pending' | 'in_progress' | 'completed'
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
  created_at: string
}

interface WorkOrderPanel {
  id: number
  panel_name: string
  display_name: string
  dents: Dent[]
  completed_dents: number
}

interface WorkOrder {
  id: number
  estimate_id: number
  customer_name: string
  vehicle: string
  status: 'not_started' | 'in_progress' | 'completed'
  panels: WorkOrderPanel[]
  discoveries: Discovery[]
  start_time?: string
  end_time?: string
  total_time_minutes?: number
}

// Discovery templates
const DISCOVERY_TEMPLATES = [
  { type: 'handle_interference', display_name: 'Handle Interference', typical_time: 0.25, typical_cost: 25 },
  { type: 'liner_removal', display_name: 'Liner Removal', typical_time: 0.17, typical_cost: 20 },
  { type: 'hidden_damage', display_name: 'Hidden Damage', typical_time: 0.5, typical_cost: 75 },
  { type: 'headliner_drop', display_name: 'Headliner Drop', typical_time: 1.5, typical_cost: 150 },
  { type: 'trim_removal', display_name: 'Trim Removal', typical_time: 0.33, typical_cost: 35 },
  { type: 'adhesive_removal', display_name: 'Adhesive Removal', typical_time: 0.25, typical_cost: 30 },
  { type: 'wiring_disconnect', display_name: 'Wiring Disconnect', typical_time: 0.25, typical_cost: 25 },
  { type: 'access_difficulty', display_name: 'Access Difficulty', typical_time: 0.5, typical_cost: 50 },
  { type: 'high_strength_steel', display_name: 'High Strength Steel', typical_time: 0.5, typical_cost: 75 },
  { type: 'aluminum_panel', display_name: 'Aluminum Panel', typical_time: 0.75, typical_cost: 100 }
]

// Mock data
const mockWorkOrder: WorkOrder = {
  id: 1,
  estimate_id: 1,
  customer_name: 'John Smith',
  vehicle: '2022 Toyota Camry',
  status: 'in_progress',
  panels: [
    {
      id: 1,
      panel_name: 'hood',
      display_name: 'Hood',
      dents: [
        { id: 1, size: 'medium', zone: 'center', final_price: 75, status: 'completed' },
        { id: 2, size: 'medium', zone: 'center', final_price: 75, status: 'completed' },
        { id: 3, size: 'small', zone: 'edge', final_price: 70, status: 'in_progress' },
        { id: 4, size: 'large', zone: 'crease', final_price: 160, status: 'pending' }
      ],
      completed_dents: 2
    },
    {
      id: 2,
      panel_name: 'roof',
      display_name: 'Roof',
      dents: [
        { id: 5, size: 'medium', zone: 'center', final_price: 90, status: 'pending' },
        { id: 6, size: 'medium', zone: 'center', final_price: 90, status: 'pending' },
        { id: 7, size: 'medium', zone: 'edge', final_price: 126, status: 'pending' }
      ],
      completed_dents: 0
    },
    {
      id: 3,
      panel_name: 'driver_door',
      display_name: 'Driver Door',
      dents: [
        { id: 8, size: 'small', zone: 'center', final_price: 50, status: 'pending' },
        { id: 9, size: 'medium', zone: 'edge', final_price: 105, status: 'pending' }
      ],
      completed_dents: 0
    }
  ],
  discoveries: [
    {
      id: 1,
      type: 'handle_interference',
      display_name: 'Handle Interference',
      description: 'Door handle removal required for tool access',
      additional_time_hours: 0.25,
      additional_cost: 25,
      panel_name: 'hood',
      created_at: new Date().toISOString()
    }
  ],
  start_time: new Date(Date.now() - 45 * 60000).toISOString(),
  total_time_minutes: 45
}

export function WorkOrder() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [workOrder, setWorkOrder] = useState<WorkOrder>(mockWorkOrder)
  const [selectedPanelId, setSelectedPanelId] = useState<number | null>(workOrder.panels[0]?.id || null)
  const [isTimerRunning, setIsTimerRunning] = useState(true)
  const [discoveryDialogOpen, setDiscoveryDialogOpen] = useState(false)

  // Selected panel
  const selectedPanel = useMemo(() => {
    return workOrder.panels.find(p => p.id === selectedPanelId) || null
  }, [workOrder.panels, selectedPanelId])

  // Progress stats
  const stats = useMemo(() => {
    let totalDents = 0
    let completedDents = 0

    workOrder.panels.forEach(panel => {
      totalDents += panel.dents.length
      completedDents += panel.dents.filter(d => d.status === 'completed').length
    })

    const discoveryTotal = workOrder.discoveries.reduce((sum, d) => sum + d.additional_cost, 0)

    return {
      totalDents,
      completedDents,
      progress: totalDents > 0 ? Math.round((completedDents / totalDents) * 100) : 0,
      discoveryCount: workOrder.discoveries.length,
      discoveryTotal
    }
  }, [workOrder])

  // Toggle dent status
  const toggleDentStatus = useCallback((dentId: number) => {
    setWorkOrder(prev => ({
      ...prev,
      panels: prev.panels.map(panel => ({
        ...panel,
        dents: panel.dents.map(dent => {
          if (dent.id === dentId) {
            const newStatus = dent.status === 'completed' ? 'pending' : 'completed'
            return { ...dent, status: newStatus }
          }
          return dent
        }),
        completed_dents: panel.dents.filter(d =>
          d.id === dentId ? d.status !== 'completed' : d.status === 'completed'
        ).length
      }))
    }))
  }, [])

  // Add discovery
  const addDiscovery = useCallback((template: typeof DISCOVERY_TEMPLATES[0]) => {
    if (!selectedPanel) return

    const newDiscovery: Discovery = {
      id: Date.now(),
      type: template.type,
      display_name: template.display_name,
      description: `${template.display_name} required for proper tool access`,
      additional_time_hours: template.typical_time,
      additional_cost: template.typical_cost,
      panel_name: selectedPanel.panel_name,
      created_at: new Date().toISOString()
    }

    setWorkOrder(prev => ({
      ...prev,
      discoveries: [...prev.discoveries, newDiscovery]
    }))

    setDiscoveryDialogOpen(false)
  }, [selectedPanel])

  // Complete work order
  const completeWorkOrder = () => {
    console.log('Completing work order:', workOrder.id)
    console.log('Discoveries:', workOrder.discoveries)
    // Navigate to invoice/supplement generator
    navigate(`/estimating/invoice/${workOrder.id}`)
  }

  // Format elapsed time
  const formatTime = (minutes: number) => {
    const hrs = Math.floor(minutes / 60)
    const mins = minutes % 60
    return hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`
  }

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Wrench className="h-6 w-6" />
              Work Order #{workOrder.id}
            </h1>
            <Badge className={
              workOrder.status === 'completed' ? 'bg-green-100 text-green-700' :
              workOrder.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
              'bg-gray-100 text-gray-700'
            }>
              {workOrder.status.replace('_', ' ').toUpperCase()}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            {workOrder.customer_name} - {workOrder.vehicle}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Timer */}
          <div className="flex items-center gap-2 bg-muted px-4 py-2 rounded-lg">
            <Clock className="h-4 w-4" />
            <span className="font-mono font-bold">
              {formatTime(workOrder.total_time_minutes || 0)}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsTimerRunning(!isTimerRunning)}
            >
              {isTimerRunning ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
          </div>
          <Button
            onClick={completeWorkOrder}
            disabled={stats.progress < 100}
          >
            <FileText className="h-4 w-4 mr-2" />
            Generate Invoice
          </Button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-muted-foreground">
            {stats.completedDents} of {stats.totalDents} dents completed
          </span>
          <span className="font-bold">{stats.progress}%</span>
        </div>
        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 transition-all duration-300"
            style={{ width: `${stats.progress}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel List */}
        <div className="space-y-2">
          <h2 className="font-semibold mb-3">Panels</h2>
          {workOrder.panels.map(panel => {
            const panelCompleted = panel.dents.filter(d => d.status === 'completed').length
            const panelTotal = panel.dents.length
            const isComplete = panelCompleted === panelTotal

            return (
              <div
                key={panel.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedPanelId === panel.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-accent/50'
                }`}
                onClick={() => setSelectedPanelId(panel.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {isComplete ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-foreground" />
                    )}
                    <span className="font-medium">{panel.display_name}</span>
                  </div>
                  <Badge variant="secondary">
                    {panelCompleted}/{panelTotal}
                  </Badge>
                </div>
              </div>
            )
          })}

          {/* Discoveries Summary */}
          {stats.discoveryCount > 0 && (
            <Card className="mt-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-orange-500" />
                  Discoveries ({stats.discoveryCount})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold text-orange-600">
                  +${stats.discoveryTotal.toFixed(0)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Supplement required
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Dent List */}
        <div className="lg:col-span-2">
          {selectedPanel ? (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between">
                  <span>{selectedPanel.display_name}</span>
                  <Dialog open={discoveryDialogOpen} onOpenChange={setDiscoveryDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" variant="outline">
                        <Plus className="h-4 w-4 mr-1" />
                        Add Discovery
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Log Discovery</DialogTitle>
                      </DialogHeader>
                      <div className="grid grid-cols-2 gap-2 mt-4">
                        {DISCOVERY_TEMPLATES.map(template => (
                          <Button
                            key={template.type}
                            variant="outline"
                            className="h-auto py-3 flex flex-col items-start"
                            onClick={() => addDiscovery(template)}
                          >
                            <span className="font-medium">{template.display_name}</span>
                            <span className="text-xs text-muted-foreground">
                              ${template.typical_cost} | {template.typical_time}h
                            </span>
                          </Button>
                        ))}
                      </div>
                    </DialogContent>
                  </Dialog>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Dent grid - tap to toggle */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {selectedPanel.dents.map(dent => (
                    <div
                      key={dent.id}
                      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                        dent.status === 'completed'
                          ? 'border-green-500 bg-green-50'
                          : dent.status === 'in_progress'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-400'
                      }`}
                      onClick={() => toggleDentStatus(dent.id)}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium capitalize">{dent.size}</span>
                        {dent.status === 'completed' ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                        ) : (
                          <Circle className="h-5 w-5 text-gray-300" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground capitalize">{dent.zone}</p>
                      <p className="text-lg font-bold mt-2">${dent.final_price.toFixed(0)}</p>
                    </div>
                  ))}
                </div>

                {/* Panel discoveries */}
                {workOrder.discoveries.filter(d => d.panel_name === selectedPanel.panel_name).length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-orange-500" />
                      Discoveries on this panel
                    </h3>
                    <div className="space-y-2">
                      {workOrder.discoveries
                        .filter(d => d.panel_name === selectedPanel.panel_name)
                        .map(discovery => (
                          <div
                            key={discovery.id}
                            className="p-3 bg-orange-50 border border-orange-200 rounded-lg"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium">{discovery.display_name}</span>
                              <span className="font-bold text-orange-600">
                                +${discovery.additional_cost.toFixed(0)}
                              </span>
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              {discovery.description}
                            </p>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
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
  )
}

export default WorkOrder
