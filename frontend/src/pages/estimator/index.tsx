import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Clock,
  FileText,
  CheckCircle,
  Plus,
  ArrowRight,
  Car,
  User,
} from "lucide-react"
import api from "@/api/client"

interface EstimateStats {
  needs_estimate: number
  drafts: number
  completed_today: number
}

interface JobNeedingEstimate {
  id: number
  customer_name: string
  vehicle: string
  checked_in_at: string
  time_ago: string
}

interface RecentEstimate {
  id: number
  estimate_number: string
  customer_name: string
  vehicle: string
  total: number
  status: string
}

export function EstimatorDashboardPage() {
  const [stats, setStats] = useState<EstimateStats>({
    needs_estimate: 0,
    drafts: 0,
    completed_today: 0,
  })
  const [jobsNeedingEstimate, setJobsNeedingEstimate] = useState<JobNeedingEstimate[]>([])
  const [recentEstimates, setRecentEstimates] = useState<RecentEstimate[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch estimator dashboard data
        const response = await api.get("/api/estimator/dashboard")
        if (response.data) {
          setStats(response.data.stats || stats)
          setJobsNeedingEstimate(response.data.jobs_needing_estimate || [])
          setRecentEstimates(response.data.recent_estimates || [])
        }
      } catch (error) {
        console.log("Using demo data for estimator dashboard")
        // Demo data for development
        setStats({
          needs_estimate: 5,
          drafts: 3,
          completed_today: 8,
        })
        setJobsNeedingEstimate([
          {
            id: 1,
            customer_name: "John Smith",
            vehicle: "2023 Toyota Camry",
            checked_in_at: "2025-01-23T09:00:00",
            time_ago: "2 hours ago",
          },
          {
            id: 2,
            customer_name: "Sarah Johnson",
            vehicle: "2022 Honda Accord",
            checked_in_at: "2025-01-23T10:30:00",
            time_ago: "30 min ago",
          },
          {
            id: 3,
            customer_name: "Mike Davis",
            vehicle: "2024 Ford F-150",
            checked_in_at: "2025-01-23T11:00:00",
            time_ago: "Just now",
          },
        ])
        setRecentEstimates([
          {
            id: 101,
            estimate_number: "EST-00101",
            customer_name: "Emily Brown",
            vehicle: "2023 BMW X5",
            total: 4250,
            status: "approved",
          },
          {
            id: 102,
            estimate_number: "EST-00102",
            customer_name: "Robert Wilson",
            vehicle: "2022 Chevrolet Silverado",
            total: 3800,
            status: "sent",
          },
          {
            id: 103,
            estimate_number: "EST-00103",
            customer_name: "Lisa Martinez",
            vehicle: "2021 Tesla Model 3",
            total: 2950,
            status: "draft",
          },
          {
            id: 104,
            estimate_number: "EST-00104",
            customer_name: "David Lee",
            vehicle: "2024 Audi Q7",
            total: 5600,
            status: "approved",
          },
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Approved</Badge>
      case "sent":
        return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">Sent</Badge>
      case "draft":
        return <Badge variant="secondary">Draft</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
    }).format(amount)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Estimator Dashboard"
        description="Create and manage vehicle damage estimates"
      />

      {/* Quick Start Banner */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white">
        <h2 className="text-lg font-semibold mb-2">Ready to Estimate?</h2>
        <p className="text-blue-100 mb-4">
          Start a new estimate or continue where you left off.
        </p>
        <Button asChild className="bg-white text-blue-600 hover:bg-blue-50">
          <Link to="/estimates/new">
            <Plus className="h-4 w-4 mr-2" />
            New Estimate
          </Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Needs Estimate</p>
                <p className="text-3xl font-bold text-yellow-600">{stats.needs_estimate}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-yellow-100 flex items-center justify-center">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">My Drafts</p>
                <p className="text-3xl font-bold text-blue-600">{stats.drafts}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completed Today</p>
                <p className="text-3xl font-bold text-green-600">{stats.completed_today}</p>
              </div>
              <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Jobs Needing Estimate */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base font-semibold">Needs Estimate</CardTitle>
            <span className="text-sm text-muted-foreground">
              {jobsNeedingEstimate.length} waiting
            </span>
          </CardHeader>
          <CardContent className="p-0">
            {jobsNeedingEstimate.length > 0 ? (
              <div className="divide-y">
                {jobsNeedingEstimate.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-4 hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <User className="h-5 w-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium truncate">{job.customer_name}</p>
                        <p className="text-sm text-muted-foreground truncate">
                          {job.vehicle}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 flex-shrink-0">
                      <span className="text-xs text-muted-foreground hidden sm:block">
                        {job.time_ago}
                      </span>
                      <Button size="sm" asChild>
                        <Link to={`/estimates/new?job_id=${job.id}`}>
                          Estimate
                        </Link>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
                <p className="font-medium">All caught up!</p>
                <p className="text-sm text-muted-foreground">
                  No vehicles waiting for estimates
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Estimates */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base font-semibold">My Recent Estimates</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/estimates">
                View all
                <ArrowRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {recentEstimates.length > 0 ? (
              <div className="divide-y">
                {recentEstimates.map((estimate) => (
                  <Link
                    key={estimate.id}
                    to={`/estimates/${estimate.id}`}
                    className="flex items-center justify-between p-4 hover:bg-muted/50"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                        <Car className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium truncate">{estimate.customer_name}</p>
                        <p className="text-sm text-muted-foreground truncate">
                          {estimate.vehicle}
                        </p>
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="font-semibold">{formatCurrency(estimate.total)}</p>
                      {getStatusBadge(estimate.status)}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                <p className="font-medium">No recent estimates</p>
                <p className="text-sm text-muted-foreground">
                  Start creating estimates to see them here
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Links</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <Button variant="outline" className="justify-start h-auto py-4" asChild>
              <Link to="/estimates">
                <FileText className="h-5 w-5 mr-3" />
                <div className="text-left">
                  <p className="font-medium">All Estimates</p>
                  <p className="text-xs text-muted-foreground">View and manage estimates</p>
                </div>
              </Link>
            </Button>
            <Button variant="outline" className="justify-start h-auto py-4" asChild>
              <Link to="/jobs">
                <Car className="h-5 w-5 mr-3" />
                <div className="text-left">
                  <p className="font-medium">Jobs</p>
                  <p className="text-xs text-muted-foreground">View all jobs</p>
                </div>
              </Link>
            </Button>
            <Button variant="outline" className="justify-start h-auto py-4" asChild>
              <Link to="/customers">
                <User className="h-5 w-5 mr-3" />
                <div className="text-left">
                  <p className="font-medium">Customers</p>
                  <p className="text-xs text-muted-foreground">Customer database</p>
                </div>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
