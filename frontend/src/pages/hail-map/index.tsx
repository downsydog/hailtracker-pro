import { useEffect, useRef, useState, useCallback } from "react"

import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiGet, apiPost } from "@/api/client"
import { Lead } from "@/types"
import { RefreshCw, Layers, MapPin, CloudLightning, Flame, Phone, Mail, Navigation, UserPlus, Edit, Radio } from "lucide-react"
import { useNavigate } from "react-router-dom"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import "leaflet.markercluster"
import "leaflet.markercluster/dist/MarkerCluster.css"
import "leaflet.markercluster/dist/MarkerCluster.Default.css"

// Fix Leaflet default marker icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

interface HailEvent {
  id: number
  event_name: string
  event_date: string
  latitude: number
  longitude: number
  city?: string
  state?: string
  max_hail_size?: number
  severity?: string
  affected_area_sq_miles?: number
  property_count?: number
}

interface LayerState {
  swaths: boolean
  leads: boolean
  territories: boolean
  radar: boolean
}

const SAMPLE_TERRITORIES = [
  {
    name: "Dallas Metro",
    rep: "John Smith",
    lead_count: 45,
    bounds: [[33.1, -97.1], [33.1, -96.5], [32.6, -96.5], [32.6, -97.1]] as L.LatLngExpression[],
  },
  {
    name: "Denver Area",
    rep: "Jane Doe",
    lead_count: 32,
    bounds: [[40.0, -105.2], [40.0, -104.6], [39.5, -104.6], [39.5, -105.2]] as L.LatLngExpression[],
  },
  {
    name: "Oklahoma City",
    rep: "Mike Johnson",
    lead_count: 28,
    bounds: [[35.7, -97.8], [35.7, -97.2], [35.2, -97.2], [35.2, -97.8]] as L.LatLngExpression[],
  },
]

// Sample radar sites (NEXRAD locations)
const RADAR_SITES = [
  { id: "KFWS", name: "Fort Worth", lat: 32.5731, lon: -97.3033, range: 230 },
  { id: "KAMA", name: "Amarillo", lat: 35.2333, lon: -101.7092, range: 230 },
  { id: "KOUN", name: "Norman", lat: 35.2456, lon: -97.4619, range: 230 },
  { id: "KFTG", name: "Denver", lat: 39.7867, lon: -104.5458, range: 230 },
  { id: "KTLX", name: "Oklahoma City", lat: 35.3331, lon: -97.2778, range: 230 },
]

export function HailMapPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const swathLayerRef = useRef<L.LayerGroup | null>(null)
  const leadsClusterRef = useRef<L.MarkerClusterGroup | null>(null)
  const territoryLayerRef = useRef<L.LayerGroup | null>(null)
  const radarLayerRef = useRef<L.LayerGroup | null>(null)

  const [layers, setLayers] = useState<LayerState>({
    swaths: true,
    leads: true,
    territories: true,
    radar: false,
  })

  const [stats, setStats] = useState({
    activeStorms: 0,
    leadsInView: 0,
    hotLeads: 0,
  })

  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Fetch hail events
  const { data: eventsData, isLoading: eventsLoading, refetch: refetchEvents } = useQuery({
    queryKey: ["hail-events"],
    queryFn: () => apiGet<{ events: HailEvent[], stats: any }>("/api/hail-events?days=3650"),
  })

  // Fetch leads with location
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useQuery({
    queryKey: ["leads-map"],
    queryFn: () => apiGet<{ leads: Lead[] }>("/api/leads?per_page=500"),
  })

  // Convert lead to customer mutation
  const convertMutation = useMutation({
    mutationFn: (leadId: number) => apiPost(`/api/leads/${leadId}/convert`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads-map"] })
      setDrawerOpen(false)
      setSelectedLead(null)
    },
  })

  const events = eventsData?.events || []
  const allLeads = leadsData?.leads || []
  const leads = allLeads.filter((l: any) => l.latitude && l.longitude)

  // Update stats based on map bounds
  const updateStats = useCallback(() => {
    if (!mapInstanceRef.current) return

    const bounds = mapInstanceRef.current.getBounds()

    // Count events from last 7 days
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
    const recentEvents = events.filter((e) => {
      if (!e.event_date) return false
      const eventDate = new Date(e.event_date)
      return eventDate >= sevenDaysAgo
    })

    const leadsInView = leads.filter(
      (l: any) => l.latitude && l.longitude && bounds.contains([l.latitude, l.longitude])
    )

    const hotLeads = leadsInView.filter(
      (l: any) => (l.temperature || "").toUpperCase() === "HOT"
    ).length

    setStats({
      activeStorms: recentEvents.length,
      leadsInView: leadsInView.length,
      hotLeads,
    })
  }, [events, leads])

  // Handle lead click - open drawer
  const handleLeadClick = useCallback((lead: Lead) => {
    setSelectedLead(lead)
    setDrawerOpen(true)
  }, [])

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [39.8283, -98.5795],
      zoom: 5,
      zoomControl: true,
    })

    // Dark tile layer - CartoDB dark
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap, &copy; CARTO",
      maxZoom: 19,
    }).addTo(map)

    // Force map to recalculate size after render
    setTimeout(() => {
      map.invalidateSize()
    }, 100)

    // Initialize layer groups
    swathLayerRef.current = L.layerGroup().addTo(map)
    territoryLayerRef.current = L.layerGroup().addTo(map)
    radarLayerRef.current = L.layerGroup()

    // Initialize marker cluster group with custom styling
    leadsClusterRef.current = L.markerClusterGroup({
      chunkedLoading: true,
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      iconCreateFunction: (cluster) => {
        const markers = cluster.getAllChildMarkers()
        const hotCount = markers.filter((m: any) => m.options.leadTemp === "hot").length
        const warmCount = markers.filter((m: any) => m.options.leadTemp === "warm").length
        const count = cluster.getChildCount()

        // Determine cluster color based on temperature composition
        let bgColor = "#f59e0b" // default warm
        if (hotCount > warmCount) {
          bgColor = "#ef4444" // red for mostly hot
        } else if (hotCount === 0 && warmCount === 0) {
          bgColor = "#3b82f6" // blue for cold
        }

        return L.divIcon({
          html: `<div style="width: 40px; height: 40px; border-radius: 50%; background: ${bgColor}; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; color: white;">${count}</div>`,
          className: "",
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        })
      },
    }).addTo(map)

    // Add legend
    const legend = (L.control as any)({ position: "bottomleft" })
    legend.onAdd = function () {
      const div = L.DomUtil.create("div", "map-legend")
      div.innerHTML = `
        <div style="background: rgba(255,255,255,0.95); padding: 12px 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-size: 12px; backdrop-filter: blur(4px);">
          <h4 style="margin: 0 0 8px 0; font-weight: 600; color: #374151;">Legend</h4>
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 4px; background: rgba(239, 68, 68, 0.4); border: 2px solid #ef4444;"></div>
            <span>Severe Hail (2"+)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 4px; background: rgba(251, 191, 36, 0.4); border: 2px solid #f59e0b;"></div>
            <span>Moderate (1-2")</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 4px; background: rgba(34, 197, 94, 0.4); border: 2px solid #22c55e;"></div>
            <span>Minor (&lt;1")</span>
          </div>
          <hr style="margin: 8px 0; border: none; border-top: 1px solid #e5e7eb;" />
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 50%; background: #ef4444;"></div>
            <span>Hot Lead</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 50%; background: #f59e0b;"></div>
            <span>Warm Lead</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 50%; background: #3b82f6;"></div>
            <span>Cold Lead</span>
          </div>
        </div>
      `
      return div
    }
    legend.addTo(map)

    map.on("moveend", updateStats)

    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [updateStats])

  // Render hail swaths
  useEffect(() => {
    if (!swathLayerRef.current) return

    swathLayerRef.current.clearLayers()

    if (!layers.swaths) return

    events.forEach((event) => {
      if (!event.latitude || !event.longitude) return

      const maxHail = event.max_hail_size || 1
      let color: string, fillColor: string
      if (maxHail >= 2) {
        color = "#ef4444"
        fillColor = "rgba(239, 68, 68, 0.3)"
      } else if (maxHail >= 1) {
        color = "#f59e0b"
        fillColor = "rgba(251, 191, 36, 0.3)"
      } else {
        color = "#22c55e"
        fillColor = "rgba(34, 197, 94, 0.3)"
      }

      const radiusMiles = Math.sqrt((event.affected_area_sq_miles || 10) / Math.PI)
      const radiusMeters = radiusMiles * 1609.34

      const circle = L.circle([event.latitude, event.longitude], {
        radius: radiusMeters,
        color,
        fillColor,
        fillOpacity: 0.4,
        weight: 2,
      })

      circle.bindPopup(`
        <div style="min-width: 200px;">
          <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb;">
            <strong>${event.event_name || event.city || "Unknown Location"}</strong>
          </div>
          <div style="padding: 12px 16px;">
            <p><strong>Date:</strong> ${event.event_date || "N/A"}</p>
            <p><strong>Max Hail:</strong> ${maxHail}" diameter</p>
            <p><strong>Severity:</strong> ${event.severity || "Moderate"}</p>
            ${event.property_count ? `<p><strong>Properties:</strong> ${event.property_count.toLocaleString()}</p>` : ""}
          </div>
        </div>
      `)

      swathLayerRef.current?.addLayer(circle)
    })

    updateStats()
  }, [events, layers.swaths, updateStats])

  // Render leads with clustering
  useEffect(() => {
    if (!leadsClusterRef.current) return

    leadsClusterRef.current.clearLayers()

    if (!layers.leads) return

    leads.forEach((lead: any) => {
      if (!lead.latitude || !lead.longitude) return

      const temp = (lead.temperature || "WARM").toLowerCase()
      const tempColor = temp === "hot" ? "#ef4444" : temp === "cold" ? "#3b82f6" : "#f59e0b"
      const initial = (lead.first_name || lead.company_name || "?")[0].toUpperCase()

      const icon = L.divIcon({
        html: `<div style="width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; color: white; background: ${tempColor}; cursor: pointer;">${initial}</div>`,
        className: "",
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      })

      const marker = L.marker([lead.latitude, lead.longitude], {
        icon,
        leadTemp: temp,
      } as any)

      // Click opens drawer instead of popup
      marker.on("click", () => handleLeadClick(lead))

      leadsClusterRef.current?.addLayer(marker)
    })

    updateStats()
  }, [leads, layers.leads, updateStats, handleLeadClick])

  // Render territories
  useEffect(() => {
    if (!territoryLayerRef.current) return

    territoryLayerRef.current.clearLayers()

    if (!layers.territories) return

    SAMPLE_TERRITORIES.forEach((territory) => {
      const polygon = L.polygon(territory.bounds, {
        color: "#3b82f6",
        fillColor: "rgba(59, 130, 246, 0.1)",
        fillOpacity: 0.2,
        weight: 2,
        dashArray: "5, 5",
      })

      polygon.bindPopup(`
        <div style="min-width: 150px;">
          <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb;">
            <strong>${territory.name}</strong>
          </div>
          <div style="padding: 12px 16px;">
            <p><strong>Rep:</strong> ${territory.rep}</p>
            <p><strong>Leads:</strong> ${territory.lead_count}</p>
          </div>
        </div>
      `)

      territoryLayerRef.current?.addLayer(polygon)
    })
  }, [layers.territories])

  // Render radar coverage
  useEffect(() => {
    if (!radarLayerRef.current || !mapInstanceRef.current) return

    radarLayerRef.current.clearLayers()

    if (layers.radar) {
      RADAR_SITES.forEach((site) => {
        const circle = L.circle([site.lat, site.lon], {
          radius: site.range * 1609.34, // Convert miles to meters
          color: "#60a5fa",
          fillColor: "rgba(96, 165, 250, 0.15)",
          fillOpacity: 0.2,
          weight: 1,
          dashArray: "3, 3",
        })

        circle.bindPopup(`
          <div style="min-width: 120px; text-align: center;">
            <strong>${site.id}</strong><br/>
            ${site.name}<br/>
            <small>${site.range} mi range</small>
          </div>
        `)

        radarLayerRef.current?.addLayer(circle)

        // Add radar site marker
        const radarIcon = L.divIcon({
          html: `<div style="width: 20px; height: 20px; border-radius: 50%; background: #3b82f6; border: 2px solid white; display: flex; align-items: center; justify-content: center;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg></div>`,
          className: "",
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        })

        const marker = L.marker([site.lat, site.lon], { icon: radarIcon })
        radarLayerRef.current?.addLayer(marker)
      })

      radarLayerRef.current.addTo(mapInstanceRef.current)
    } else {
      radarLayerRef.current.remove()
    }
  }, [layers.radar])

  const handleRefresh = () => {
    refetchEvents()
    refetchLeads()
  }

  const toggleLayer = (layer: keyof LayerState) => {
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }))
  }

  if (eventsLoading || leadsLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-[calc(100vh-220px)] min-h-[500px]" />
      </div>
    )
  }

  const getTemperatureBadge = (temp: string) => {
    const t = (temp || "WARM").toUpperCase()
    if (t === "HOT") return <Badge className="bg-red-100 text-red-700 hover:bg-red-100">HOT</Badge>
    if (t === "COLD") return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">COLD</Badge>
    return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100">WARM</Badge>
  }

  const getStatusBadge = (status: string) => {
    const s = (status || "NEW").toUpperCase()
    const variants: Record<string, string> = {
      NEW: "bg-green-100 text-green-700",
      CONTACTED: "bg-blue-100 text-blue-700",
      QUALIFIED: "bg-purple-100 text-purple-700",
      CONVERTED: "bg-emerald-100 text-emerald-700",
      LOST: "bg-gray-100 text-gray-700",
    }
    return <Badge className={`${variants[s] || variants.NEW} hover:${variants[s] || variants.NEW}`}>{s}</Badge>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Hail Map"
          description="Hail swaths, territories, and leads visualization"
        />
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="flex items-center gap-2 text-green-600 bg-green-50">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live
          </Badge>
          <Button variant="outline" size="icon" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="relative bg-card rounded-xl border overflow-hidden" style={{ height: "calc(100vh - 220px)", minHeight: "500px" }}>
        <div ref={mapRef} style={{ width: "100%", height: "100%", position: "absolute", top: 0, left: 0 }} />

        {/* Layer Controls */}
        <div className="absolute top-4 right-4 z-[1000] bg-card rounded-lg shadow-lg border p-3 min-w-[160px]">
          <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-muted-foreground uppercase">
            <Layers className="h-4 w-4" />
            Layers
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.swaths}
                onChange={() => toggleLayer("swaths")}
                className="rounded"
              />
              Hail Swaths
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.territories}
                onChange={() => toggleLayer("territories")}
                className="rounded"
              />
              Territories
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.leads}
                onChange={() => toggleLayer("leads")}
                className="rounded"
              />
              Leads
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.radar}
                onChange={() => toggleLayer("radar")}
                className="rounded"
              />
              <Radio className="h-3 w-3" />
              Radar Coverage
            </label>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="absolute bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 bg-card rounded-lg shadow-lg border p-4 z-[1000]">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-red-600 flex items-center justify-center gap-1">
                <CloudLightning className="h-5 w-5" />
                {stats.activeStorms}
              </p>
              <p className="text-xs text-muted-foreground">Active (7d)</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-600 flex items-center justify-center gap-1">
                <MapPin className="h-5 w-5" />
                {stats.leadsInView}
              </p>
              <p className="text-xs text-muted-foreground">Leads in View</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600 flex items-center justify-center gap-1">
                <Flame className="h-5 w-5" />
                {stats.hotLeads}
              </p>
              <p className="text-xs text-muted-foreground">Hot Leads</p>
            </div>
          </div>
        </div>
      </div>

      {/* Lead Detail Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-[400px] sm:w-[450px] overflow-y-auto">
          {selectedLead && (
            <>
              <SheetHeader className="pb-4 border-b">
                <div className="flex items-start justify-between">
                  <div>
                    <SheetTitle className="text-xl">
                      {selectedLead.first_name} {selectedLead.last_name}
                    </SheetTitle>
                    {selectedLead.company_name && (
                      <p className="text-sm text-muted-foreground">{selectedLead.company_name}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {getTemperatureBadge(selectedLead.temperature || "")}
                    {getStatusBadge(selectedLead.status || "")}
                  </div>
                </div>
              </SheetHeader>

              <div className="space-y-6 py-6">
                {/* Contact Info */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Contact</h4>
                  {selectedLead.phone && (
                    <a
                      href={`tel:${selectedLead.phone}`}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <Phone className="h-5 w-5 text-green-600" />
                      <span>{selectedLead.phone}</span>
                    </a>
                  )}
                  {selectedLead.email && (
                    <a
                      href={`mailto:${selectedLead.email}`}
                      className="flex items-center gap-3 p-3 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
                    >
                      <Mail className="h-5 w-5 text-blue-600" />
                      <span className="truncate">{selectedLead.email}</span>
                    </a>
                  )}
                </div>

                {/* Vehicle Info */}
                {(selectedLead.vehicle_year || selectedLead.vehicle_make) && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Vehicle</h4>
                    <p className="text-lg">
                      {selectedLead.vehicle_year} {selectedLead.vehicle_make} {selectedLead.vehicle_model}
                    </p>
                  </div>
                )}

                {/* Source & Damage */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-1">Source</h4>
                    <p>{(selectedLead.source || "Unknown").replace(/_/g, " ")}</p>
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-1">Damage</h4>
                    <p>{selectedLead.damage_type || "N/A"}</p>
                  </div>
                </div>

                {/* Notes */}
                {selectedLead.notes && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Notes</h4>
                    <p className="text-sm bg-muted p-3 rounded-lg">{selectedLead.notes}</p>
                  </div>
                )}

                {/* Created Date */}
                <div>
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide mb-1">Created</h4>
                  <p className="text-sm">
                    {selectedLead.created_at
                      ? new Date(selectedLead.created_at).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })
                      : "Unknown"}
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="space-y-3 pt-4 border-t">
                  <div className="grid grid-cols-2 gap-3">
                    {selectedLead.phone && (
                      <Button asChild className="bg-green-600 hover:bg-green-700">
                        <a href={`tel:${selectedLead.phone}`}>
                          <Phone className="h-4 w-4 mr-2" />
                          Call
                        </a>
                      </Button>
                    )}
                    {selectedLead.email && (
                      <Button asChild variant="outline">
                        <a href={`mailto:${selectedLead.email}`}>
                          <Mail className="h-4 w-4 mr-2" />
                          Email
                        </a>
                      </Button>
                    )}
                  </div>

                  {selectedLead.latitude && selectedLead.longitude && (
                    <Button asChild variant="outline" className="w-full">
                      <a
                        href={`https://www.google.com/maps/dir/?api=1&destination=${selectedLead.latitude},${selectedLead.longitude}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Navigation className="h-4 w-4 mr-2" />
                        Get Directions
                      </a>
                    </Button>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <Button
                      variant="default"
                      onClick={() => convertMutation.mutate(selectedLead.id)}
                      disabled={convertMutation.isPending || selectedLead.status === "CONVERTED"}
                    >
                      <UserPlus className="h-4 w-4 mr-2" />
                      Convert
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => navigate(`/leads/${selectedLead.id}`)}
                    >
                      <Edit className="h-4 w-4 mr-2" />
                      Edit Lead
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
