import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

import { PageHeader } from "@/components/app/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { hailEventsApi, LocationCheckResult } from "@/api/weather"
import {
  Search,
  MapPin,
  CloudLightning,
  Calendar,
  Ruler,
  CheckCircle2,
  XCircle,
  Download,
  Loader2,
} from "lucide-react"

// Fix Leaflet default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

const SEVERITY_COLORS: Record<string, string> = {
  SEVERE: "#ef4444",
  MODERATE: "#f59e0b",
  MINOR: "#22c55e",
}

export function HailLookupPage() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.LayerGroup | null>(null)

  const [lat, setLat] = useState("")
  const [lon, setLon] = useState("")
  const [years, setYears] = useState("5")
  const [radius, setRadius] = useState("5")
  const [searchTriggered, setSearchTriggered] = useState(false)

  // Fetch location check
  const { data: result, isLoading, refetch } = useQuery({
    queryKey: ["hail-lookup", lat, lon, years, radius],
    queryFn: () => hailEventsApi.checkLocation({
      lat: parseFloat(lat),
      lon: parseFloat(lon),
      years: parseInt(years),
      radius_miles: parseFloat(radius),
    }),
    enabled: searchTriggered && !!lat && !!lon,
  })

  const locationData = result?.data as LocationCheckResult | undefined

  // PDF generation mutation
  const generateReportMutation = useMutation({
    mutationFn: () =>
      hailEventsApi.generateImpactReport({
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        years: parseInt(years),
        radius_miles: parseFloat(radius),
      }),
    onSuccess: (blob) => {
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `hail_impact_report_${new Date().toISOString().slice(0, 10)}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
    onError: (error) => {
      console.error("Failed to generate report:", error)
      alert("Failed to generate report. Please try again.")
    },
  })

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [39.8283, -98.5795], // Center of US
      zoom: 4,
      zoomControl: true,
    })

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map)

    markersRef.current = L.layerGroup().addTo(map)
    mapInstanceRef.current = map

    setTimeout(() => map.invalidateSize(), 100)

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Update map when results change
  useEffect(() => {
    if (!mapInstanceRef.current || !markersRef.current) return

    markersRef.current.clearLayers()

    if (!locationData) return

    const { location, events } = locationData

    // Add search location marker
    const searchIcon = L.divIcon({
      html: `<div style="width: 30px; height: 30px; border-radius: 50%; background: #3b82f6; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="white" stroke="white" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
          <circle cx="12" cy="10" r="3"/>
        </svg>
      </div>`,
      className: "",
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    })

    L.marker([location.lat, location.lon], { icon: searchIcon })
      .bindPopup(`<strong>Search Location</strong><br/>Lat: ${location.lat.toFixed(4)}<br/>Lon: ${location.lon.toFixed(4)}`)
      .addTo(markersRef.current!)

    // Add radius circle
    const radiusMiles = parseFloat(radius)
    const radiusMeters = radiusMiles * 1609.34
    L.circle([location.lat, location.lon], {
      radius: radiusMeters,
      color: "#3b82f6",
      fillColor: "rgba(59, 130, 246, 0.1)",
      fillOpacity: 0.3,
      weight: 2,
      dashArray: "5, 5",
    }).addTo(markersRef.current!)

    // Add event markers
    events.forEach((event) => {
      // Determine color based on hail size
      let color = SEVERITY_COLORS.MINOR
      if (event.hail_size_inches >= 2.0) {
        color = SEVERITY_COLORS.SEVERE
      } else if (event.hail_size_inches >= 1.0) {
        color = SEVERITY_COLORS.MODERATE
      }

      const icon = L.divIcon({
        html: `<div style="width: 24px; height: 24px; border-radius: 50%; background: ${color}; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center;">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
            <path d="M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9"/>
            <polyline points="13 11 9 17 15 17 11 23"/>
          </svg>
        </div>`,
        className: "",
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      })

      // Note: We don't have exact event coordinates, so we'll place them near the search location
      // with a small offset based on distance
      const offsetLat = (Math.random() - 0.5) * 0.1
      const offsetLon = (Math.random() - 0.5) * 0.1

      L.marker([location.lat + offsetLat, location.lon + offsetLon], { icon })
        .bindPopup(`
          <div style="min-width: 180px;">
            <strong>${event.event_name}</strong><br/>
            <p><strong>Date:</strong> ${event.event_date}</p>
            <p><strong>Hail Size:</strong> ${event.hail_size_inches.toFixed(2)}"</p>
            <p><strong>Distance:</strong> ${event.distance_miles.toFixed(1)} mi</p>
          </div>
        `)
        .addTo(markersRef.current!)
    })

    // Zoom to location
    mapInstanceRef.current.setView([location.lat, location.lon], 10)

  }, [locationData, radius])

  const handleSearch = () => {
    if (!lat || !lon) return
    setSearchTriggered(true)
    refetch()
  }

  const handleUseCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLat(position.coords.latitude.toFixed(6))
          setLon(position.coords.longitude.toFixed(6))
        },
        (error) => {
          console.error("Geolocation error:", error)
          alert("Unable to get your location. Please enter coordinates manually.")
        }
      )
    }
  }

  // Sample locations for quick testing
  const sampleLocations = [
    { name: "Dallas, TX", lat: "32.7767", lon: "-96.7970" },
    { name: "Oklahoma City, OK", lat: "35.4676", lon: "-97.5164" },
    { name: "Wichita, KS", lat: "37.6872", lon: "-97.3301" },
    { name: "Denver, CO", lat: "39.7392", lon: "-104.9903" },
    { name: "Omaha, NE", lat: "41.2565", lon: "-95.9345" },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Hail Lookup"
        description="Check if a location was affected by hail storms"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Search Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Search Location
              </CardTitle>
              <CardDescription>
                Enter coordinates or use a sample location
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Coordinates */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="lat">Latitude</Label>
                  <Input
                    id="lat"
                    placeholder="e.g., 32.7767"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lon">Longitude</Label>
                  <Input
                    id="lon"
                    placeholder="e.g., -96.7970"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                  />
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={handleUseCurrentLocation}
              >
                <MapPin className="h-4 w-4 mr-2" />
                Use My Location
              </Button>

              {/* Sample Locations */}
              <div className="space-y-2">
                <Label>Quick Select</Label>
                <div className="flex flex-wrap gap-2">
                  {sampleLocations.map((loc) => (
                    <Button
                      key={loc.name}
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setLat(loc.lat)
                        setLon(loc.lon)
                      }}
                    >
                      {loc.name}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Search Options */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Years to Search</Label>
                  <Select value={years} onValueChange={setYears}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Last 1 year</SelectItem>
                      <SelectItem value="3">Last 3 years</SelectItem>
                      <SelectItem value="5">Last 5 years</SelectItem>
                      <SelectItem value="10">Last 10 years</SelectItem>
                      <SelectItem value="15">Since 2011</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Search Radius</Label>
                  <Select value={radius} onValueChange={setRadius}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 mile</SelectItem>
                      <SelectItem value="3">3 miles</SelectItem>
                      <SelectItem value="5">5 miles</SelectItem>
                      <SelectItem value="10">10 miles</SelectItem>
                      <SelectItem value="25">25 miles</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                className="w-full"
                onClick={handleSearch}
                disabled={!lat || !lon || isLoading}
              >
                {isLoading ? (
                  "Searching..."
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Check for Hail History
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Summary */}
          {locationData && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2">
                  {locationData.was_hit ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-red-500" />
                      <span className="text-red-600">Location Was Hit</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-5 w-5 text-green-500" />
                      <span className="text-green-600">No Hail Found</span>
                    </>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {locationData.was_hit ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="bg-red-50 rounded-lg p-3">
                        <div className="text-2xl font-bold text-red-600">
                          {locationData.summary.total_events}
                        </div>
                        <div className="text-xs text-muted-foreground">Total Events</div>
                      </div>
                      <div className="bg-orange-50 rounded-lg p-3">
                        <div className="text-2xl font-bold text-orange-600">
                          {locationData.summary.max_hail_size.toFixed(2)}"
                        </div>
                        <div className="text-xs text-muted-foreground">Max Hail Size</div>
                      </div>
                    </div>

                    {locationData.summary.most_recent && (
                      <div className="text-sm">
                        <strong>Most Recent:</strong> {locationData.summary.most_recent}
                      </div>
                    )}

                    {/* Events by Year */}
                    {Object.keys(locationData.summary.by_year).length > 0 && (
                      <div>
                        <div className="text-sm font-medium mb-2">Events by Year:</div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(locationData.summary.by_year).map(([year, count]) => (
                            <Badge key={year} variant="secondary">
                              {year}: {count}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => generateReportMutation.mutate()}
                      disabled={generateReportMutation.isPending}
                    >
                      {generateReportMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Generating PDF...
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-2" />
                          Download PDF Report
                        </>
                      )}
                    </Button>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    No hail events found within {radius} miles of this location
                    in the last {years} years.
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Map and Event List */}
        <div className="lg:col-span-2 space-y-4">
          {/* Map */}
          <Card>
            <CardContent className="p-0">
              <div
                ref={mapRef}
                className="h-[400px] rounded-lg"
                style={{ minHeight: "400px" }}
              />
            </CardContent>
          </Card>

          {/* Event List */}
          {locationData && locationData.events.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CloudLightning className="h-5 w-5 text-orange-500" />
                  Hail Events ({locationData.events.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-[300px] overflow-y-auto">
                  {locationData.events.map((event) => (
                    <div
                      key={event.id}
                      className="p-3 rounded-lg border hover:border-primary transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="font-medium">{event.event_name}</div>
                          <div className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
                            <Calendar className="h-3 w-3" />
                            {event.event_date}
                          </div>
                        </div>
                        <Badge
                          className={
                            event.hail_size_inches >= 2.0
                              ? "bg-red-100 text-red-700"
                              : event.hail_size_inches >= 1.0
                              ? "bg-orange-100 text-orange-700"
                              : "bg-yellow-100 text-yellow-700"
                          }
                        >
                          {event.hail_size_inches.toFixed(2)}" hail
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Ruler className="h-3 w-3" />
                          {event.distance_miles.toFixed(1)} mi away
                        </span>
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {event.data_source}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default HailLookupPage
