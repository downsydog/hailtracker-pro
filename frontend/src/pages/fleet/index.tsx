import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
// Card components imported but only some used
// import { CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  hailEventsApi,
  fleetLocationsApi,
  mainCrmLeadsApi,
  recentStormsApi,
  HailEvent,
  AffectedBusiness,
} from "@/api/fleet"
import { CalendarDayEvent } from "@/api/weather"
import { StormCalendar } from "@/components/app/storm-calendar"
import { EmailTemplateModal, CallScriptModal } from "@/components/fleet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import {
  CloudRain,
  Loader2,
  ExternalLink,
  Target,
  CheckCircle2,
  Building2,
  Car,
  DollarSign,
  ChevronDown,
  RefreshCw,
  AlertTriangle,
  Zap,
  Download,
  List,
  MapPin,
} from "lucide-react"

// ============================================================================
// STORM-FIRST FLEET INTELLIGENCE PAGE
// ============================================================================
// Simple 4-step workflow:
// 1. Select Storm → 2. See Swath → 3. Find Businesses → 4. Prospect Them

// Severity colors based on hail size
const getSeverityStyle = (size: number) => {
  if (size >= 2.0) return { bg: "bg-red-500", text: "text-red-700", border: "border-red-300", label: "SEVERE" }
  if (size >= 1.5) return { bg: "bg-orange-500", text: "text-orange-700", border: "border-orange-300", label: "SIGNIFICANT" }
  return { bg: "bg-yellow-500", text: "text-yellow-700", border: "border-yellow-300", label: "MODERATE" }
}

// Tier colors for businesses
const getTierColor = (tier: number) => {
  if (tier === 1) return "#ef4444" // Red - highest priority
  if (tier === 2) return "#f97316" // Orange
  return "#eab308" // Yellow
}

// Format date for display
const formatDate = (dateStr: string) => {
  return new Date(dateStr + "T12:00:00").toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export function FleetMapPage() {
  useQueryClient() // Keep hook call but don't store result

  // Map refs
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const swathLayerRef = useRef<L.LayerGroup | null>(null)
  const markersLayerRef = useRef<L.LayerGroup | null>(null)

  // ========== STATE ==========

  // Step 1: Storm Selection
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  // Step 2: Swath Data
  const [hailEvents, setHailEvents] = useState<HailEvent[]>([])
  const [loadingSwath, setLoadingSwath] = useState(false)

  // Step 3: Businesses
  const [businesses, setBusinesses] = useState<AffectedBusiness[]>([])
  const [loadingBusinesses, setLoadingBusinesses] = useState(false)
  const [scrapeStatus, setScrapeStatus] = useState<"idle" | "scraping" | "done">("idle")

  // Step 4: CRM Actions
  const [addingToCRM, setAddingToCRM] = useState(false)
  const [crmResult, setCrmResult] = useState<{ created: number; skipped: number } | null>(null)

  // UI State
  const [selectedBusiness, setSelectedBusiness] = useState<AffectedBusiness | null>(null)
  const [emailModalBusiness, setEmailModalBusiness] = useState<AffectedBusiness | null>(null)
  const [callModalBusiness, setCallModalBusiness] = useState<AffectedBusiness | null>(null)

  // Filters
  const [minVehicles, setMinVehicles] = useState(5)
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set())

  // Scan depth: controls how many tiles to search
  // With 0.5 mi tiles (0.25 sq mile each), OKC storm has ~700 tiles total
  // 200 = Quick (~800 businesses, ~50 sq mi coverage)
  // 500 = Full (~2,000 businesses, ~125 sq mi coverage)
  // 0 = Deep/All tiles (~3,500+ businesses, full swath coverage)
  const [scanDepth, setScanDepth] = useState<number>(500)

  // UI: Calendar vs Quick Picks toggle
  const [showQuickPicks, setShowQuickPicks] = useState(false)

  // Swath selection state
  const [selectedSwathIds, setSelectedSwathIds] = useState<Set<number>>(new Set())
  const [showSwathSelector, setShowSwathSelector] = useState(false)

  // ========== DATA LOADING ==========

  // Fetch recent significant storms
  const { data: stormsData, isLoading: loadingStorms, refetch: refetchStorms } = useQuery({
    queryKey: ["recent-significant-storms"],
    queryFn: () => recentStormsApi.getRecentStorms({ days: 90, min_size: 1.0, limit: 30 }),
    staleTime: 60000, // 1 minute
  })
  const recentStorms = stormsData?.storms || []

  // Load swath when date selected
  useEffect(() => {
    console.log(`[Fleet] useEffect triggered - selectedDate: ${selectedDate}`)
    if (selectedDate) {
      console.log(`[Fleet] Calling loadSwathForDate for: ${selectedDate}`)
      loadSwathForDate(selectedDate)
    }
  }, [selectedDate])

  const loadSwathForDate = async (date: string) => {
    setLoadingSwath(true)
    setHailEvents([])
    setBusinesses([])
    setCrmResult(null)
    setScrapeStatus("idle")

    try {
      console.log(`[Fleet] ========== Loading swaths for date: ${date} ==========`)
      const res = await hailEventsApi.getEventsByDate({ date })
      console.log(`[Fleet] Raw API response:`, res)

      const events = res.events || []
      console.log(`[Fleet] Events array:`, events)

      // Debug logging
      const eventsWithSwath = events.filter(e => e.swath_polygon)
      const eventsWithCenter = events.filter(e => e.center_lat && e.center_lon)
      console.log(`[Fleet] Event stats:`)
      console.log(`  - Total events: ${events.length}`)
      console.log(`  - With swath_polygon: ${eventsWithSwath.length}`)
      console.log(`  - With center coordinates: ${eventsWithCenter.length}`)
      console.log(`  - Cities: ${[...new Set(events.map(e => e.city).filter(Boolean))].join(', ')}`)

      if (events.length > 0) {
        console.log(`[Fleet] First event sample:`, events[0])
        console.log(`[Fleet] First event keys:`, Object.keys(events[0]))
      }

      if (eventsWithSwath.length > 0) {
        console.log(`[Fleet] First event with swath:`, eventsWithSwath[0])
        console.log(`[Fleet] Swath type:`, typeof eventsWithSwath[0].swath_polygon)
      }

      // Check map readiness
      console.log(`[Fleet] Map ready check:`)
      console.log(`  - mapInstanceRef.current:`, !!mapInstanceRef.current)
      console.log(`  - swathLayerRef.current:`, !!swathLayerRef.current)

      setHailEvents(events)
      // Note: renderSwaths is called automatically via useEffect when hailEvents changes
    } catch (error) {
      console.error("[Fleet] Failed to load swath:", error)
      if (error instanceof Error) {
        console.error("[Fleet] Error message:", error.message)
        console.error("[Fleet] Error stack:", error.stack)
      }
    } finally {
      setLoadingSwath(false)
    }
  }

  // Render hail swaths on map with numbering and selection highlighting
  const renderSwaths = useCallback((events: HailEvent[], selectedIds: Set<number>, bizCounts: Record<number, number>) => {
    console.log(`[Fleet] renderSwaths called with ${events.length} events`)

    if (!mapInstanceRef.current || !swathLayerRef.current) {
      console.warn("[Fleet] Map not ready for rendering")
      return
    }

    swathLayerRef.current.clearLayers()
    markersLayerRef.current?.clearLayers()

    if (events.length === 0) {
      console.log("[Fleet] No events to render")
      return
    }

    // Sort by hail size (largest first) to assign swath numbers
    const sortedEvents = [...events]
      .filter(e => e.swath_polygon)
      .sort((a, b) => b.max_hail_size - a.max_hail_size)

    // Create swath number map
    const swathNumberMap = new Map<number, number>()
    sortedEvents.forEach((e, i) => swathNumberMap.set(e.id, i + 1))

    const bounds: L.LatLngBounds[] = []
    let swathCount = 0
    let markerCount = 0
    const totalSwaths = sortedEvents.length

    events.forEach((event) => {
      // Add swath polygon if available
      if (event.swath_polygon) {
        try {
          const geojson = typeof event.swath_polygon === "string"
            ? JSON.parse(event.swath_polygon)
            : event.swath_polygon

          const swathNum = swathNumberMap.get(event.id) || 0
          const isSelected = selectedIds.has(event.id)
          const bizCount = bizCounts[event.id] || 0

          // Color based on hail size
          const baseColor = event.max_hail_size >= 2 ? "#ef4444" : event.max_hail_size >= 1.5 ? "#f97316" : "#eab308"

          const layer = L.geoJSON(geojson, {
            style: {
              fillColor: baseColor,
              fillOpacity: isSelected ? 0.45 : 0.2,
              color: isSelected ? baseColor : "#666",
              weight: isSelected ? 3 : 1,
              opacity: isSelected ? 1.0 : 0.5,
              dashArray: isSelected ? undefined : "5, 5",
            },
          })

          // Enhanced popup with swath number, NOAA ID, business count
          const severity = event.max_hail_size >= 2 ? "SEVERE" : event.max_hail_size >= 1.5 ? "SIGNIFICANT" : "MODERATE"
          const severityColor = event.max_hail_size >= 2 ? "#ef4444" : event.max_hail_size >= 1.5 ? "#f97316" : "#eab308"

          layer.bindPopup(`
            <div style="min-width: 220px;">
              <div style="background: ${severityColor}; color: white; padding: 8px 12px; margin: -10px -10px 10px -10px; border-radius: 4px 4px 0 0;">
                <div style="font-size: 18px; font-weight: bold;">Swath ${swathNum} of ${totalSwaths}</div>
                <div style="font-size: 12px; opacity: 0.9;">${severity}</div>
              </div>
              <div style="padding: 4px;">
                <div style="margin-bottom: 8px;">
                  <div style="font-weight: bold; font-size: 14px;">${event.city || "Unknown location"}</div>
                  <div style="color: #666; font-size: 12px;">${event.event_name || ""}</div>
                </div>
                <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                  <tr>
                    <td style="padding: 4px 0; color: #666;">NOAA ID:</td>
                    <td style="padding: 4px 0; font-weight: 500;">${event.id}</td>
                  </tr>
                  <tr>
                    <td style="padding: 4px 0; color: #666;">Max Hail:</td>
                    <td style="padding: 4px 0; font-weight: bold; color: ${severityColor};">${event.max_hail_size}" diameter</td>
                  </tr>
                  ${event.area_sq_miles ? `
                  <tr>
                    <td style="padding: 4px 0; color: #666;">Area:</td>
                    <td style="padding: 4px 0;">${event.area_sq_miles.toFixed(1)} sq mi</td>
                  </tr>
                  ` : ""}
                  <tr>
                    <td style="padding: 4px 0; color: #666;">Date:</td>
                    <td style="padding: 4px 0;">${event.event_date}</td>
                  </tr>
                  <tr style="border-top: 1px solid #eee;">
                    <td style="padding: 8px 0 4px; color: #666;">Businesses:</td>
                    <td style="padding: 8px 0 4px; font-weight: bold; color: #2563eb;">${bizCount > 0 ? bizCount : "—"}</td>
                  </tr>
                </table>
              </div>
            </div>
          `)

          swathLayerRef.current?.addLayer(layer)
          bounds.push(layer.getBounds())
          swathCount++
        } catch (e) {
          console.error(`[Fleet] Error rendering swath for event ${event.id}:`, e)
        }
      }

      // Add center marker if no swath polygon
      if (!event.swath_polygon && event.center_lat && event.center_lon) {
        const marker = L.circleMarker([event.center_lat, event.center_lon], {
          radius: Math.max(10, Math.min(25, event.max_hail_size * 8)),
          fillColor: event.max_hail_size >= 2 ? "#ef4444" : event.max_hail_size >= 1.5 ? "#f97316" : "#eab308",
          fillOpacity: 0.6,
          color: "#fff",
          weight: 2,
        })

        marker.bindPopup(`
          <div class="p-2">
            <div class="font-bold">🌨️ ${event.event_name || "Hail Event"}</div>
            <div class="text-sm">${event.city || "Unknown"}</div>
            <div class="text-sm mt-1"><strong>${event.max_hail_size}"</strong> hail</div>
          </div>
        `)

        swathLayerRef.current?.addLayer(marker)
        bounds.push(L.latLngBounds([event.center_lat, event.center_lon], [event.center_lat, event.center_lon]))
        markerCount++
      }
    })

    console.log(`[Fleet] Rendered ${swathCount} swaths and ${markerCount} markers`)

    // Fit map to all swaths
    if (bounds.length > 0) {
      const combinedBounds = bounds.reduce((acc, b) => acc.extend(b), bounds[0])
      mapInstanceRef.current?.fitBounds(combinedBounds, { padding: [50, 50], maxZoom: 10 })
      console.log(`[Fleet] Map fitted to bounds covering ${bounds.length} items`)
    }
  }, [])

  // ========== BUSINESS DISCOVERY ==========

  const findBusinessesInSwath = async () => {
    if (!selectedDate || hailEvents.length === 0) return

    setLoadingBusinesses(true)
    setScrapeStatus("scraping")

    try {
      // Get visible event IDs from map viewport
      let visibleEventIds: number[] = []

      if (mapInstanceRef.current) {
        const bounds = mapInstanceRef.current.getBounds()
        const sw = bounds.getSouthWest()
        const ne = bounds.getNorthEast()

        console.log(`[Fleet] Map viewport: SW(${sw.lat.toFixed(4)}, ${sw.lng.toFixed(4)}) to NE(${ne.lat.toFixed(4)}, ${ne.lng.toFixed(4)})`)

        // Filter events to only those visible in the current viewport
        const visibleEvents = hailEvents.filter((event) => {
          if (!event.center_lat || !event.center_lon) return false
          return (
            event.center_lat >= sw.lat &&
            event.center_lat <= ne.lat &&
            event.center_lon >= sw.lng &&
            event.center_lon <= ne.lng
          )
        })

        visibleEventIds = visibleEvents.map((e) => e.id)
        console.log(`[Fleet] Visible events in viewport: ${visibleEventIds.length} of ${hailEvents.length} total`)
      } else {
        // Fallback: use all events
        visibleEventIds = hailEvents.map((e) => e.id)
      }

      if (visibleEventIds.length === 0) {
        console.log("[Fleet] No visible events - zooming to all events")
        visibleEventIds = hailEvents.map((e) => e.id)
      }

      console.log(`[Fleet] Calling tile-based discovery for ${visibleEventIds.length} events`)

      // Use tile-based discovery for complete swath coverage
      // All 6 APIs for maximum business coverage
      // tile_size_miles is LINEAR (0.5 mi = 0.25 sq mile tiles - Kyle's proven config)
      const result = await fleetLocationsApi.tileDiscover({
        event_ids: visibleEventIds,
        tile_size_miles: 0.5,   // 0.5 mi linear = 0.25 sq mile tiles (Kyle's proven config)
        sources: ['yelp', 'foursquare', 'here', 'tomtom', 'google', 'osm'],  // All 6 APIs
        force_refresh: false,   // Use tile cache if available
        max_tiles: scanDepth,   // User-selected scan depth
      })

      if (result.success) {
        // Filter by minimum vehicles
        const vehicleFilteredBusinesses = result.businesses.filter(
          (biz) => biz.estimated_vehicles >= minVehicles
        )

        setBusinesses(vehicleFilteredBusinesses)
        // Note: Map markers will be updated by useEffect when filteredBusinesses changes
        setScrapeStatus("done")

        console.log(`[Fleet] Tile discovery complete:`)
        console.log(`  - Tiles searched: ${result.tile_stats?.count || 0}`)
        console.log(`  - Tile size: ${result.tile_stats?.tile_size_miles || 0.5} miles`)
        console.log(`  - Area covered: ${result.tile_stats?.estimated_area_sq_miles?.toFixed(1) || 0} sq miles`)
        console.log(`  - By source:`, result.stats.by_source)
        console.log(`  - Total found: ${result.stats.total_found}`)
        console.log(`  - Duplicates removed: ${result.stats.duplicates_removed}`)
        console.log(`  - Tiles from cache: ${result.stats.tiles_from_cache || 0}`)
        console.log(`  - After min vehicles filter: ${vehicleFilteredBusinesses.length}`)
        console.log(`  - Total vehicles: ${result.stats.total_vehicles}`)
        console.log(`  - By category:`, result.stats.by_category)
      } else {
        console.error("[Fleet] Tile discovery returned failure")
        setScrapeStatus("idle")
      }
    } catch (error) {
      console.error("[Fleet] Tile discovery failed:", error)
      setScrapeStatus("idle")
    } finally {
      setLoadingBusinesses(false)
    }
  }

  // Render business markers on map with swath info
  const renderBusinessMarkers = useCallback((
    businessList: AffectedBusiness[],
    swaths: Array<HailEvent & { swathNumber: number }>
  ) => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return

    markersLayerRef.current.clearLayers()

    // Helper to find closest swath for a business
    const getSwathForBusiness = (biz: AffectedBusiness) => {
      if (!biz.latitude || !biz.longitude || swaths.length === 0) return null
      let closestSwath = swaths[0]
      let minDist = Infinity
      swaths.forEach(swath => {
        if (swath.center_lat && swath.center_lon) {
          const dist = Math.sqrt(
            Math.pow(biz.latitude - swath.center_lat, 2) +
            Math.pow(biz.longitude - swath.center_lon, 2)
          )
          if (dist < minDist) {
            minDist = dist
            closestSwath = swath
          }
        }
      })
      return closestSwath
    }

    businessList.forEach((biz) => {
      if (!biz.latitude || !biz.longitude) return

      const color = getTierColor(biz.tier)
      const swath = getSwathForBusiness(biz)

      const icon = L.divIcon({
        html: `
          <div style="
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: ${color};
            border: 3px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: bold;
            color: white;
            animation: pulse 1.5s ease-in-out infinite;
          ">
            ${biz.tier}
          </div>
          <style>
            @keyframes pulse {
              0%, 100% { transform: scale(1); }
              50% { transform: scale(1.1); }
            }
          </style>
        `,
        className: "",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      })

      const marker = L.marker([biz.latitude, biz.longitude], { icon })

      // Build swath info for popup
      const swathInfo = swath ? `
        <div style="font-size: 11px; color: #666; margin-bottom: 4px;">
          Swath ${swath.swathNumber} of ${swaths.length} · ${swath.max_hail_size}" hail · ${swath.city || 'Unknown'}
        </div>
      ` : ''

      const severityColor = swath && swath.max_hail_size >= 2 ? "#ef4444" : swath && swath.max_hail_size >= 1.5 ? "#f97316" : "#eab308"

      marker.bindPopup(`
        <div style="min-width: 220px;">
          <div style="font-weight: bold; font-size: 14px; padding: 8px; background: ${severityColor}; color: white; border-bottom: 1px solid ${severityColor};">
            ⚠️ HAIL AFFECTED
          </div>
          <div style="padding: 12px;">
            ${swathInfo}
            <div style="font-weight: bold; font-size: 14px;">${biz.name}</div>
            <div style="color: #6b7280; font-size: 12px; margin-top: 4px;">${biz.address || ""}</div>
            <div style="color: #6b7280; font-size: 12px;">${biz.city}, ${biz.state}</div>
            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb;">
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #6b7280;">Category:</span>
                <span style="font-weight: 500;">${biz.category || 'Other'}</span>
              </div>
              <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color: #6b7280;">Vehicles:</span>
                <span style="font-weight: bold; color: #2563eb;">~${biz.estimated_vehicles}</span>
              </div>
              <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color: #6b7280;">Potential:</span>
                <span style="font-weight: bold; color: #16a34a;">$${((biz.estimated_vehicles * 500) / 1000).toFixed(0)}K</span>
              </div>
              ${biz.phone ? `
              <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color: #6b7280;">Phone:</span>
                <a href="tel:${biz.phone}" style="color: #2563eb;">${biz.phone}</a>
              </div>
              ` : ''}
            </div>
          </div>
        </div>
      `)

      marker.on("click", () => setSelectedBusiness(biz))
      markersLayerRef.current?.addLayer(marker)
    })
  }, [])

  // ========== CRM ACTIONS ==========

  const addAllToCRM = async () => {
    if (filteredBusinesses.length === 0 || !selectedDate) return

    const confirmed = confirm(
      `Add ${filteredBusinesses.length} filtered businesses to CRM as HOT leads?\n\n` +
        `These will appear in your main Leads list ready to call.`
    )

    if (!confirmed) return

    setAddingToCRM(true)

    try {
      const maxHailSize = hailEvents.length > 0 ? Math.max(...hailEvents.map((e) => e.max_hail_size)) : 1.0

      const result = await mainCrmLeadsApi.bulkAddFromHailSwath({
        businesses: filteredBusinesses.map((b) => ({
          name: b.name,
          address: b.address,
          city: b.city,
          state: b.state,
          phone: b.phone,
          category: b.category,
          estimated_vehicles: b.estimated_vehicles,
          tier: b.tier,
          latitude: b.latitude,
          longitude: b.longitude,
        })),
        hail_date: selectedDate,
        hail_size: maxHailSize,
      })

      setCrmResult({ created: result.created, skipped: result.skipped })
    } catch (error) {
      console.error("Failed to add to CRM:", error)
      alert("Failed to add leads. Check console for details.")
    } finally {
      setAddingToCRM(false)
    }
  }

  const addSingleToCRM = async (business: AffectedBusiness) => {
    if (!selectedDate) return

    try {
      const maxHailSize = hailEvents.length > 0 ? Math.max(...hailEvents.map((e) => e.max_hail_size)) : 1.0

      await mainCrmLeadsApi.addBusinessToLeads({
        name: business.name,
        address: business.address,
        city: business.city,
        state: business.state,
        phone: business.phone,
        category: business.category,
        estimated_vehicles: business.estimated_vehicles,
        tier: business.tier,
        latitude: business.latitude,
        longitude: business.longitude,
        hail_affected: true,
        hail_date: selectedDate,
        hail_size: maxHailSize,
      })

      // Mark as added in local state
      setBusinesses((prev) => prev.map((b) => (b.id === business.id ? { ...b, added_to_crm: true } as any : b)))
    } catch (error) {
      console.error("Failed to add to CRM:", error)
    }
  }

  // ========== CALENDAR EVENT HANDLER ==========

  const handleCalendarEventSelect = useCallback((event: CalendarDayEvent) => {
    console.log("[Fleet] handleCalendarEventSelect called with:", event)
    // When user clicks on an event in the calendar, set the date
    if (event.event_date) {
      const date = new Date(event.event_date)
      console.log("[Fleet] Parsed date:", date, "isValid:", !isNaN(date.getTime()))
      if (!isNaN(date.getTime())) {
        const dateStr = date.toISOString().split("T")[0]
        console.log("[Fleet] Setting selectedDate to:", dateStr)
        setSelectedDate(dateStr)
      }
    } else {
      console.warn("[Fleet] No event_date in event:", event)
    }
  }, [])

  const handleCalendarDateSelect = useCallback((date: string) => {
    console.log("[Fleet] handleCalendarDateSelect called with:", date)
    // When user clicks on a date in the calendar
    setSelectedDate(date)
  }, [])

  // ========== CATEGORY FILTERING ==========

  // Initialize selected categories when businesses load
  useEffect(() => {
    if (businesses.length > 0) {
      const allCategories = new Set(businesses.map(b => b.category))
      setSelectedCategories(allCategories)
    }
  }, [businesses])

  // Get category counts from all businesses
  const categoryCounts = useMemo(() => {
    return businesses.reduce((acc, b) => {
      const cat = b.category || 'other'
      acc[cat] = (acc[cat] || 0) + 1
      return acc
    }, {} as Record<string, number>)
  }, [businesses])

  // Filter businesses by selected categories
  const filteredBusinesses = useMemo(() => {
    if (selectedCategories.size === 0) return []
    return businesses.filter(b => selectedCategories.has(b.category || 'other'))
  }, [businesses, selectedCategories])

  // Category filter helpers
  const toggleCategory = useCallback((category: string) => {
    setSelectedCategories(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }, [])

  const selectAllCategories = useCallback(() => {
    setSelectedCategories(new Set(Object.keys(categoryCounts)))
  }, [categoryCounts])

  const clearAllCategories = useCallback(() => {
    setSelectedCategories(new Set())
  }, [])

  const formatCategoryName = (category: string) => {
    return category
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase())
  }

  // ========== STATS ==========

  const stats = useMemo(() => {
    const totalVehicles = filteredBusinesses.reduce((sum, b) => sum + (b.estimated_vehicles || 0), 0)
    return {
      businesses: filteredBusinesses.length,
      totalBusinesses: businesses.length,
      vehicles: totalVehicles,
      value: totalVehicles * 500,
    }
  }, [filteredBusinesses, businesses])

  // ========== NUMBERED SWATHS (sorted by hail size) ==========

  // Create numbered swaths sorted by max_hail_size (largest first)
  const numberedSwaths = useMemo(() => {
    return [...hailEvents]
      .filter(e => e.swath_polygon)
      .sort((a, b) => b.max_hail_size - a.max_hail_size)
      .map((event, index) => ({
        ...event,
        swathNumber: index + 1,
      }))
  }, [hailEvents])

  // Count businesses per swath (based on location inside polygon)
  const businessesBySwath = useMemo(() => {
    const counts: Record<number, number> = {}
    numberedSwaths.forEach(s => { counts[s.id] = 0 })

    // For now, distribute businesses evenly or by proximity
    // In a real implementation, this would use point-in-polygon
    if (businesses.length > 0 && numberedSwaths.length > 0) {
      businesses.forEach(biz => {
        // Find closest swath center for this business
        let closestSwathId = numberedSwaths[0]?.id
        let minDist = Infinity

        numberedSwaths.forEach(swath => {
          if (biz.latitude && biz.longitude && swath.center_lat && swath.center_lon) {
            const dist = Math.sqrt(
              Math.pow(biz.latitude - swath.center_lat, 2) +
              Math.pow(biz.longitude - swath.center_lon, 2)
            )
            if (dist < minDist) {
              minDist = dist
              closestSwathId = swath.id
            }
          }
        })

        if (closestSwathId !== undefined) {
          counts[closestSwathId] = (counts[closestSwathId] || 0) + 1
        }
      })
    }

    return counts
  }, [businesses, numberedSwaths])

  // Re-render swaths when hailEvents, selection, or business counts change
  useEffect(() => {
    console.log(`[Fleet] hailEvents useEffect triggered, count: ${hailEvents.length}`)
    if (hailEvents.length > 0 && mapInstanceRef.current && swathLayerRef.current) {
      console.log(`[Fleet] Re-rendering swaths via useEffect`)
      renderSwaths(hailEvents, selectedSwathIds, businessesBySwath)
    }
  }, [hailEvents, selectedSwathIds, businessesBySwath, renderSwaths])

  // Select all swaths when hailEvents loads
  useEffect(() => {
    if (hailEvents.length > 0) {
      setSelectedSwathIds(new Set(hailEvents.filter(e => e.swath_polygon).map(e => e.id)))
    }
  }, [hailEvents])

  // Swath selection helpers
  const toggleSwathSelection = useCallback((eventId: number) => {
    setSelectedSwathIds(prev => {
      const next = new Set(prev)
      if (next.has(eventId)) {
        next.delete(eventId)
      } else {
        next.add(eventId)
      }
      return next
    })
  }, [])

  const selectAllSwaths = useCallback(() => {
    setSelectedSwathIds(new Set(numberedSwaths.map(s => s.id)))
  }, [numberedSwaths])

  const clearAllSwaths = useCallback(() => {
    setSelectedSwathIds(new Set())
  }, [])

  // Filter businesses by selected swaths
  const businessesInSelectedSwaths = useMemo(() => {
    if (selectedSwathIds.size === 0) return []
    if (selectedSwathIds.size === numberedSwaths.length) return filteredBusinesses

    // Filter businesses to only those in selected swaths
    return filteredBusinesses.filter(biz => {
      // Find which swath this business belongs to
      let closestSwathId: number | undefined
      let minDist = Infinity

      numberedSwaths.forEach(swath => {
        if (biz.latitude && biz.longitude && swath.center_lat && swath.center_lon) {
          const dist = Math.sqrt(
            Math.pow(biz.latitude - swath.center_lat, 2) +
            Math.pow(biz.longitude - swath.center_lon, 2)
          )
          if (dist < minDist) {
            minDist = dist
            closestSwathId = swath.id
          }
        }
      })

      return closestSwathId !== undefined && selectedSwathIds.has(closestSwathId)
    })
  }, [filteredBusinesses, selectedSwathIds, numberedSwaths])

  // ========== CSV EXPORT ==========

  const exportToCSV = useCallback(() => {
    if (businessesInSelectedSwaths.length === 0) return

    // Create CSV header
    const headers = [
      'Swath #',
      'Name',
      'Address',
      'City',
      'State',
      'Zip',
      'Phone',
      'Email',
      'Website',
      'Category',
      'Est. Vehicles',
      'Tier',
    ]

    // Create rows
    const rows = businessesInSelectedSwaths.map(biz => {
      // Find swath number for this business
      let swathNum = ''
      let minDist = Infinity
      numberedSwaths.forEach(swath => {
        if (biz.latitude && biz.longitude && swath.center_lat && swath.center_lon) {
          const dist = Math.sqrt(
            Math.pow(biz.latitude - swath.center_lat, 2) +
            Math.pow(biz.longitude - swath.center_lon, 2)
          )
          if (dist < minDist) {
            minDist = dist
            swathNum = String(swath.swathNumber)
          }
        }
      })

      return [
        swathNum,
        biz.name || '',
        biz.address || '',
        biz.city || '',
        biz.state || '',
        biz.zip || '',
        biz.phone || '',
        (biz as any).email || '',
        biz.website || '',
        biz.category || '',
        String(biz.estimated_vehicles || ''),
        String(biz.tier || ''),
      ]
    })

    // Build CSV content
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    // Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `fleet-leads-${selectedDate || 'export'}-swaths-${selectedSwathIds.size}.csv`
    link.click()
  }, [businessesInSelectedSwaths, numberedSwaths, selectedDate, selectedSwathIds.size])

  // ========== MAP INITIALIZATION ==========

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [35.4676, -97.5164], // Oklahoma City default
      zoom: 6,
      zoomControl: true,
    })

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map)

    swathLayerRef.current = L.layerGroup().addTo(map)
    markersLayerRef.current = L.layerGroup().addTo(map)

    setTimeout(() => map.invalidateSize(), 100)

    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Update map markers when filtered businesses change
  useEffect(() => {
    if (filteredBusinesses.length > 0) {
      renderBusinessMarkers(filteredBusinesses, numberedSwaths)
    }
  }, [filteredBusinesses, numberedSwaths, renderBusinessMarkers])

  // ========== RENDER ==========

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="bg-white dark:bg-gray-900 border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Target className="h-6 w-6 text-red-500" />
              Fleet Intelligence
            </h1>
            <p className="text-muted-foreground text-sm">
              Find hail-affected businesses and add them to your CRM
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetchStorms()}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loadingStorms ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* ========== LEFT SIDEBAR ========== */}
        <div className="w-96 bg-white dark:bg-gray-900 border-r flex flex-col">
          {/* Scrollable sidebar content */}
          <div className="flex-1 overflow-y-auto">
          {/* STEP 1: Storm Selection with Calendar */}
          <div className="border-b">
            <div className="p-4 pb-2">
              <h2 className="font-bold text-lg mb-2 flex items-center gap-2">
                <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">
                  1
                </span>
                Select a Storm
              </h2>
              {selectedDate && (
                <div className="text-sm text-blue-600 dark:text-blue-400 mb-2">
                  Selected: {formatDate(selectedDate)}
                </div>
              )}
            </div>

            {/* Storm Calendar - main date picker */}
            <div className="px-2 max-h-80 overflow-y-auto">
              <StormCalendar
                onSelectEvent={handleCalendarEventSelect}
                onSelectDate={handleCalendarDateSelect}
                className="border-0 shadow-none"
              />
            </div>

            {/* Quick Picks for Recent Significant Storms */}
            <div className="border-t">
              <button
                onClick={() => setShowQuickPicks(!showQuickPicks)}
                className="w-full p-3 flex items-center justify-between text-sm font-medium text-muted-foreground hover:bg-muted/50"
              >
                <span className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-orange-500" />
                  Quick Picks: Recent 1"+ Storms ({recentStorms.length})
                </span>
                <ChevronDown className={`h-4 w-4 transition-transform ${showQuickPicks ? "rotate-180" : ""}`} />
              </button>

              {showQuickPicks && (
                <div className="max-h-48 overflow-y-auto border-t">
                  {loadingStorms ? (
                    <div className="text-center py-4 text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin mx-auto" />
                    </div>
                  ) : recentStorms.length === 0 ? (
                    <div className="text-center py-4 text-muted-foreground text-sm">
                      No 1"+ storms in last 90 days
                    </div>
                  ) : (
                    <div className="divide-y">
                      {recentStorms.slice(0, 10).map((storm) => {
                        const severity = getSeverityStyle(storm.max_hail_size)
                        const isSelected = selectedDate === storm.date

                        return (
                          <button
                            key={storm.date}
                            onClick={() => setSelectedDate(storm.date)}
                            className={`
                              w-full p-2 text-left text-sm transition-all flex items-center justify-between
                              ${isSelected ? "bg-blue-50 dark:bg-blue-900/30" : "hover:bg-gray-50 dark:hover:bg-gray-800"}
                            `}
                          >
                            <div className="flex-1 min-w-0">
                              <div className="font-medium truncate">
                                {formatDate(storm.date)}
                              </div>
                              <div className="text-xs text-muted-foreground truncate">
                                {storm.major_cities?.slice(0, 2).join(", ")}
                              </div>
                            </div>
                            <div className="flex items-center gap-2 ml-2">
                              <span className={`font-bold ${severity.text}`}>{storm.max_hail_size}"</span>
                              <Badge className={`${severity.bg} text-white text-xs`}>{severity.label}</Badge>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* STEP 2: Storm Details */}
          {selectedDate && (
            <div className="p-4 border-b">
              <h2 className="font-bold text-lg mb-3 flex items-center gap-2">
                <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">
                  2
                </span>
                Storm Details
              </h2>

              {loadingSwath ? (
                <div className="text-center py-4 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                  Loading swath data...
                </div>
              ) : hailEvents.length === 0 ? (
                <div className="text-muted-foreground text-sm">No swath data for this date</div>
              ) : (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 space-y-2">
                  <div className="flex items-center gap-2 text-red-700 dark:text-red-300 font-bold text-lg">
                    <CloudRain className="h-5 w-5" />
                    {hailEvents.length} Hail Events
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-white dark:bg-gray-800 rounded p-2">
                      <div className="text-red-600 dark:text-red-400 font-bold">
                        {Math.max(...hailEvents.map((e) => e.max_hail_size)).toFixed(2)}"
                      </div>
                      <div className="text-xs text-muted-foreground">Max Hail</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded p-2">
                      <div className="text-orange-600 dark:text-orange-400 font-bold">
                        {hailEvents.filter(e => e.swath_polygon).length}
                      </div>
                      <div className="text-xs text-muted-foreground">Swath Polygons</div>
                    </div>
                  </div>

                  <div className="text-sm text-red-600 dark:text-red-400">
                    <span className="font-medium">📍 Areas:</span>{" "}
                    {[...new Set(hailEvents.map((e) => e.city).filter(Boolean))].slice(0, 5).join(", ")}
                    {[...new Set(hailEvents.map((e) => e.city).filter(Boolean))].length > 5 &&
                      ` +${[...new Set(hailEvents.map((e) => e.city).filter(Boolean))].length - 5} more`}
                  </div>

                  {/* Swath stats */}
                  <div className="text-xs text-red-500 dark:text-red-400 pt-1 border-t border-red-200 dark:border-red-700">
                    {hailEvents.filter(e => e.swath_polygon).length > 0 ? (
                      <span className="text-green-600">
                        ✓ {hailEvents.filter(e => e.swath_polygon).length} events with swath polygons on map
                      </span>
                    ) : (
                      <span className="text-orange-600">
                        ⚠ No swath polygons - showing {hailEvents.filter(e => e.center_lat).length} center points
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* SWATH SELECTOR - Between Storm Details and Find Businesses */}
          {numberedSwaths.length > 0 && (
            <div className="border-b">
              <button
                onClick={() => setShowSwathSelector(!showSwathSelector)}
                className="w-full p-3 flex items-center justify-between text-sm font-medium hover:bg-muted/50"
              >
                <span className="flex items-center gap-2">
                  <List className="h-4 w-4 text-blue-500" />
                  <span>Select Swaths</span>
                  <Badge variant="secondary" className="text-xs">
                    {selectedSwathIds.size} of {numberedSwaths.length}
                  </Badge>
                </span>
                <ChevronDown className={`h-4 w-4 transition-transform ${showSwathSelector ? "rotate-180" : ""}`} />
              </button>

              {showSwathSelector && (
                <div className="px-3 pb-3">
                  {/* Select All / Clear All */}
                  <div className="flex justify-between items-center mb-2 text-xs">
                    <button
                      onClick={selectAllSwaths}
                      className="text-blue-600 hover:underline"
                    >
                      Select All
                    </button>
                    <button
                      onClick={clearAllSwaths}
                      className="text-blue-600 hover:underline"
                    >
                      Clear All
                    </button>
                  </div>

                  {/* Swath List */}
                  <div className="max-h-48 overflow-y-auto space-y-1 border rounded-lg p-1 bg-gray-50 dark:bg-gray-800/50">
                    {numberedSwaths.map((swath) => {
                      const isSelected = selectedSwathIds.has(swath.id)
                      const bizCount = businessesBySwath[swath.id] || 0
                      const severity = getSeverityStyle(swath.max_hail_size)

                      return (
                        <label
                          key={swath.id}
                          className={`
                            flex items-center gap-2 p-2 rounded cursor-pointer transition-all
                            ${isSelected
                              ? "bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700"
                              : "hover:bg-gray-100 dark:hover:bg-gray-700 border border-transparent"}
                          `}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSwathSelection(swath.id)}
                            className="rounded text-blue-600"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-sm">#{swath.swathNumber}</span>
                              <Badge className={`${severity.bg} text-white text-xs px-1.5`}>
                                {swath.max_hail_size}"
                              </Badge>
                            </div>
                            <div className="text-xs text-muted-foreground truncate">
                              {swath.city || swath.event_name || "Unknown"}
                            </div>
                          </div>
                          <div className="text-right">
                            {bizCount > 0 && (
                              <div className="text-xs font-medium text-blue-600">
                                {bizCount} biz
                              </div>
                            )}
                          </div>
                        </label>
                      )
                    })}
                  </div>

                  {/* Selection Summary */}
                  <div className="mt-2 pt-2 border-t text-xs text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Selected swaths:</span>
                      <span className="font-medium">{selectedSwathIds.size}</span>
                    </div>
                    {businesses.length > 0 && (
                      <div className="flex justify-between">
                        <span>Businesses in selection:</span>
                        <span className="font-medium text-blue-600">{businessesInSelectedSwaths.length}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Find Businesses */}
          {selectedDate && hailEvents.length > 0 && (
            <div className="p-4 border-b">
              <h2 className="font-bold text-lg mb-3 flex items-center gap-2">
                <span className="bg-blue-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">
                  3
                </span>
                Find Businesses
              </h2>

              {/* Min Vehicles Filter */}
              <div className="mb-3">
                <label className="text-sm text-muted-foreground">Min. Vehicles</label>
                <Select value={String(minVehicles)} onValueChange={(v) => setMinVehicles(Number(v))}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Any (1+)</SelectItem>
                    <SelectItem value="5">5+ vehicles</SelectItem>
                    <SelectItem value="10">10+ vehicles</SelectItem>
                    <SelectItem value="25">25+ vehicles</SelectItem>
                    <SelectItem value="50">50+ vehicles (large fleets)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Scan Depth Selector */}
              <div className="mb-3">
                <label className="text-sm text-muted-foreground">Scan Depth</label>
                <div className="mt-1 space-y-1">
                  <label className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                    <input
                      type="radio"
                      name="scanDepth"
                      checked={scanDepth === 200}
                      onChange={() => setScanDepth(200)}
                      className="text-blue-600"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-sm">Quick Scan</div>
                      <div className="text-xs text-muted-foreground">200 tiles · ~50 sq mi · ~800 businesses</div>
                    </div>
                  </label>
                  <label className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 border-blue-300 bg-blue-50 dark:bg-blue-900/20">
                    <input
                      type="radio"
                      name="scanDepth"
                      checked={scanDepth === 500}
                      onChange={() => setScanDepth(500)}
                      className="text-blue-600"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-sm">Full Scan <Badge variant="secondary" className="ml-1 text-xs">Recommended</Badge></div>
                      <div className="text-xs text-muted-foreground">500 tiles · ~125 sq mi · ~2,000 businesses</div>
                    </div>
                  </label>
                  <label className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                    <input
                      type="radio"
                      name="scanDepth"
                      checked={scanDepth === 0}
                      onChange={() => setScanDepth(0)}
                      className="text-blue-600"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-sm">Deep Scan</div>
                      <div className="text-xs text-muted-foreground">All tiles · Full swath coverage · ~3,500+ businesses</div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Search Button */}
              <Button
                onClick={findBusinessesInSwath}
                disabled={loadingBusinesses}
                className={`w-full ${loadingBusinesses ? "bg-gray-400" : "bg-blue-600 hover:bg-blue-700"}`}
              >
                {loadingBusinesses ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : scrapeStatus === "done" ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Search Again
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    Find Businesses in Swath
                  </>
                )}
              </Button>

              {loadingBusinesses && (
                <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 text-sm font-medium">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {scanDepth === 200 && "Quick Scan: 200 tiles with 6 APIs..."}
                    {scanDepth === 500 && "Full Scan: 500 tiles with 6 APIs..."}
                    {scanDepth === 0 && "Deep Scan: All tiles with 6 APIs..."}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Searching Yelp, Foursquare, HERE, TomTom, Google, and OSM.
                    {scanDepth === 200 && " Estimated time: 2-4 minutes."}
                    {scanDepth === 500 && " Estimated time: 10-15 minutes."}
                    {scanDepth === 0 && " This may take over an hour."}
                  </p>
                  <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-1.5 mt-2">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full animate-pulse"
                      style={{ width: '60%' }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: Results & CRM */}
          {businesses.length > 0 && (
            <div className="flex flex-col">
              <div className="p-4 border-b bg-green-50 dark:bg-green-900/20">
                <h2 className="font-bold text-lg mb-2 flex items-center gap-2">
                  <span className="bg-green-500 text-white w-6 h-6 rounded-full flex items-center justify-center text-sm">
                    4
                  </span>
                  Results
                  {stats.businesses !== stats.totalBusinesses && (
                    <span className="text-xs text-muted-foreground font-normal">
                      ({stats.businesses} of {stats.totalBusinesses})
                    </span>
                  )}
                </h2>

                {/* Stats Cards */}
                <div className="grid grid-cols-3 gap-2 text-center mb-3">
                  <div className="bg-white dark:bg-gray-800 rounded p-2">
                    <div className="text-2xl font-bold text-blue-600">{stats.businesses}</div>
                    <div className="text-xs text-muted-foreground">Businesses</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded p-2">
                    <div className="text-2xl font-bold text-purple-600">{stats.vehicles.toLocaleString()}</div>
                    <div className="text-xs text-muted-foreground">Vehicles</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 rounded p-2">
                    <div className="text-2xl font-bold text-green-600">${(stats.value / 1000).toFixed(0)}K</div>
                    <div className="text-xs text-muted-foreground">Est. Value</div>
                  </div>
                </div>

                {/* Swath Selection Summary */}
                {selectedSwathIds.size < numberedSwaths.length && numberedSwaths.length > 0 && (
                  <div className="bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700 rounded-lg p-2 mb-3 text-sm">
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-blue-600" />
                      <span>
                        <strong>{selectedSwathIds.size}</strong> of {numberedSwaths.length} swaths selected
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {businessesInSelectedSwaths.length} businesses in selected swaths
                    </div>
                  </div>
                )}

                {/* Action Buttons Row */}
                <div className="flex gap-2 mb-3">
                  {/* Add All to CRM */}
                  {crmResult ? (
                    <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-300 dark:border-green-700">
                      <div className="flex items-center gap-2 text-green-700 dark:text-green-300 font-medium">
                        <CheckCircle2 className="h-5 w-5" />
                        Added to CRM!
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {crmResult.created} new leads, {crmResult.skipped} already existed
                      </div>
                      <Link
                        to="/leads?source=FLEET_DISCOVERY&temperature=HOT"
                        className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Go to Leads → Start Calling
                      </Link>
                    </div>
                  ) : (
                    <>
                      <Button
                        onClick={addAllToCRM}
                        disabled={addingToCRM || businessesInSelectedSwaths.length === 0}
                        className={`flex-1 ${addingToCRM ? "bg-gray-400" : "bg-red-600 hover:bg-red-700"}`}
                      >
                        {addingToCRM ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Adding...
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="h-4 w-4 mr-2" />
                            Add {businessesInSelectedSwaths.length} to CRM
                          </>
                        )}
                      </Button>

                      {/* Export CSV Button */}
                      <Button
                        onClick={exportToCSV}
                        disabled={businessesInSelectedSwaths.length === 0}
                        variant="outline"
                        className="flex-shrink-0"
                        title="Export selected businesses to CSV"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>

                {/* Export Summary when swaths are filtered */}
                {selectedSwathIds.size < numberedSwaths.length && businessesInSelectedSwaths.length > 0 && (
                  <button
                    onClick={exportToCSV}
                    className="w-full text-left p-2 mb-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Download className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-medium">Export {businessesInSelectedSwaths.length} businesses</span>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        CSV
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      From {selectedSwathIds.size} selected swaths · Includes swath # for each business
                    </div>
                  </button>
                )}
              </div>

              {/* Category Filter */}
              <div className="p-3 border-b bg-gray-50 dark:bg-gray-800/50">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold text-sm">Filter by Category</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={selectAllCategories}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      All
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                      onClick={clearAllCategories}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      None
                    </button>
                  </div>
                </div>

                <div className="max-h-40 overflow-y-auto space-y-1">
                  {Object.entries(categoryCounts)
                    .sort((a, b) => b[1] - a[1])
                    .map(([category, count]) => (
                      <label
                        key={category}
                        className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 p-1 rounded"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCategories.has(category)}
                          onChange={() => toggleCategory(category)}
                          className="rounded text-blue-600"
                        />
                        <span className="flex-1">{formatCategoryName(category)}</span>
                        <span className="text-gray-400 text-xs">({count})</span>
                      </label>
                    ))}
                </div>

                <div className="text-xs text-muted-foreground mt-2 pt-2 border-t">
                  Showing {filteredBusinesses.length} of {businesses.length} businesses
                </div>
              </div>

              {/* Business List */}
              <div className="max-h-96 overflow-y-auto p-2">
                {filteredBusinesses
                  .sort((a, b) => b.estimated_vehicles - a.estimated_vehicles)
                  .map((business) => {
                    const isAdded = (business as any).added_to_crm
                    return (
                      <div
                        key={business.id}
                        onClick={() => {
                          setSelectedBusiness(business)
                          if (business.latitude && business.longitude) {
                            mapInstanceRef.current?.setView([business.latitude, business.longitude], 15)
                          }
                        }}
                        className={`
                          p-3 mb-2 rounded-lg border cursor-pointer transition-all
                          ${
                            selectedBusiness?.id === business.id
                              ? "bg-blue-50 dark:bg-blue-900/30 border-blue-300"
                              : "bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                          }
                          ${isAdded ? "opacity-60" : ""}
                        `}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium flex items-center gap-2">
                              <span className="truncate">{business.name}</span>
                              {isAdded && (
                                <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                                  ✓ In CRM
                                </Badge>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {business.category?.replace(/_/g, " ")} • {business.city}
                            </div>
                            {/* Address */}
                            {business.address && (
                              <div className="text-xs text-muted-foreground mt-1 truncate" title={business.address}>
                                📍 {business.address}
                              </div>
                            )}
                            {/* Contact Info */}
                            <div className="flex flex-wrap gap-2 mt-1">
                              {business.phone && (
                                <a
                                  href={`tel:${business.phone}`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-xs text-blue-600 hover:underline"
                                >
                                  📞 {business.phone}
                                </a>
                              )}
                              {(business as any).email && (
                                <a
                                  href={`mailto:${(business as any).email}`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-xs text-blue-600 hover:underline"
                                >
                                  ✉️ {(business as any).email}
                                </a>
                              )}
                            </div>
                            {business.website && (
                              <a
                                href={business.website.startsWith('http') ? business.website : `https://${business.website}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-xs text-green-600 hover:underline block mt-1 truncate"
                              >
                                🌐 {business.website.replace(/^https?:\/\//, '').slice(0, 30)}...
                              </a>
                            )}
                          </div>
                          <div className="text-right ml-2">
                            <div className="font-bold text-purple-600">~{business.estimated_vehicles}</div>
                            <div className="text-xs text-muted-foreground">vehicles</div>
                            <div className="text-xs text-green-600 font-medium">
                              ${((business.estimated_vehicles * 500) / 1000).toFixed(0)}K
                            </div>
                          </div>
                        </div>

                        {/* Quick Actions */}
                        <div className="flex gap-1 mt-2">
                          {business.phone && (
                            <a
                              href={`tel:${business.phone}`}
                              onClick={(e) => e.stopPropagation()}
                              className="flex-1 text-center text-xs bg-green-500 text-white py-1.5 rounded hover:bg-green-600"
                            >
                              📞 Call
                            </a>
                          )}
                          {business.website && (
                            <a
                              href={business.website.startsWith('http') ? business.website : `https://${business.website}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="flex-1 text-center text-xs bg-teal-500 text-white py-1.5 rounded hover:bg-teal-600"
                            >
                              🌐 Web
                            </a>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setEmailModalBusiness(business)
                            }}
                            className="flex-1 text-center text-xs bg-blue-500 text-white py-1.5 rounded hover:bg-blue-600"
                          >
                            📧 Email
                          </button>
                          {!isAdded && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                addSingleToCRM(business)
                              }}
                              className="flex-1 text-center text-xs bg-red-500 text-white py-1.5 rounded hover:bg-red-600"
                            >
                              ➕ CRM
                            </button>
                          )}
                        </div>
                      </div>
                    )
                  })}
              </div>
            </div>
          )}

          {/* Empty state when search done but no results */}
          {scrapeStatus === "done" && businesses.length === 0 && (
            <div className="p-4 text-center text-muted-foreground">
              <div className="text-4xl mb-2">🔍</div>
              <div>No businesses found in swath area</div>
              <div className="text-sm mt-1">Try lowering the minimum vehicles filter</div>
            </div>
          )}
          </div>{/* End scrollable sidebar content */}
        </div>{/* End sidebar */}

        {/* ========== MAP ========== */}
        <div className="flex-1 relative">
          <div ref={mapRef} className="h-full w-full" />

          {/* Map Legend */}
          <div className="absolute bottom-4 right-4 bg-white dark:bg-gray-900 rounded-lg shadow-lg p-3 z-[1000]">
            <div className="text-xs font-bold mb-2">Legend</div>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-red-500 opacity-30 border-2 border-red-600 rounded"></div>
                <span>Hail Swath (2"+)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-orange-500 opacity-30 border-2 border-orange-600 rounded"></div>
                <span>Hail Swath (1.5-2")</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-yellow-500 opacity-30 border-2 border-yellow-600 rounded"></div>
                <span>Hail Swath (1-1.5")</span>
              </div>
              <div className="border-t my-2"></div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-white text-[8px] flex items-center justify-center text-white font-bold">
                  1
                </div>
                <span>Tier 1 (Highest Value)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-orange-500 border-2 border-white text-[8px] flex items-center justify-center text-white font-bold">
                  2
                </div>
                <span>Tier 2 (High Value)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-yellow-500 border-2 border-white text-[8px] flex items-center justify-center text-white font-bold">
                  3
                </div>
                <span>Tier 3 (Good)</span>
              </div>
            </div>
          </div>

          {/* Stats Overlay (when businesses found) */}
          {businesses.length > 0 && (
            <div className="absolute top-4 left-4 bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 z-[1000]">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <Building2 className="h-5 w-5 mx-auto mb-1 text-blue-500" />
                  <div className="text-lg font-bold">{stats.businesses}</div>
                  <div className="text-xs text-muted-foreground">Businesses</div>
                </div>
                <div>
                  <Car className="h-5 w-5 mx-auto mb-1 text-purple-500" />
                  <div className="text-lg font-bold">{stats.vehicles.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">Vehicles</div>
                </div>
                <div>
                  <DollarSign className="h-5 w-5 mx-auto mb-1 text-green-500" />
                  <div className="text-lg font-bold">${(stats.value / 1000).toFixed(0)}K</div>
                  <div className="text-xs text-muted-foreground">Value</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ========== MODALS ========== */}

      {/* Email Template Modal */}
      {emailModalBusiness && (
        <EmailTemplateModal
          business={{
            id: emailModalBusiness.id,
            name: emailModalBusiness.name,
            city: emailModalBusiness.city,
            state: emailModalBusiness.state,
            phone: emailModalBusiness.phone,
            email: undefined,
            website: emailModalBusiness.website,
            category: emailModalBusiness.category,
            estimated_vehicles: emailModalBusiness.estimated_vehicles,
            hail_date: selectedDate || undefined,
            hail_size: hailEvents.length > 0 ? Math.max(...hailEvents.map((e) => e.max_hail_size)) : undefined,
          }}
          onClose={() => setEmailModalBusiness(null)}
          onSent={() => setEmailModalBusiness(null)}
        />
      )}

      {/* Call Script Modal */}
      {callModalBusiness && (
        <CallScriptModal
          business={{
            id: callModalBusiness.id,
            name: callModalBusiness.name,
            address: callModalBusiness.address,
            city: callModalBusiness.city,
            state: callModalBusiness.state,
            phone: callModalBusiness.phone,
            website: callModalBusiness.website,
            category: callModalBusiness.category,
            estimated_vehicles: callModalBusiness.estimated_vehicles,
            hail_date: selectedDate || undefined,
          }}
          onClose={() => setCallModalBusiness(null)}
          onLogCall={async (outcome, notes) => {
            console.log("Call logged:", outcome, notes)
            setCallModalBusiness(null)
          }}
        />
      )}
    </div>
  )
}

// Default export for compatibility
export default FleetMapPage
