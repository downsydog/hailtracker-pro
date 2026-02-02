import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { StatCard } from "@/components/app/stat-card"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useJobs } from "@/hooks/use-jobs"
import { useLeads } from "@/hooks/use-leads"
import { Job, Lead } from "@/types"
import {
  Briefcase,
  Users,
  DollarSign,
  TrendingUp,
  ArrowRight,
} from "lucide-react"

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
    key: "customer_name",
    header: "Customer",
  },
  {
    key: "vehicle",
    header: "Vehicle",
    render: (job) => job.vehicle_year ? `${job.vehicle_year} ${job.vehicle_make || ''} ${job.vehicle_model || ''}`.trim() : "—",
  },
  {
    key: "status",
    header: "Status",
    render: (job) => <Badge variant="outline">{job.status}</Badge>,
  },
]

const leadColumns: Column<Lead>[] = [
  {
    key: "name",
    header: "Name",
    render: (lead) => (
      <Link to={`/leads/${lead.id}`} className="font-medium hover:underline">
        {lead.display_name || lead.name || `${lead.first_name || ''} ${lead.last_name || ''}`.trim() || "—"}
      </Link>
    ),
  },
  {
    key: "source",
    header: "Source",
  },
  {
    key: "status",
    header: "Status",
    render: (lead) => <Badge variant="secondary">{lead.status}</Badge>,
  },
]

export function DashboardPage() {
  const { data: jobsData, isLoading: jobsLoading } = useJobs({ limit: 5 })
  const { data: leadsData, isLoading: leadsLoading } = useLeads({ limit: 5, status: "NEW" })

  const jobs = jobsData?.jobs || []
  const leads = leadsData?.leads || []
  const stats = jobsData?.stats || { total: 0, in_progress: 0, completed_this_week: 0, total_revenue: 0 }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Welcome back! Here's an overview of your business."
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Active Jobs"
          value={stats.in_progress || 0}
          icon={Briefcase}
          description="Currently in progress"
        />
        <StatCard
          title="Total Jobs"
          value={stats.total || 0}
          icon={Users}
          description="All time"
        />
        <StatCard
          title="Total Revenue"
          value={`$${(stats.total_revenue || 0).toLocaleString()}`}
          icon={DollarSign}
          description="From completed jobs"
        />
        <StatCard
          title="New Leads"
          value={leadsData?.total || leads.length || 0}
          icon={TrendingUp}
          description="Awaiting follow-up"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Jobs</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/jobs">
                View all <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={jobColumns}
              data={jobs}
              isLoading={jobsLoading}
              emptyMessage="No recent jobs"
              keyExtractor={(job) => job.id}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>New Leads</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/leads">
                View all <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={leadColumns}
              data={leads}
              isLoading={leadsLoading}
              emptyMessage="No new leads"
              keyExtractor={(lead) => lead.id}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
