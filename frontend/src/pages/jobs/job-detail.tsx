import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useJob, useUpdateJobStatus } from "@/hooks/use-jobs"
import {
  ArrowLeft,
  Calendar,
  Car,
  User,
  Phone,
  Mail,
  Wrench,
  DollarSign,
  FileText,
  Clock,
} from "lucide-react"

const statusColors: Record<string, string> = {
  SCHEDULED: "bg-blue-100 text-blue-800",
  IN_PROGRESS: "bg-yellow-100 text-yellow-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
  ON_HOLD: "bg-gray-100 text-gray-800",
}

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: job, isLoading } = useJob(Number(id))
  const updateStatus = useUpdateJobStatus()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="space-y-6">
        <PageHeader title="Job Not Found" />
        <p className="text-muted-foreground">The job you're looking for doesn't exist.</p>
        <Button onClick={() => navigate("/jobs")}>Back to Jobs</Button>
      </div>
    )
  }

  const handleStatusChange = async (newStatus: string) => {
    await updateStatus.mutateAsync({ id: job.id, status: newStatus })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/jobs")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={`Job ${job.job_number}`}
          description={`Created ${new Date(job.created_at).toLocaleDateString()}`}
        >
          <Badge className={statusColors[job.status] || "bg-gray-100 text-gray-800"}>
            {job.status.replace("_", " ")}
          </Badge>
        </PageHeader>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Customer Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Customer Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="font-medium">{job.customer_name}</p>
            </div>
            {job.customer_phone && (
              <div className="flex items-center gap-2 text-sm">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <a href={`tel:${job.customer_phone}`} className="hover:underline">
                  {job.customer_phone}
                </a>
              </div>
            )}
            {job.customer_email && (
              <div className="flex items-center gap-2 text-sm">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <a href={`mailto:${job.customer_email}`} className="hover:underline">
                  {job.customer_email}
                </a>
              </div>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link to={`/customers/${job.customer_id}`}>View Customer</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Vehicle Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicle Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="font-medium">
                {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
              </p>
              {job.vehicle_color && (
                <p className="text-sm text-muted-foreground">Color: {job.vehicle_color}</p>
              )}
            </div>
            {job.vehicle_vin && (
              <div className="text-sm">
                <span className="text-muted-foreground">VIN:</span> {job.vehicle_vin}
              </div>
            )}
            {job.license_plate && (
              <div className="text-sm">
                <span className="text-muted-foreground">License Plate:</span> {job.license_plate}
              </div>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link to={`/vehicles/${job.vehicle_id}`}>View Vehicle</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Job Details */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wrench className="h-5 w-5" />
              Job Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {job.damage_type && (
              <div>
                <p className="text-sm text-muted-foreground">Damage Type</p>
                <p className="font-medium">{job.damage_type}</p>
              </div>
            )}
            {job.tech_name && (
              <div>
                <p className="text-sm text-muted-foreground">Assigned Technician</p>
                <p className="font-medium">{job.tech_name}</p>
              </div>
            )}
            {job.scheduled_date && (
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Scheduled Date</p>
                  <p className="font-medium">
                    {new Date(job.scheduled_date).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}
            {job.estimated_completion && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Est. Completion</p>
                  <p className="font-medium">
                    {new Date(job.estimated_completion).toLocaleDateString()}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Financial Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Financial Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">${job.total?.toLocaleString() || "0"}</p>
            </div>
            {job.insurance_company && (
              <div>
                <p className="text-sm text-muted-foreground">Insurance</p>
                <p className="font-medium">{job.insurance_company}</p>
                {job.claim_number && (
                  <p className="text-sm text-muted-foreground">
                    Claim #: {job.claim_number}
                  </p>
                )}
              </div>
            )}
            {job.deductible && (
              <div>
                <p className="text-sm text-muted-foreground">Deductible</p>
                <p className="font-medium">${job.deductible.toLocaleString()}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Notes */}
        {(job.notes || job.tech_notes || job.internal_notes) && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Notes
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {job.notes && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Customer Notes</p>
                  <p className="mt-1">{job.notes}</p>
                </div>
              )}
              {job.tech_notes && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Tech Notes</p>
                  <p className="mt-1">{job.tech_notes}</p>
                </div>
              )}
              {job.internal_notes && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Internal Notes</p>
                  <p className="mt-1">{job.internal_notes}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button asChild>
              <Link to={`/jobs/${job.id}/edit`}>Edit Job</Link>
            </Button>
            {job.status === "SCHEDULED" && (
              <Button
                variant="outline"
                onClick={() => handleStatusChange("IN_PROGRESS")}
                disabled={updateStatus.isPending}
              >
                Start Job
              </Button>
            )}
            {job.status === "IN_PROGRESS" && (
              <Button
                variant="outline"
                onClick={() => handleStatusChange("COMPLETED")}
                disabled={updateStatus.isPending}
              >
                Complete Job
              </Button>
            )}
            <Button variant="outline" asChild>
              <Link to={`/invoices/new?job_id=${job.id}`}>Create Invoice</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
