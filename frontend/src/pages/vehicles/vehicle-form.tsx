import * as React from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useVehicle, useCreateVehicle, useUpdateVehicle, useDecodeVIN } from "@/hooks/use-vehicles"
import { useCustomers } from "@/hooks/use-customers"
import { ArrowLeft, Save, Search, Loader2 } from "lucide-react"

export function VehicleFormPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEdit = !!id && id !== "new"

  const { data: vehicle, isLoading } = useVehicle(isEdit ? Number(id) : 0)
  const { data: customersData } = useCustomers({ per_page: 100 })
  const createVehicle = useCreateVehicle()
  const updateVehicle = useUpdateVehicle()
  const decodeVIN = useDecodeVIN()

  const [formData, setFormData] = React.useState({
    customer_id: searchParams.get("customer_id") || "",
    year: "",
    make: "",
    model: "",
    color: "",
    vin: "",
    license_plate: "",
  })

  React.useEffect(() => {
    if (vehicle && isEdit) {
      setFormData({
        customer_id: vehicle.customer_id?.toString() || "",
        year: vehicle.year?.toString() || "",
        make: vehicle.make || "",
        model: vehicle.model || "",
        color: vehicle.color || "",
        vin: vehicle.vin || "",
        license_plate: vehicle.license_plate || "",
      })
    }
  }, [vehicle, isEdit])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const data = {
      customer_id: formData.customer_id ? Number(formData.customer_id) : undefined,
      year: formData.year ? Number(formData.year) : undefined,
      make: formData.make,
      model: formData.model,
      color: formData.color || undefined,
      vin: formData.vin || undefined,
      license_plate: formData.license_plate || undefined,
    }

    try {
      if (isEdit) {
        await updateVehicle.mutateAsync({ id: Number(id), data })
        navigate(`/vehicles/${id}`)
      } else {
        const result = await createVehicle.mutateAsync(data)
        navigate(`/vehicles/${(result as { id?: number }).id || ""}`)
      }
    } catch (error) {
      console.error("Failed to save vehicle:", error)
    }
  }

  const customers = customersData?.customers || []
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 40 }, (_, i) => currentYear - i)

  if (isEdit && isLoading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/vehicles")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEdit ? "Edit Vehicle" : "New Vehicle"}
          description={
            isEdit
              ? `Editing ${vehicle?.year} ${vehicle?.make} ${vehicle?.model}`
              : "Add a new vehicle"
          }
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Vehicle Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="year">Year *</Label>
                <Select
                  value={formData.year}
                  onValueChange={(value) => setFormData({ ...formData, year: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select year" />
                  </SelectTrigger>
                  <SelectContent>
                    {years.map((year) => (
                      <SelectItem key={year} value={year.toString()}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="make">Make *</Label>
                <Input
                  id="make"
                  value={formData.make}
                  onChange={(e) => setFormData({ ...formData, make: e.target.value })}
                  placeholder="Toyota, Ford, Honda..."
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">Model *</Label>
                <Input
                  id="model"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  placeholder="Camry, F-150, Civic..."
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="color">Color</Label>
                <Input
                  id="color"
                  value={formData.color}
                  onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                  placeholder="Silver, Black, White..."
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Registration Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="customer_id">Owner</Label>
                <Select
                  value={formData.customer_id}
                  onValueChange={(value) => setFormData({ ...formData, customer_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select owner" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id.toString()}>
                        {customer.first_name} {customer.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="vin">VIN</Label>
                <div className="flex gap-2">
                  <Input
                    id="vin"
                    value={formData.vin}
                    onChange={(e) => setFormData({ ...formData, vin: e.target.value.toUpperCase() })}
                    placeholder="17-character VIN"
                    maxLength={17}
                    className="font-mono flex-1"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={formData.vin.length !== 17 || decodeVIN.isPending}
                    onClick={async () => {
                      const result = await decodeVIN.mutateAsync(formData.vin)
                      if (result.success) {
                        setFormData((prev) => ({
                          ...prev,
                          year: result.year?.toString() || prev.year,
                          make: result.make || prev.make,
                          model: result.model || prev.model,
                        }))
                      }
                    }}
                  >
                    {decodeVIN.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Enter a 17-character VIN and click the search button to auto-fill vehicle info
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="license_plate">License Plate</Label>
                <Input
                  id="license_plate"
                  value={formData.license_plate}
                  onChange={(e) =>
                    setFormData({ ...formData, license_plate: e.target.value.toUpperCase() })
                  }
                  placeholder="ABC-1234"
                  className="font-mono"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end gap-4 mt-6">
          <Button type="button" variant="outline" onClick={() => navigate("/vehicles")}>
            Cancel
          </Button>
          <Button type="submit" disabled={createVehicle.isPending || updateVehicle.isPending}>
            <Save className="h-4 w-4 mr-2" />
            {isEdit ? "Save Changes" : "Add Vehicle"}
          </Button>
        </div>
      </form>
    </div>
  )
}
