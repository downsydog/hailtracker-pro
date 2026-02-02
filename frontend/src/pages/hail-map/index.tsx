import { useEffect, useRef, useState, useCallback, useMemo } from "react"
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Switch } from "@/components/ui/switch"
import { Lead } from "@/types"
import { leadsApi } from "@/api/leads"
import {
  hailEventsApi,
  stormCellsApi,
  stormMonitorApi,
  HailEvent,
  StormCell,
  RadarSite,
  CalendarDayEvent,
  StormPhoto,
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
  Camera,
  ExternalLink,
  ImageIcon,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  Pause,
  SkipBack,
  SkipForward,
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
  console.log("=== HailMapPage RENDER ===")

  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const mapRef = useRef<HTMLDivElement | null>(null)
  const [mapContainerReady, setMapContainerReady] = useState(false)
  const [mapInitialized, setMapInitialized] = useState(false)

  // Callback ref to detect when map container is mounted
  const mapContainerRef = useCallback((node: HTMLDivElement | null) => {
    mapRef.current = node
    if (node && !mapContainerReady) {
      setMapContainerReady(true)
    }
  }, [mapContainerReady])
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
  const [selectedEvent, setSelectedEvent] = useState<HailEvent | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [cellDrawerOpen, setCellDrawerOpen] = useState(false)
  const [eventDrawerOpen, setEventDrawerOpen] = useState(false)
  const [calendarOpen, setCalendarOpen] = useState(true)
  const [radarReplayOpen, setRadarReplayOpen] = useState(false)
  const [territoryAlertsOpen, setTerritoryAlertsOpen] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [pendingZoomEventId, setPendingZoomEventId] = useState<number | null>(null)

  // ============================================================================
  // LIVE RADAR SYSTEM STATE
  // ============================================================================
  const [showLiveRadar, setShowLiveRadar] = useState(false)
  const [liveRadarOpacity, setLiveRadarOpacity] = useState(0.6)
  const [radarFrames, setRadarFrames] = useState<any[]>([])
  const [radarHost, setRadarHost] = useState('')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [animationSpeed, setAnimationSpeed] = useState(500) // ms between frames
  const liveRadarLayerRef = useRef<L.TileLayer | null>(null)

  // Real-time overlay state
  const [showAlertPolygons, setShowAlertPolygons] = useState(true)
  const [showHailReports, setShowHailReports] = useState(true)
  const [showTornadoReports, setShowTornadoReports] = useState(true)
  const [showWatchBoxes, setShowWatchBoxes] = useState(true)
  const [realtimeData, setRealtimeData] = useState<any>(null)
  const alertPolygonLayerRef = useRef<L.LayerGroup | null>(null)
  const hailReportLayerRef = useRef<L.LayerGroup | null>(null)
  const tornadoReportLayerRef = useRef<L.LayerGroup | null>(null)
  const watchBoxLayerRef = useRef<L.LayerGroup | null>(null)

  // Clear any cached hail events on mount to ensure clean start
  useEffect(() => {
    console.log("Clearing cached hail-events data on mount")
    queryClient.removeQueries({ queryKey: ["hail-events-map"] })
  }, [queryClient])

  // Fetch hail events - only when date is selected
  const { data: eventsData, refetch: refetchEvents } = useQuery({
    queryKey: ["hail-events-map", selectedDate],
    queryFn: async () => {
      console.log("API CALL: hailEventsApi.list with event_date:", selectedDate)
      const response = await hailEventsApi.list({ event_date: selectedDate || undefined })
      console.log("API RESPONSE _debug:", response.data?._debug)
      return response
    },
    enabled: !!selectedDate,
  })

  // Note: Swaths come from the events data (swath_polygon field) - no separate swaths query needed
  // The getAllSwaths API doesn't support date filtering, so we rely on events for date-filtered swaths

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

  // Fetch photos for selected storm event
  const { data: photosData, isLoading: photosLoading, refetch: refetchPhotos } = useQuery({
    queryKey: ["storm-photos", selectedEvent?.id],
    queryFn: () => hailEventsApi.getStormPhotos(selectedEvent!.id),
    enabled: !!selectedEvent?.id && eventDrawerOpen,
  })

  const stormPhotos = useMemo<StormPhoto[]>(
    () => photosData?.data?.photos || [],
    [photosData?.data?.photos]
  )

  // ============================================================================
  // LIVE RADAR SYSTEM - DATA FETCHING
  // ============================================================================

  // Fetch radar data from RainViewer (FREE API)
  const fetchRadarData = useCallback(async () => {
    try {
      const response = await fetch('https://api.rainviewer.com/public/weather-maps.json')
      const data = await response.json()

      // Combine past frames and nowcast (forecast)
      const frames = [
        ...data.radar.past,
        ...data.radar.nowcast
      ]

      setRadarHost(data.host)
      setRadarFrames(frames)
      // Start at most recent past frame
      setCurrentFrame(data.radar.past.length - 1)

      console.log(`Loaded ${frames.length} radar frames from RainViewer`)
    } catch (error) {
      console.error('Failed to fetch radar data:', error)
    }
  }, [])

  // Fetch real-time weather data from our API
  const fetchRealtimeData = useCallback(async () => {
    try {
      const response = await fetch('/api/realtime/fetch?hours=6')
      const data = await response.json()
      setRealtimeData(data)
      console.log('Realtime weather data:', {
        alerts: data.alerts?.length || 0,
        hailReports: data.hail_reports?.length || 0,
        tornadoReports: data.tornado_reports?.length || 0,
        watches: data.watches?.length || 0,
      })
    } catch (error) {
      console.error('Failed to fetch realtime data:', error)
    }
  }, [])

  // Auto-refresh radar data every 10 minutes when enabled
  useEffect(() => {
    if (!showLiveRadar) return

    fetchRadarData()
    const interval = setInterval(fetchRadarData, 10 * 60 * 1000)
    return () => clearInterval(interval)
  }, [showLiveRadar, fetchRadarData])

  // Fetch realtime data when radar is enabled, refresh every 60 seconds
  useEffect(() => {
    if (!showLiveRadar) return

    fetchRealtimeData()
    const interval = setInterval(fetchRealtimeData, 60 * 1000)
    return () => clearInterval(interval)
  }, [showLiveRadar, fetchRealtimeData])

  // Animation loop for radar frames
  useEffect(() => {
    if (!isAnimating || radarFrames.length === 0) return

    const interval = setInterval(() => {
      setCurrentFrame(prev => {
        const next = prev + 1
        return next >= radarFrames.length ? 0 : next
      })
    }, animationSpeed)

    return () => clearInterval(interval)
  }, [isAnimating, radarFrames.length, animationSpeed])

  // Zoom map to fit a storm's swath bounds
  const zoomToStorm = useCallback((storm: HailEvent) => {
    if (!mapInstanceRef.current) return

    try {
      // If storm has a swath polygon, fit bounds to it
      if (storm.swath_polygon) {
        const geojson = typeof storm.swath_polygon === 'string'
          ? JSON.parse(storm.swath_polygon)
          : storm.swath_polygon

        if (geojson && geojson.coordinates) {
          const layer = L.geoJSON({
            type: 'Feature',
            geometry: geojson,
            properties: {}
          } as any)
          const bounds = layer.getBounds()
          if (bounds.isValid()) {
            mapInstanceRef.current.fitBounds(bounds, {
              padding: [50, 50],
              maxZoom: 12,
              animate: true
            })
            console.log("Zoomed to swath polygon bounds")
            return
          }
        }
      }

      // Fall back to center coordinates with calculated zoom
      const lat = storm.center_lat ?? storm.latitude
      const lon = storm.center_lon ?? storm.longitude

      if (lat != null && lon != null) {
        // Calculate zoom based on swath area
        const areaSquareMiles = storm.swath_area_sqmi || storm.affected_area_sq_miles || 10
        // Larger areas = lower zoom, smaller areas = higher zoom
        let zoom = 10
        if (areaSquareMiles > 100) zoom = 8
        else if (areaSquareMiles > 50) zoom = 9
        else if (areaSquareMiles > 20) zoom = 10
        else if (areaSquareMiles > 5) zoom = 11
        else zoom = 12

        mapInstanceRef.current.setView([lat, lon], zoom, { animate: true })
        console.log(`Zoomed to storm center [${lat}, ${lon}] at zoom ${zoom}`)
      }
    } catch (error) {
      console.error("Error zooming to storm:", error)
    }
  }, [])

  // Search for photos when none exist
  const searchPhotosMutation = useMutation({
    mutationFn: (eventId: number) => hailEventsApi.searchStormPhotos(eventId),
    onSuccess: () => {
      refetchPhotos()
    },
  })

  // Memoize derived arrays to prevent infinite re-renders
  const events = useMemo<HailEvent[]>(() => {
    const eventsList = eventsData?.data?.events || []
    if (eventsList.length > 0) {
      // Log unique dates in the returned events to check date filtering
      const uniqueDates = [...new Set(eventsList.map((e: HailEvent) => e.event_date))]
      console.log("API RETURNED events with dates:", uniqueDates, "count:", eventsList.length)
    }
    return eventsList
  }, [eventsData?.data?.events])
  const activeCells = useMemo<StormCell[]>(
    () => cellsData?.data?.active_cells || [],
    [cellsData?.data?.active_cells]
  )
  const radars = useMemo<RadarSite[]>(
    () => radarsData?.data?.radars || [],
    [radarsData?.data?.radars]
  )
  const leads = useMemo(() => {
    const allLeads = leadsData?.leads || []
    return allLeads.filter((l: any) => l.latitude && l.longitude)
  }, [leadsData?.leads])

  // Update stats based on map bounds
  const updateStats = useCallback(() => {
    if (!mapInstanceRef.current) return

    try {
      const bounds = mapInstanceRef.current.getBounds()
      if (!bounds) return

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
    } catch (error) {
      console.error("Error updating stats:", error)
    }
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

  // Listen for custom event from popup to open storm photos
  useEffect(() => {
    const handleOpenStormPhotos = (e: CustomEvent) => {
      const eventId = e.detail
      const event = events.find((ev) => ev.id === eventId)
      if (event) {
        setSelectedEvent(event)
        setEventDrawerOpen(true)
        // Also zoom to the storm
        zoomToStorm(event)
      }
    }

    window.addEventListener('openStormPhotos', handleOpenStormPhotos as EventListener)
    return () => {
      window.removeEventListener('openStormPhotos', handleOpenStormPhotos as EventListener)
    }
  }, [events, zoomToStorm])

  // Initialize map - runs when container is ready
  useEffect(() => {
    if (!mapContainerReady || !mapRef.current || mapInstanceRef.current) return

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

    mapInstanceRef.current = map
    setMapInitialized(true)
    console.log("Map fully initialized, swathLayerRef:", !!swathLayerRef.current)
    } catch (error) {
      console.error("Error initializing map:", error)
      return
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
        setMapInitialized(false)
      }
    }
  }, [mapContainerReady])

  // Resize map when calendar sidebar toggles
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    // Small delay to allow CSS transition to complete
    const timer = setTimeout(() => {
      map.invalidateSize()
    }, 350)

    return () => clearTimeout(timer)
  }, [calendarOpen])

  // Update stats when map moves - separate effect to avoid reinitializing map
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map) return

    const handler = () => updateStats()
    map.on("moveend", handler)

    return () => {
      map.off("moveend", handler)
    }
  }, [updateStats])

  // Update stats when data changes (separate from moveend to avoid loops)
  useEffect(() => {
    updateStats()
  }, [events.length, leads.length, activeCells.length])

  // Debug logging - only runs when data actually changes
  useEffect(() => {
    console.log("HailMap Data:", {
      selectedDate,
      eventsCount: events.length,
      activeCellsCount: activeCells.length,
      leadsCount: leads.length,
      radarsCount: radars.length,
    })
  }, [selectedDate, events.length, activeCells.length, leads.length, radars.length])

  // Render hail swaths from events data (only when date is selected)
  useEffect(() => {
    console.log("RENDER useEffect triggered:", {
      mapInitialized,
      selectedDate,
      swathLayerExists: !!swathLayerRef.current,
      layersSwaths: layers.swaths,
      eventsCount: events.length,
    })

    if (!swathLayerRef.current) {
      console.log("EARLY RETURN: swathLayerRef.current is null")
      return
    }

    // ALWAYS clear old layers first
    swathLayerRef.current.clearLayers()
    console.log("Cleared old swath layers")

    // If no date selected, don't render anything (keep map empty)
    if (!selectedDate) {
      console.log("NO DATE SELECTED - keeping map empty")
      return
    }

    if (!layers.swaths) {
      console.log("EARLY RETURN: layers.swaths is false")
      return
    }

    // Only render if we have events for the selected date
    if (events.length === 0) {
      console.log("EARLY RETURN: events.length is 0 for date", selectedDate)
      return
    }

    console.log("Processing", events.length, "events...")
    let addedCount = 0

    // Render events - use swath_polygon if available, otherwise fall back to circle
    events.forEach((event, index) => {
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
            <div style="padding: 8px 16px 12px; border-top: 1px solid #e5e7eb;">
              <button
                onclick="window.dispatchEvent(new CustomEvent('openStormPhotos', {detail: ${event.id}}))"
                style="width: 100%; padding: 8px 12px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 6px;"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                View Photos
              </button>
            </div>
          </div>
        `)

        swathLayerRef.current?.addLayer(polygon)
        addedCount++
        console.log(`Added polygon for event ${index}:`, event.event_name || event.id)
      } else {
        // Fall back to circle representation
        const lat = event.center_lat ?? event.latitude
        const lon = event.center_lon ?? event.longitude
        if (lat == null || lon == null) {
          console.log(`Skipping event ${index} - no coordinates:`, {
            id: event.id,
            center_lat: event.center_lat,
            center_lon: event.center_lon,
            latitude: event.latitude,
            longitude: event.longitude,
          })
          return
        }

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
            <div style="padding: 8px 16px 12px; border-top: 1px solid #e5e7eb;">
              <button
                onclick="window.dispatchEvent(new CustomEvent('openStormPhotos', {detail: ${event.id}}))"
                style="width: 100%; padding: 8px 12px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 6px;"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                View Photos
              </button>
            </div>
          </div>
        `)

        swathLayerRef.current?.addLayer(circle)
        addedCount++
        console.log(`Added circle for event ${index}:`, event.event_name || event.id, `at [${lat}, ${lon}]`)
      }
    })

    console.log(`RENDER COMPLETE: Added ${addedCount} of ${events.length} events to map`)
    updateStats()
  }, [events, layers.swaths, updateStats, mapInitialized, selectedDate])

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

  // ============================================================================
  // LIVE RADAR SYSTEM - LAYER RENDERING
  // ============================================================================

  // Render live radar tile layer from RainViewer
  const updateLiveRadarLayer = useCallback(() => {
    if (!mapInstanceRef.current || !showLiveRadar || radarFrames.length === 0 || !radarHost) return

    // Remove existing radar layer
    if (liveRadarLayerRef.current) {
      mapInstanceRef.current.removeLayer(liveRadarLayerRef.current)
    }

    const frame = radarFrames[currentFrame]
    if (!frame) return

    // RainViewer tile URL format:
    // {host}{path}/{size}/{z}/{x}/{y}/{colorScheme}/{smooth}_{snow}.png
    // colorScheme: 2 = original colors (good for seeing intensity)
    // smooth: 1 = smoothed, snow: 1 = show snow in blue
    const tileUrl = `${radarHost}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`

    liveRadarLayerRef.current = L.tileLayer(tileUrl, {
      opacity: liveRadarOpacity,
      zIndex: 100,
      attribution: '© RainViewer'
    }).addTo(mapInstanceRef.current)

  }, [showLiveRadar, currentFrame, radarFrames, radarHost, liveRadarOpacity])

  useEffect(() => {
    updateLiveRadarLayer()
  }, [updateLiveRadarLayer])

  // Render NWS alert polygons (Tornado/Severe Thunderstorm Warnings)
  const updateAlertPolygons = useCallback(() => {
    if (!mapInstanceRef.current) return

    // Initialize or clear layer
    if (alertPolygonLayerRef.current) {
      alertPolygonLayerRef.current.clearLayers()
    } else {
      alertPolygonLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current)
    }

    if (!showLiveRadar || !showAlertPolygons || !realtimeData?.alerts) return

    realtimeData.alerts.forEach((alert: any) => {
      if (!alert.geometry) return

      // Red for tornado warnings, yellow for severe thunderstorm
      const isTornado = alert.event?.toLowerCase().includes('tornado')
      const color = isTornado ? '#FF0000' : '#FFFF00'

      try {
        const polygon = L.geoJSON(alert.geometry, {
          style: {
            color: color,
            weight: 3,
            fillOpacity: 0.25,
            fillColor: color
          }
        })

        polygon.bindPopup(`
          <div style="min-width: 200px;">
            <div style="padding: 10px; background: ${isTornado ? '#fef2f2' : '#fefce8'}; border-bottom: 1px solid #e5e7eb;">
              <strong style="color: ${isTornado ? '#dc2626' : '#ca8a04'};">${alert.event || 'Alert'}</strong>
            </div>
            <div style="padding: 10px; font-size: 13px;">
              <p>${alert.headline || ''}</p>
              ${alert.hail_size_inches ? `<p><strong>Hail:</strong> ${alert.hail_size_inches}"</p>` : ''}
              ${alert.wind_mph ? `<p><strong>Wind:</strong> ${alert.wind_mph} mph</p>` : ''}
              <p style="color: #666; font-size: 11px; margin-top: 8px;">Expires: ${alert.expires ? new Date(alert.expires).toLocaleString() : 'N/A'}</p>
            </div>
          </div>
        `)

        alertPolygonLayerRef.current?.addLayer(polygon)
      } catch (e) {
        console.error('Error adding alert polygon:', e)
      }
    })
  }, [showLiveRadar, showAlertPolygons, realtimeData])

  useEffect(() => {
    updateAlertPolygons()
  }, [updateAlertPolygons])

  // Render hail report markers
  const updateHailReportMarkers = useCallback(() => {
    if (!mapInstanceRef.current) return

    if (hailReportLayerRef.current) {
      hailReportLayerRef.current.clearLayers()
    } else {
      hailReportLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current)
    }

    if (!showLiveRadar || !showHailReports || !realtimeData?.hail_reports) return

    realtimeData.hail_reports.forEach((report: any) => {
      if (!report.lat || !report.lon) return

      // Size the marker based on hail size
      const size = Math.max(8, (report.hail_size_inches || 1) * 8)

      const marker = L.circleMarker([report.lat, report.lon], {
        radius: size,
        color: '#00FF00',
        fillColor: '#00FF00',
        fillOpacity: 0.7,
        weight: 2
      })

      marker.bindPopup(`
        <div style="min-width: 180px;">
          <div style="padding: 10px; background: #f0fdf4; border-bottom: 1px solid #e5e7eb;">
            <strong style="color: #16a34a;">🧊 HAIL REPORT</strong>
          </div>
          <div style="padding: 10px; font-size: 13px;">
            <p><strong>Size:</strong> ${report.hail_size_inches || 'Unknown'}"</p>
            <p><strong>Location:</strong> ${report.city || ''}, ${report.state || ''}</p>
            <p><strong>Time:</strong> ${report.valid_time || ''}</p>
            <p style="color: #666; font-size: 11px;">Source: ${report.source || 'LSR'}</p>
          </div>
        </div>
      `)

      hailReportLayerRef.current?.addLayer(marker)
    })
  }, [showLiveRadar, showHailReports, realtimeData])

  useEffect(() => {
    updateHailReportMarkers()
  }, [updateHailReportMarkers])

  // Render tornado report markers
  const updateTornadoReportMarkers = useCallback(() => {
    if (!mapInstanceRef.current) return

    if (tornadoReportLayerRef.current) {
      tornadoReportLayerRef.current.clearLayers()
    } else {
      tornadoReportLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current)
    }

    if (!showLiveRadar || !showTornadoReports || !realtimeData?.tornado_reports) return

    realtimeData.tornado_reports.forEach((report: any) => {
      if (!report.lat || !report.lon) return

      const icon = L.divIcon({
        html: `
          <div style="width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#dc2626" stroke="#dc2626" stroke-width="2">
              <path d="M12 2L2 12h3v8h6v-6h2v6h6v-8h3L12 2z"/>
            </svg>
          </div>
        `,
        className: '',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      })

      const marker = L.marker([report.lat, report.lon], { icon })

      marker.bindPopup(`
        <div style="min-width: 180px;">
          <div style="padding: 10px; background: #fef2f2; border-bottom: 1px solid #e5e7eb;">
            <strong style="color: #dc2626;">🌪️ TORNADO REPORT</strong>
          </div>
          <div style="padding: 10px; font-size: 13px;">
            <p><strong>Location:</strong> ${report.city || ''}, ${report.state || ''}</p>
            <p><strong>Time:</strong> ${report.valid_time || ''}</p>
            ${report.remarks ? `<p><strong>Remarks:</strong> ${report.remarks}</p>` : ''}
            <p style="color: #666; font-size: 11px;">Source: ${report.source || 'LSR'}</p>
          </div>
        </div>
      `)

      tornadoReportLayerRef.current?.addLayer(marker)
    })
  }, [showLiveRadar, showTornadoReports, realtimeData])

  useEffect(() => {
    updateTornadoReportMarkers()
  }, [updateTornadoReportMarkers])

  // Render watch boxes (Tornado/Severe Thunderstorm Watches)
  const updateWatchBoxes = useCallback(() => {
    if (!mapInstanceRef.current) return

    if (watchBoxLayerRef.current) {
      watchBoxLayerRef.current.clearLayers()
    } else {
      watchBoxLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current)
    }

    if (!showLiveRadar || !showWatchBoxes || !realtimeData?.watches) return

    realtimeData.watches.forEach((watch: any) => {
      if (!watch.geometry) return

      const isTornado = watch.event?.toLowerCase().includes('tornado')
      const color = isTornado ? '#FF0000' : '#FFAA00'

      try {
        const polygon = L.geoJSON(watch.geometry, {
          style: {
            color: color,
            weight: 4,
            fillOpacity: 0.1,
            fillColor: color,
            dashArray: '10, 5'  // Dashed line for watches
          }
        })

        polygon.bindPopup(`
          <div style="min-width: 200px;">
            <div style="padding: 10px; background: ${isTornado ? '#fef2f2' : '#fff7ed'}; border-bottom: 1px solid #e5e7eb;">
              <strong style="color: ${isTornado ? '#dc2626' : '#ea580c'};">📦 ${watch.event || 'Watch'}</strong>
            </div>
            <div style="padding: 10px; font-size: 13px;">
              <p>${watch.areas || ''}</p>
              <p style="color: #666; font-size: 11px; margin-top: 8px;">Expires: ${watch.expires ? new Date(watch.expires).toLocaleString() : 'N/A'}</p>
            </div>
          </div>
        `)

        watchBoxLayerRef.current?.addLayer(polygon)
      } catch (e) {
        console.error('Error adding watch polygon:', e)
      }
    })
  }, [showLiveRadar, showWatchBoxes, realtimeData])

  useEffect(() => {
    updateWatchBoxes()
  }, [updateWatchBoxes])

  // Cleanup radar layers when disabled
  useEffect(() => {
    if (!showLiveRadar) {
      if (liveRadarLayerRef.current && mapInstanceRef.current) {
        mapInstanceRef.current.removeLayer(liveRadarLayerRef.current)
        liveRadarLayerRef.current = null
      }
      if (alertPolygonLayerRef.current) {
        alertPolygonLayerRef.current.clearLayers()
      }
      if (hailReportLayerRef.current) {
        hailReportLayerRef.current.clearLayers()
      }
      if (tornadoReportLayerRef.current) {
        tornadoReportLayerRef.current.clearLayers()
      }
      if (watchBoxLayerRef.current) {
        watchBoxLayerRef.current.clearLayers()
      }
    }
  }, [showLiveRadar])

  const handleRefresh = () => {
    refetchEvents()
    refetchCells()
    refetchLeads()
  }

  const toggleLayer = (layer: keyof LayerState) => {
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }))
  }

  // Handle calendar event selection - set date filter and zoom to storm
  // MUST be before any early returns to maintain hook order
  const handleCalendarEventSelect = useCallback((event: CalendarDayEvent) => {
    console.log("Calendar event selected:", event)

    // Set the date filter to load storms for this date
    if (event.event_date) {
      const date = new Date(event.event_date)
      if (!isNaN(date.getTime())) {
        setSelectedDate(date.toISOString().split('T')[0])
      }
    }

    // Immediately zoom to the calendar event's coordinates while full data loads
    if (mapInstanceRef.current && event.lat && event.lon) {
      // Calculate zoom based on area
      const areaSquareMiles = event.area_sqmi || 10
      let zoom = 10
      if (areaSquareMiles > 100) zoom = 8
      else if (areaSquareMiles > 50) zoom = 9
      else if (areaSquareMiles > 20) zoom = 10
      else if (areaSquareMiles > 5) zoom = 11
      else zoom = 12

      mapInstanceRef.current.setView([event.lat, event.lon], zoom, { animate: true })
      console.log(`Immediate zoom to calendar event [${event.lat}, ${event.lon}]`)
    }

    // Also set pending zoom ID to refine zoom after full data loads (with swath polygon)
    if (event.id) {
      setPendingZoomEventId(event.id)
    }
  }, [])

  // Effect to zoom to pending event after events data loads
  useEffect(() => {
    if (!pendingZoomEventId || events.length === 0) return

    // Find the event we need to zoom to
    const targetEvent = events.find(e => e.id === pendingZoomEventId)
    if (targetEvent) {
      console.log("Zooming to pending event:", targetEvent.event_name || targetEvent.id)
      // Small delay to ensure map layers are rendered
      setTimeout(() => {
        zoomToStorm(targetEvent)
      }, 300)
      // Clear the pending zoom
      setPendingZoomEventId(null)
    }
  }, [events, pendingZoomEventId, zoomToStorm])

  // Only wait for leads - events load after date selection
  if (leadsLoading) {
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
    <div className="flex flex-col h-[calc(100vh-80px)]">
      {/* Header Row */}
      <div className="flex items-center justify-between gap-4 mb-2">
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
          <Button variant="outline" size="icon" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Toolbar Row */}
      <div className="flex items-center gap-2 mb-2 p-2 bg-card rounded-lg border">
        {/* Live Radar Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant={showLiveRadar ? "default" : "outline"} size="sm" className="gap-2">
              <Radio className="h-4 w-4" />
              Live Radar
              <ChevronDown className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-80 p-4" align="start">
            <div className="flex items-center justify-between mb-3">
              <DropdownMenuLabel className="p-0 font-bold">Live Radar</DropdownMenuLabel>
              <Switch checked={showLiveRadar} onCheckedChange={setShowLiveRadar} />
            </div>

            {showLiveRadar && (
              <>
                {/* Animation Controls */}
                <div className="mb-4">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setCurrentFrame(prev => Math.max(0, prev - 1))}
                    >
                      <SkipBack className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant={isAnimating ? "destructive" : "default"}
                      onClick={() => setIsAnimating(!isAnimating)}
                    >
                      {isAnimating ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setCurrentFrame(prev => Math.min(radarFrames.length - 1, prev + 1))}
                    >
                      <SkipForward className="h-4 w-4" />
                    </Button>
                  </div>

                  <input
                    type="range"
                    min={0}
                    max={Math.max(0, radarFrames.length - 1)}
                    value={currentFrame}
                    onChange={(e) => {
                      setIsAnimating(false)
                      setCurrentFrame(parseInt(e.target.value))
                    }}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />

                  <div className="text-center text-xs text-muted-foreground mt-1">
                    {radarFrames[currentFrame] &&
                      new Date(radarFrames[currentFrame].time * 1000).toLocaleString()
                    }
                    {radarFrames.length > 0 && currentFrame >= (radarFrames.length - 6) &&
                      <span className="ml-2 text-blue-500 font-medium">(Forecast)</span>
                    }
                  </div>
                </div>

                {/* Speed & Opacity */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Speed</label>
                    <select
                      value={animationSpeed}
                      onChange={(e) => setAnimationSpeed(parseInt(e.target.value))}
                      className="w-full text-sm border rounded px-2 py-1.5 bg-background"
                    >
                      <option value={1000}>Slow</option>
                      <option value={500}>Normal</option>
                      <option value={250}>Fast</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">
                      Opacity: {Math.round(liveRadarOpacity * 100)}%
                    </label>
                    <input
                      type="range"
                      min={20}
                      max={100}
                      value={liveRadarOpacity * 100}
                      onChange={(e) => setLiveRadarOpacity(parseInt(e.target.value) / 100)}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    />
                  </div>
                </div>

                <DropdownMenuSeparator />

                {/* Weather Overlays */}
                <div className="pt-2">
                  <div className="text-xs font-semibold text-muted-foreground uppercase mb-2">Weather Overlays</div>
                  <div className="space-y-2">
                    <label className="flex items-center justify-between cursor-pointer">
                      <div className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={showAlertPolygons} onChange={(e) => setShowAlertPolygons(e.target.checked)} className="rounded" />
                        <AlertTriangle className="h-3 w-3 text-red-500" />
                        Warning Polygons
                      </div>
                      {realtimeData?.alerts?.length > 0 && <Badge variant="destructive" className="text-xs">{realtimeData.alerts.length}</Badge>}
                    </label>
                    <label className="flex items-center justify-between cursor-pointer">
                      <div className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={showHailReports} onChange={(e) => setShowHailReports(e.target.checked)} className="rounded" />
                        <CloudLightning className="h-3 w-3 text-green-500" />
                        Hail Reports
                      </div>
                      {realtimeData?.hail_reports?.length > 0 && <Badge className="bg-green-500 text-xs">{realtimeData.hail_reports.length}</Badge>}
                    </label>
                    <label className="flex items-center justify-between cursor-pointer">
                      <div className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={showTornadoReports} onChange={(e) => setShowTornadoReports(e.target.checked)} className="rounded" />
                        <Activity className="h-3 w-3 text-red-600" />
                        Tornado Reports
                      </div>
                      {realtimeData?.tornado_reports?.length > 0 && <Badge variant="destructive" className="text-xs">{realtimeData.tornado_reports.length}</Badge>}
                    </label>
                    <label className="flex items-center justify-between cursor-pointer">
                      <div className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={showWatchBoxes} onChange={(e) => setShowWatchBoxes(e.target.checked)} className="rounded" />
                        <AlertTriangle className="h-3 w-3 text-orange-500" />
                        Watch Boxes
                      </div>
                      {realtimeData?.watches?.length > 0 && <Badge className="bg-orange-500 text-xs">{realtimeData.watches.length}</Badge>}
                    </label>
                  </div>
                </div>

                <DropdownMenuSeparator className="my-2" />

                {/* Radar Legend */}
                <div className="text-xs">
                  <div className="font-semibold text-muted-foreground uppercase mb-1">Radar Intensity</div>
                  <div className="flex items-center gap-1">
                    <div className="flex-1 h-2 rounded" style={{ background: 'linear-gradient(to right, #00ff00, #ffff00, #ff8800, #ff0000, #ff00ff)' }}></div>
                    <span className="text-muted-foreground ml-1">Light → Extreme</span>
                  </div>
                </div>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Layers Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <Layers className="h-4 w-4" />
              Layers
              <ChevronDown className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="start">
            <DropdownMenuLabel>Map Layers</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuCheckboxItem checked={layers.swaths} onCheckedChange={() => toggleLayer("swaths")}>
              <CloudLightning className="h-4 w-4 mr-2 text-yellow-500" />
              Hail Swaths
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem checked={layers.activeCells} onCheckedChange={() => toggleLayer("activeCells")}>
              <Zap className="h-4 w-4 mr-2 text-orange-500" />
              Active Cells
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem checked={layers.forecasts} onCheckedChange={() => toggleLayer("forecasts")}>
              <Activity className="h-4 w-4 mr-2 text-purple-500" />
              Cell Forecasts
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem checked={layers.leads} onCheckedChange={() => toggleLayer("leads")}>
              <MapPin className="h-4 w-4 mr-2 text-blue-500" />
              Leads
            </DropdownMenuCheckboxItem>
            <DropdownMenuCheckboxItem checked={layers.radar} onCheckedChange={() => toggleLayer("radar")}>
              <Radio className="h-4 w-4 mr-2 text-blue-500" />
              Radar Coverage ({radars.length})
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="h-6 w-px bg-border mx-1" />

        {/* Sidebar Toggles */}
        <Button
          variant={territoryAlertsOpen ? "default" : "outline"}
          size="sm"
          onClick={() => {
            setTerritoryAlertsOpen(!territoryAlertsOpen)
            if (!territoryAlertsOpen) {
              setRadarReplayOpen(false)
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
            }
          }}
          className="gap-2"
        >
          <Play className="h-4 w-4" />
          Radar Replay
        </Button>
        <Button
          variant={calendarOpen ? "default" : "ghost"}
          size="sm"
          onClick={() => setCalendarOpen(!calendarOpen)}
          className="gap-2"
        >
          {calendarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
          <Calendar className="h-4 w-4" />
          Calendar
        </Button>
      </div>

      {/* Main Content Row */}
      <div className="flex gap-2 flex-1 min-h-0">
        {/* Collapsible Calendar Sidebar */}
        <div
          className={`transition-all duration-300 ease-in-out overflow-hidden ${calendarOpen ? 'w-80' : 'w-0'}`}
          style={{ minHeight: 0 }}
        >
          {calendarOpen && (
            <div className="h-full bg-card rounded-lg border overflow-auto">
              <StormCalendar
                onSelectEvent={handleCalendarEventSelect}
                onSelectDate={(date) => {
                  console.log("Date selected:", date)
                  setSelectedDate(date)
                }}
                className="h-full"
              />
            </div>
          )}
        </div>

        {/* Map Container */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 relative bg-card rounded-lg border overflow-hidden">
            <div
              ref={mapContainerRef}
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

            {/* Active Cells Alert - small indicator on map */}
            {activeCells.length > 0 && (
              <div className="absolute top-3 left-3 z-[1000] bg-orange-500 text-white rounded-lg shadow-lg px-3 py-1.5 flex items-center gap-2 text-sm">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-medium">{activeCells.length} Active Cells</span>
              </div>
            )}
          </div>

          {/* Stats Bar - Below Map */}
          <div className="mt-2 bg-card rounded-lg border p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <CloudLightning className="h-5 w-5 text-red-500" />
                  <div>
                    <span className="text-xl font-bold text-red-600">{stats.activeStorms}</span>
                    <span className="text-xs text-muted-foreground ml-1">Storms (7d)</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="text-xl font-bold text-orange-600">{stats.activeCells}</span>
                    <span className="text-xs text-muted-foreground ml-1">Active Cells</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-blue-500" />
                  <div>
                    <span className="text-xl font-bold text-blue-600">{stats.leadsInView}</span>
                    <span className="text-xs text-muted-foreground ml-1">Leads</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Flame className="h-5 w-5 text-orange-500" />
                  <div>
                    <span className="text-xl font-bold text-orange-600">{stats.hotLeads}</span>
                    <span className="text-xs text-muted-foreground ml-1">Hot Leads</span>
                  </div>
                </div>
              </div>

              {/* Compact Hail Size Legend */}
              {layers.swaths && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Hail Size:</span>
                  <div className="flex items-center gap-0.5">
                    {HAIL_SIZE_COLORS.map((level) => (
                      <div
                        key={level.label}
                        className="w-4 h-4 rounded-sm border cursor-help"
                        style={{ backgroundColor: level.fill, borderColor: level.border }}
                        title={level.label}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">(&lt;0.5" - 3"+)</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Territory Alerts Panel */}
        {territoryAlertsOpen && (
          <div className="w-80 flex-shrink-0 bg-card rounded-lg border overflow-auto">
            <TerritoryAlerts className="h-full" />
          </div>
        )}

        {/* Radar Replay Panel */}
        {radarReplayOpen && !territoryAlertsOpen && (
          <div className="w-80 flex-shrink-0 bg-card rounded-lg border overflow-auto">
            <RadarReplay className="h-full" />
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

      {/* Storm Photo Drawer */}
      <Sheet open={eventDrawerOpen} onOpenChange={setEventDrawerOpen}>
        <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
          {selectedEvent && (
            <>
              <SheetHeader className="pb-4 border-b">
                <div className="flex items-start justify-between">
                  <div>
                    <SheetTitle className="text-xl flex items-center gap-2">
                      <Camera className="h-5 w-5 text-blue-500" />
                      Storm Photos
                    </SheetTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      {selectedEvent.event_name || selectedEvent.city || "Unknown Location"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {selectedEvent.event_date} • {selectedEvent.max_hail_size || "N/A"}" hail
                    </p>
                  </div>
                </div>
              </SheetHeader>

              <div className="py-6 space-y-6">
                {/* Storm Info */}
                <div className="space-y-3">
                  <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Storm Details</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground">Max Hail Size</div>
                      <div className="font-bold text-lg">{selectedEvent.max_hail_size || "N/A"}"</div>
                    </div>
                    <div className="p-3 bg-muted rounded-lg">
                      <div className="text-xs text-muted-foreground">Area</div>
                      <div className="font-bold text-lg">{selectedEvent.swath_area_sqmi?.toFixed(1) || "N/A"} sq mi</div>
                    </div>
                  </div>
                </div>

                {/* Photos Section */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
                      Social Media Photos ({stormPhotos.length})
                    </h4>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => searchPhotosMutation.mutate(selectedEvent.id)}
                      disabled={searchPhotosMutation.isPending}
                    >
                      {searchPhotosMutation.isPending ? (
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4 mr-2" />
                      )}
                      Search for Photos
                    </Button>
                  </div>

                  {photosLoading ? (
                    <div className="space-y-3">
                      <Skeleton className="h-48 w-full" />
                      <Skeleton className="h-48 w-full" />
                    </div>
                  ) : stormPhotos.length === 0 ? (
                    <div className="text-center py-12 bg-muted rounded-lg">
                      <ImageIcon className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                      <p className="text-muted-foreground">No photos found for this storm</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Click "Search for Photos" to find social media posts
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-4">
                      {stormPhotos.map((photo) => (
                        <Card key={photo.id} className="overflow-hidden">
                          <div className="relative">
                            <img
                              src={photo.photo_url}
                              alt={photo.title || "Storm photo"}
                              className="w-full h-48 object-cover"
                              onError={(e) => {
                                (e.target as HTMLImageElement).src = "/placeholder-image.jpg"
                              }}
                            />
                            {photo.ai_detected_hail && (
                              <Badge className="absolute top-2 right-2 bg-green-500">
                                AI Verified Hail
                              </Badge>
                            )}
                          </div>
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate">{photo.title || "Untitled"}</p>
                                <p className="text-xs text-muted-foreground">
                                  {photo.source} • {photo.author || "Unknown"}
                                </p>
                              </div>
                              <a
                                href={photo.post_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-shrink-0"
                              >
                                <Button size="sm" variant="ghost">
                                  <ExternalLink className="h-4 w-4" />
                                </Button>
                              </a>
                            </div>
                            {photo.ai_analyzed && (
                              <div className="mt-3 p-2 bg-muted rounded text-xs">
                                <div className="flex justify-between">
                                  <span>AI Estimated Size:</span>
                                  <span className="font-medium">{photo.ai_estimated_size?.toFixed(2) || "N/A"}"</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>Confidence:</span>
                                  <span className="font-medium">{((photo.ai_confidence || 0) * 100).toFixed(0)}%</span>
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="space-y-3 pt-4 border-t">
                  <Button className="w-full" variant="outline" asChild>
                    <a
                      href={`https://www.google.com/maps?q=${selectedEvent.center_lat || selectedEvent.latitude},${selectedEvent.center_lon || selectedEvent.longitude}`}
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
