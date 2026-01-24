/**
 * Sales Routes Page
 * Optimized canvassing route with map and stops list
 */

import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Navigation,
  MapPin,
  RefreshCw,
  Ban,
  CheckCircle,
  SkipForward,
  Clock,
  Car,
  Home,
  Settings,
  CloudLightning,
  Zap,
} from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { optimizeRoute, generateStormRoute, type CanvassingRoute } from "@/api/elite-sales";
import { hailEventsApi, HailEvent } from "@/api/weather";

// Fix Leaflet default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

export function SalesRoutesPage() {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const swathLayerRef = useRef<L.GeoJSON | null>(null);
  const { user } = useAuth();

  // Get the current user's ID for the salesperson ID
  const salespersonId = user?.id || 0;

  const [route, setRoute] = useState<CanvassingRoute | null>(null);
  const [currentStopIndex, setCurrentStopIndex] = useState(0);
  const [isRouteActive, setIsRouteActive] = useState(false);
  const [targetHomes, setTargetHomes] = useState(50);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [selectedStormId, setSelectedStormId] = useState<string>("");
  const [activeStorm, setActiveStorm] = useState<{
    id: number;
    event_name: string;
    event_date: string;
    max_hail_size: number;
    swath_polygon?: any;
  } | null>(null);

  // Fetch recent hail events for storm selection
  const { data: eventsData } = useQuery({
    queryKey: ["hail-events-routes"],
    queryFn: () => hailEventsApi.list({ days: 30 }),
  });

  const recentStorms: HailEvent[] = eventsData?.data?.events || [];

  // Generate route mutation
  const generateRouteMutation = useMutation({
    mutationFn: () =>
      optimizeRoute({
        salesperson_id: salespersonId,
        target_homes: targetHomes,
      }),
    onSuccess: (data) => {
      if (data.route) {
        setRoute(data.route);
        setCurrentStopIndex(0);
        setIsRouteActive(true);
        setActiveStorm(null);
      }
    },
  });

  // Generate storm-based route mutation
  const generateStormRouteMutation = useMutation({
    mutationFn: () =>
      generateStormRoute({
        salesperson_id: salespersonId,
        hail_event_id: parseInt(selectedStormId),
        target_homes: targetHomes,
      }),
    onSuccess: (data) => {
      if (data.route) {
        setRoute(data.route);
        setCurrentStopIndex(0);
        setIsRouteActive(true);
        if (data.storm) {
          setActiveStorm(data.storm);
        }
      }
    },
  });

  // Initialize map
  useEffect(() => {
    if (mapContainerRef.current && !mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current).setView([32.7767, -96.797], 14);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(mapRef.current);
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update map markers when route changes
  useEffect(() => {
    if (!mapRef.current || !route) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // Add markers for each stop
    route.stops.forEach((stop, index) => {
      const isCurrentStop = index === currentStopIndex;
      const isVisited = stop.status === "visited";
      const isDNK = stop.do_not_knock;

      // Create custom icon
      const iconHtml = `
        <div class="flex items-center justify-center w-8 h-8 rounded-full text-white font-bold text-sm
          ${isDNK ? "bg-red-500" : isVisited ? "bg-green-500" : isCurrentStop ? "bg-blue-500" : "bg-gray-400"}
          ${isCurrentStop ? "ring-4 ring-blue-300" : ""}
        ">
          ${index + 1}
        </div>
      `;

      const icon = L.divIcon({
        html: iconHtml,
        className: "custom-marker",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([stop.latitude, stop.longitude], { icon })
        .bindPopup(`
          <div class="p-2">
            <p class="font-bold">#${stop.stop_number}</p>
            <p>${stop.address}</p>
            ${isDNK ? `<p class="text-red-500">DNK: ${stop.dnk_reason}</p>` : ""}
          </div>
        `)
        .addTo(mapRef.current!);

      markersRef.current.push(marker);
    });

    // Draw route line
    const coordinates = route.stops.map((stop) => [stop.latitude, stop.longitude] as [number, number]);
    if (coordinates.length > 1) {
      L.polyline(coordinates, { color: "#3b82f6", weight: 3, opacity: 0.7 }).addTo(mapRef.current);
    }

    // Fit bounds to show all markers
    if (coordinates.length > 0) {
      mapRef.current.fitBounds(coordinates);
    }
  }, [route, currentStopIndex]);

  // Render storm swath overlay
  useEffect(() => {
    if (!mapRef.current) return;

    // Remove existing swath layer
    if (swathLayerRef.current) {
      mapRef.current.removeLayer(swathLayerRef.current);
      swathLayerRef.current = null;
    }

    if (!activeStorm?.swath_polygon) return;

    try {
      const swathGeojson = typeof activeStorm.swath_polygon === 'string'
        ? JSON.parse(activeStorm.swath_polygon)
        : activeStorm.swath_polygon;

      if (swathGeojson && (swathGeojson.type === 'Polygon' || swathGeojson.type === 'Feature')) {
        const feature = swathGeojson.type === 'Feature'
          ? swathGeojson
          : { type: 'Feature', geometry: swathGeojson, properties: {} };

        swathLayerRef.current = L.geoJSON(feature as any, {
          style: {
            color: "#ef4444",
            fillColor: "rgba(239, 68, 68, 0.2)",
            fillOpacity: 0.3,
            weight: 2,
            dashArray: "5, 5",
          },
        }).addTo(mapRef.current);

        // Fit bounds to show swath
        const bounds = swathLayerRef.current.getBounds();
        if (bounds.isValid()) {
          mapRef.current.fitBounds(bounds, { padding: [50, 50] });
        }
      }
    } catch (e) {
      console.error("Failed to render storm swath:", e);
    }
  }, [activeStorm]);

  const currentStop = route?.stops[currentStopIndex];

  const handleNavigate = () => {
    if (currentStop) {
      const url = `https://www.google.com/maps/dir/?api=1&destination=${currentStop.latitude},${currentStop.longitude}`;
      window.open(url, "_blank");
    }
  };

  const handleSkipStop = () => {
    if (route && currentStopIndex < route.stops.length - 1) {
      setCurrentStopIndex(currentStopIndex + 1);
    }
  };

  const handleCompleteStop = () => {
    if (route && currentStopIndex < route.stops.length - 1) {
      // Mark as visited
      const updatedStops = [...route.stops];
      updatedStops[currentStopIndex].status = "visited";
      setRoute({ ...route, stops: updatedStops });
      setCurrentStopIndex(currentStopIndex + 1);
    } else if (route) {
      // Route complete
      const updatedStops = [...route.stops];
      updatedStops[currentStopIndex].status = "visited";
      setRoute({ ...route, stops: updatedStops });
      setIsRouteActive(false);
    }
  };

  const completedStops = route?.stops.filter((s) => s.status === "visited").length || 0;
  const progressPercent = route ? (completedStops / route.stops.length) * 100 : 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Canvassing Route</h1>
          <p className="text-muted-foreground">
            Optimized door-to-door route for today
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="icon">
                <Settings className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Route Settings</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Target Homes</Label>
                  <Input
                    type="number"
                    value={targetHomes}
                    onChange={(e) => setTargetHomes(parseInt(e.target.value) || 50)}
                    min={10}
                    max={100}
                  />
                  <p className="text-sm text-muted-foreground">
                    Number of homes to visit (10-100)
                  </p>
                </div>
              </div>
              <Button onClick={() => setSettingsOpen(false)}>Save</Button>
            </DialogContent>
          </Dialog>
          <Button
            onClick={() => generateRouteMutation.mutate()}
            disabled={generateRouteMutation.isPending}
            variant="outline"
          >
            {generateRouteMutation.isPending ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Standard Route
          </Button>
        </div>
      </div>

      {/* Storm Route Generator */}
      <Card className="border-orange-500/30 bg-orange-500/5">
        <CardContent className="p-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <CloudLightning className="h-5 w-5 text-orange-500" />
              <span className="font-medium">Storm Route</span>
            </div>
            <div className="flex-1 min-w-[200px]">
              <Select value={selectedStormId} onValueChange={setSelectedStormId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a recent storm..." />
                </SelectTrigger>
                <SelectContent>
                  {recentStorms.map((storm) => (
                    <SelectItem key={storm.id} value={String(storm.id)}>
                      <div className="flex items-center gap-2">
                        <Zap className="h-3 w-3 text-yellow-500" />
                        <span>{storm.event_name || storm.city || `Storm #${storm.id}`}</span>
                        <span className="text-muted-foreground text-xs">
                          {storm.event_date} - {storm.max_hail_size || storm.hail_size_inches}"
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              onClick={() => generateStormRouteMutation.mutate()}
              disabled={!selectedStormId || generateStormRouteMutation.isPending}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {generateStormRouteMutation.isPending ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CloudLightning className="h-4 w-4 mr-2" />
              )}
              Generate Storm Route
            </Button>
          </div>
          {activeStorm && (
            <div className="mt-3 p-2 bg-orange-500/10 rounded-lg flex items-center gap-2">
              <Badge variant="outline" className="border-orange-500 text-orange-500">
                Active Storm
              </Badge>
              <span className="text-sm">
                {activeStorm.event_name} - {activeStorm.max_hail_size}" hail on {activeStorm.event_date}
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Route Stats */}
      {route && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <Home className="h-6 w-6 mx-auto mb-1 text-blue-500" />
              <p className="text-2xl font-bold">{route.total_stops}</p>
              <p className="text-sm text-muted-foreground">Total Stops</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <CheckCircle className="h-6 w-6 mx-auto mb-1 text-green-500" />
              <p className="text-2xl font-bold">{completedStops}</p>
              <p className="text-sm text-muted-foreground">Completed</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Car className="h-6 w-6 mx-auto mb-1 text-purple-500" />
              <p className="text-2xl font-bold">{route.total_distance_miles.toFixed(1)}</p>
              <p className="text-sm text-muted-foreground">Miles</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Clock className="h-6 w-6 mx-auto mb-1 text-orange-500" />
              <p className="text-2xl font-bold">{route.start_time}</p>
              <p className="text-sm text-muted-foreground">Start Time</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <Clock className="h-6 w-6 mx-auto mb-1 text-gray-500" />
              <p className="text-2xl font-bold">{route.estimated_completion}</p>
              <p className="text-sm text-muted-foreground">Est. Complete</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Progress Bar */}
      {route && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Route Progress</span>
              <span className="text-sm text-muted-foreground">
                {progressPercent.toFixed(0)}% complete
              </span>
            </div>
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Map */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Route Map</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              ref={mapContainerRef}
              className="h-[400px] rounded-lg border"
            />
          </CardContent>
        </Card>

        {/* Current Stop / Stops List */}
        <div className="space-y-4">
          {/* Current Stop Card */}
          {currentStop && isRouteActive && (
            <Card className="border-blue-500">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <MapPin className="h-5 w-5 text-blue-500" />
                    Current Stop
                  </CardTitle>
                  <Badge>#{currentStop.stop_number} of {route?.total_stops}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-lg font-medium">{currentStop.address}</p>
                  <p className="text-sm text-muted-foreground">
                    ETA: {currentStop.estimated_time}
                  </p>
                </div>

                {currentStop.do_not_knock && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2">
                    <Ban className="h-5 w-5 text-red-500" />
                    <div>
                      <p className="font-medium text-red-500">Do Not Knock</p>
                      <p className="text-sm">{currentStop.dnk_reason}</p>
                    </div>
                  </div>
                )}

                {currentStop.property_data && (
                  <div className="p-3 bg-muted rounded-lg space-y-2">
                    <p className="font-medium text-sm">Property Intel</p>
                    {currentStop.property_data.owner_name && (
                      <p className="text-sm">
                        Owner: {currentStop.property_data.owner_name}
                      </p>
                    )}
                    {currentStop.property_data.vehicles_registered && currentStop.property_data.vehicles_registered.length > 0 && (
                      <div className="text-sm">
                        <span className="text-muted-foreground">Vehicles: </span>
                        {currentStop.property_data.vehicles_registered.map((v, i) => (
                          <span key={i}>
                            {v.year} {v.make} {v.model}
                            {i < currentStop.property_data!.vehicles_registered!.length - 1 && ", "}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex gap-2">
                  <Button className="flex-1" onClick={handleNavigate}>
                    <Navigation className="h-4 w-4 mr-2" />
                    Navigate
                  </Button>
                  <Button variant="outline" onClick={handleSkipStop}>
                    <SkipForward className="h-4 w-4 mr-2" />
                    Skip
                  </Button>
                  <Button variant="default" className="bg-green-500 hover:bg-green-600" onClick={handleCompleteStop}>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Done
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Stops List */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">All Stops</CardTitle>
            </CardHeader>
            <CardContent>
              {!route ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Navigation className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No route generated</p>
                  <p className="text-sm">Click "Generate Route" to create an optimized canvassing route</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {route.stops.map((stop, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition-colors
                        ${index === currentStopIndex ? "border-blue-500 bg-blue-500/5" : ""}
                        ${stop.status === "visited" ? "bg-green-500/5 border-green-500/20" : ""}
                        ${stop.do_not_knock ? "bg-red-500/5 border-red-500/20" : ""}
                      `}
                      onClick={() => setCurrentStopIndex(index)}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm
                            ${stop.do_not_knock ? "bg-red-500" : stop.status === "visited" ? "bg-green-500" : index === currentStopIndex ? "bg-blue-500" : "bg-gray-400"}
                          `}
                        >
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{stop.address}</p>
                          <p className="text-xs text-muted-foreground">{stop.estimated_time}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {stop.do_not_knock && (
                          <Badge variant="destructive" className="text-xs">DNK</Badge>
                        )}
                        {stop.status === "visited" && (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default SalesRoutesPage;
