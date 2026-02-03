import * as React from "react"
import { Link } from "react-router-dom"
import { usePortal } from "@/contexts/portal-context"
import { portalApi, PortalDashboardData, PortalJob } from "@/api/portal"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Car,
  Clock,
  Calendar,
  MessageSquare,
  FileText,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Wrench,
} from "lucide-react"

const statusColors: Record<string, string> = {
  CHECKED_IN: "bg-yellow-100 text-yellow-800",
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  ON_HOLD: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-green-100 text-green-800",
  READY_FOR_PICKUP: "bg-purple-100 text-purple-800",
}

function JobCard({ job }: { job: PortalJob }) {
  return (
    <Link to={`/portal/jobs/${job.id}`}>
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <Car className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold">
                  {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Job #{job.job_number}
                </p>
              </div>
            </div>
            <Badge className={statusColors[job.status] || "bg-gray-100 text-gray-800"}>
              {job.status_label}
            </Badge>
          </div>

          {job.progress_percent !== undefined && job.status === "IN_PROGRESS" && (
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-1">
                <span>Progress</span>
                <span>{job.progress_percent}%</span>
              </div>
              <Progress value={job.progress_percent} className="h-2" />
            </div>
          )}

          {job.tech_name && (
            <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
              <Wrench className="h-4 w-4" />
              <span>Technician: {job.tech_name}</span>
            </div>
          )}

          {job.estimated_completion && (
            <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>Est. completion: {new Date(job.estimated_completion).toLocaleDateString()}</span>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <FileText className="h-4 w-4 text-muted-foreground" />
                {job.documents_count}
              </span>
              <span className="flex items-center gap-1">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                {job.messages_count}
              </span>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

export function PortalDashboardPage() {
  const { customer } = usePortal()
  const [data, setData] = React.useState<PortalDashboardData | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const result = await portalApi.getDashboard()
        setData(result)
      } catch (error) {
        console.log("Using demo data for dashboard")
        // Demo data
        setData({
          customer: customer!,
          active_jobs: [
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
          ],
          completed_jobs: [
            {
              id: 2,
              job_number: "JOB-2024-089",
              vehicle_year: 2022,
              vehicle_make: "Honda",
              vehicle_model: "Accord",
              status: "COMPLETED",
              status_label: "Completed",
              photos_count: 8,
              documents_count: 4,
              messages_count: 3,
              created_at: "2024-12-01",
              updated_at: "2024-12-15",
            },
          ],
          upcoming_appointments: [
            {
              id: 1,
              job_id: 1,
              type: "pick_up",
              scheduled_at: "2025-01-28T14:00:00",
              status: "scheduled",
            },
          ],
          unread_messages: 2,
          pending_actions: [
            {
              id: "1",
              type: "approve_estimate",
              title: "Approve Supplement",
              description: "Additional repairs found - please review and approve",
              job_id: 1,
              priority: "high",
            },
          ],
        })
      } finally {
        setLoading(false)
      }
    }
    fetchDashboard()
  }, [customer])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white">
        <h1 className="text-2xl font-bold mb-2">
          Welcome back, {customer?.first_name}!
        </h1>
        <p className="text-blue-100">
          Track your vehicle repairs and stay updated on progress.
        </p>
      </div>

      {/* Pending Actions */}
      {(data.pending_actions?.length ?? 0) > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-orange-800">
              <AlertCircle className="h-5 w-5" />
              Action Required
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.pending_actions?.map((action) => (
              <div
                key={action.id}
                className="flex items-center justify-between p-3 bg-white rounded-lg"
              >
                <div>
                  <h4 className="font-medium">{action.title}</h4>
                  <p className="text-sm text-muted-foreground">{action.description}</p>
                </div>
                <Button size="sm" asChild>
                  <Link to={`/portal/jobs/${action.job_id}`}>
                    Review
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Link>
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <Car className="h-8 w-8 mx-auto text-blue-600 mb-2" />
              <p className="text-2xl font-bold">{data.active_jobs?.length ?? 0}</p>
              <p className="text-sm text-muted-foreground">Active Jobs</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <CheckCircle className="h-8 w-8 mx-auto text-green-600 mb-2" />
              <p className="text-2xl font-bold">{data.completed_jobs?.length ?? 0}</p>
              <p className="text-sm text-muted-foreground">Completed</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <Calendar className="h-8 w-8 mx-auto text-purple-600 mb-2" />
              <p className="text-2xl font-bold">{data.upcoming_appointments?.length ?? 0}</p>
              <p className="text-sm text-muted-foreground">Appointments</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <MessageSquare className="h-8 w-8 mx-auto text-orange-600 mb-2" />
              <p className="text-2xl font-bold">{data.unread_messages}</p>
              <p className="text-sm text-muted-foreground">Messages</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Jobs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Active Jobs</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/portal/jobs">
              View All
              <ChevronRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
        {(data.active_jobs?.length ?? 0) > 0 ? (
          <div className="space-y-4">
            {data.active_jobs?.map((job) => (
              <JobCard key={job.id} job={job as any} />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-8 text-center">
              <Car className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <p className="font-medium">No active jobs</p>
              <p className="text-sm text-muted-foreground">
                You'll see your active repairs here
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Upcoming Appointments */}
      {(data.upcoming_appointments?.length ?? 0) > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Upcoming Appointments</h2>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/portal/appointments">
                View All
                <ChevronRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </div>
          <Card>
            <CardContent className="p-0 divide-y">
              {data.upcoming_appointments?.map((apt) => (
                <div key={apt.id} className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                      <Clock className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium capitalize">{apt.type.replace("_", " ")}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(apt.scheduled_at || '').toLocaleDateString()} at{" "}
                        {new Date(apt.scheduled_at || '').toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">{apt.status}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Completed Jobs */}
      {(data.completed_jobs?.length ?? 0) > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Completed Jobs</h2>
          <div className="space-y-4">
            {data.completed_jobs?.slice(0, 2).map((job) => (
              <JobCard key={job.id} job={job as any} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
