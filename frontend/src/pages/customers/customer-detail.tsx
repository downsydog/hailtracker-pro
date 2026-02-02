import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useCustomer, useDeleteCustomer } from "@/hooks/use-customers"
import { Job, Vehicle } from "@/types"
import { ArrowLeft, User, Mail, Phone, MapPin, Car, Briefcase, Pencil, Trash2 } from "lucide-react"

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: customer, isLoading } = useCustomer(Number(id))
  const deleteCustomer = useDeleteCustomer()

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this customer? This action cannot be undone.")) {
      try {
        await deleteCustomer.mutateAsync(Number(id))
        navigate("/customers")
      } catch (error) {
        console.error("Failed to delete customer:", error)
      }
    }
  }

  const jobColumns: Column<Job>[] = [
    {
      key: "job_number",
      header: "Job #",
      render: (job) => (
        <Link to={`/jobs/${job.id}`} className="font-medium hover:underline">
          {job.job_number}
        </Link>
      ),
    },
    {
      key: "vehicle",
      header: "Vehicle",
      render: (job) => `${job.vehicle_year} ${job.vehicle_make} ${job.vehicle_model}`,
    },
    {
      key: "status",
      header: "Status",
      render: (job) => <Badge variant="outline">{job.status}</Badge>,
    },
    {
      key: "created_at",
      header: "Date",
      render: (job) => new Date(job.created_at).toLocaleDateString(),
    },
  ]

  const vehicleColumns: Column<Vehicle>[] = [
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
  ]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64" />
          <Skeleton className="h-64 lg:col-span-2" />
        </div>
      </div>
    )
  }

  if (!customer) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Customer not found</h2>
        <Button variant="link" onClick={() => navigate("/customers")}>
          Back to customers
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/customers")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <PageHeader
            title={`${customer.first_name} ${customer.last_name}`}
            description={`Customer since ${new Date(customer.created_at).toLocaleDateString()}`}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate(`/customers/${id}/edit`)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Contact Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {customer.email && (
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <a href={`mailto:${customer.email}`} className="hover:underline">
                  {customer.email}
                </a>
              </div>
            )}
            {customer.phone && (
              <div className="flex items-center gap-3">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <a href={`tel:${customer.phone}`} className="hover:underline">
                  {customer.phone}
                </a>
              </div>
            )}
            {customer.address && (
              <div className="flex items-start gap-3">
                <MapPin className="h-4 w-4 text-muted-foreground mt-0.5" />
                <span>
                  {customer.address}
                  {customer.city && `, ${customer.city}`}
                  {customer.state && `, ${customer.state}`}
                  {customer.zip && ` ${customer.zip}`}
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Car className="h-5 w-5" />
                Vehicles
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={vehicleColumns}
                data={customer.vehicles || []}
                emptyMessage="No vehicles registered"
                keyExtractor={(vehicle) => vehicle.id}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="h-5 w-5" />
                Job History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                columns={jobColumns}
                data={customer.jobs || []}
                emptyMessage="No jobs yet"
                keyExtractor={(job) => job.id}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
