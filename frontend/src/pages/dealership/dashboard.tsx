import { useQuery } from "@tanstack/react-query"
import { dealershipApi, DealerStats, DealerJob } from "@/api/dealership"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Link } from "react-router-dom"
import {
  Car,
  Wrench,
  CheckCircle2,
  Clock,
  DollarSign,
  TrendingUp,
  MapPin,
  ArrowRight,
  Calendar,
} from "lucide-react"

// Demo data for development
const DEMO_STATS: DealerStats = {
  total_vehicles: 47,
  pending_repair: 12,
  in_repair: 8,
  completed_this_month: 23,
  total_spent_this_month: 34500,
  avg_repair_time_days: 2.3,
  locations: [
    { id: 1, name: "Main Lot - Downtown", vehicles: 28, active_jobs: 5 },
    { id: 2, name: "North Campus", vehicles: 12, active_jobs: 3 },
    { id: 3, name: "Service Center", vehicles: 7, active_jobs: 2 },
  ],
}

const DEMO_RECENT_JOBS: DealerJob[] = [
  {
    id: 1,
    job_number: "DJ-2024-001",
    dealership_id: 1,
    vehicle_id: 1,
    vehicle: {
      id: 1,
      dealership_id: 1,
      stock_number: "A12345",
      vin: "1HGBH41JXMN109186",
      year: 2023,
      make: "Honda",
      model: "Accord",
      status: "in_repair",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    status: "IN_PROGRESS",
    status_label: "In Progress",
    scheduled_date: "2024-01-25",
    estimate_total: 1250,
  },
  {
    id: 2,
    job_number: "DJ-2024-002",
    dealership_id: 1,
    vehicle_id: 2,
    vehicle: {
      id: 2,
      dealership_id: 1,
      stock_number: "B67890",
      vin: "2HGBH41JXMN109187",
      year: 2024,
      make: "Toyota",
      model: "Camry",
      status: "pending_repair",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    status: "SCHEDULED",
    status_label: "Scheduled",
    scheduled_date: "2024-01-26",
    estimate_total: 890,
  },
  {
    id: 3,
    job_number: "DJ-2024-003",
    dealership_id: 1,
    vehicle_id: 3,
    vehicle: {
      id: 3,
      dealership_id: 1,
      stock_number: "C11223",
      vin: "3HGBH41JXMN109188",
      year: 2023,
      make: "Ford",
      model: "F-150",
      status: "ready",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    status: "COMPLETED",
    status_label: "Completed",
    completed_at: "2024-01-24",
    invoice_total: 1650,
  },
]

const statusColors: Record<string, string> = {
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  SCHEDULED: "bg-purple-100 text-purple-800",
  COMPLETED: "bg-green-100 text-green-800",
  PENDING: "bg-yellow-100 text-yellow-800",
}

export function DealershipDashboardPage() {
  // In production, replace with actual dealership ID from auth context
  const dealershipId = 1

  const { data: stats } = useQuery({
    queryKey: ["dealership", dealershipId, "stats"],
    queryFn: () => dealershipApi.getStats(dealershipId),
    placeholderData: DEMO_STATS,
  })

  const { data: jobsData } = useQuery({
    queryKey: ["dealership", dealershipId, "jobs"],
    queryFn: () => dealershipApi.getJobs(dealershipId),
    placeholderData: { jobs: DEMO_RECENT_JOBS, total: DEMO_RECENT_JOBS.length },
  })

  const recentJobs = jobsData?.jobs?.slice(0, 5) ?? DEMO_RECENT_JOBS

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Vehicles</CardTitle>
            <Car className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_vehicles ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              In inventory
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Repair</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.pending_repair ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              Awaiting service
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Repair</CardTitle>
            <Wrench className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.in_repair ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              Currently being repaired
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed This Month</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.completed_this_month ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              Vehicles repaired
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Secondary Stats */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Spend</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${(stats?.total_spent_this_month ?? 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              Total repair costs this month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg. Repair Time</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.avg_repair_time_days?.toFixed(1) ?? "0"} days
            </div>
            <p className="text-xs text-muted-foreground">
              Average turnaround time
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Jobs</CardTitle>
                <CardDescription>Latest repair requests</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/dealership/vehicles">
                  View All <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {job.vehicle?.year} {job.vehicle?.make} {job.vehicle?.model}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {job.vehicle?.stock_number}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {job.job_number}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {job.estimate_total && (
                      <span className="text-sm font-medium">
                        ${job.estimate_total.toLocaleString()}
                      </span>
                    )}
                    <Badge className={statusColors[job.status] ?? "bg-gray-100 text-gray-800"}>
                      {job.status_label}
                    </Badge>
                  </div>
                </div>
              ))}

              {recentJobs.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No active jobs
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Locations Overview */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Locations</CardTitle>
                <CardDescription>Vehicle distribution by location</CardDescription>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/dealership/locations">
                  Manage <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats?.locations?.map((location) => {
                const totalVehicles = stats.total_vehicles || 1
                const percentage = ((location.vehicles ?? 0) / totalVehicles) * 100

                return (
                  <div key={location.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{location.name}</span>
                      </div>
                      <div className="flex items-center gap-3 text-sm">
                        <span>{location.vehicles} vehicles</span>
                        <Badge variant="outline">{location.active_jobs} active</Badge>
                      </div>
                    </div>
                    <Progress value={percentage} className="h-2" />
                  </div>
                )
              })}

              {(!stats?.locations || stats.locations.length === 0) && (
                <div className="text-center py-8 text-muted-foreground">
                  No locations configured
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks for managing your fleet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Button variant="outline" className="h-auto py-4 flex flex-col gap-2" asChild>
              <Link to="/dealership/upload">
                <Car className="h-6 w-6" />
                <span>Batch Upload</span>
                <span className="text-xs text-muted-foreground">Import vehicles from CSV</span>
              </Link>
            </Button>

            <Button variant="outline" className="h-auto py-4 flex flex-col gap-2" asChild>
              <Link to="/dealership/vehicles?status=pending_repair">
                <Wrench className="h-6 w-6" />
                <span>Request Repairs</span>
                <span className="text-xs text-muted-foreground">Submit vehicles for repair</span>
              </Link>
            </Button>

            <Button variant="outline" className="h-auto py-4 flex flex-col gap-2" asChild>
              <Link to="/dealership/locations">
                <MapPin className="h-6 w-6" />
                <span>Manage Locations</span>
                <span className="text-xs text-muted-foreground">Add or edit locations</span>
              </Link>
            </Button>

            <Button variant="outline" className="h-auto py-4 flex flex-col gap-2" asChild>
              <Link to="/dealership/api">
                <Calendar className="h-6 w-6" />
                <span>API Settings</span>
                <span className="text-xs text-muted-foreground">Manage integration</span>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
