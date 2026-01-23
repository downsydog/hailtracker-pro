import { useState } from "react"
import { PageHeader } from "@/components/app/page-header"
import { StatCard } from "@/components/app/stat-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { reportsApi } from "@/api/reports"
import { useQuery } from "@tanstack/react-query"
import {
  RevenueChart,
  JobsStatusChart,
  LeadSourcesChart,
  TechPerformanceChart,
} from "@/components/app/charts"
import {
  Briefcase,
  DollarSign,
  Users,
  TrendingUp,
  Calendar,
} from "lucide-react"

const timeRanges = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
  { value: "1y", label: "Last year" },
]

function getDateRange(range: string): { start_date?: string; end_date?: string } {
  const end = new Date()
  const start = new Date()

  switch (range) {
    case "7d":
      start.setDate(start.getDate() - 7)
      break
    case "30d":
      start.setDate(start.getDate() - 30)
      break
    case "90d":
      start.setDate(start.getDate() - 90)
      break
    case "1y":
      start.setFullYear(start.getFullYear() - 1)
      break
  }

  return {
    start_date: start.toISOString().split("T")[0],
    end_date: end.toISOString().split("T")[0],
  }
}

export function ReportsPage() {
  const [timeRange, setTimeRange] = useState("30d")
  const dateRange = getDateRange(timeRange)

  // Dashboard stats
  const { data: dashboardData } = useQuery({
    queryKey: ["reports", "dashboard", timeRange],
    queryFn: () => reportsApi.dashboard(dateRange),
  })

  // Revenue report with chart data
  const { data: revenueData, isLoading: revenueLoading } = useQuery({
    queryKey: ["reports", "revenue", timeRange],
    queryFn: () => reportsApi.revenue(dateRange),
  })

  // Jobs by status
  const { data: jobsStatusData, isLoading: jobsStatusLoading } = useQuery({
    queryKey: ["reports", "jobs-status"],
    queryFn: () => reportsApi.jobsByStatus(),
  })

  // Lead sources
  const { data: leadSourcesData, isLoading: leadSourcesLoading } = useQuery({
    queryKey: ["reports", "lead-sources"],
    queryFn: () => reportsApi.leadSources(),
  })

  // Tech performance
  const { data: techPerfData, isLoading: techPerfLoading } = useQuery({
    queryKey: ["reports", "tech-performance", timeRange],
    queryFn: () => reportsApi.techs(dateRange),
  })

  // Extract stats from dashboard data
  const revenue = dashboardData?.revenue
  const jobsCompleted = dashboardData?.jobs_completed
  const avgJobValue = dashboardData?.avg_job_value
  const leadConversion = dashboardData?.lead_conversion

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="Business analytics and insights.">
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-40">
            <Calendar className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {timeRanges.map((range) => (
              <SelectItem key={range.value} value={range.value}>
                {range.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </PageHeader>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Revenue"
          value={`$${(revenue?.total || 0).toLocaleString()}`}
          icon={DollarSign}
          trend={
            revenue?.change
              ? { value: revenue.change, isPositive: revenue.change > 0 }
              : undefined
          }
          description={revenue?.period || "This period"}
        />
        <StatCard
          title="Jobs Completed"
          value={jobsCompleted?.total || 0}
          icon={Briefcase}
          trend={
            jobsCompleted?.change
              ? { value: jobsCompleted.change, isPositive: jobsCompleted.change > 0 }
              : undefined
          }
        />
        <StatCard
          title="Avg Job Value"
          value={`$${(avgJobValue?.total || 0).toLocaleString()}`}
          icon={TrendingUp}
          trend={
            avgJobValue?.change
              ? { value: avgJobValue.change, isPositive: avgJobValue.change > 0 }
              : undefined
          }
        />
        <StatCard
          title="Lead Conversion"
          value={`${(leadConversion?.rate || 0).toFixed(1)}%`}
          icon={Users}
          trend={
            leadConversion?.change
              ? { value: leadConversion.change, isPositive: leadConversion.change > 0 }
              : undefined
          }
        />
      </div>

      {/* Tabs for different report views */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="revenue">Revenue</TabsTrigger>
          <TabsTrigger value="jobs">Jobs</TabsTrigger>
          <TabsTrigger value="leads">Leads</TabsTrigger>
          <TabsTrigger value="techs">Technicians</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <RevenueChart
              data={revenueData?.chart_data}
              isLoading={revenueLoading}
            />
            <JobsStatusChart
              data={jobsStatusData}
              isLoading={jobsStatusLoading}
            />
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <LeadSourcesChart
              data={leadSourcesData}
              isLoading={leadSourcesLoading}
            />
            <TechPerformanceChart
              data={techPerfData?.jobs_comparison}
              isLoading={techPerfLoading}
            />
          </div>
        </TabsContent>

        {/* Revenue Tab */}
        <TabsContent value="revenue" className="space-y-6">
          <RevenueChart
            data={revenueData?.chart_data}
            isLoading={revenueLoading}
          />

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Service Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Service Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                {revenueData?.service_breakdown?.labels?.length ? (
                  <div className="space-y-3">
                    {revenueData.service_breakdown.labels.map((label, index) => {
                      const value = revenueData.service_breakdown.values[index] || 0
                      const total = revenueData.service_breakdown.values.reduce((a, b) => a + b, 0)
                      const percent = total > 0 ? (value / total) * 100 : 0
                      return (
                        <div key={label} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span>{label}</span>
                            <span className="font-medium">${value.toLocaleString()}</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full"
                              style={{ width: `${percent}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No service data available</p>
                )}
              </CardContent>
            </Card>

            {/* Revenue Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Revenue Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm text-muted-foreground">Total Revenue</dt>
                    <dd className="text-2xl font-bold">
                      ${(revenueData?.stats?.total_revenue || 0).toLocaleString()}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">Avg Per Job</dt>
                    <dd className="text-2xl font-bold">
                      ${(revenueData?.stats?.avg_per_job || 0).toLocaleString()}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">Best Day</dt>
                    <dd className="text-lg font-semibold">
                      {revenueData?.stats?.best_day || "N/A"}
                    </dd>
                    <dd className="text-sm text-muted-foreground">
                      ${(revenueData?.stats?.best_day_revenue || 0).toLocaleString()}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">Projected Monthly</dt>
                    <dd className="text-2xl font-bold">
                      ${(revenueData?.stats?.projected_monthly || 0).toLocaleString()}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </div>

          {/* Top Jobs */}
          {revenueData?.top_jobs?.length ? (
            <Card>
              <CardHeader>
                <CardTitle>Top Jobs by Revenue</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {revenueData.top_jobs.slice(0, 5).map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{job.customer}</p>
                        <p className="text-sm text-muted-foreground">
                          {job.vehicle} - {job.service}
                        </p>
                        <p className="text-xs text-muted-foreground">{job.date}</p>
                      </div>
                      <span className="text-lg font-bold text-green-600">
                        ${job.amount.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </TabsContent>

        {/* Jobs Tab */}
        <TabsContent value="jobs" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <JobsStatusChart
              data={jobsStatusData}
              isLoading={jobsStatusLoading}
            />
            <Card>
              <CardHeader>
                <CardTitle>Job Statistics</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm text-muted-foreground">Total Jobs</dt>
                    <dd className="text-2xl font-bold">
                      {jobsStatusData?.values?.reduce((a, b) => a + b, 0) || 0}
                    </dd>
                  </div>
                  {jobsStatusData?.labels?.map((label, index) => (
                    <div key={label}>
                      <dt className="text-sm text-muted-foreground">{label}</dt>
                      <dd className="text-xl font-bold">
                        {jobsStatusData.values[index] || 0}
                      </dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Leads Tab */}
        <TabsContent value="leads" className="space-y-6">
          <LeadSourcesChart
            data={leadSourcesData}
            isLoading={leadSourcesLoading}
          />

          <Card>
            <CardHeader>
              <CardTitle>Lead Source Details</CardTitle>
            </CardHeader>
            <CardContent>
              {leadSourcesData?.labels?.length ? (
                <div className="space-y-3">
                  {leadSourcesData.labels.map((label, index) => {
                    const value = leadSourcesData.values[index] || 0
                    const total = leadSourcesData.values.reduce((a, b) => a + b, 0)
                    const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0
                    return (
                      <div
                        key={label}
                        className="flex items-center justify-between p-3 border rounded-lg"
                      >
                        <span className="font-medium">{label}</span>
                        <div className="text-right">
                          <span className="text-lg font-bold">{value}</span>
                          <span className="text-sm text-muted-foreground ml-2">
                            ({percent}%)
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-muted-foreground">No lead data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Technicians Tab */}
        <TabsContent value="techs" className="space-y-6">
          <TechPerformanceChart
            data={techPerfData?.jobs_comparison}
            isLoading={techPerfLoading}
          />

          <Card>
            <CardHeader>
              <CardTitle>Technician Details</CardTitle>
            </CardHeader>
            <CardContent>
              {techPerfData?.techs?.length ? (
                <div className="space-y-3">
                  {techPerfData.techs.map((tech: { id: number; name: string; jobs_completed: number; revenue: number; efficiency: number; customer_rating: number }) => (
                    <div
                      key={tech.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <span className="font-medium">{tech.name}</span>
                      <div className="flex gap-4 text-sm">
                        <span className="text-muted-foreground">
                          Jobs: <strong>{tech.jobs_completed}</strong>
                        </span>
                        <span className="text-muted-foreground">
                          Revenue: <strong>${tech.revenue.toLocaleString()}</strong>
                        </span>
                        <span className="text-muted-foreground">
                          Efficiency: <strong>{tech.efficiency}%</strong>
                        </span>
                        <span className="text-muted-foreground">
                          Rating: <strong>{tech.customer_rating}</strong>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No technician data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
