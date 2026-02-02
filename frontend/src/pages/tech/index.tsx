import * as React from "react"
import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TimeStatusBanner } from "@/components/app/time-status-banner"
import { LogTimeDialog } from "@/components/app/log-time-dialog"
import { WeekSummary } from "@/components/app/week-summary"
import { useTechDashboard } from "@/hooks/use-tech"
import { useJobs } from "@/hooks/use-jobs"
import {
  Wrench,
  Clock,
  CheckCircle,
  AlertCircle,
  Calendar,
  Car,
  Timer,
  Camera,
  MapPin,
  Users,
  Activity,
} from "lucide-react"

export function TechDashboardPage() {
  // Try tech-specific API first (handles both tech and admin views)
  const { data: techData, isLoading: techLoading, error: techError } = useTechDashboard()

  // Fallback to jobs API if tech API fails
  const { data: jobsData, isLoading: jobsLoading } = useJobs(
    { status: "active", per_page: 50 },
  )

  const [logTimeOpen, setLogTimeOpen] = React.useState(false)
  const [selectedJobId, setSelectedJobId] = React.useState<number | undefined>()

  // Use tech API data if available, otherwise fallback to jobs API
  const isLoading = techLoading || (techError && jobsLoading)
  const isAdminView = techData?.is_admin_view ?? false

  // For tech view, use tech API data
  // techStats available via techData?.stats if needed for tech-specific stats
  const techJobs = techData?.today_jobs || []
  // currentJob is available in techData?.current_job if needed

  // For admin view or fallback, use jobs API
  const jobs = techJobs.length > 0 ? techJobs : (jobsData?.jobs || [])
  // Stats from jobs API (has scheduled_today) - techStats has different structure
  const jobStats = jobsData?.stats

  // Group jobs by status for the tech view
  const inProgressJobs = jobs.filter((j) => j.status === "IN_PROGRESS")
  const scheduledJobs = jobs.filter((j) => j.status === "SCHEDULED")
  const waitingPartsJobs = jobs.filter((j) => j.status === "WAITING_PARTS")
  const qualityCheckJobs = jobs.filter((j) => j.status === "QUALITY_CHECK")

  const handleLogTime = (jobId?: number) => {
    setSelectedJobId(jobId)
    setLogTimeOpen(true)
  }

  // Admin view - show overview of all technicians
  if (isAdminView && techData) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Tech Overview"
          description="Admin view - all technician activity"
        />

        {/* Admin Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Jobs Today</CardTitle>
              <Calendar className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{techData.jobs_today || 0}</div>
              <p className="text-xs text-muted-foreground">Scheduled for today</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">In Progress</CardTitle>
              <Wrench className="h-4 w-4 text-yellow-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{techData.jobs_in_progress || 0}</div>
              <p className="text-xs text-muted-foreground">Being worked on</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{techData.jobs_completed_today || 0}</div>
              <p className="text-xs text-muted-foreground">Finished today</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Active Techs</CardTitle>
              <Users className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{techData.active_techs || 0}</div>
              <p className="text-xs text-muted-foreground">Currently working</p>
            </CardContent>
          </Card>
        </div>

        {/* Technicians List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Technician Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!techData.technicians || techData.technicians.length === 0 ? (
              <p className="text-muted-foreground">No technicians found</p>
            ) : (
              <div className="space-y-3">
                {techData.technicians.map((tech) => (
                  <div
                    key={tech.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="text-sm font-semibold">
                          {(tech.first_name?.[0] || "?") + (tech.last_name?.[0] || "")}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium">{tech.name || `${tech.first_name} ${tech.last_name}`}</p>
                        <p className="text-sm text-muted-foreground">
                          {tech.current_job ? `Working on: ${tech.current_job}` : "No active job"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {tech.jobs_today !== undefined && (
                        <span className="text-sm text-muted-foreground">
                          {tech.jobs_today} jobs today
                        </span>
                      )}
                      <Badge
                        variant={tech.status === "ACTIVE" ? "default" : "secondary"}
                      >
                        {tech.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Link to full jobs list */}
        <div className="flex justify-center">
          <Button variant="outline" asChild>
            <Link to="/jobs">View All Jobs</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tech Dashboard"
        description="Your assigned jobs and daily tasks"
      />

      {/* Time Status Banner */}
      <TimeStatusBanner />

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={() => handleLogTime()}>
          <Timer className="h-4 w-4 mr-2" />
          Log Hours
        </Button>
        <Button variant="outline" disabled>
          <Camera className="h-4 w-4 mr-2" />
          Upload Photo
        </Button>
        <Button variant="outline" disabled>
          <MapPin className="h-4 w-4 mr-2" />
          Gas Station Mode
        </Button>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Wrench className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{inProgressJobs.length}</div>
            <p className="text-xs text-muted-foreground">Jobs being worked on</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Scheduled Today</CardTitle>
            <Calendar className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{jobStats?.scheduled_today || scheduledJobs.length}</div>
            <p className="text-xs text-muted-foreground">Coming in today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Waiting Parts</CardTitle>
            <Clock className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{waitingPartsJobs.length}</div>
            <p className="text-xs text-muted-foreground">On hold for parts</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Quality Check</CardTitle>
            <CheckCircle className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{qualityCheckJobs.length}</div>
            <p className="text-xs text-muted-foreground">Ready for review</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main content - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Currently Working On */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wrench className="h-5 w-5" />
                Currently Working On
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <p className="text-muted-foreground">Loading...</p>
              ) : inProgressJobs.length === 0 ? (
                <div className="text-center py-8">
                  <Wrench className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                  <p className="text-muted-foreground">No jobs in progress</p>
                  <p className="text-sm text-muted-foreground">Start a scheduled job to begin working</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {inProgressJobs.slice(0, 5).map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center justify-between p-4 border rounded-lg bg-blue-50/50 dark:bg-blue-950/20"
                    >
                      <div className="flex items-center gap-3">
                        <Car className="h-10 w-10 text-blue-500" />
                        <div>
                          <Link
                            to={`/jobs/${job.id}`}
                            className="font-semibold hover:underline text-lg"
                          >
                            {job.job_number}
                          </Link>
                          <p className="text-sm text-muted-foreground">
                            {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {job.customer_name}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleLogTime(job.id)}
                        >
                          <Timer className="h-4 w-4 mr-1" />
                          Log Time
                        </Button>
                        <Button variant="default" size="sm" asChild>
                          <Link to={`/jobs/${job.id}`}>Details</Link>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Scheduled Jobs */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Scheduled Jobs
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <p className="text-muted-foreground">Loading...</p>
              ) : scheduledJobs.length === 0 ? (
                <p className="text-muted-foreground">No scheduled jobs</p>
              ) : (
                <div className="space-y-3">
                  {scheduledJobs.slice(0, 5).map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <Car className="h-8 w-8 text-muted-foreground" />
                        <div>
                          <Link
                            to={`/jobs/${job.id}`}
                            className="font-medium hover:underline"
                          >
                            {job.job_number}
                          </Link>
                          <p className="text-sm text-muted-foreground">
                            {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
                          </p>
                          {('scheduled_drop_off' in job && job.scheduled_drop_off) && (
                            <p className="text-xs text-muted-foreground">
                              Drop-off: {new Date(job.scheduled_drop_off as string).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                      <Button variant="outline" size="sm" asChild>
                        <Link to={`/jobs/${job.id}`}>View</Link>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Waiting for Parts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <AlertCircle className="h-5 w-5 text-orange-500" />
                  Waiting for Parts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <p className="text-muted-foreground">Loading...</p>
                ) : waitingPartsJobs.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No jobs waiting</p>
                ) : (
                  <div className="space-y-3">
                    {waitingPartsJobs.slice(0, 3).map((job) => (
                      <div
                        key={job.id}
                        className="flex items-center justify-between p-2 border rounded"
                      >
                        <div>
                          <Link
                            to={`/jobs/${job.id}`}
                            className="font-medium hover:underline text-sm"
                          >
                            {job.job_number}
                          </Link>
                          <p className="text-xs text-muted-foreground">
                            {job.vehicle_make} {job.vehicle_model}
                          </p>
                        </div>
                        <Badge variant="outline" className="text-orange-500 border-orange-500 text-xs">
                          Waiting
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quality Check Queue */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <CheckCircle className="h-5 w-5 text-purple-500" />
                  Quality Check
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <p className="text-muted-foreground">Loading...</p>
                ) : qualityCheckJobs.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No jobs to review</p>
                ) : (
                  <div className="space-y-3">
                    {qualityCheckJobs.slice(0, 3).map((job) => (
                      <div
                        key={job.id}
                        className="flex items-center justify-between p-2 border rounded"
                      >
                        <div>
                          <Link
                            to={`/jobs/${job.id}`}
                            className="font-medium hover:underline text-sm"
                          >
                            {job.job_number}
                          </Link>
                          <p className="text-xs text-muted-foreground">
                            {job.vehicle_make} {job.vehicle_model}
                          </p>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/jobs/${job.id}`}>Review</Link>
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Sidebar - Week Summary & Quick Actions */}
        <div className="space-y-6">
          <WeekSummary />

          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2"
                  onClick={() => handleLogTime()}
                >
                  <Timer className="h-5 w-5 text-blue-500" />
                  <span className="text-xs">Log Hours</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2"
                  onClick={() => {/* Photo upload would go here */}}
                >
                  <Camera className="h-5 w-5 text-green-500" />
                  <span className="text-xs">Upload Photo</span>
                </Button>
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2"
                  asChild
                >
                  <Link to="/leads/new">
                    <MapPin className="h-5 w-5 text-orange-500" />
                    <span className="text-xs">Gas Station Lead</span>
                  </Link>
                </Button>
                <Button
                  variant="outline"
                  className="h-auto py-4 flex flex-col items-center gap-2"
                  asChild
                >
                  <Link to="/schedule">
                    <Calendar className="h-5 w-5 text-purple-500" />
                    <span className="text-xs">Schedule</span>
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Log Time Dialog */}
      <LogTimeDialog
        open={logTimeOpen}
        onOpenChange={setLogTimeOpen}
        jobs={jobs}
        preselectedJobId={selectedJobId}
      />
    </div>
  )
}
