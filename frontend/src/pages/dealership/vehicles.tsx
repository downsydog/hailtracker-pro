import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { dealershipApi, DealerVehicle, DealerLocation } from "@/api/dealership"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Search,
  Filter,
  Plus,
  Wrench,
  Car,
  MoreHorizontal,
  Eye,
  Trash2,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

// Demo data
const DEMO_VEHICLES: DealerVehicle[] = [
  {
    id: 1,
    dealership_id: 1,
    location_id: 1,
    stock_number: "A12345",
    vin: "1HGBH41JXMN109186",
    year: 2023,
    make: "Honda",
    model: "Accord",
    trim: "EX-L",
    color: "White",
    mileage: 12500,
    status: "available",
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: 2,
    dealership_id: 1,
    location_id: 1,
    stock_number: "B67890",
    vin: "2HGBH41JXMN109187",
    year: 2024,
    make: "Toyota",
    model: "Camry",
    trim: "SE",
    color: "Silver",
    mileage: 500,
    status: "pending_repair",
    damage_type: "Hail Damage",
    damage_description: "Light hail damage on hood and roof",
    estimated_repair_cost: 1250,
    created_at: "2024-01-18T14:30:00Z",
    updated_at: "2024-01-20T09:00:00Z",
  },
  {
    id: 3,
    dealership_id: 1,
    location_id: 2,
    stock_number: "C11223",
    vin: "3HGBH41JXMN109188",
    year: 2023,
    make: "Ford",
    model: "F-150",
    trim: "XLT",
    color: "Blue",
    mileage: 8200,
    status: "in_repair",
    damage_type: "Door Dings",
    damage_description: "Multiple door dings on driver side",
    estimated_repair_cost: 450,
    created_at: "2024-01-10T08:00:00Z",
    updated_at: "2024-01-22T11:00:00Z",
  },
  {
    id: 4,
    dealership_id: 1,
    location_id: 1,
    stock_number: "D44556",
    vin: "4HGBH41JXMN109189",
    year: 2024,
    make: "Chevrolet",
    model: "Silverado",
    trim: "LT",
    color: "Black",
    mileage: 150,
    status: "ready",
    created_at: "2024-01-05T16:00:00Z",
    updated_at: "2024-01-23T14:00:00Z",
  },
]

const DEMO_LOCATIONS: DealerLocation[] = [
  { id: 1, dealership_id: 1, name: "Main Lot - Downtown", address: "123 Main St", city: "Denver", state: "CO", zip: "80202", is_primary: true, vehicles_count: 28, active_jobs: 5 },
  { id: 2, dealership_id: 1, name: "North Campus", address: "456 North Ave", city: "Denver", state: "CO", zip: "80203", is_primary: false, vehicles_count: 12, active_jobs: 3 },
]

const statusConfig: Record<string, { label: string; color: string }> = {
  available: { label: "Available", color: "bg-green-100 text-green-800" },
  pending_repair: { label: "Pending Repair", color: "bg-yellow-100 text-yellow-800" },
  in_repair: { label: "In Repair", color: "bg-blue-100 text-blue-800" },
  ready: { label: "Ready", color: "bg-emerald-100 text-emerald-800" },
  sold: { label: "Sold", color: "bg-gray-100 text-gray-800" },
}

export function DealershipVehiclesPage() {
  const dealershipId = 1
  const queryClient = useQueryClient()

  const [searchQuery, setSearchQuery] = React.useState("")
  const [statusFilter, setStatusFilter] = React.useState<string>("all")
  const [locationFilter, setLocationFilter] = React.useState<string>("all")
  const [selectedVehicle, setSelectedVehicle] = React.useState<DealerVehicle | null>(null)
  const [showJobDialog, setShowJobDialog] = React.useState(false)
  const [showAddDialog, setShowAddDialog] = React.useState(false)
  const [jobNotes, setJobNotes] = React.useState("")

  const { data: vehiclesData } = useQuery({
    queryKey: ["dealership", dealershipId, "vehicles", statusFilter, locationFilter],
    queryFn: () => dealershipApi.getVehicles(dealershipId, {
      status: statusFilter !== "all" ? statusFilter : undefined,
      location_id: locationFilter !== "all" ? parseInt(locationFilter) : undefined,
    }),
    placeholderData: { vehicles: DEMO_VEHICLES, total: DEMO_VEHICLES.length, page: 1 },
  })

  const { data: locationsData } = useQuery({
    queryKey: ["dealership", dealershipId, "locations"],
    queryFn: () => dealershipApi.getLocations(dealershipId),
    placeholderData: { locations: DEMO_LOCATIONS },
  })

  const createJobMutation = useMutation({
    mutationFn: ({ vehicleId, notes }: { vehicleId: number; notes?: string }) =>
      dealershipApi.createJob(dealershipId, vehicleId, { notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dealership", dealershipId] })
      setShowJobDialog(false)
      setSelectedVehicle(null)
      setJobNotes("")
    },
  })

  const vehicles = vehiclesData?.vehicles ?? DEMO_VEHICLES
  const locations = locationsData?.locations ?? DEMO_LOCATIONS

  const filteredVehicles = vehicles.filter((v) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      (v.stock_number ?? '').toLowerCase().includes(query) ||
      v.vin.toLowerCase().includes(query) ||
      v.make.toLowerCase().includes(query) ||
      v.model.toLowerCase().includes(query)
    )
  })

  const handleCreateJob = (vehicle: DealerVehicle) => {
    setSelectedVehicle(vehicle)
    setShowJobDialog(true)
  }

  const submitJob = () => {
    if (selectedVehicle) {
      createJobMutation.mutate({
        vehicleId: selectedVehicle.id,
        notes: jobNotes || undefined,
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by stock #, VIN, make, or model..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="available">Available</SelectItem>
                <SelectItem value="pending_repair">Pending Repair</SelectItem>
                <SelectItem value="in_repair">In Repair</SelectItem>
                <SelectItem value="ready">Ready</SelectItem>
                <SelectItem value="sold">Sold</SelectItem>
              </SelectContent>
            </Select>

            <Select value={locationFilter} onValueChange={setLocationFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Location" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Locations</SelectItem>
                {locations.map((loc) => (
                  <SelectItem key={loc.id} value={loc.id.toString()}>
                    {loc.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button onClick={() => setShowAddDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Vehicle
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Vehicles Table */}
      <Card>
        <CardHeader>
          <CardTitle>Vehicle Inventory</CardTitle>
          <CardDescription>
            {filteredVehicles.length} vehicle{filteredVehicles.length !== 1 ? "s" : ""} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Stock #</TableHead>
                <TableHead>Vehicle</TableHead>
                <TableHead>VIN</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Damage</TableHead>
                <TableHead className="text-right">Est. Cost</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredVehicles.map((vehicle) => {
                const location = locations.find((l) => l.id === vehicle.location_id)
                const status = statusConfig[vehicle.status] ?? { label: vehicle.status, color: "bg-gray-100" }

                return (
                  <TableRow key={vehicle.id}>
                    <TableCell className="font-medium">{vehicle.stock_number}</TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">
                          {vehicle.year} {vehicle.make} {vehicle.model}
                        </div>
                        {vehicle.trim && (
                          <div className="text-sm text-muted-foreground">{vehicle.trim}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{vehicle.vin}</TableCell>
                    <TableCell>{location?.name ?? "—"}</TableCell>
                    <TableCell>
                      <Badge className={status.color}>{status.label}</Badge>
                    </TableCell>
                    <TableCell>
                      {vehicle.damage_type ? (
                        <div>
                          <div className="text-sm">{vehicle.damage_type}</div>
                          {vehicle.damage_description && (
                            <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                              {vehicle.damage_description}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {vehicle.estimated_repair_cost ? (
                        <span className="font-medium">
                          ${vehicle.estimated_repair_cost.toLocaleString()}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>
                            <Eye className="h-4 w-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {(vehicle.status === "available" || vehicle.status === "pending_repair") && (
                            <DropdownMenuItem onClick={() => handleCreateJob(vehicle)}>
                              <Wrench className="h-4 w-4 mr-2" />
                              Create Repair Job
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem className="text-destructive">
                            <Trash2 className="h-4 w-4 mr-2" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )
              })}

              {filteredVehicles.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    <Car className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    No vehicles found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create Job Dialog */}
      <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Repair Job</DialogTitle>
            <DialogDescription>
              Submit this vehicle for repair service
            </DialogDescription>
          </DialogHeader>

          {selectedVehicle && (
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg">
                <div className="font-medium">
                  {selectedVehicle.year} {selectedVehicle.make} {selectedVehicle.model}
                </div>
                <div className="text-sm text-muted-foreground">
                  Stock #{selectedVehicle.stock_number} • VIN: {selectedVehicle.vin}
                </div>
                {selectedVehicle.damage_type && (
                  <div className="mt-2 text-sm">
                    <span className="font-medium">Damage:</span> {selectedVehicle.damage_type}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="job-notes">Additional Notes</Label>
                <Textarea
                  id="job-notes"
                  placeholder="Any special instructions or notes for the repair..."
                  value={jobNotes}
                  onChange={(e) => setJobNotes(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowJobDialog(false)}>
              Cancel
            </Button>
            <Button onClick={submitJob} disabled={createJobMutation.isPending}>
              {createJobMutation.isPending ? "Creating..." : "Create Job"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Vehicle Dialog (placeholder) */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Vehicle</DialogTitle>
            <DialogDescription>
              Add a new vehicle to your inventory. For bulk imports, use the Batch Upload feature.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="stock">Stock Number *</Label>
                <Input id="stock" placeholder="e.g., A12345" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vin">VIN *</Label>
                <Input id="vin" placeholder="17-character VIN" />
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="year">Year *</Label>
                <Input id="year" type="number" placeholder="2024" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="make">Make *</Label>
                <Input id="make" placeholder="Honda" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model *</Label>
                <Input id="model" placeholder="Accord" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="trim">Trim</Label>
                <Input id="trim" placeholder="EX-L" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="color">Color</Label>
                <Input id="color" placeholder="White" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mileage">Mileage</Label>
                <Input id="mileage" type="number" placeholder="12500" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="Select location" />
                  </SelectTrigger>
                  <SelectContent>
                    {locations.map((loc) => (
                      <SelectItem key={loc.id} value={loc.id.toString()}>
                        {loc.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="damage">Damage Description</Label>
              <Textarea id="damage" placeholder="Describe any existing damage..." rows={2} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button>Add Vehicle</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
