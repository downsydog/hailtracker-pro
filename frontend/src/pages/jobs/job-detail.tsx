import { useParams, useNavigate, Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useJob, useUpdateJobStatus, useDeleteJob } from "@/hooks/use-jobs"
import { ArrowLeft, Car, User, FileText, Calendar, Pencil, Trash2 } from "lucide-react"

const statusOptions = [
  "PENDING",
  "SCHEDULED",
  "IN_PROGRESS",
  "WAITING_PARTS",
  "QUALITY_CHECK",
  "COMPLETED",
  "CANCELLED",
]

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: job, isLoading } = useJob(Number(id))
  const updateStatus = useUpdateJobStatus()
  const deleteJob = useDeleteJob()

  const handleStatusChange = (newStatus: string) => {
    if (job) {
      updateStatus.mutate({ id: job.id, status: newStatus })
    }
  }

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this job? This action cannot be undone.")) {
      try {
        await deleteJob.mutateAsync(Number(id))
        navigate("/jobs")
      } catch (error) {
        console.error("Failed to delete job:", error)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Job not found</h2>
        <Button variant="link" onClick={() => navigate("/jobs")}>
          Back to jobs
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/jobs")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <PageHeader
            title={`Job ${job.job_number}`}
            description={`Created on ${new Date(job.created_at).toLocaleDateString()}`}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate(`/jobs/${id}/edit`)}>
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
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Car className="h-5 w-5" />
                Vehicle Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm text-muted-foreground">Vehicle</dt>
                  <dd className="font-medium">
                    {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">VIN</dt>
                  <dd className="font-mono text-sm">{job.vehicle_vin || "—"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Color</dt>
                  <dd>{job.vehicle_color || "—"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">License Plate</dt>
                  <dd>{job.license_plate || "—"}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Job Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm text-muted-foreground">Damage Type</dt>
                  <dd>{job.damage_type || "Hail Damage"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Insurance Company</dt>
                  <dd>{job.insurance_company || "—"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Claim Number</dt>
                  <dd>{job.claim_number || "—"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Deductible</dt>
                  <dd>${job.deductible?.toFixed(2) || "0.00"}</dd>
                </div>
              </dl>
              {job.notes && (
                <div className="mt-4 pt-4 border-t">
                  <dt className="text-sm text-muted-foreground mb-2">Notes</dt>
                  <dd className="text-sm whitespace-pre-wrap">{job.notes}</dd>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={job.status} onValueChange={handleStatusChange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {statusOptions.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent>
              {job.customer_id ? (
                <div>
                  <p className="font-medium">{job.customer_name}</p>
                  <p className="text-sm text-muted-foreground">{job.customer_email}</p>
                  <p className="text-sm text-muted-foreground">{job.customer_phone}</p>
                  <Button variant="link" className="px-0 mt-2" asChild>
                    <Link to={`/customers/${job.customer_id}`}>View customer</Link>
                  </Button>
                </div>
              ) : (
                <p className="text-muted-foreground">No customer assigned</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Schedule
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2">
                <div>
                  <dt className="text-sm text-muted-foreground">Scheduled Date</dt>
                  <dd>{job.scheduled_date ? new Date(job.scheduled_date).toLocaleDateString() : "—"}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Estimated Completion</dt>
                  <dd>{job.estimated_completion ? new Date(job.estimated_completion).toLocaleDateString() : "—"}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
