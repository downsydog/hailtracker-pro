import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useVehicle, useDeleteVehicle } from "@/hooks/use-vehicles"
import { Job } from "@/types"
import { ArrowLeft, Edit, Trash2, Car, User, Briefcase } from "lucide-react"

export function VehicleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: vehicle, isLoading } = useVehicle(Number(id))
  const deleteVehicle = useDeleteVehicle()

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this vehicle?")) {
      try {
        await deleteVehicle.mutateAsync(Number(id))
        navigate("/vehicles")
      } catch (error) {
        console.error("Failed to delete vehicle:", error)
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

  if (!vehicle) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Vehicle not found</h2>
        <Button variant="link" onClick={() => navigate("/vehicles")}>
          Back to vehicles
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/vehicles")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <PageHeader
            title={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
            description={vehicle.vin ? `VIN: ${vehicle.vin}` : ""}
          />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate(`/vehicles/${id}/edit`)}>
            <Edit className="h-4 w-4 mr-2" />
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
              <Car className="h-5 w-5" />
              Vehicle Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Year / Make / Model</p>
              <p className="font-medium">
                {vehicle.year} {vehicle.make} {vehicle.model}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Color</p>
              <p className="font-medium">{vehicle.color || "Not specified"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">VIN</p>
              <p className="font-mono text-sm">{vehicle.vin || "Not specified"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">License Plate</p>
              <p className="font-mono">{vehicle.license_plate || "Not specified"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Owner
            </CardTitle>
          </CardHeader>
          <CardContent>
            {vehicle.customer_id ? (
              <div>
                <p className="font-medium">{vehicle.customer_name}</p>
                <Button variant="link" className="px-0 mt-2" asChild>
                  <Link to={`/customers/${vehicle.customer_id}`}>View customer</Link>
                </Button>
              </div>
            ) : (
              <p className="text-muted-foreground">No owner assigned</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Job History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={jobColumns}
              data={(vehicle as { jobs?: Job[] }).jobs || []}
              emptyMessage="No jobs for this vehicle"
              keyExtractor={(job) => job.id}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
