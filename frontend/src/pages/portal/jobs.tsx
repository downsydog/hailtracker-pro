import * as React from "react"
import { Link } from "react-router-dom"
import { portalApi, PortalJob } from "@/api/portal"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  Car,
  Calendar,
  MessageSquare,
  FileText,
  ChevronRight,
  Wrench,
  CheckCircle,
  Clock,
} from "lucide-react"

const statusColors: Record<string, string> = {
  CHECKED_IN: "bg-yellow-100 text-yellow-800",
  AWAITING_PARTS: "bg-orange-100 text-orange-800",
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  ON_HOLD: "bg-red-100 text-red-800",
  QUALITY_CHECK: "bg-purple-100 text-purple-800",
  COMPLETED: "bg-green-100 text-green-800",
  READY_FOR_PICKUP: "bg-emerald-100 text-emerald-800",
}

function JobCard({ job }: { job: PortalJob }) {
  const isActive = !["COMPLETED", "CANCELLED", "PICKED_UP"].includes(job.status)

  return (
    <Link to={`/portal/jobs/${job.id}`}>
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`h-12 w-12 rounded-lg flex items-center justify-center ${
                isActive ? "bg-blue-100" : "bg-gray-100"
              }`}>
                <Car className={`h-6 w-6 ${isActive ? "text-blue-600" : "text-gray-500"}`} />
              </div>
              <div>
                <h3 className="font-semibold">
                  {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {job.vehicle_color && `${job.vehicle_color} • `}Job #{job.job_number}
                </p>
              </div>
            </div>
            <Badge className={statusColors[job.status] || "bg-gray-100 text-gray-800"}>
              {job.status_label}
            </Badge>
          </div>

          {job.damage_type && (
            <div className="mt-3">
              <span className="text-sm text-muted-foreground">
                Damage: {job.damage_type}
              </span>
            </div>
          )}

          {job.progress_percent !== undefined && isActive && (
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-1">
                <span>Repair Progress</span>
                <span>{job.progress_percent}%</span>
              </div>
              <Progress value={job.progress_percent} className="h-2" />
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
            {job.tech_name && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Wrench className="h-4 w-4" />
                <span>{job.tech_name}</span>
              </div>
            )}
            {job.estimated_completion && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>{new Date(job.estimated_completion).toLocaleDateString()}</span>
              </div>
            )}
          </div>

          <div className="mt-4 flex items-center justify-between text-sm border-t pt-3">
            <div className="flex items-center gap-4 text-muted-foreground">
              <span className="flex items-center gap-1">
                <FileText className="h-4 w-4" />
                {job.documents_count} docs
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="h-4 w-4" />
                {job.messages_count} msgs
              </span>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

export function PortalJobsPage() {
  const [jobs, setJobs] = React.useState<PortalJob[]>([])
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const fetchJobs = async () => {
      try {
        const result = await portalApi.getJobs()
        setJobs(result.jobs)
      } catch {
        // Demo data
        setJobs([
          {
            id: 1,
            job_number: "JOB-2025-001",
            vehicle_year: 2023,
            vehicle_make: "Toyota",
            vehicle_model: "Camry",
            vehicle_color: "Silver",
            status: "IN_PROGRESS",
            status_label: "In Progress",
            damage_type: "Hail Damage",
            estimated_completion: "2025-01-28",
            tech_name: "Mike Johnson",
            progress_percent: 65,
            photos_count: 12,
            documents_count: 3,
            messages_count: 5,
            created_at: "2025-01-20",
            updated_at: "2025-01-23",
          },
          {
            id: 2,
            job_number: "JOB-2024-089",
            vehicle_year: 2022,
            vehicle_make: "Honda",
            vehicle_model: "Accord",
            vehicle_color: "Blue",
            status: "COMPLETED",
            status_label: "Completed",
            damage_type: "Door Dings",
            photos_count: 8,
            documents_count: 4,
            messages_count: 3,
            created_at: "2024-12-01",
            updated_at: "2024-12-15",
          },
          {
            id: 3,
            job_number: "JOB-2024-075",
            vehicle_year: 2021,
            vehicle_make: "Ford",
            vehicle_model: "F-150",
            vehicle_color: "White",
            status: "COMPLETED",
            status_label: "Completed",
            damage_type: "Hail Damage",
            photos_count: 15,
            documents_count: 5,
            messages_count: 8,
            created_at: "2024-10-15",
            updated_at: "2024-11-01",
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchJobs()
  }, [])

  const activeJobs = jobs.filter(
    (j) => !["COMPLETED", "CANCELLED", "PICKED_UP"].includes(j.status)
  )
  const completedJobs = jobs.filter(
    (j) => ["COMPLETED", "PICKED_UP"].includes(j.status)
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Jobs</h1>
        <p className="text-muted-foreground">Track all your vehicle repairs</p>
      </div>

      <Tabs defaultValue="active">
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="active" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Active ({activeJobs.length})
          </TabsTrigger>
          <TabsTrigger value="completed" className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            Completed ({completedJobs.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="mt-4">
          {activeJobs.length > 0 ? (
            <div className="space-y-4">
              {activeJobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <Car className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <h3 className="font-medium mb-1">No Active Jobs</h3>
                <p className="text-sm text-muted-foreground">
                  You don't have any vehicles currently being repaired
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="completed" className="mt-4">
          {completedJobs.length > 0 ? (
            <div className="space-y-4">
              {completedJobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <h3 className="font-medium mb-1">No Completed Jobs</h3>
                <p className="text-sm text-muted-foreground">
                  Your completed repairs will appear here
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
