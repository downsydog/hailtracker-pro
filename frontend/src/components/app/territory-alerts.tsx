/**
 * Territory Alerts Component
 * Manage territories and view storm alerts
 */

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Bell,
  Plus,
  Trash2,
  Edit,
  RefreshCw,
  Check,
  AlertTriangle,
  MapPinned,
  Mail,
  Smartphone,
  Target,
} from "lucide-react"
import { territoryAlertsApi, Territory, TerritoryAlert } from "@/api/weather"

interface TerritoryAlertsProps {
  className?: string
}

export function TerritoryAlerts({ className = "" }: TerritoryAlertsProps) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState("alerts")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTerritory, setEditingTerritory] = useState<Territory | null>(null)

  // Form state
  const [name, setName] = useState("")
  const [centerLat, setCenterLat] = useState("")
  const [centerLon, setCenterLon] = useState("")
  const [radiusMiles, setRadiusMiles] = useState(25)
  const [minHailSize, setMinHailSize] = useState(0.75)
  const [emailAlerts, setEmailAlerts] = useState(true)
  const [smsAlerts, setSmsAlerts] = useState(false)
  const [pushAlerts, setPushAlerts] = useState(true)

  // Fetch territories
  const { data: territoriesData, isLoading: territoriesLoading } = useQuery({
    queryKey: ["territories"],
    queryFn: () => territoryAlertsApi.listTerritories(),
  })

  // Fetch alerts
  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ["territory-alerts"],
    queryFn: () => territoryAlertsApi.listAlerts({ days: 7 }),
  })

  // Fetch stats
  const { data: statsData } = useQuery({
    queryKey: ["territory-stats"],
    queryFn: () => territoryAlertsApi.getStats(),
  })

  const territories = territoriesData?.data?.territories || []
  const alerts = alertsData?.data?.alerts || []
  const stats = statsData?.data || { territories_count: 0, unread_alerts: 0, alerts_this_week: 0 }

  // Create territory mutation
  const createMutation = useMutation({
    mutationFn: () =>
      territoryAlertsApi.createTerritory({
        name,
        center_lat: parseFloat(centerLat),
        center_lon: parseFloat(centerLon),
        radius_miles: radiusMiles,
        min_hail_size: minHailSize,
        email_alerts: emailAlerts,
        sms_alerts: smsAlerts,
        push_alerts: pushAlerts,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["territories"] })
      queryClient.invalidateQueries({ queryKey: ["territory-stats"] })
      setDialogOpen(false)
      resetForm()
    },
  })

  // Update territory mutation
  const updateMutation = useMutation({
    mutationFn: () =>
      territoryAlertsApi.updateTerritory(editingTerritory!.id, {
        name,
        center_lat: parseFloat(centerLat),
        center_lon: parseFloat(centerLon),
        radius_miles: radiusMiles,
        min_hail_size: minHailSize,
        email_alerts: emailAlerts,
        sms_alerts: smsAlerts,
        push_alerts: pushAlerts,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["territories"] })
      setDialogOpen(false)
      resetForm()
    },
  })

  // Delete territory mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => territoryAlertsApi.deleteTerritory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["territories"] })
      queryClient.invalidateQueries({ queryKey: ["territory-stats"] })
    },
  })

  // Check storms mutation
  const checkStormsMutation = useMutation({
    mutationFn: () => territoryAlertsApi.checkStorms(24),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["territory-alerts"] })
      queryClient.invalidateQueries({ queryKey: ["territory-stats"] })
    },
  })

  // Mark alert read mutation
  const markReadMutation = useMutation({
    mutationFn: (id: number) => territoryAlertsApi.markAlertRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["territory-alerts"] })
      queryClient.invalidateQueries({ queryKey: ["territory-stats"] })
    },
  })

  const resetForm = () => {
    setName("")
    setCenterLat("")
    setCenterLon("")
    setRadiusMiles(25)
    setMinHailSize(0.75)
    setEmailAlerts(true)
    setSmsAlerts(false)
    setPushAlerts(true)
    setEditingTerritory(null)
  }

  const openEditDialog = (territory: Territory) => {
    setEditingTerritory(territory)
    setName(territory.name)
    setCenterLat(String(territory.center_lat))
    setCenterLon(String(territory.center_lon))
    setRadiusMiles(territory.radius_miles || 25)
    setMinHailSize(territory.min_hail_size || 0.75)
    setEmailAlerts(territory.email_alerts)
    setSmsAlerts(territory.sms_alerts)
    setPushAlerts(territory.push_alerts)
    setDialogOpen(true)
  }

  const handleSubmit = () => {
    if (editingTerritory) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bell className="h-5 w-5 text-orange-500" />
            Territory Alerts
            {stats.unread_alerts > 0 && (
              <Badge variant="destructive" className="ml-2">
                {stats.unread_alerts}
              </Badge>
            )}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => checkStormsMutation.mutate()}
            disabled={checkStormsMutation.isPending}
          >
            <RefreshCw
              className={`h-4 w-4 ${checkStormsMutation.isPending ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="p-2 bg-muted rounded">
            <p className="text-lg font-bold">{stats.territories_count}</p>
            <p className="text-xs text-muted-foreground">Territories</p>
          </div>
          <div className="p-2 bg-muted rounded">
            <p className="text-lg font-bold text-orange-500">{stats.unread_alerts}</p>
            <p className="text-xs text-muted-foreground">Unread</p>
          </div>
          <div className="p-2 bg-muted rounded">
            <p className="text-lg font-bold">{stats.alerts_this_week}</p>
            <p className="text-xs text-muted-foreground">This Week</p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="territories">Territories</TabsTrigger>
          </TabsList>

          {/* Alerts Tab */}
          <TabsContent value="alerts" className="space-y-2 mt-2">
            {alertsLoading ? (
              <div className="text-center py-4 text-muted-foreground">Loading...</div>
            ) : alerts.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No alerts</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[250px] overflow-y-auto">
                {alerts.map((alert: TerritoryAlert) => (
                  <div
                    key={alert.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      alert.is_read
                        ? "bg-muted/50"
                        : "bg-orange-500/10 border-orange-500/30"
                    }`}
                    onClick={() => !alert.is_read && markReadMutation.mutate(alert.id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <AlertTriangle
                            className={`h-4 w-4 ${
                              alert.is_read ? "text-muted-foreground" : "text-orange-500"
                            }`}
                          />
                          <span className="font-medium text-sm">
                            {alert.territory_name}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {alert.alert_message}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(alert.sent_at).toLocaleString()}
                        </p>
                      </div>
                      {!alert.is_read && (
                        <Badge variant="destructive" className="text-xs">New</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Territories Tab */}
          <TabsContent value="territories" className="space-y-2 mt-2">
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="w-full" onClick={resetForm}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Territory
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>
                    {editingTerritory ? "Edit Territory" : "Add Territory"}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label>Territory Name</Label>
                    <Input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g., Dallas Metro Area"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Center Latitude</Label>
                      <Input
                        value={centerLat}
                        onChange={(e) => setCenterLat(e.target.value)}
                        placeholder="32.7767"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Center Longitude</Label>
                      <Input
                        value={centerLon}
                        onChange={(e) => setCenterLon(e.target.value)}
                        placeholder="-96.7970"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Radius: {radiusMiles} miles</Label>
                    <Slider
                      value={[radiusMiles]}
                      onValueChange={([v]) => setRadiusMiles(v)}
                      min={5}
                      max={100}
                      step={5}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Minimum Hail Size: {minHailSize}"</Label>
                    <Slider
                      value={[minHailSize]}
                      onValueChange={([v]) => setMinHailSize(v)}
                      min={0.25}
                      max={3}
                      step={0.25}
                    />
                  </div>
                  <div className="space-y-3">
                    <Label>Alert Methods</Label>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4" />
                        <span className="text-sm">Email</span>
                      </div>
                      <Switch checked={emailAlerts} onCheckedChange={setEmailAlerts} />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Smartphone className="h-4 w-4" />
                        <span className="text-sm">SMS</span>
                      </div>
                      <Switch checked={smsAlerts} onCheckedChange={setSmsAlerts} />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Bell className="h-4 w-4" />
                        <span className="text-sm">Push</span>
                      </div>
                      <Switch checked={pushAlerts} onCheckedChange={setPushAlerts} />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSubmit}
                    disabled={
                      createMutation.isPending ||
                      updateMutation.isPending ||
                      !name ||
                      !centerLat ||
                      !centerLon
                    }
                  >
                    {(createMutation.isPending || updateMutation.isPending) ? (
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Check className="h-4 w-4 mr-2" />
                    )}
                    {editingTerritory ? "Update" : "Create"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {territoriesLoading ? (
              <div className="text-center py-4 text-muted-foreground">Loading...</div>
            ) : territories.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                <MapPinned className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No territories configured</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[250px] overflow-y-auto">
                {territories.map((territory: Territory) => (
                  <div
                    key={territory.id}
                    className="p-3 rounded-lg border flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <Target className="h-4 w-4 text-blue-500" />
                      <div>
                        <p className="font-medium text-sm">{territory.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {territory.radius_miles} mi radius, {territory.min_hail_size}"+ hail
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => openEditDialog(territory)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-500"
                        onClick={() => deleteMutation.mutate(territory.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default TerritoryAlerts
