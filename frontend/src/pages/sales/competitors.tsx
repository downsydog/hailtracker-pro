/**
 * Competitor Tracking Page
 * Log and monitor competitor activity in the field
 */

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Eye,
  Plus,
  MapPin,
  Truck,
  Users,
  Flag,
  Briefcase,
  Calendar,
  Clock,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  getCompetitorActivity,
  getCompetitorSummary,
  logCompetitorActivity,
} from "@/api/elite-sales";

// Fix Leaflet default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const ACTIVITY_TYPES = [
  { value: "CANVASSING", label: "Canvassing / Door-to-Door", icon: Users },
  { value: "TRUCK_PARKED", label: "Truck Parked", icon: Truck },
  { value: "WORKING_JOB", label: "Working on Vehicle", icon: Briefcase },
  { value: "SIGN_PLACED", label: "Yard Sign Placed", icon: Flag },
];

const KNOWN_COMPETITORS = [
  "Dent Wizard",
  "PDR Nation",
  "Dent Pro",
  "Paintless Dent Repair Co",
  "Local PDR",
  "Other",
];

export function CompetitorsPage() {
  const queryClient = useQueryClient();
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const salespersonId = 1; // TODO: Get from auth context

  const [isLogOpen, setIsLogOpen] = useState(false);
  const [daysBack, setDaysBack] = useState(7);
  const [newActivity, setNewActivity] = useState({
    competitor_name: "",
    activity_type: "CANVASSING",
    notes: "",
  });

  // Fetch competitor activity
  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ["competitor-activity", daysBack],
    queryFn: () => getCompetitorActivity({ days: daysBack, limit: 100 }),
  });

  // Fetch competitor summary
  const { data: summaryData } = useQuery({
    queryKey: ["competitor-summary", daysBack],
    queryFn: () => getCompetitorSummary(daysBack),
  });

  // Log activity mutation
  const logActivityMutation = useMutation({
    mutationFn: () =>
      logCompetitorActivity({
        salesperson_id: salespersonId,
        competitor_name: newActivity.competitor_name,
        location_lat: 32.7767, // TODO: Get actual GPS location
        location_lon: -96.797,
        activity_type: newActivity.activity_type,
        notes: newActivity.notes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["competitor-activity"] });
      queryClient.invalidateQueries({ queryKey: ["competitor-summary"] });
      setIsLogOpen(false);
      setNewActivity({ competitor_name: "", activity_type: "CANVASSING", notes: "" });
    },
  });

  // Initialize map
  useEffect(() => {
    if (mapContainerRef.current && !mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current).setView([32.7767, -96.797], 12);

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

  // Update map markers when activity changes
  useEffect(() => {
    if (!mapRef.current || !activityData?.activity) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // Add markers for each activity
    activityData.activity.forEach((activity) => {
      const activityType = ACTIVITY_TYPES.find((t) => t.value === activity.activity_type);

      const iconHtml = `
        <div class="flex items-center justify-center w-8 h-8 rounded-full bg-red-500 text-white">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
            <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
          </svg>
        </div>
      `;

      const icon = L.divIcon({
        html: iconHtml,
        className: "custom-marker",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([activity.location_lat, activity.location_lon], { icon })
        .bindPopup(`
          <div class="p-2">
            <p class="font-bold text-red-500">${activity.competitor_name}</p>
            <p class="text-sm">${activityType?.label || activity.activity_type}</p>
            <p class="text-xs text-gray-500">${new Date(activity.spotted_at).toLocaleString()}</p>
            ${activity.notes ? `<p class="text-sm mt-1">${activity.notes}</p>` : ""}
          </div>
        `)
        .addTo(mapRef.current!);

      markersRef.current.push(marker);
    });

    // Fit bounds if we have markers
    if (markersRef.current.length > 0) {
      const coordinates = activityData.activity.map(
        (a) => [a.location_lat, a.location_lon] as [number, number]
      );
      mapRef.current.fitBounds(coordinates, { padding: [50, 50] });
    }
  }, [activityData]);

  const getActivityIcon = (type: string) => {
    const activity = ACTIVITY_TYPES.find((t) => t.value === type);
    if (!activity) return <Eye className="h-4 w-4" />;
    const Icon = activity.icon;
    return <Icon className="h-4 w-4" />;
  };

  const totalSightings = summaryData?.competitors.reduce((sum, c) => sum + c.total_sightings, 0) || 0;
  const uniqueCompetitors = summaryData?.competitors.length || 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Competitor Tracking</h1>
          <p className="text-muted-foreground">
            Monitor and log competitor activity in your territory
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={String(daysBack)} onValueChange={(v) => setDaysBack(parseInt(v))}>
            <SelectTrigger className="w-[150px]">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="14">Last 14 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
          <Dialog open={isLogOpen} onOpenChange={setIsLogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Log Competitor
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Log Competitor Activity</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Competitor Name *</Label>
                  <Select
                    value={newActivity.competitor_name}
                    onValueChange={(v) => setNewActivity({ ...newActivity, competitor_name: v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select competitor" />
                    </SelectTrigger>
                    <SelectContent>
                      {KNOWN_COMPETITORS.map((comp) => (
                        <SelectItem key={comp} value={comp}>
                          {comp}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Activity Type *</Label>
                  <Select
                    value={newActivity.activity_type}
                    onValueChange={(v) => setNewActivity({ ...newActivity, activity_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTIVITY_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          <div className="flex items-center gap-2">
                            <type.icon className="h-4 w-4" />
                            {type.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={newActivity.notes}
                    onChange={(e) => setNewActivity({ ...newActivity, notes: e.target.value })}
                    placeholder="Description of what you saw..."
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsLogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => logActivityMutation.mutate()}
                  disabled={!newActivity.competitor_name || logActivityMutation.isPending}
                >
                  <AlertTriangle className="h-4 w-4 mr-2" />
                  Log Activity
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-red-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Sightings</p>
                <p className="text-2xl font-bold text-red-500">{totalSightings}</p>
              </div>
              <Eye className="h-6 w-6 text-red-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Competitors</p>
                <p className="text-2xl font-bold">{uniqueCompetitors}</p>
              </div>
              <Users className="h-6 w-6 text-purple-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Period</p>
                <p className="text-2xl font-bold">{daysBack} days</p>
              </div>
              <Calendar className="h-6 w-6 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg/Day</p>
                <p className="text-2xl font-bold">
                  {(totalSightings / daysBack).toFixed(1)}
                </p>
              </div>
              <TrendingUp className="h-6 w-6 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Map */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Activity Map</CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={mapContainerRef} className="h-[400px] rounded-lg border" />
          </CardContent>
        </Card>

        {/* Competitor Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Competitor Summary</CardTitle>
          </CardHeader>
          <CardContent>
            {summaryData?.competitors && summaryData.competitors.length > 0 ? (
              <div className="space-y-3">
                {summaryData.competitors.map((comp, index) => (
                  <div
                    key={comp.competitor_name}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white ${
                          index === 0
                            ? "bg-red-500"
                            : index === 1
                            ? "bg-orange-500"
                            : "bg-gray-500"
                        }`}
                      >
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium">{comp.competitor_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {comp.active_days} active days
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-red-500">{comp.total_sightings}</p>
                      <p className="text-xs text-muted-foreground">
                        Last: {new Date(comp.last_seen).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Eye className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No competitor activity logged</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {activityLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : activityData?.activity && activityData.activity.length > 0 ? (
            <div className="space-y-3">
              {activityData.activity.slice(0, 10).map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-full bg-red-500/10 text-red-500">
                      {getActivityIcon(activity.activity_type)}
                    </div>
                    <div>
                      <p className="font-medium text-red-500">{activity.competitor_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {ACTIVITY_TYPES.find((t) => t.value === activity.activity_type)?.label ||
                          activity.activity_type}
                      </p>
                      {activity.notes && (
                        <p className="text-sm mt-1">{activity.notes}</p>
                      )}
                    </div>
                  </div>
                  <div className="text-right text-sm text-muted-foreground">
                    <p className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(activity.spotted_at).toLocaleString()}
                    </p>
                    <p className="flex items-center gap-1 mt-1">
                      <MapPin className="h-3 w-3" />
                      {activity.location_lat.toFixed(4)}, {activity.location_lon.toFixed(4)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Eye className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No competitor activity in the last {daysBack} days</p>
              <Button variant="link" onClick={() => setIsLogOpen(true)}>
                Log your first sighting
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default CompetitorsPage;
