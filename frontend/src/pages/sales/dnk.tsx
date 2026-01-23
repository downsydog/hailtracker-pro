/**
 * Do Not Knock Management Page
 * Manage addresses that should not be canvassed
 */

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Ban,
  Plus,
  MapPin,
  Search,
  Trash2,
  AlertTriangle,
  User,
  Shield,
  Users,
  Clock,
} from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { getDNKList, addDNK, removeDNK } from "@/api/elite-sales";

// Fix Leaflet default marker icon
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const DNK_REASONS = [
  { value: "NO_SOLICITING", label: "No Soliciting Sign", icon: Ban },
  { value: "REQUESTED", label: "Customer Requested", icon: User },
  { value: "AGGRESSIVE", label: "Hostile/Aggressive", icon: AlertTriangle },
  { value: "COMPETITOR", label: "Working with Competitor", icon: Users },
];

export function DNKPage() {
  const queryClient = useQueryClient();
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const salespersonId = 1; // TODO: Get from auth context

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [reasonFilter, setReasonFilter] = useState("all");
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [newDNK, setNewDNK] = useState({
    address: "",
    reason: "NO_SOLICITING",
    notes: "",
  });

  // Fetch DNK list
  const { data, isLoading } = useQuery({
    queryKey: ["dnk-list", reasonFilter],
    queryFn: () =>
      getDNKList(100, reasonFilter !== "all" ? reasonFilter : undefined),
  });

  // Add DNK mutation
  const addDNKMutation = useMutation({
    mutationFn: () =>
      addDNK({
        address: newDNK.address,
        latitude: 32.7767, // TODO: Geocode address or get GPS
        longitude: -96.797,
        reason: newDNK.reason,
        notes: newDNK.notes || undefined,
        salesperson_id: salespersonId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dnk-list"] });
      setIsAddOpen(false);
      setNewDNK({ address: "", reason: "NO_SOLICITING", notes: "" });
    },
  });

  // Remove DNK mutation
  const removeDNKMutation = useMutation({
    mutationFn: (id: number) => removeDNK(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dnk-list"] });
      setDeleteConfirmId(null);
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

  // Update map markers when DNK list changes
  useEffect(() => {
    if (!mapRef.current || !data?.dnk_list) return;

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    // Add markers for each DNK entry
    data.dnk_list.forEach((entry) => {
      const reason = DNK_REASONS.find((r) => r.value === entry.reason);

      const iconHtml = `
        <div class="flex items-center justify-center w-8 h-8 rounded-full bg-red-500 text-white border-2 border-white shadow-lg">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
          </svg>
        </div>
      `;

      const icon = L.divIcon({
        html: iconHtml,
        className: "custom-marker",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([entry.latitude, entry.longitude], { icon })
        .bindPopup(`
          <div class="p-2">
            <p class="font-bold text-red-500">Do Not Knock</p>
            <p class="text-sm">${entry.address}</p>
            <p class="text-xs text-gray-500">${reason?.label || entry.reason}</p>
            ${entry.notes ? `<p class="text-sm mt-1 text-gray-600">${entry.notes}</p>` : ""}
          </div>
        `)
        .addTo(mapRef.current!);

      markersRef.current.push(marker);
    });

    // Fit bounds if we have markers
    if (markersRef.current.length > 0) {
      const coordinates = data.dnk_list.map(
        (e) => [e.latitude, e.longitude] as [number, number]
      );
      mapRef.current.fitBounds(coordinates, { padding: [50, 50] });
    }
  }, [data]);

  // Filter DNK entries by search
  const filteredDNK =
    data?.dnk_list.filter(
      (entry) =>
        entry.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
        entry.notes?.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

  const getReasonIcon = (reason: string) => {
    const r = DNK_REASONS.find((x) => x.value === reason);
    if (!r) return <Ban className="h-4 w-4" />;
    const Icon = r.icon;
    return <Icon className="h-4 w-4" />;
  };

  const getReasonBadgeColor = (reason: string) => {
    switch (reason) {
      case "NO_SOLICITING":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      case "REQUESTED":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "AGGRESSIVE":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      case "COMPETITOR":
        return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      default:
        return "";
    }
  };

  // Stats by reason
  const statsByReason = DNK_REASONS.map((reason) => ({
    ...reason,
    count: data?.dnk_list.filter((e) => e.reason === reason.value).length || 0,
  }));

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Do Not Knock List</h1>
          <p className="text-muted-foreground">
            Manage addresses that should not be canvassed
          </p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive">
              <Plus className="h-4 w-4 mr-2" />
              Add DNK
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Do Not Knock Address</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Address *</Label>
                <Input
                  value={newDNK.address}
                  onChange={(e) => setNewDNK({ ...newDNK, address: e.target.value })}
                  placeholder="123 Main St, Dallas, TX"
                />
              </div>
              <div className="space-y-2">
                <Label>Reason *</Label>
                <Select
                  value={newDNK.reason}
                  onValueChange={(v) => setNewDNK({ ...newDNK, reason: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DNK_REASONS.map((reason) => (
                      <SelectItem key={reason.value} value={reason.value}>
                        <div className="flex items-center gap-2">
                          <reason.icon className="h-4 w-4" />
                          {reason.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea
                  value={newDNK.notes}
                  onChange={(e) => setNewDNK({ ...newDNK, notes: e.target.value })}
                  placeholder="Additional details..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => addDNKMutation.mutate()}
                disabled={!newDNK.address || addDNKMutation.isPending}
              >
                <Ban className="h-4 w-4 mr-2" />
                Add to DNK List
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats by Reason */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statsByReason.map((stat) => (
          <Card key={stat.value}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-2xl font-bold">{stat.count}</p>
                </div>
                <stat.icon className="h-6 w-6 text-red-500" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Map */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <MapPin className="h-5 w-5 text-red-500" />
              DNK Map
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div ref={mapContainerRef} className="h-[400px] rounded-lg border" />
          </CardContent>
        </Card>

        {/* DNK List */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Address List</CardTitle>
              <Badge variant="destructive">{data?.count || 0} addresses</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Search and Filter */}
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search addresses..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={reasonFilter} onValueChange={setReasonFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="Filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Reasons</SelectItem>
                  {DNK_REASONS.map((reason) => (
                    <SelectItem key={reason.value} value={reason.value}>
                      {reason.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* List */}
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">Loading...</div>
            ) : filteredDNK.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Ban className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No DNK addresses found</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {filteredDNK.map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-start justify-between p-3 rounded-lg border"
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-full bg-red-500/10 text-red-500">
                        {getReasonIcon(entry.reason)}
                      </div>
                      <div>
                        <p className="font-medium">{entry.address}</p>
                        <Badge
                          variant="outline"
                          className={`text-xs mt-1 ${getReasonBadgeColor(entry.reason)}`}
                        >
                          {DNK_REASONS.find((r) => r.value === entry.reason)?.label ||
                            entry.reason}
                        </Badge>
                        {entry.notes && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {entry.notes}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(entry.added_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
                      onClick={() => setDeleteConfirmId(entry.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* DNK Guidelines */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            DNK Guidelines
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {DNK_REASONS.map((reason) => (
              <div key={reason.value} className="p-4 rounded-lg border">
                <div className="flex items-center gap-2 mb-2">
                  <reason.icon className="h-5 w-5 text-red-500" />
                  <p className="font-medium">{reason.label}</p>
                </div>
                <p className="text-sm text-muted-foreground">
                  {reason.value === "NO_SOLICITING" &&
                    "Visible 'No Soliciting' sign posted. Respect the homeowner's wishes."}
                  {reason.value === "REQUESTED" &&
                    "Homeowner explicitly asked not to be contacted again."}
                  {reason.value === "AGGRESSIVE" &&
                    "Hostile or threatening behavior. Do not return for safety reasons."}
                  {reason.value === "COMPETITOR" &&
                    "Already working with a competitor. May revisit after 30 days."}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteConfirmId !== null}
        onOpenChange={() => setDeleteConfirmId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove from DNK List?</AlertDialogTitle>
            <AlertDialogDescription>
              This will allow this address to appear on canvassing routes again. Are you
              sure you want to remove it from the Do Not Knock list?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-500 hover:bg-red-600"
              onClick={() => deleteConfirmId && removeDNKMutation.mutate(deleteConfirmId)}
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default DNKPage;
