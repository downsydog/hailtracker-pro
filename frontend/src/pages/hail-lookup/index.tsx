import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { hailEventsApi, HailEvent } from "@/api/weather"
import {
  Search,
  MapPin,
  CloudLightning,
  Calendar,
  TrendingUp,
  Eye,
  Download,
  Loader2,
  X,
  Navigation,
  AlertTriangle,
  CheckCircle,
} from "lucide-react"

// Fix Leaflet default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

// Debounce utility
function debounce<T extends (...args: any[]) => any>(func: T, wait: number) {
  let timeout: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Hail size color coding
function getHailSizeColor(size: number): string {
  if (size >= 2.5) return "#9333ea" // Purple - catastrophic
  if (size >= 2.0) return "#dc2626" // Red - severe
  if (size >= 1.5) return "#f97316" // Orange
  if (size >= 1.0) return "#eab308" // Yellow
  return "#22c55e" // Green - minor
}

interface CityResult {
  name: string
  state: string
  county?: string
  lat: number
  lon: number
  display: string
}

export function HailLookupPage() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.LayerGroup | null>(null)
  const swathLayerRef = useRef<L.LayerGroup | null>(null)
  const cityMarkerRef = useRef<L.Marker | null>(null)
  const radiusCircleRef = useRef<L.Circle | null>(null)

  // City search state
  const [searchQuery, setSearchQuery] = useState("")
  const [suggestions, setSuggestions] = useState<CityResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedCity, setSelectedCity] = useState<CityResult | null>(null)
  const [showSuggestions, setShowSuggestions] = useState(false)

  // Search parameters
  const [radius, setRadius] = useState("30")
  const [years, setYears] = useState("10")

  // Results state
  const [hailEvents, setHailEvents] = useState<HailEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<HailEvent | null>(null)

  // City autocomplete search using Nominatim (FREE)
  const searchCities = useCallback(
    debounce(async (query: string) => {
      if (query.length < 3) {
        setSuggestions([])
        return
      }

      setIsSearching(true)
      try {
        // Nominatim API - FREE, no key needed
        const response = await fetch(
          `https://nominatim.openstreetmap.org/search?` +
            `q=${encodeURIComponent(query)}&` +
            `format=json&` +
            `addressdetails=1&` +
            `limit=8&` +
            `countrycodes=us,ca&` +
            `featuretype=city`,
          {
            headers: {
              "User-Agent": "HailTrackerPro/1.0",
            },
          }
        )
        const data = await response.json()

        // Filter to cities/towns and format
        const cities: CityResult[] = data
          .filter(
            (item: any) =>
              item.type === "city" ||
              item.type === "town" ||
              item.type === "village" ||
              item.type === "administrative" ||
              item.class === "place"
          )
          .map((item: any) => ({
            name:
              item.address?.city ||
              item.address?.town ||
              item.address?.village ||
              item.name,
            state: item.address?.state || "",
            county: item.address?.county,
            lat: parseFloat(item.lat),
            lon: parseFloat(item.lon),
            display: `${item.address?.city || item.address?.town || item.address?.village || item.name}, ${item.address?.state || ""}`,
          }))

        setSuggestions(cities)
        setShowSuggestions(true)
      } catch (error) {
        console.error("Geocoding error:", error)
        setSuggestions([])
      } finally {
        setIsSearching(false)
      }
    }, 300),
    []
  )

  // Trigger search on input change
  useEffect(() => {
    if (searchQuery && !selectedCity) {
      searchCities(searchQuery)
    }
  }, [searchQuery, searchCities, selectedCity])

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [39.8283, -98.5795], // Center of US
      zoom: 4,
      zoomControl: true,
    })

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map)

    markersRef.current = L.layerGroup().addTo(map)
    swathLayerRef.current = L.layerGroup().addTo(map)
    mapInstanceRef.current = map

    setTimeout(() => map.invalidateSize(), 100)

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Search hail history for selected city
  const searchHailHistory = async (city: CityResult) => {
    setLoading(true)
    setHailEvents([])
    setSelectedEvent(null)

    // Clear previous markers
    if (markersRef.current) markersRef.current.clearLayers()
    if (swathLayerRef.current) swathLayerRef.current.clearLayers()

    try {
      // Use the check-location API with larger radius
      const response = await hailEventsApi.checkLocation({
        lat: city.lat,
        lon: city.lon,
        years: parseInt(years),
        radius_miles: parseFloat(radius),
      })

      const data = response.data
      if (data && data.events) {
        setHailEvents(data.events as any)
      }

      // Center map on city and add city marker
      if (mapInstanceRef.current) {
        mapInstanceRef.current.setView([city.lat, city.lon], 9)

        // Add city marker
        const cityIcon = L.divIcon({
          html: `<div style="width: 36px; height: 36px; border-radius: 50%; background: #3b82f6; border: 4px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
          </div>`,
          className: "",
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        })

        if (cityMarkerRef.current) {
          mapInstanceRef.current.removeLayer(cityMarkerRef.current)
        }
        cityMarkerRef.current = L.marker([city.lat, city.lon], { icon: cityIcon })
          .bindPopup(`<strong>${city.name}, ${city.state}</strong>`)
          .addTo(mapInstanceRef.current)

        // Add radius circle
        if (radiusCircleRef.current) {
          mapInstanceRef.current.removeLayer(radiusCircleRef.current)
        }
        const radiusMeters = parseFloat(radius) * 1609.34
        radiusCircleRef.current = L.circle([city.lat, city.lon], {
          radius: radiusMeters,
          color: "#3b82f6",
          fillColor: "rgba(59, 130, 246, 0.08)",
          fillOpacity: 0.5,
          weight: 2,
          dashArray: "8, 8",
        }).addTo(mapInstanceRef.current)
      }
    } catch (error) {
      console.error("Error fetching hail history:", error)
    } finally {
      setLoading(false)
    }
  }

  // Show event swath on map
  const showEventOnMap = (event: HailEvent) => {
    if (!mapInstanceRef.current || !swathLayerRef.current) return

    swathLayerRef.current.clearLayers()
    setSelectedEvent(event)

    const hailSize = event.max_hail_size ?? (event as any).hail_size_inches ?? 0
    const color = getHailSizeColor(hailSize)

    // Try to show swath polygon if available
    if (event.swath_polygon) {
      try {
        const geojson =
          typeof event.swath_polygon === "string"
            ? JSON.parse(event.swath_polygon)
            : event.swath_polygon

        const layer = L.geoJSON(geojson, {
          style: {
            color: color,
            weight: 3,
            fillColor: color,
            fillOpacity: 0.35,
          },
        })

        layer.bindPopup(`
          <div style="min-width: 200px;">
            <strong>${event.event_name || event.city || "Unknown"}</strong><br/>
            <p><strong>Date:</strong> ${event.event_date}</p>
            <p><strong>Hail Size:</strong> ${hailSize.toFixed(2)}"</p>
            ${event.swath_area_sqmi ? `<p><strong>Area:</strong> ${event.swath_area_sqmi.toFixed(1)} sq mi</p>` : ""}
          </div>
        `)

        swathLayerRef.current.addLayer(layer)
        mapInstanceRef.current.fitBounds(layer.getBounds(), { padding: [50, 50] })
        return
      } catch (e) {
        console.error("Error displaying swath:", e)
      }
    }

    // Fallback to circle marker
    const lat = event.center_lat ?? (event as any).latitude ?? selectedCity?.lat
    const lon = event.center_lon ?? (event as any).longitude ?? selectedCity?.lon

    if (lat && lon) {
      const areaSquareMiles = event.swath_area_sqmi || 10
      const radiusMiles = Math.sqrt(areaSquareMiles / Math.PI)
      const radiusMeters = radiusMiles * 1609.34

      const circle = L.circle([lat, lon], {
        radius: Math.max(radiusMeters, 3000),
        color: color,
        fillColor: color,
        fillOpacity: 0.35,
        weight: 3,
      })

      circle.bindPopup(`
        <div style="min-width: 200px;">
          <strong>${event.event_name || event.city || "Unknown"}</strong><br/>
          <p><strong>Date:</strong> ${event.event_date}</p>
          <p><strong>Hail Size:</strong> ${hailSize.toFixed(2)}"</p>
        </div>
      `)

      swathLayerRef.current.addLayer(circle)
      mapInstanceRef.current.setView([lat, lon], 11)
    }
  }

  // Calculate statistics
  const stats = useMemo(() => {
    if (hailEvents.length === 0) return null

    const sizes = hailEvents.map((e) => e.max_hail_size ?? (e as any).hail_size_inches ?? 0)
    const dates = hailEvents.map((e) => e.event_date).filter(Boolean)
    const years = new Set(dates.map((d) => d?.split("-")[0]))

    return {
      totalEvents: hailEvents.length,
      maxHailSize: Math.max(...sizes),
      avgHailSize: sizes.reduce((a, b) => a + b, 0) / sizes.length,
      yearsWithHail: years.size,
      mostRecent: dates.sort().reverse()[0] || "N/A",
      severeEvents: hailEvents.filter((e) => (e.max_hail_size ?? (e as any).hail_size_inches ?? 0) >= 2.0).length,
    }
  }, [hailEvents])

  // Group events by year
  const eventsByYear = useMemo(() => {
    const grouped: Record<string, HailEvent[]> = {}
    hailEvents.forEach((event) => {
      const year = event.event_date?.split("-")[0] || "Unknown"
      if (!grouped[year]) grouped[year] = []
      grouped[year].push(event)
    })
    return Object.entries(grouped).sort(([a], [b]) => b.localeCompare(a))
  }, [hailEvents])

  // PDF report
  const generateReportMutation = useMutation({
    mutationFn: () =>
      hailEventsApi.generateImpactReport({
        lat: selectedCity?.lat || 0,
        lon: selectedCity?.lon || 0,
        years: parseInt(years),
        radius_miles: parseFloat(radius),
        address: selectedCity?.display,
      }),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `hail_report_${selectedCity?.name?.replace(/\s+/g, "_") || "location"}_${new Date().toISOString().slice(0, 10)}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
  })

  // Clear selection
  const clearSelection = () => {
    setSelectedCity(null)
    setSearchQuery("")
    setHailEvents([])
    setSelectedEvent(null)
    setSuggestions([])
    if (markersRef.current) markersRef.current.clearLayers()
    if (swathLayerRef.current) swathLayerRef.current.clearLayers()
    if (cityMarkerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(cityMarkerRef.current)
      cityMarkerRef.current = null
    }
    if (radiusCircleRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(radiusCircleRef.current)
      radiusCircleRef.current = null
    }
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([39.8283, -98.5795], 4)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-80px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <PageHeader
          title="Hail Lookup"
          description="Research a city's hail history before deciding to work there"
        />
      </div>

      {/* Search Bar */}
      <div className="mb-4">
        <div className="flex gap-3">
          {/* City Search Input */}
          <div className="relative flex-1 max-w-xl">
            <div className="relative">
              <Input
                type="text"
                placeholder="Search for a city... (e.g., Oklahoma City, Dallas)"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  if (selectedCity) setSelectedCity(null)
                }}
                onFocus={() => setShowSuggestions(true)}
                className="pl-10 pr-10 h-12 text-lg"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-blue-500 animate-spin" />
              )}
              {selectedCity && (
                <button
                  onClick={clearSelection}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded"
                >
                  <X className="h-4 w-4 text-gray-500" />
                </button>
              )}
            </div>

            {/* Autocomplete Dropdown */}
            {showSuggestions && suggestions.length > 0 && !selectedCity && (
              <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                {suggestions.map((city, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setSelectedCity(city)
                      setSearchQuery(city.display)
                      setSuggestions([])
                      setShowSuggestions(false)
                      searchHailHistory(city)
                    }}
                    className="w-full px-4 py-3 text-left hover:bg-blue-50 flex items-center gap-3 border-b last:border-b-0"
                  >
                    <MapPin className="h-5 w-5 text-blue-500" />
                    <div>
                      <div className="font-medium">
                        {city.name}, {city.state}
                      </div>
                      {city.county && (
                        <div className="text-sm text-muted-foreground">
                          {city.county}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Search Parameters */}
          <Select value={radius} onValueChange={setRadius}>
            <SelectTrigger className="w-36 h-12">
              <SelectValue placeholder="Radius" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10 mile radius</SelectItem>
              <SelectItem value="20">20 mile radius</SelectItem>
              <SelectItem value="30">30 mile radius</SelectItem>
              <SelectItem value="50">50 mile radius</SelectItem>
            </SelectContent>
          </Select>

          <Select value={years} onValueChange={setYears}>
            <SelectTrigger className="w-36 h-12">
              <SelectValue placeholder="Years" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3">Last 3 years</SelectItem>
              <SelectItem value="5">Last 5 years</SelectItem>
              <SelectItem value="10">Last 10 years</SelectItem>
              <SelectItem value="15">Since 2011</SelectItem>
            </SelectContent>
          </Select>

          {selectedCity && (
            <Button
              onClick={() => searchHailHistory(selectedCity)}
              disabled={loading}
              className="h-12 px-6"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Search className="h-5 w-5 mr-2" />
                  Search
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Map */}
        <div className="w-1/2 bg-card rounded-lg border overflow-hidden">
          <div ref={mapRef} className="w-full h-full" />
        </div>

        {/* Results Panel */}
        <div className="w-1/2 flex flex-col min-h-0">
          {!selectedCity ? (
            // Empty State
            <div className="flex-1 flex items-center justify-center bg-card rounded-lg border">
              <div className="text-center text-muted-foreground p-8">
                <Search className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <h3 className="text-lg font-medium mb-2">Search for a City</h3>
                <p className="text-sm">
                  Enter a city name above to see its historical hail activity.
                  <br />
                  Research if an area has been over-worked or is a good
                  opportunity.
                </p>
              </div>
            </div>
          ) : loading ? (
            // Loading State
            <div className="flex-1 bg-card rounded-lg border p-6">
              <div className="space-y-4">
                <Skeleton className="h-8 w-64" />
                <div className="grid grid-cols-4 gap-3">
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                  <Skeleton className="h-24" />
                </div>
                <Skeleton className="h-64" />
              </div>
            </div>
          ) : (
            // Results
            <div className="flex-1 flex flex-col bg-card rounded-lg border overflow-hidden">
              {/* City Header */}
              <div className="p-4 border-b bg-muted/30">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold flex items-center gap-2">
                      <MapPin className="h-5 w-5 text-blue-500" />
                      {selectedCity.name}, {selectedCity.state}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {radius} mile radius • Last {years} years
                    </p>
                  </div>
                  {stats && stats.totalEvents > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => generateReportMutation.mutate()}
                      disabled={generateReportMutation.isPending}
                    >
                      {generateReportMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4 mr-2" />
                      )}
                      PDF Report
                    </Button>
                  )}
                </div>
              </div>

              {/* Stats */}
              {stats && stats.totalEvents > 0 ? (
                <>
                  <div className="p-4 border-b">
                    <div className="grid grid-cols-4 gap-3">
                      <div className="bg-blue-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-blue-600">
                          {stats.totalEvents}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Total Events
                        </div>
                      </div>
                      <div className="bg-orange-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-orange-600">
                          {stats.maxHailSize.toFixed(2)}"
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Max Hail Size
                        </div>
                      </div>
                      <div className="bg-red-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-red-600">
                          {stats.severeEvents}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Severe (2"+)
                        </div>
                      </div>
                      <div className="bg-purple-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-purple-600">
                          {stats.yearsWithHail}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Years Hit
                        </div>
                      </div>
                    </div>

                    {/* Assessment */}
                    <div className="mt-3 p-3 rounded-lg bg-muted/50">
                      {stats.totalEvents >= 20 ? (
                        <div className="flex items-center gap-2 text-orange-600">
                          <AlertTriangle className="h-5 w-5" />
                          <span className="font-medium">
                            High Activity Area - May be over-worked by other PDR
                            companies
                          </span>
                        </div>
                      ) : stats.totalEvents >= 5 ? (
                        <div className="flex items-center gap-2 text-blue-600">
                          <TrendingUp className="h-5 w-5" />
                          <span className="font-medium">
                            Good Opportunity - Regular hail activity, potential
                            for work
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-green-600">
                          <CheckCircle className="h-5 w-5" />
                          <span className="font-medium">
                            Low Activity - Less competition but fewer storms
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Event List */}
                  <div className="flex-1 overflow-y-auto">
                    <div className="divide-y">
                      {eventsByYear.map(([year, events]) => (
                        <div key={year}>
                          <div className="px-4 py-2 bg-muted/30 font-semibold text-sm flex items-center gap-2 sticky top-0">
                            <Calendar className="h-4 w-4" />
                            {year}
                            <Badge variant="secondary" className="ml-auto">
                              {events.length} events
                            </Badge>
                          </div>
                          {events.map((event) => {
                            const hailSize =
                              event.max_hail_size ??
                              (event as any).hail_size_inches ??
                              0
                            const isSelected = selectedEvent?.id === event.id
                            return (
                              <div
                                key={event.id}
                                onClick={() => showEventOnMap(event)}
                                className={`px-4 py-3 flex items-center gap-4 cursor-pointer hover:bg-blue-50 transition-colors ${
                                  isSelected ? "bg-blue-100" : ""
                                }`}
                              >
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium truncate">
                                    {event.event_name ||
                                      event.city ||
                                      "Unknown Location"}
                                  </div>
                                  <div className="text-sm text-muted-foreground">
                                    {event.event_date} •{" "}
                                    {(event as any).distance_miles?.toFixed(1) ||
                                      "?"}{" "}
                                    mi away
                                  </div>
                                </div>
                                <Badge
                                  style={{
                                    backgroundColor: `${getHailSizeColor(hailSize)}20`,
                                    color: getHailSizeColor(hailSize),
                                    borderColor: getHailSizeColor(hailSize),
                                  }}
                                  className="border"
                                >
                                  {hailSize.toFixed(2)}" hail
                                </Badge>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    showEventOnMap(event)
                                  }}
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </div>
                            )
                          })}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                // No events found
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center p-8">
                    <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
                    <h3 className="text-lg font-medium mb-2 text-green-600">
                      No Hail Events Found
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      No significant hail events were recorded within {radius}{" "}
                      miles
                      <br />
                      of {selectedCity.name} in the last {years} years.
                    </p>
                    <p className="text-sm text-muted-foreground mt-4">
                      This could indicate a low-risk area or limited data
                      coverage.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default HailLookupPage
