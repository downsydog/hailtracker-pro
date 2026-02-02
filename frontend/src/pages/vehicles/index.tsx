import * as React from "react"
import { Link, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useVehicles } from "@/hooks/use-vehicles"
import { Vehicle } from "@/types"
import { Plus, Search } from "lucide-react"

export function VehiclesPage() {
  const navigate = useNavigate()
  const [search, setSearch] = React.useState("")

  const { data, isLoading } = useVehicles({
    search: search || undefined,
  })

  const vehicles = data?.vehicles || []

  const columns: Column<Vehicle>[] = [
    {
      key: "vehicle",
      header: "Vehicle",
      render: (vehicle) => (
        <Link to={`/vehicles/${vehicle.id}`} className="font-medium hover:underline">
          {vehicle.year} {vehicle.make} {vehicle.model}
        </Link>
      ),
    },
    {
      key: "vin",
      header: "VIN",
      render: (vehicle) => (
        <span className="font-mono text-sm">{vehicle.vin || "—"}</span>
      ),
    },
    {
      key: "color",
      header: "Color",
      render: (vehicle) => vehicle.color || "—",
    },
    {
      key: "owner_name",
      header: "Owner",
      render: (vehicle: Vehicle & { owner_name?: string }) =>
        vehicle.customer_id ? (
          <Link to={`/customers/${vehicle.customer_id}`} className="hover:underline">
            {vehicle.owner_name || "—"}
          </Link>
        ) : (
          "—"
        ),
    },
    {
      key: "license_plate",
      header: "License Plate",
      render: (vehicle) => vehicle.license_plate || "—",
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vehicles"
        description="View and manage vehicle records."
        actions={[
          {
            label: "New Vehicle",
            onClick: () => navigate("/vehicles/new"),
            icon: Plus,
          },
        ]}
      />

      <Card>
        <CardContent className="pt-6">
          <div className="relative mb-6">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by VIN, make, model..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 max-w-md"
            />
          </div>

          <DataTable
            columns={columns}
            data={vehicles}
            isLoading={isLoading}
            onRowClick={(vehicle) => navigate(`/vehicles/${vehicle.id}`)}
            emptyMessage="No vehicles found"
            keyExtractor={(vehicle) => vehicle.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}
