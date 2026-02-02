import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  hailEventsApi,
  stormCellsApi,
  stormMonitorApi,
  mlApi,
  HailEvent,
  StormCell,
  MonitorStatus,
  OverallStats,
} from '@/api/weather'
import { PageHeader } from '@/components/app/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  CloudLightning,
  MapPin,
  Activity,
  Play,
  Square,
  RefreshCw,
  Truck,
  Zap,
  Plus,
  Map,
  BarChart3,
} from 'lucide-react'

const SEVERITY_COLORS: Record<string, string> = {
  MINOR: 'bg-green-500',
  MODERATE: 'bg-yellow-500',
  SEVERE: 'bg-red-500',
  CATASTROPHIC: 'bg-purple-500',
}

export function WeatherPage() {
  const [showNewEvent, setShowNewEvent] = React.useState(false)
  const [daysFilter, setDaysFilter] = React.useState('90')
  const [severityFilter, setSeverityFilter] = React.useState('all')
  const queryClient = useQueryClient()

  // Queries
  const { data: eventsData, isLoading: eventsLoading, refetch: refetchEvents } = useQuery({
    queryKey: ['hail-events', daysFilter, severityFilter],
    queryFn: () => hailEventsApi.list({
      days: parseInt(daysFilter),
      severity: severityFilter !== 'all' ? severityFilter : undefined,
    }),
  })

  const { data: monitorData } = useQuery({
    queryKey: ['storm-monitor-status'],
    queryFn: () => stormMonitorApi.getStatus(),
    refetchInterval: 10000, // Refresh every 10s
  })

  const { data: cellsData } = useQuery({
    queryKey: ['active-cells'],
    queryFn: () => stormCellsApi.getActiveCells(),
    refetchInterval: 30000, // Refresh every 30s
  })

  const { data: mlStatusData } = useQuery({
    queryKey: ['ml-status'],
    queryFn: () => mlApi.getStatus(),
  })

  const { data: performanceData } = useQuery({
    queryKey: ['storms-performance'],
    queryFn: () => hailEventsApi.getPerformance({ min_jobs: 1 }),
  })

  // Mutations
  const startMonitorMutation = useMutation({
    mutationFn: stormMonitorApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storm-monitor-status'] })
    },
  })

  const stopMonitorMutation = useMutation({
    mutationFn: stormMonitorApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storm-monitor-status'] })
    },
  })

  const createEventMutation = useMutation({
    mutationFn: hailEventsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hail-events'] })
      setShowNewEvent(false)
    },
  })

  const events = eventsData?.data?.events || []
  const stats: OverallStats = eventsData?.data?.stats || {
    period_days: parseInt(daysFilter),
    total_storms: 0,
    active_storms: 0,
    total_estimated_vehicles: 0,
    by_severity: {},
    by_state: {},
  }
  const monitor: MonitorStatus = monitorData?.data || { running: false, initialized: false }
  const activeCells: StormCell[] = cellsData?.data?.active_cells || []
  const performanceStorms = performanceData?.data?.storms || []

  const handleCreateEvent = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    createEventMutation.mutate({
      event_name: form.get('event_name') as string,
      event_date: form.get('event_date') as string,
      location: form.get('location') as string,
      city: form.get('city') as string,
      state: form.get('state') as string,
      severity: form.get('severity') as 'MINOR' | 'MODERATE' | 'SEVERE' | 'CATASTROPHIC',
      hail_size_inches: parseFloat(form.get('hail_size_inches') as string) || undefined,
      estimated_vehicles_affected: parseInt(form.get('estimated_vehicles') as string) || undefined,
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Storm & Hail Tracking"
        description="Monitor storms, track hail events, and identify market opportunities."
      >
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/hail-map">
              <Map className="h-4 w-4 mr-2" />
              Hail Map
            </Link>
          </Button>
          <Dialog open={showNewEvent} onOpenChange={setShowNewEvent}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Storm Event
              </Button>
            </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Storm Event</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleCreateEvent} className="space-y-4">
                  <div>
                    <Label htmlFor="event_name">Event Name</Label>
                    <Input id="event_name" name="event_name" required placeholder="e.g., Dallas Hail Storm" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="event_date">Date</Label>
                      <Input id="event_date" name="event_date" type="date" required />
                    </div>
                    <div>
                      <Label htmlFor="severity">Severity</Label>
                      <Select name="severity" defaultValue="MODERATE">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="MINOR">Minor</SelectItem>
                          <SelectItem value="MODERATE">Moderate</SelectItem>
                          <SelectItem value="SEVERE">Severe</SelectItem>
                          <SelectItem value="CATASTROPHIC">Catastrophic</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="city">City</Label>
                      <Input id="city" name="city" required placeholder="Dallas" />
                    </div>
                    <div>
                      <Label htmlFor="state">State</Label>
                      <Input id="state" name="state" required placeholder="TX" maxLength={2} />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="location">Location Description</Label>
                    <Input id="location" name="location" required placeholder="North Dallas area" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="hail_size_inches">Hail Size (inches)</Label>
                      <Input id="hail_size_inches" name="hail_size_inches" type="number" step="0.25" placeholder="1.5" />
                    </div>
                    <div>
                      <Label htmlFor="estimated_vehicles">Est. Vehicles</Label>
                      <Input id="estimated_vehicles" name="estimated_vehicles" type="number" placeholder="10000" />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setShowNewEvent(false)}>Cancel</Button>
                    <Button type="submit" disabled={createEventMutation.isPending}>
                      {createEventMutation.isPending ? 'Creating...' : 'Create Event'}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
        </div>
      </PageHeader>

      {/* Stats Row */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Storms</CardTitle>
            <CloudLightning className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active_storms}</div>
            <p className="text-xs text-muted-foreground">Last {stats.period_days} days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Storms</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_storms}</div>
            <p className="text-xs text-muted-foreground">In period</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Est. Vehicles</CardTitle>
            <Truck className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_estimated_vehicles.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">Affected</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Cells</CardTitle>
            <Zap className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeCells.length}</div>
            <p className="text-xs text-muted-foreground">Tracking now</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monitor</CardTitle>
            {monitor.running ? (
              <Activity className="h-4 w-4 text-green-500 animate-pulse" />
            ) : (
              <Square className="h-4 w-4 text-gray-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{monitor.running ? 'Running' : 'Stopped'}</div>
            <div className="flex gap-1 mt-1">
              {monitor.running ? (
                <Button size="sm" variant="outline" onClick={() => stopMonitorMutation.mutate()}>
                  <Square className="h-3 w-3 mr-1" /> Stop
                </Button>
              ) : (
                <Button size="sm" onClick={() => startMonitorMutation.mutate({})}>
                  <Play className="h-3 w-3 mr-1" /> Start
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="events" className="space-y-4">
        <TabsList>
          <TabsTrigger value="events">Storm Events</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="ml">ML Status</TabsTrigger>
        </TabsList>

        <TabsContent value="events" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex gap-4 items-end">
                <div className="flex-1 relative">
                  <Label>Time Period</Label>
                  <Select value={daysFilter} onValueChange={setDaysFilter}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7">Last 7 days</SelectItem>
                      <SelectItem value="30">Last 30 days</SelectItem>
                      <SelectItem value="90">Last 90 days</SelectItem>
                      <SelectItem value="365">Last year</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1">
                  <Label>Severity</Label>
                  <Select value={severityFilter} onValueChange={setSeverityFilter}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Severities</SelectItem>
                      <SelectItem value="MINOR">Minor</SelectItem>
                      <SelectItem value="MODERATE">Moderate</SelectItem>
                      <SelectItem value="SEVERE">Severe</SelectItem>
                      <SelectItem value="CATASTROPHIC">Catastrophic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button variant="outline" onClick={() => refetchEvents()}>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Severity Breakdown */}
          <div className="grid gap-4 md:grid-cols-4">
            {['CATASTROPHIC', 'SEVERE', 'MODERATE', 'MINOR'].map(sev => {
              const data = stats.by_severity[sev] || { count: 0, estimated_vehicles: 0 }
              return (
                <Card key={sev} className="cursor-pointer hover:bg-muted/50" onClick={() => setSeverityFilter(sev)}>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${SEVERITY_COLORS[sev]}`} />
                      <span className="text-sm font-medium">{sev}</span>
                    </div>
                    <div className="text-2xl font-bold mt-1">{data.count}</div>
                    <p className="text-xs text-muted-foreground">
                      {data.estimated_vehicles.toLocaleString()} vehicles
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Events Table */}
          {eventsLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : events.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CloudLightning className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">No storm events</h3>
                <p className="text-muted-foreground">No storms found for the selected filters.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Event</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Hail Size</TableHead>
                    <TableHead className="text-right">Est. Vehicles</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((event: HailEvent) => (
                    <TableRow key={event.id}>
                      <TableCell>
                        <Link to={`/hail-map?event=${event.id}`} className="font-medium hover:text-primary">
                          {event.event_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3 text-muted-foreground" />
                          {event.city}, {event.state}
                        </div>
                      </TableCell>
                      <TableCell>{new Date(event.event_date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Badge className={SEVERITY_COLORS[event.severity]}>
                          {event.severity}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {event.hail_size_inches || event.max_hail_size
                          ? `${event.hail_size_inches || event.max_hail_size}"`
                          : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        {(event.estimated_vehicles || event.estimated_vehicles_affected || 0).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant={event.status === 'ACTIVE' ? 'default' : 'secondary'}>
                          {event.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Storm Performance</CardTitle>
              <CardDescription>Revenue and conversion metrics by storm</CardDescription>
            </CardHeader>
            {performanceStorms.length === 0 ? (
              <CardContent className="py-8 text-center">
                <BarChart3 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No storms with jobs yet.</p>
              </CardContent>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Storm</TableHead>
                    <TableHead className="text-right">Jobs</TableHead>
                    <TableHead className="text-right">Revenue</TableHead>
                    <TableHead className="text-right">Avg/Job</TableHead>
                    <TableHead className="text-right">Penetration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {performanceStorms.slice(0, 10).map((storm: any) => (
                    <TableRow key={storm.storm_id || storm.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{storm.event_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {storm.location || `${storm.city || ''}, ${storm.state || ''}`}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{storm.jobs_created || storm.job_count || 0}</TableCell>
                      <TableCell className="text-right">
                        ${(storm.total_revenue || 0).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        ${(storm.avg_revenue_per_job || 0).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        {(storm.market_penetration || 0).toFixed(4)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="ml" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>ML Models Status</CardTitle>
                <CardDescription>Machine learning model availability</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {mlStatusData?.data ? (
                  <>
                    <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                      <div>
                        <div className="font-medium">Hail Classifier</div>
                        <div className="text-sm text-muted-foreground">Classification + PDR scoring</div>
                      </div>
                      <Badge variant={mlStatusData.data.classifier?.available ? 'default' : 'secondary'}>
                        {mlStatusData.data.classifier?.available ? 'Available' : 'Unavailable'}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                      <div>
                        <div className="font-medium">Storm Forecaster</div>
                        <div className="text-sm text-muted-foreground">15/30/60/120 min forecasts</div>
                      </div>
                      <Badge variant={mlStatusData.data.forecaster?.is_fitted ? 'default' : 'secondary'}>
                        {mlStatusData.data.forecaster?.is_fitted ? 'Trained' : 'Untrained'}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                      <div>
                        <div className="font-medium">Size Estimator</div>
                        <div className="text-sm text-muted-foreground">Photo-based hail sizing</div>
                      </div>
                      <Badge variant={mlStatusData.data.size_estimator?.is_fitted ? 'default' : 'secondary'}>
                        {mlStatusData.data.size_estimator?.is_fitted ? 'Trained' : 'Untrained'}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                      <div>
                        <div className="font-medium">ML Model</div>
                        <div className="text-sm text-muted-foreground">Core prediction engine</div>
                      </div>
                      <Badge variant={mlStatusData.data.ml_model?.is_fitted ? 'default' : 'secondary'}>
                        {mlStatusData.data.ml_model?.is_fitted ? 'Trained' : 'Untrained'}
                      </Badge>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-4 text-muted-foreground">
                    Loading ML status...
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Monitor Configuration</CardTitle>
                <CardDescription>Storm monitor settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>Status</span>
                  <Badge variant={monitor.running ? 'default' : 'secondary'}>
                    {monitor.running ? 'Running' : 'Stopped'}
                  </Badge>
                </div>

                {monitor.radars && monitor.radars.length > 0 && (
                  <div className="flex items-center justify-between">
                    <span>Radars</span>
                    <span className="text-sm text-muted-foreground">
                      {monitor.radars.join(', ')}
                    </span>
                  </div>
                )}

                {monitor.scans_processed !== undefined && (
                  <div className="flex items-center justify-between">
                    <span>Scans Processed</span>
                    <span className="font-medium">{monitor.scans_processed}</span>
                  </div>
                )}

                {monitor.alerts_generated !== undefined && (
                  <div className="flex items-center justify-between">
                    <span>Alerts Generated</span>
                    <span className="font-medium">{monitor.alerts_generated}</span>
                  </div>
                )}

                {monitor.last_scan && (
                  <div className="flex items-center justify-between">
                    <span>Last Scan</span>
                    <span className="text-sm text-muted-foreground">
                      {new Date(monitor.last_scan).toLocaleTimeString()}
                    </span>
                  </div>
                )}

                <div className="pt-4 flex gap-2">
                  {monitor.running ? (
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => stopMonitorMutation.mutate()}
                      disabled={stopMonitorMutation.isPending}
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop Monitor
                    </Button>
                  ) : (
                    <Button
                      className="flex-1"
                      onClick={() => startMonitorMutation.mutate({})}
                      disabled={startMonitorMutation.isPending}
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Start Monitor
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default WeatherPage
