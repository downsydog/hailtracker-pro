import * as React from "react"
import { Link, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useJobs } from "@/hooks/use-jobs"
import { Job } from "@/types"
import { Plus, Search } from "lucide-react"

const statusOptions = [
  { value: "all", label: "All Statuses" },
  { value: "PENDING", label: "Pending" },
  { value: "IN_PROGRESS", label: "In Progress" },
  { value: "WAITING_PARTS", label: "Waiting Parts" },
  { value: "COMPLETED", label: "Completed" },
  { value: "CANCELLED", label: "Cancelled" },
]

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  PENDING: "secondary",
  IN_PROGRESS: "default",
  WAITING_PARTS: "outline",
  COMPLETED: "default",
  CANCELLED: "destructive",
}

export function JobsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = React.useState("")
  const [status, setStatus] = React.useState("all")

  const { data, isLoading } = useJobs({
    search: search || undefined,
    status: status !== "all" ? status : undefined,
  })

  const jobs = data?.jobs || []

  const columns: Column<Job>[] = [
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
      key: "customer_name",
      header: "Customer",
      render: (job) => job.customer_name || "—",
    },
    {
      key: "vehicle",
      header: "Vehicle",
      render: (job) =>
        job.vehicle_year && job.vehicle_make
          ? `${job.vehicle_year} ${job.vehicle_make} ${job.vehicle_model}`
          : "—",
    },
    {
      key: "status",
      header: "Status",
      render: (job) => (
        <Badge variant={statusColors[job.status] || "outline"}>
          {job.status.replace(/_/g, " ")}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      render: (job) => new Date(job.created_at).toLocaleDateString(),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Manage repair jobs and track their progress."
        actions={[
          {
            label: "New Job",
            onClick: () => navigate("/jobs/new"),
            icon: Plus,
          },
        ]}
      />

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search jobs..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-full md:w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DataTable
            columns={columns}
            data={jobs}
            isLoading={isLoading}
            onRowClick={(job) => navigate(`/jobs/${job.id}`)}
            emptyMessage="No jobs found"
            keyExtractor={(job) => job.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}
