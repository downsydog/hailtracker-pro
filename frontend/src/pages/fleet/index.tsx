import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { fleetLocationsApi } from "@/api/fleet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import {
  RefreshCw,
  Search,
  Car,
  DollarSign,
  Building2,
} from "lucide-react"

// Category styles
const CATEGORY_STYLES: Record<string, { icon: string; color: string; name: string }> = {
  car_dealership: { icon: "🚗", color: "#4CAF50", name: "Car Dealership" },
  rental_car: { icon: "🚙", color: "#2196F3", name: "Rental Car" },
  parking_structure: { icon: "🅿️", color: "#9C27B0", name: "Parking Structure" },
  municipal: { icon: "🏛️", color: "#F44336", name: "Municipal" },
  utility: { icon: "⚡", color: "#FFEB3B", name: "Utility" },
  service_company: { icon: "🔨", color: "#795548", name: "Service Company" },
  delivery: { icon: "📦", color: "#607D8B", name: "Delivery" },
  body_shop: { icon: "🔧", color: "#FF9800", name: "Body Shop" },
  golf_course: { icon: "⛳", color: "#8BC34A", name: "Golf Course" },
  apartment: { icon: "🏘️", color: "#00BCD4", name: "Apartment" },
  school: { icon: "🏫", color: "#673AB7", name: "School" },
  hospital: { icon: "🏥", color: "#E91E63", name: "Hospital" },
  hotel: { icon: "🏨", color: "#009688", name: "Hotel" },
  event_venue: { icon: "🎪", color: "#FF5722", name: "Event Venue" },
}


export function FleetMapPage() {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.LayerGroup | null>(null)

  const [search, setSearch] = useState("")
  const [minVehicles, setMinVehicles] = useState(0)
  const [selectedCategory, setSelectedCategory] = useState<string>("all")

  // Fetch fleet locations from API
  const { data: locationsData, refetch, isLoading } = useQuery({
    queryKey: ["fleet-locations", selectedCategory, minVehicles],
    queryFn: () =>
      fleetLocationsApi.getLocations({
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        min_vehicles: minVehicles > 0 ? minVehicles : undefined,
        per_page: 500,
      }),
  })

  const locations = locationsData?.locations || []

  // Filter locations by search only (category and minVehicles are handled by API)
  const filteredLocations = locations.filter((loc) => {
    if (search) {
      const searchLower = search.toLowerCase()
      if (
        !loc.name.toLowerCase().includes(searchLower) &&
        !loc.city.toLowerCase().includes(searchLower)
      )
        return false
    }
    return true
  })

  // Calculate stats from filtered data
  const totalVehicles = filteredLocations.reduce((sum, loc) => sum + loc.estimated_vehicles, 0)
  const stats = {
    totalLocations: filteredLocations.length,
    totalVehicles,
    potentialRevenue: totalVehicles * 1500,
  }

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    const map = L.map(mapRef.current, {
      center: [32.7767, -96.797],
      zoom: 10,
      zoomControl: true,
    })

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap, &copy; CARTO",
      maxZoom: 19,
    }).addTo(map)

    markersRef.current = L.layerGroup().addTo(map)

    setTimeout(() => {
      map.invalidateSize()
    }, 100)

    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Render markers
  useEffect(() => {
    if (!markersRef.current) return

    markersRef.current.clearLayers()

    filteredLocations.forEach((loc) => {
      const style = CATEGORY_STYLES[loc.category] || { icon: "📍", color: "#888", name: loc.category }

      let size = 28
      if (loc.estimated_vehicles >= 500) size = 44
      else if (loc.estimated_vehicles >= 200) size = 36

      const icon = L.divIcon({
        html: `<div style="width: ${size}px; height: ${size}px; border-radius: 50%; background: ${style.color}; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; font-size: ${size * 0.4}px;">${style.icon}</div>`,
        className: "",
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
      })

      const marker = L.marker([loc.lat, loc.lon], { icon })

      const revenue = loc.estimated_vehicles * 1500

      marker.bindPopup(`
        <div style="min-width: 240px;">
          <div style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb;">
            <strong style="font-size: 14px;">${style.icon} ${loc.name}</strong>
            <p style="color: #6b7280; font-size: 12px; margin: 4px 0 0 0;">${style.name}</p>
          </div>
          <div style="padding: 12px 16px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
              <div style="text-align: center; padding: 8px; background: #f3f4f6; border-radius: 6px;">
                <div style="font-size: 18px; font-weight: bold; color: #2563eb;">~${loc.estimated_vehicles.toLocaleString()}</div>
                <div style="font-size: 11px; color: #6b7280;">Vehicles</div>
              </div>
              <div style="text-align: center; padding: 8px; background: #f3f4f6; border-radius: 6px;">
                <div style="font-size: 18px; font-weight: bold; color: #16a34a;">$${(revenue / 1000).toFixed(0)}K</div>
                <div style="font-size: 11px; color: #6b7280;">Potential</div>
              </div>
            </div>
            <p style="color: #6b7280; font-size: 12px; margin: 0;">${loc.city}, ${loc.state}</p>
          </div>
          <div style="padding: 12px 16px; border-top: 1px solid #e5e7eb; display: flex; gap: 8px;">
            <button onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${loc.lat},${loc.lon}')" style="flex: 1; padding: 8px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">
              Navigate
            </button>
          </div>
        </div>
      `)

      markersRef.current?.addLayer(marker)
    })
  }, [filteredLocations])

  const formatCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  const getGrade = (vehicles: number) => {
    if (vehicles >= 300) return { grade: "A", color: "bg-green-500" }
    if (vehicles >= 150) return { grade: "B", color: "bg-blue-500" }
    if (vehicles >= 75) return { grade: "C", color: "bg-yellow-500" }
    return { grade: "D", color: "bg-red-500" }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Fleet Intelligence"
          description="Find high-value fleet locations for hail damage repair opportunities"
        />
        <Button variant="outline" size="icon" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Locations</p>
                <p className="text-2xl font-bold">{stats.totalLocations}</p>
              </div>
              <Building2 className="h-8 w-8 text-blue-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Vehicles</p>
                <p className="text-2xl font-bold">
                  {(stats.totalVehicles / 1000).toFixed(1)}K
                </p>
              </div>
              <Car className="h-8 w-8 text-green-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Potential</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(stats.potentialRevenue)}
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-yellow-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {/* Sidebar */}
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search locations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Filters */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Category</label>
                <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {Object.entries(CATEGORY_STYLES).map(([key, style]) => (
                      <SelectItem key={key} value={key}>
                        {style.icon} {style.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">
                  Min Vehicles: {minVehicles}+
                </label>
                <Slider
                  value={[minVehicles]}
                  onValueChange={(values: number[]) => setMinVehicles(values[0])}
                  max={500}
                  step={10}
                />
              </div>
            </CardContent>
          </Card>

          {/* Results List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">
                Top Locations ({filteredLocations.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="max-h-[400px] overflow-y-auto">
                {filteredLocations
                  .sort((a, b) => b.estimated_vehicles - a.estimated_vehicles)
                  .slice(0, 20)
                  .map((loc) => {
                    const style = CATEGORY_STYLES[loc.category] || { icon: "📍", name: loc.category }
                    const grade = getGrade(loc.estimated_vehicles)

                    return (
                      <div
                        key={loc.id}
                        className="flex items-center justify-between p-3 border-b hover:bg-muted/50 cursor-pointer"
                        onClick={() => {
                          mapInstanceRef.current?.setView([loc.lat, loc.lon], 14)
                        }}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-lg">{style.icon}</span>
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate">
                              {loc.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {loc.city} • {loc.estimated_vehicles} vehicles
                            </p>
                          </div>
                        </div>
                        <Badge className={`${grade.color} text-white text-xs`}>
                          {grade.grade}
                        </Badge>
                      </div>
                    )
                  })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Map */}
        <div className="lg:col-span-3">
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <div
                ref={mapRef}
                style={{ height: "calc(100vh - 280px)", minHeight: "500px" }}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
