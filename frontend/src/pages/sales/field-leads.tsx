/**
 * Field Leads Page
 * Manage leads captured during door-to-door canvassing
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Plus,
  Upload,
  MapPin,
  Phone,
  Mail,
  Flame,
  Sun,
  Snowflake,
  MoreVertical,
  RefreshCw,
  CheckCircle,
  Clock,
  Search,
  Filter,
  Car,
} from "lucide-react";
import {
  getFieldLeads,
  createFieldLead,
  syncLeadToCRM,
  bulkSyncLeads,
} from "@/api/elite-sales";

export function FieldLeadsPage() {
  const queryClient = useQueryClient();
  const salespersonId = 1; // TODO: Get from auth context

  const [qualityFilter, setQualityFilter] = useState<string>("all");
  const [syncedFilter, setSyncedFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isAddLeadOpen, setIsAddLeadOpen] = useState(false);

  // Form state for new lead
  const [newLead, setNewLead] = useState({
    customer_name: "",
    phone: "",
    email: "",
    address: "",
    lead_quality: "WARM",
    notes: "",
    damage_description: "",
    vehicle_year: "",
    vehicle_make: "",
    vehicle_model: "",
  });

  // Fetch leads
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["field-leads", salespersonId, qualityFilter, syncedFilter],
    queryFn: () =>
      getFieldLeads({
        salesperson_id: salespersonId,
        quality: qualityFilter !== "all" ? qualityFilter : undefined,
        synced: syncedFilter !== "all" ? syncedFilter === "synced" : undefined,
        limit: 100,
      }),
  });

  // Create lead mutation
  const createLeadMutation = useMutation({
    mutationFn: () =>
      createFieldLead({
        salesperson_id: salespersonId,
        latitude: 0, // TODO: Get actual GPS location
        longitude: 0,
        address: newLead.address,
        customer_name: newLead.customer_name,
        phone: newLead.phone || undefined,
        email: newLead.email || undefined,
        lead_quality: newLead.lead_quality,
        notes: newLead.notes || undefined,
        damage_description: newLead.damage_description || undefined,
        vehicle_info: newLead.vehicle_year
          ? {
              year: parseInt(newLead.vehicle_year),
              make: newLead.vehicle_make,
              model: newLead.vehicle_model,
            }
          : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["field-leads"] });
      setIsAddLeadOpen(false);
      resetNewLeadForm();
    },
  });

  // Sync lead mutation
  const syncLeadMutation = useMutation({
    mutationFn: (leadId: number) => syncLeadToCRM(leadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["field-leads"] });
    },
  });

  // Bulk sync mutation
  const bulkSyncMutation = useMutation({
    mutationFn: (leadIds: number[]) => bulkSyncLeads(leadIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["field-leads"] });
    },
  });

  const resetNewLeadForm = () => {
    setNewLead({
      customer_name: "",
      phone: "",
      email: "",
      address: "",
      lead_quality: "WARM",
      notes: "",
      damage_description: "",
      vehicle_year: "",
      vehicle_make: "",
      vehicle_model: "",
    });
  };

  // Filter leads by search query
  const filteredLeads =
    data?.leads.filter(
      (lead) =>
        lead.customer_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.address?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.phone?.includes(searchQuery)
    ) || [];

  // Stats
  const totalLeads = data?.leads.length || 0;
  const hotLeads = data?.leads.filter((l) => l.lead_quality === "HOT").length || 0;
  const warmLeads = data?.leads.filter((l) => l.lead_quality === "WARM").length || 0;
  const syncedLeads = data?.leads.filter((l) => l.synced_to_crm).length || 0;
  const pendingLeads = data?.leads.filter((l) => !l.synced_to_crm) || [];

  const getQualityIcon = (quality: string) => {
    switch (quality) {
      case "HOT":
        return <Flame className="h-4 w-4 text-orange-500" />;
      case "WARM":
        return <Sun className="h-4 w-4 text-yellow-500" />;
      case "COLD":
        return <Snowflake className="h-4 w-4 text-blue-500" />;
      default:
        return null;
    }
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case "HOT":
        return "bg-orange-500";
      case "WARM":
        return "bg-yellow-500";
      case "COLD":
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Field Leads</h1>
          <p className="text-muted-foreground">
            Leads captured during door-to-door canvassing
          </p>
        </div>
        <div className="flex gap-2">
          {pendingLeads.length > 0 && (
            <Button
              variant="outline"
              onClick={() => bulkSyncMutation.mutate(pendingLeads.map((l) => l.id))}
              disabled={bulkSyncMutation.isPending}
            >
              <Upload className="h-4 w-4 mr-2" />
              Sync All ({pendingLeads.length})
            </Button>
          )}
          <Dialog open={isAddLeadOpen} onOpenChange={setIsAddLeadOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Lead
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Add Field Lead</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Customer Name *</Label>
                  <Input
                    value={newLead.customer_name}
                    onChange={(e) =>
                      setNewLead({ ...newLead, customer_name: e.target.value })
                    }
                    placeholder="John Smith"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Phone</Label>
                    <Input
                      value={newLead.phone}
                      onChange={(e) =>
                        setNewLead({ ...newLead, phone: e.target.value })
                      }
                      placeholder="(555) 123-4567"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input
                      value={newLead.email}
                      onChange={(e) =>
                        setNewLead({ ...newLead, email: e.target.value })
                      }
                      placeholder="john@email.com"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Address *</Label>
                  <Input
                    value={newLead.address}
                    onChange={(e) =>
                      setNewLead({ ...newLead, address: e.target.value })
                    }
                    placeholder="123 Main St, Dallas, TX"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Lead Quality</Label>
                  <div className="flex gap-2">
                    {["HOT", "WARM", "COLD"].map((quality) => (
                      <Button
                        key={quality}
                        type="button"
                        variant={newLead.lead_quality === quality ? "default" : "outline"}
                        className={`flex-1 ${
                          newLead.lead_quality === quality
                            ? quality === "HOT"
                              ? "bg-orange-500 hover:bg-orange-600"
                              : quality === "WARM"
                              ? "bg-yellow-500 hover:bg-yellow-600 text-black"
                              : "bg-blue-500 hover:bg-blue-600"
                            : ""
                        }`}
                        onClick={() => setNewLead({ ...newLead, lead_quality: quality })}
                      >
                        {getQualityIcon(quality)}
                        <span className="ml-1">{quality}</span>
                      </Button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="space-y-2">
                    <Label>Year</Label>
                    <Input
                      value={newLead.vehicle_year}
                      onChange={(e) =>
                        setNewLead({ ...newLead, vehicle_year: e.target.value })
                      }
                      placeholder="2022"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Make</Label>
                    <Input
                      value={newLead.vehicle_make}
                      onChange={(e) =>
                        setNewLead({ ...newLead, vehicle_make: e.target.value })
                      }
                      placeholder="Toyota"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Model</Label>
                    <Input
                      value={newLead.vehicle_model}
                      onChange={(e) =>
                        setNewLead({ ...newLead, vehicle_model: e.target.value })
                      }
                      placeholder="Camry"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={newLead.notes}
                    onChange={(e) =>
                      setNewLead({ ...newLead, notes: e.target.value })
                    }
                    placeholder="Damage description, details..."
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsAddLeadOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={() => createLeadMutation.mutate()}
                  disabled={
                    !newLead.customer_name || !newLead.address || createLeadMutation.isPending
                  }
                >
                  {createLeadMutation.isPending ? "Saving..." : "Save Lead"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Leads</p>
                <p className="text-2xl font-bold">{totalLeads}</p>
              </div>
              <MapPin className="h-6 w-6 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-orange-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Hot Leads</p>
                <p className="text-2xl font-bold text-orange-500">{hotLeads}</p>
              </div>
              <Flame className="h-6 w-6 text-orange-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Warm Leads</p>
                <p className="text-2xl font-bold text-yellow-500">{warmLeads}</p>
              </div>
              <Sun className="h-6 w-6 text-yellow-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Synced to CRM</p>
                <p className="text-2xl font-bold text-green-500">{syncedLeads}</p>
              </div>
              <CheckCircle className="h-6 w-6 text-green-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search leads..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={qualityFilter} onValueChange={setQualityFilter}>
              <SelectTrigger className="w-[150px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Quality" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Quality</SelectItem>
                <SelectItem value="HOT">Hot</SelectItem>
                <SelectItem value="WARM">Warm</SelectItem>
                <SelectItem value="COLD">Cold</SelectItem>
              </SelectContent>
            </Select>
            <Select value={syncedFilter} onValueChange={setSyncedFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Sync Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="synced">Synced</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Leads List */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground">Loading leads...</div>
          ) : filteredLeads.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <MapPin className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No leads found</p>
              <Button variant="link" onClick={() => setIsAddLeadOpen(true)}>
                Add your first lead
              </Button>
            </div>
          ) : (
            <div className="divide-y">
              {filteredLeads.map((lead) => (
                <div
                  key={lead.id}
                  className="p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-3 h-3 rounded-full mt-1.5 ${getQualityColor(
                          lead.lead_quality
                        )}`}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{lead.customer_name}</p>
                          {getQualityIcon(lead.lead_quality)}
                          {lead.synced_to_crm ? (
                            <Badge variant="default" className="text-xs">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Synced
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">
                              <Clock className="h-3 w-3 mr-1" />
                              Pending
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {lead.address}
                        </p>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          {lead.phone && (
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {lead.phone}
                            </span>
                          )}
                          {lead.email && (
                            <span className="flex items-center gap-1">
                              <Mail className="h-3 w-3" />
                              {lead.email}
                            </span>
                          )}
                          {lead.vehicle_info && (
                            <span className="flex items-center gap-1">
                              <Car className="h-3 w-3" />
                              {lead.vehicle_info.year} {lead.vehicle_info.make} {lead.vehicle_info.model}
                            </span>
                          )}
                        </div>
                        {lead.notes && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {lead.notes}
                          </p>
                        )}
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {!lead.synced_to_crm && (
                          <DropdownMenuItem
                            onClick={() => syncLeadMutation.mutate(lead.id)}
                          >
                            <Upload className="h-4 w-4 mr-2" />
                            Sync to CRM
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem>
                          <Phone className="h-4 w-4 mr-2" />
                          Call
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Mail className="h-4 w-4 mr-2" />
                          Email
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default FieldLeadsPage;
