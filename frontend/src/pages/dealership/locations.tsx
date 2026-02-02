import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { dealershipApi, DealerLocation } from "@/api/dealership"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  MapPin,
  Plus,
  Pencil,
  Trash2,
  Car,
  Wrench,
  Phone,
  Mail,
  Building2,
  Star,
} from "lucide-react"

// Demo data
const DEMO_LOCATIONS: DealerLocation[] = [
  {
    id: 1,
    dealership_id: 1,
    name: "Main Lot - Downtown",
    address: "123 Main Street",
    city: "Denver",
    state: "CO",
    zip: "80202",
    phone: "(303) 555-1234",
    manager_name: "John Smith",
    manager_email: "john.smith@example.com",
    is_primary: true,
    vehicles_count: 28,
    active_jobs: 5,
  },
  {
    id: 2,
    dealership_id: 1,
    name: "North Campus",
    address: "456 North Avenue",
    city: "Denver",
    state: "CO",
    zip: "80203",
    phone: "(303) 555-5678",
    manager_name: "Jane Doe",
    manager_email: "jane.doe@example.com",
    is_primary: false,
    vehicles_count: 12,
    active_jobs: 3,
  },
  {
    id: 3,
    dealership_id: 1,
    name: "Service Center",
    address: "789 Industrial Blvd",
    city: "Aurora",
    state: "CO",
    zip: "80010",
    phone: "(303) 555-9012",
    is_primary: false,
    vehicles_count: 7,
    active_jobs: 2,
  },
]

interface LocationFormData {
  name: string
  address: string
  city: string
  state: string
  zip: string
  phone: string
  manager_name: string
  manager_email: string
  is_primary: boolean
}

const initialFormData: LocationFormData = {
  name: "",
  address: "",
  city: "",
  state: "",
  zip: "",
  phone: "",
  manager_name: "",
  manager_email: "",
  is_primary: false,
}

export function DealershipLocationsPage() {
  const dealershipId = 1
  const queryClient = useQueryClient()

  const [showFormDialog, setShowFormDialog] = React.useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false)
  const [editingLocation, setEditingLocation] = React.useState<DealerLocation | null>(null)
  const [deletingLocation, setDeletingLocation] = React.useState<DealerLocation | null>(null)
  const [formData, setFormData] = React.useState<LocationFormData>(initialFormData)

  const { data: locationsData } = useQuery({
    queryKey: ["dealership", dealershipId, "locations"],
    queryFn: () => dealershipApi.getLocations(dealershipId),
    placeholderData: { locations: DEMO_LOCATIONS },
  })

  const createMutation = useMutation({
    mutationFn: (data: Partial<DealerLocation>) =>
      dealershipApi.createLocation(dealershipId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dealership", dealershipId, "locations"] })
      closeForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<DealerLocation> }) =>
      dealershipApi.updateLocation(dealershipId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dealership", dealershipId, "locations"] })
      closeForm()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => dealershipApi.deleteLocation(dealershipId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dealership", dealershipId, "locations"] })
      setShowDeleteDialog(false)
      setDeletingLocation(null)
    },
  })

  const locations = locationsData?.locations ?? DEMO_LOCATIONS

  const openAddForm = () => {
    setEditingLocation(null)
    setFormData(initialFormData)
    setShowFormDialog(true)
  }

  const openEditForm = (location: DealerLocation) => {
    setEditingLocation(location)
    setFormData({
      name: location.name,
      address: location.address,
      city: location.city,
      state: location.state,
      zip: location.zip,
      phone: location.phone ?? "",
      manager_name: location.manager_name ?? "",
      manager_email: location.manager_email ?? "",
      is_primary: location.is_primary,
    })
    setShowFormDialog(true)
  }

  const closeForm = () => {
    setShowFormDialog(false)
    setEditingLocation(null)
    setFormData(initialFormData)
  }

  const openDeleteDialog = (location: DealerLocation) => {
    setDeletingLocation(location)
    setShowDeleteDialog(true)
  }

  const handleSubmit = () => {
    if (editingLocation) {
      updateMutation.mutate({ id: editingLocation.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = () => {
    if (deletingLocation) {
      deleteMutation.mutate(deletingLocation.id)
    }
  }

  const updateFormField = (field: keyof LocationFormData, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Locations</h2>
          <p className="text-sm text-muted-foreground">
            Manage your dealership locations and contact information
          </p>
        </div>
        <Button onClick={openAddForm}>
          <Plus className="h-4 w-4 mr-2" />
          Add Location
        </Button>
      </div>

      {/* Locations Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {locations.map((location) => (
          <Card key={location.id} className={location.is_primary ? "ring-2 ring-primary" : ""}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                    <Building2 className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      {location.name}
                      {location.is_primary && (
                        <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                      )}
                    </CardTitle>
                    {location.is_primary && (
                      <Badge variant="secondary" className="text-xs">Primary</Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => openEditForm(location)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  {!location.is_primary && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={() => openDeleteDialog(location)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Address */}
              <div className="flex items-start gap-2 text-sm">
                <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                <div>
                  <div>{location.address}</div>
                  <div className="text-muted-foreground">
                    {location.city}, {location.state} {location.zip}
                  </div>
                </div>
              </div>

              {/* Phone */}
              {location.phone && (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <span>{location.phone}</span>
                </div>
              )}

              {/* Manager */}
              {location.manager_name && (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <span className="font-medium">{location.manager_name}</span>
                    {location.manager_email && (
                      <span className="text-muted-foreground ml-1">
                        ({location.manager_email})
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Stats */}
              <div className="flex items-center gap-4 pt-2 border-t">
                <div className="flex items-center gap-1.5 text-sm">
                  <Car className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{location.vehicles_count}</span>
                  <span className="text-muted-foreground">vehicles</span>
                </div>
                <div className="flex items-center gap-1.5 text-sm">
                  <Wrench className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{location.active_jobs}</span>
                  <span className="text-muted-foreground">active jobs</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {locations.length === 0 && (
          <Card className="col-span-full">
            <CardContent className="py-12 text-center">
              <MapPin className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <h3 className="font-medium mb-1">No locations yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Add your first location to start managing vehicles
              </p>
              <Button onClick={openAddForm}>
                <Plus className="h-4 w-4 mr-2" />
                Add Location
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Add/Edit Dialog */}
      <Dialog open={showFormDialog} onOpenChange={setShowFormDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingLocation ? "Edit Location" : "Add Location"}
            </DialogTitle>
            <DialogDescription>
              {editingLocation
                ? "Update the location information below"
                : "Add a new dealership location"}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Location Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Main Lot - Downtown"
                value={formData.name}
                onChange={(e) => updateFormField("name", e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">Street Address *</Label>
              <Input
                id="address"
                placeholder="123 Main Street"
                value={formData.address}
                onChange={(e) => updateFormField("address", e.target.value)}
              />
            </div>

            <div className="grid grid-cols-6 gap-4">
              <div className="col-span-3 space-y-2">
                <Label htmlFor="city">City *</Label>
                <Input
                  id="city"
                  placeholder="Denver"
                  value={formData.city}
                  onChange={(e) => updateFormField("city", e.target.value)}
                />
              </div>
              <div className="col-span-1 space-y-2">
                <Label htmlFor="state">State *</Label>
                <Input
                  id="state"
                  placeholder="CO"
                  maxLength={2}
                  value={formData.state}
                  onChange={(e) => updateFormField("state", e.target.value.toUpperCase())}
                />
              </div>
              <div className="col-span-2 space-y-2">
                <Label htmlFor="zip">ZIP Code *</Label>
                <Input
                  id="zip"
                  placeholder="80202"
                  value={formData.zip}
                  onChange={(e) => updateFormField("zip", e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <Input
                id="phone"
                placeholder="(303) 555-1234"
                value={formData.phone}
                onChange={(e) => updateFormField("phone", e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="manager_name">Manager Name</Label>
                <Input
                  id="manager_name"
                  placeholder="John Smith"
                  value={formData.manager_name}
                  onChange={(e) => updateFormField("manager_name", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="manager_email">Manager Email</Label>
                <Input
                  id="manager_email"
                  type="email"
                  placeholder="john@example.com"
                  value={formData.manager_email}
                  onChange={(e) => updateFormField("manager_email", e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <Checkbox
                id="is_primary"
                checked={formData.is_primary}
                onCheckedChange={(checked: boolean | "indeterminate") => updateFormField("is_primary", !!checked)}
              />
              <Label htmlFor="is_primary" className="text-sm font-normal">
                Set as primary location
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeForm}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={
                !formData.name ||
                !formData.address ||
                !formData.city ||
                !formData.state ||
                !formData.zip ||
                createMutation.isPending ||
                updateMutation.isPending
              }
            >
              {createMutation.isPending || updateMutation.isPending
                ? "Saving..."
                : editingLocation
                ? "Update Location"
                : "Add Location"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Location</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deletingLocation?.name}"? This will remove
              the location from your account. Vehicles at this location will need to be
              reassigned.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Location"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
