import { useEffect, useRef, useState, useCallback } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import "leaflet.markercluster/dist/MarkerCluster.css"
import "leaflet.markercluster/dist/MarkerCluster.Default.css"

// Import markercluster - must be after L is defined
import "leaflet.markercluster"

// Ensure markerClusterGroup is available
declare module "leaflet" {
  function markerClusterGroup(options?: any): any
}

import { PageHeader } from "@/components/app/page-header"
import { StormCalendar } from "@/components/app/storm-calendar"
import { RadarReplay } from "@/components/app/radar-replay"
import { TerritoryAlerts } from "@/components/app/territory-alerts"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Card, CardContent } from "@/components/ui/card"
import { Lead } from "@/types"
import { leadsApi } from "@/api/leads"
import {
  hailEventsApi,
  stormCellsApi,
  stormMonitorApi,
  HailEvent,
  StormCell,
  SwathFeature,
  RadarSite,
  CalendarDayEvent,
} from "@/api/weather"
import {
  RefreshCw,
  Layers,
  MapPin,
  CloudLightning,
  Flame,
  Phone,
  Mail,
  Navigation,
  UserPlus,
  Edit,
  Radio,
  Zap,
  Activity,
  AlertTriangle,
  Calendar,
  Play,
  Bell,
} from "lucide-react"

// Fix Leaflet default marker icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

interface LayerState {
  swaths: boolean
  leads: boolean
  activeCells: boolean
  radar: boolean
  forecasts: boolean
}

// 10-level hail size color scale (1/2" to 3"+ in 1/4" increments)
const HAIL_SIZE_COLORS: { min: number; max: number; label: string; border: string; fill: string }[] = [
  { min: 0, max: 0.5, label: '<0.5"', border: "#a3e635", fill: "rgba(163, 230, 53, 0.35)" },      // Lime
  { min: 0.5, max: 0.75, label: '0.5"', border: "#84cc16", fill: "rgba(132, 204, 22, 0.35)" },   // Lime-600
  { min: 0.75, max: 1.0, label: '0.75"', border: "#22c55e", fill: "rgba(34, 197, 94, 0.35)" },   // Green
  { min: 1.0, max: 1.25, label: '1.0"', border: "#facc15", fill: "rgba(250, 204, 21, 0.35)" },   // Yellow
  { min: 1.25, max: 1.5, label: '1.25"', border: "#fbbf24", fill: "rgba(251, 191, 36, 0.35)" },  // Amber
  { min: 1.5, max: 1.75, label: '1.5"', border: "#f59e0b", fill: "rgba(245, 158, 11, 0.35)" },   // Amber-500
  { min: 1.75, max: 2.0, label: '1.75"', border: "#f97316", fill: "rgba(249, 115, 22, 0.35)" },  // Orange
  { min: 2.0, max: 2.5, label: '2.0"', border: "#ef4444", fill: "rgba(239, 68, 68, 0.35)" },     // Red
  { min: 2.5, max: 3.0, label: '2.5"', border: "#dc2626", fill: "rgba(220, 38, 38, 0.35)" },     // Red-600
  { min: 3.0, max: 99, label: '3.0"+', border: "#9333ea", fill: "rgba(147, 51, 234, 0.35)" },    // Purple (catastrophic)
]

function getHailSizeColor(hailSizeInches: number | undefined | null): { border: string; fill: string } {
  const size = hailSizeInches ?? 0
  const level = HAIL_SIZE_COLORS.find(l => size >= l.min && size < l.max)
  return level ?? HAIL_SIZE_COLORS[HAIL_SIZE_COLORS.length - 1]
}

export function HailMapPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const swathLayerRef = useRef<L.LayerGroup | null>(null)
  const leadsClusterRef = useRef<L.MarkerClusterGroup | null>(null)
  const activeCellsLayerRef = useRef<L.LayerGroup | null>(null)
  const radarLayerRef = useRef<L.LayerGroup | null>(null)
  const forecastLayerRef = useRef<L.LayerGroup | null>(null)

  const [layers, setLayers] = useState<LayerState>({
    swaths: true,
    leads: true,
    activeCells: true,
    radar: false,
    forecasts: false,
  })

  const [stats, setStats] = useState({
    activeStorms: 0,
    activeCells: 0,
    leadsInView: 0,
    hotLeads: 0,
  })

  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [selectedCell, setSelectedCell] = useState<StormCell | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [cellDrawerOpen, setCellDrawerOpen] = useState(false)
  const [calendarOpen, setCalendarOpen] = useState(true)
  const [radarReplayOpen, setRadarReplayOpen] = useState(false)
  const [territoryAlertsOpen, setTerritoryAlertsOpen] = useState(false)

  // Fetch hail events using typed API
  const { data: eventsData, isLoading: eventsLoading, refetch: refetchEvents } = useQuery({
    queryKey: ["hail-events-map"],
    queryFn: () => hailEventsApi.list({ days: 90 }),
  })

  // Fetch real GeoJSON swaths
  const { data: swathsData, refetch: refetchSwaths } = useQuery({
    queryKey: ["storm-swaths"],
    queryFn: () => stormCellsApi.getAllSwaths(),
  })

  // Fetch active storm cells
  const { data: cellsData, refetch: refetchCells } = useQuery({
    queryKey: ["active-cells-map"],
    queryFn: () => stormCellsApi.getActiveCells(),
    refetchInterval: 30000, // Refresh every 30s
  })

  // Fetch radar sites from backend
  const { data: radarsData } = useQuery({
    queryKey: ["radar-sites"],
    queryFn: () => stormMonitorApi.getAvailableRadars(),
  })

  // Fetch leads with location
  const { data: leadsData, isLoading: leadsLoading, refetch: refetchLeads } = useQuery({
    queryKey: ["leads-map"],
    queryFn: () => leadsApi.list({ per_page: 500 }),
  })

  // Convert lead to customer mutation
  const convertMutation = useMutation({
    mutationFn: (leadId: number) => leadsApi.convert(leadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads-map"] })
      setDrawerOpen(false)
      setSelectedLead(null)
    },
  })

  const events: HailEvent[] = eventsData?.data?.events || []
  const swaths: SwathFeature[] = swathsData?.data?.features || (swathsData as any)?.features || []
  const activeCells: StormCell[] = cellsData?.data?.active_cells || []
  const radars: RadarSite[] = radarsData?.data?.radars || []
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
      activeCells: activeCells.length,
      leadsInView: leadsInView.length,
      hotLeads,
    })
  }, [events, leads, activeCells])

  // Handle lead click - open drawer
  const handleLeadClick = useCallback((lead: Lead) => {
    setSelectedLead(lead)
    setDrawerOpen(true)
  }, [])

  // Handle cell click - open cell drawer
  const handleCellClick = useCallback((cell: StormCell) => {
    setSelectedCell(cell)
    setCellDrawerOpen(true)
  }, [])

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    try {
      console.log("Initializing Leaflet map...")
      console.log("Map container:", mapRef.current)
      console.log("Container dimensions:", mapRef.current.offsetWidth, "x", mapRef.current.offsetHeight)

      const map = L.map(mapRef.current, {
        center: [39.8283, -98.5795],
        zoom: 5,
        zoomControl: true,
      })

    console.log("Map created, adding tile layer...")

    // OpenStreetMap tile layer (reliable fallback)
    const tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    })

    tileLayer.on('tileerror', (error) => {
      console.error("Tile load error:", error)
    })

    tileLayer.on('tileload', () => {
      console.log("Tile loaded successfully")
    })

    tileLayer.addTo(map)

    // Force map to recalculate size after render (multiple times to ensure proper sizing)
    setTimeout(() => {
      console.log("Invalidating size (100ms)...")
      map.invalidateSize()
    }, 100)
    setTimeout(() => map.invalidateSize(), 300)
    setTimeout(() => map.invalidateSize(), 500)

    // Initialize layer groups
    swathLayerRef.current = L.layerGroup().addTo(map)
    activeCellsLayerRef.current = L.layerGroup().addTo(map)
    radarLayerRef.current = L.layerGroup()
    forecastLayerRef.current = L.layerGroup()

    // Initialize marker cluster group with custom styling
    leadsClusterRef.current = L.markerClusterGroup({
      chunkedLoading: true,
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      iconCreateFunction: (cluster: any) => {
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
            <div style="width: 16px; height: 16px; border-radius: 4px; background: rgba(147, 51, 234, 0.4); border: 2px solid #9333ea;"></div>
            <span>Catastrophic (3"+)</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <div style="width: 16px; height: 16px; border-radius: 4px; background: rgba(239, 68, 68, 0.4); border: 2px solid #ef4444;"></div>
            <span>Severe (2-3")</span>
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
            <div style="width: 16px; height: 16px; border-radius: 50%; background: #f97316; border: 2px solid white;"></div>
            <span>Active Storm Cell</span>
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
    } catch (error) {
      console.error("Error initializing map:", error)
      return
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [updateStats])

  // Render hail swaths from real GeoJSON data
  useEffect(() => {
    if (!swathLayerRef.current) return

    swathLayerRef.current.clearLayers()

    if (!layers.swaths) return

    // First try to use real GeoJSON swaths
    if (swaths.length > 0) {
      swaths.forEach((swath) => {
        if (!swath.geometry || swath.geometry.type !== 'Polygon') return

        // Use hail size for color (10-level scale)
        const hailSize = swath.properties.max_hail_size
        const colors = getHailSizeColor(hailSize)
        const severity = swath.properties.severity || 'MODERATE'

        const polygon = L.geoJSON(swath as any, {
          style: {
            color: colors.border,
            fillColor: colors.fill,
            fillOpacity: 0.5,
            weight: 2,
          },
        })

        polygon.bindPopup(`
          <div style="min-width: 200px;">
            <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; background: ${colors.fill};">
              <strong>${swath.properties.event_name || 'Storm Swath'}</strong>
            </div>
            <div style="padding: 12px 16px;">
              <p><strong>Cell ID:</strong> ${swath.properties.cell_id || 'N/A'}</p>
              <p><strong>Max Hail:</strong> <span style="color: ${colors.border}; font-weight: bold;">${hailSize || 'Unknown'}"</span></p>
              <p><strong>Severity:</strong> ${severity}</p>
              <p><strong>Area:</strong> ${swath.properties.area_sq_miles?.toFixed(1) || 'N/A'} sq mi</p>
            </div>
          </div>
        `)

        swathLayerRef.current?.addLayer(polygon)
      })
    }

    // Render events - use swath_polygon if available, otherwise fall back to circle
    events.forEach((event) => {
      // Skip if we already have a swath for this event from the separate swaths API
      if (swaths.some(s => s.properties.event_id === event.id)) return

      // Use hail size for 10-level color scale
      const hailSize = event.max_hail_size || event.hail_size_inches
      const colors = getHailSizeColor(hailSize)
      const severity = event.severity || 'MODERATE'

      // Try to parse swath_polygon GeoJSON if available
      let swathGeojson: { type: string; coordinates: number[][][] } | null = null
      try {
        if (event.swath_polygon) {
          swathGeojson = typeof event.swath_polygon === 'string'
            ? JSON.parse(event.swath_polygon)
            : event.swath_polygon
        }
      } catch (e) {
        // Parsing failed, will fall back to circle
      }

      if (swathGeojson && swathGeojson.type === 'Polygon' && swathGeojson.coordinates) {
        // Render actual polygon swath
        const polygon = L.geoJSON({
          type: 'Feature',
          geometry: swathGeojson,
          properties: {}
        } as any, {
          style: {
            color: colors.border,
            fillColor: colors.fill,
            fillOpacity: 0.5,
            weight: 2,
          },
        })

        polygon.bindPopup(`
          <div style="min-width: 200px;">
            <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; background: ${colors.fill};">
              <strong>${event.event_name || event.city || "Unknown Location"}</strong>
            </div>
            <div style="padding: 12px 16px;">
              <p><strong>Date:</strong> ${event.event_date || "N/A"}</p>
              <p><strong>Max Hail:</strong> <span style="color: ${colors.border}; font-weight: bold;">${hailSize || 'N/A'}"</span></p>
              <p><strong>Severity:</strong> ${severity}</p>
              ${event.swath_area_sqmi ? `<p><strong>Area:</strong> ${event.swath_area_sqmi.toFixed(1)} sq mi</p>` : ""}
              ${event.estimated_vehicles_affected ? `<p><strong>Est. Vehicles:</strong> ${event.estimated_vehicles_affected.toLocaleString()}</p>` : ""}
              ${event.jobs_created ? `<p><strong>Jobs Created:</strong> ${event.jobs_created}</p>` : ""}
            </div>
          </div>
        `)

        swathLayerRef.current?.addLayer(polygon)
      } else {
        // Fall back to circle representation
        const lat = event.center_lat ?? event.latitude
        const lon = event.center_lon ?? event.longitude
        if (lat == null || lon == null) return

        const areaSquareMiles = event.swath_area_sqmi || event.affected_area_sq_miles || 10
        const radiusMiles = Math.sqrt(areaSquareMiles / Math.PI)
        const radiusMeters = radiusMiles * 1609.34

        const circle = L.circle([lat, lon], {
          radius: radiusMeters,
          color: colors.border,
          fillColor: colors.fill,
          fillOpacity: 0.5,
          weight: 2,
        })

        circle.bindPopup(`
          <div style="min-width: 200px;">
            <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; background: ${colors.fill};">
              <strong>${event.event_name || event.city || "Unknown Location"}</strong>
            </div>
            <div style="padding: 12px 16px;">
              <p><strong>Date:</strong> ${event.event_date || "N/A"}</p>
              <p><strong>Max Hail:</strong> <span style="color: ${colors.border}; font-weight: bold;">${hailSize || 'N/A'}"</span></p>
              <p><strong>Severity:</strong> ${severity}</p>
              ${event.estimated_vehicles_affected ? `<p><strong>Est. Vehicles:</strong> ${event.estimated_vehicles_affected.toLocaleString()}</p>` : ""}
              ${event.jobs_created ? `<p><strong>Jobs Created:</strong> ${event.jobs_created}</p>` : ""}
            </div>
          </div>
        `)

        swathLayerRef.current?.addLayer(circle)
      }
    })

    updateStats()
  }, [events, swaths, layers.swaths, updateStats])

  // Render active storm cells
  useEffect(() => {
    if (!activeCellsLayerRef.current) return

    activeCellsLayerRef.current.clearLayers()

    if (!layers.activeCells) return

    activeCells.forEach((cell) => {
      if (!cell.lat || !cell.lon) return

      // Cell marker - pulsing orange circle
      const icon = L.divIcon({
        html: `
          <div style="position: relative;">
            <div style="width: 24px; height: 24px; border-radius: 50%; background: #f97316; border: 3px solid white; box-shadow: 0 0 10px rgba(249, 115, 22, 0.5); animation: pulse 2s infinite;"></div>
            <div style="position: absolute; top: -8px; left: 50%; transform: translateX(-50%); background: #1f2937; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; white-space: nowrap;">
              ${cell.max_hail_size ? `${cell.max_hail_size}"` : 'Active'}
            </div>
          </div>
        `,
        className: "",
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      })

      const marker = L.marker([cell.lat, cell.lon], { icon })

      marker.on("click", () => handleCellClick(cell))

      marker.bindPopup(`
        <div style="min-width: 180px;">
          <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; background: rgba(249, 115, 22, 0.1);">
            <strong>Active Cell #${cell.id}</strong>
          </div>
          <div style="padding: 12px 16px;">
            <p><strong>Max Reflectivity:</strong> ${cell.max_reflectivity?.toFixed(1) || 'N/A'} dBZ</p>
            <p><strong>MESH:</strong> ${cell.mesh ? `${cell.mesh.toFixed(1)}"` : 'N/A'}</p>
            <p><strong>VIL:</strong> ${cell.vil?.toFixed(1) || 'N/A'} kg/m²</p>
            <p><strong>Movement:</strong> ${cell.motion_speed?.toFixed(0) || 'N/A'} mph @ ${cell.motion_direction?.toFixed(0) || 'N/A'}°</p>
            <p><strong>Stage:</strong> ${cell.lifecycle_stage || 'Unknown'}</p>
          </div>
        </div>
      `)

      activeCellsLayerRef.current?.addLayer(marker)

      // Draw motion vector if available
      if (cell.motion_speed && cell.motion_direction && layers.forecasts) {
        const forecastMinutes = 30
        const distanceMiles = (cell.motion_speed * forecastMinutes) / 60
        const distanceMeters = distanceMiles * 1609.34

        // Calculate forecast position
        const bearing = cell.motion_direction * (Math.PI / 180)
        const lat1 = cell.lat * (Math.PI / 180)
        const lon1 = cell.lon * (Math.PI / 180)
        const R = 6371000 // Earth radius in meters

        const lat2 = Math.asin(
          Math.sin(lat1) * Math.cos(distanceMeters / R) +
          Math.cos(lat1) * Math.sin(distanceMeters / R) * Math.cos(bearing)
        )
        const lon2 = lon1 + Math.atan2(
          Math.sin(bearing) * Math.sin(distanceMeters / R) * Math.cos(lat1),
          Math.cos(distanceMeters / R) - Math.sin(lat1) * Math.sin(lat2)
        )

        const forecastLat = lat2 * (180 / Math.PI)
        const forecastLon = lon2 * (180 / Math.PI)

        // Draw motion vector line
        const line = L.polyline(
          [[cell.lat, cell.lon], [forecastLat, forecastLon]],
          {
            color: "#f97316",
            weight: 2,
            dashArray: "5, 5",
            opacity: 0.7,
          }
        )

        // Forecast position circle
        const forecastCircle = L.circle([forecastLat, forecastLon], {
          radius: 3000,
          color: "#f97316",
          fillColor: "rgba(249, 115, 22, 0.2)",
          fillOpacity: 0.3,
          weight: 1,
          dashArray: "3, 3",
        })

        forecastCircle.bindPopup(`
          <div style="text-align: center;">
            <strong>30-min Forecast</strong><br/>
            Cell #${cell.id}
          </div>
        `)

        forecastLayerRef.current?.addLayer(line)
        forecastLayerRef.current?.addLayer(forecastCircle)
      }
    })
  }, [activeCells, layers.activeCells, layers.forecasts, handleCellClick])

  // Render forecasts layer
  useEffect(() => {
    if (!forecastLayerRef.current || !mapInstanceRef.current) return

    if (layers.forecasts) {
      forecastLayerRef.current.addTo(mapInstanceRef.current)
    } else {
      forecastLayerRef.current.remove()
    }
  }, [layers.forecasts])

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

  // Render radar coverage from real API
  useEffect(() => {
    if (!radarLayerRef.current || !mapInstanceRef.current) return

    radarLayerRef.current.clearLayers()

    if (layers.radar && radars.length > 0) {
      radars.forEach((site) => {
        if (site.lat == null || site.lon == null) return

        const range = 230 // Default NEXRAD range in km
        const rangeMeters = range * 1000

        const circle = L.circle([site.lat, site.lon], {
          radius: rangeMeters,
          color: "#60a5fa",
          fillColor: "rgba(96, 165, 250, 0.15)",
          fillOpacity: 0.2,
          weight: 1,
          dashArray: "3, 3",
        })

        circle.bindPopup(`
          <div style="min-width: 120px; text-align: center;">
            <strong>${site.site_code}</strong><br/>
            ${site.name}<br/>
            <small>${site.state}</small>
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
  }, [layers.radar, radars])

  const handleRefresh = () => {
    refetchEvents()
    refetchSwaths()
    refetchCells()
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

  // Handle calendar event selection - zoom map to event location
  const handleCalendarEventSelect = useCallback((event: CalendarDayEvent) => {
    if (mapInstanceRef.current && event.lat && event.lon) {
      mapInstanceRef.current.setView([event.lat, event.lon], 10, { animate: true })
    }
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Hail Map"
          description="Real-time storm tracking, hail swaths, and lead visualization"
        />
        <div className="flex items-center gap-2">
          {activeCells.length > 0 && (
            <Badge variant="outline" className="flex items-center gap-2 text-orange-600 bg-orange-50">
              <Zap className="w-3 h-3" />
              {activeCells.length} Active Cells
            </Badge>
          )}
          <Badge variant="outline" className="flex items-center gap-2 text-green-600 bg-green-50">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live
          </Badge>
          <Button
            variant={territoryAlertsOpen ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setTerritoryAlertsOpen(!territoryAlertsOpen)
              if (!territoryAlertsOpen) {
                setRadarReplayOpen(false)
                setCalendarOpen(false)
              }
            }}
            className="gap-2"
          >
            <Bell className="h-4 w-4" />
            Alerts
          </Button>
          <Button
            variant={radarReplayOpen ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setRadarReplayOpen(!radarReplayOpen)
              if (!radarReplayOpen) {
                setTerritoryAlertsOpen(false)
                setCalendarOpen(false)
              }
            }}
            className="gap-2"
          >
            <Play className="h-4 w-4" />
            Radar
          </Button>
          <Button
            variant={calendarOpen ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setCalendarOpen(!calendarOpen)
              if (!calendarOpen) {
                setRadarReplayOpen(false)
                setTerritoryAlertsOpen(false)
              }
            }}
            className="gap-2"
          >
            <Calendar className="h-4 w-4" />
            Calendar
          </Button>
          <Button variant="outline" size="icon" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Map Container */}
        <div className={`relative bg-card rounded-xl border overflow-hidden transition-all ${calendarOpen ? 'flex-1' : 'w-full'}`} style={{ height: "calc(100vh - 220px)", minHeight: "500px" }}>
        <div
          ref={mapRef}
          style={{
            width: "100%",
            height: "100%",
            position: "absolute",
            top: 0,
            left: 0,
            zIndex: 1,
            background: "#f0f0f0"
          }}
        />

        {/* Layer Controls */}
        <div className="absolute top-4 right-4 z-[1000] bg-card rounded-lg shadow-lg border p-3 min-w-[180px]">
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
              <CloudLightning className="h-3 w-3 text-yellow-500" />
              Hail Swaths
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.activeCells}
                onChange={() => toggleLayer("activeCells")}
                className="rounded"
              />
              <Zap className="h-3 w-3 text-orange-500" />
              Active Cells
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.forecasts}
                onChange={() => toggleLayer("forecasts")}
                className="rounded"
              />
              <Activity className="h-3 w-3 text-purple-500" />
              Cell Forecasts
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.leads}
                onChange={() => toggleLayer("leads")}
                className="rounded"
              />
              <MapPin className="h-3 w-3 text-blue-500" />
              Leads
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={layers.radar}
                onChange={() => toggleLayer("radar")}
                className="rounded"
              />
              <Radio className="h-3 w-3 text-blue-500" />
              Radar Coverage ({radars.length})
            </label>
          </div>

          {/* Hail Size Legend */}
          {layers.swaths && (
            <div className="mt-3 pt-3 border-t">
              <div className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                Hail Size
              </div>
              <div className="grid grid-cols-2 gap-1 text-xs">
                {HAIL_SIZE_COLORS.map((level) => (
                  <div key={level.label} className="flex items-center gap-1">
                    <div
                      className="w-3 h-3 rounded-sm border"
                      style={{ backgroundColor: level.fill, borderColor: level.border }}
                    />
                    <span className="text-muted-foreground">{level.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Active Cells Alert */}
        {activeCells.length > 0 && (
          <div className="absolute top-4 left-4 z-[1000] bg-orange-500 text-white rounded-lg shadow-lg px-4 py-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span className="font-medium">{activeCells.length} Active Storm Cells Tracking</span>
          </div>
        )}

        {/* Stats Bar */}
        <div className="absolute bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-96 bg-card rounded-lg shadow-lg border p-4 z-[1000]">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-red-600 flex items-center justify-center gap-1">
                <CloudLightning className="h-5 w-5" />
                {stats.activeStorms}
              </p>
              <p className="text-xs text-muted-foreground">Storms (7d)</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-600 flex items-center justify-center gap-1">
                <Zap className="h-5 w-5" />
                {stats.activeCells}
              </p>
              <p className="text-xs text-muted-foreground">Active Cells</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-600 flex items-center justify-center gap-1">
                <MapPin className="h-5 w-5" />
                {stats.leadsInView}
              </p>
              <p className="text-xs text-muted-foreground">Leads</p>
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

        {/* Territory Alerts Panel */}
        {territoryAlertsOpen && (
          <div className="w-96 flex-shrink-0" style={{ height: "calc(100vh - 220px)", minHeight: "500px" }}>
            <TerritoryAlerts className="h-full overflow-auto" />
          </div>
        )}

        {/* Radar Replay Panel */}
        {radarReplayOpen && !territoryAlertsOpen && (
          <div className="w-96 flex-shrink-0" style={{ height: "calc(100vh - 220px)", minHeight: "500px" }}>
            <RadarReplay className="h-full overflow-auto" />
          </div>
        )}

        {/* Storm Calendar Panel */}
        {calendarOpen && !radarReplayOpen && !territoryAlertsOpen && (
          <div className="w-96 flex-shrink-0" style={{ height: "calc(100vh - 220px)", minHeight: "500px" }}>
            <StormCalendar
              onSelectEvent={handleCalendarEventSelect}
              className="h-full overflow-auto"
            />
          </div>
        )}
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

      {/* Storm Cell Detail Drawer */}
      <Sheet open={cellDrawerOpen} onOpenChange={setCellDrawerOpen}>
        <SheetContent className="w-[400px] sm:w-[450px] overflow-y-auto">
          {selectedCell && (
            <>
              <SheetHeader className="pb-4 border-b">
                <div className="flex items-start justify-between">
                  <div>
                    <SheetTitle className="text-xl flex items-center gap-2">
                      <Zap className="h-5 w-5 text-orange-500" />
                      Storm Cell #{selectedCell.id}
                    </SheetTitle>
                    <p className="text-sm text-muted-foreground">
                      {selectedCell.lifecycle_stage || 'Active'} Stage
                    </p>
                  </div>
                  <Badge className="bg-orange-100 text-orange-700">
                    {selectedCell.max_hail_size ? `${selectedCell.max_hail_size}" Hail` : 'Tracking'}
                  </Badge>
                </div>
              </SheetHeader>

              <div className="space-y-6 py-6">
                {/* Radar Metrics */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Radar Metrics</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <Card>
                      <CardContent className="p-3 text-center">
                        <div className="text-2xl font-bold text-red-600">
                          {selectedCell.max_reflectivity?.toFixed(0) || '--'}
                        </div>
                        <div className="text-xs text-muted-foreground">Max dBZ</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-3 text-center">
                        <div className="text-2xl font-bold text-purple-600">
                          {selectedCell.mesh?.toFixed(1) || '--'}"
                        </div>
                        <div className="text-xs text-muted-foreground">MESH</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-3 text-center">
                        <div className="text-2xl font-bold text-blue-600">
                          {selectedCell.vil?.toFixed(0) || '--'}
                        </div>
                        <div className="text-xs text-muted-foreground">VIL kg/m²</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-3 text-center">
                        <div className="text-2xl font-bold text-green-600">
                          {selectedCell.echo_tops?.toFixed(0) || '--'}
                        </div>
                        <div className="text-xs text-muted-foreground">Echo Tops kft</div>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                {/* Motion */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Cell Motion</h4>
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="flex justify-between mb-2">
                      <span>Speed</span>
                      <span className="font-medium">{selectedCell.motion_speed?.toFixed(0) || '--'} mph</span>
                    </div>
                    <div className="flex justify-between mb-2">
                      <span>Direction</span>
                      <span className="font-medium">{selectedCell.motion_direction?.toFixed(0) || '--'}°</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Track Duration</span>
                      <span className="font-medium">{selectedCell.track_duration_minutes?.toFixed(0) || '--'} min</span>
                    </div>
                  </div>
                </div>

                {/* Location */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Location</h4>
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="flex justify-between mb-2">
                      <span>Latitude</span>
                      <span className="font-mono">{selectedCell.lat?.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Longitude</span>
                      <span className="font-mono">{selectedCell.lon?.toFixed(4)}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-3 pt-4 border-t">
                  <Button className="w-full" variant="outline" asChild>
                    <a
                      href={`https://www.google.com/maps?q=${selectedCell.lat},${selectedCell.lon}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <MapPin className="h-4 w-4 mr-2" />
                      View on Google Maps
                    </a>
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Add CSS for pulse animation and Leaflet fixes */}
      <style>{`
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.7); }
          70% { box-shadow: 0 0 0 15px rgba(249, 115, 22, 0); }
          100% { box-shadow: 0 0 0 0 rgba(249, 115, 22, 0); }
        }
        /* Leaflet tile layer fix */
        .leaflet-tile-pane {
          z-index: 1 !important;
        }
        .leaflet-tile {
          visibility: visible !important;
          opacity: 1 !important;
        }
        .leaflet-container {
          background: #1a1a2e !important;
        }
      `}</style>
    </div>
  )
}
