import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useLeads } from "@/hooks/use-leads"
import { useEstimates } from "@/hooks/use-estimates"
import { useJobs } from "@/hooks/use-jobs"
import {
  DollarSign,
  Users,
  FileText,
  TrendingUp,
  Phone,
  Calendar,
  Target,
  Award,
} from "lucide-react"

export function SalesDashboardPage() {
  const { data: leadsData, isLoading: leadsLoading } = useLeads({ per_page: 50 })
  const { data: estimatesData, isLoading: estimatesLoading } = useEstimates({ per_page: 50 })
  const { data: jobsData, isLoading: jobsLoading } = useJobs({ per_page: 10 })

  const leads = leadsData?.leads || []
  const estimates = estimatesData?.estimates || []
  const stats = jobsData?.stats

  // Calculate lead stats
  const newLeads = leads.filter((l) => l.status === "NEW")
  const qualifiedLeads = leads.filter((l) => l.status === "QUALIFIED")

  // Calculate estimate stats
  const pendingEstimates = estimates.filter((e) => e.status === "DRAFT" || e.status === "SENT")
  const approvedEstimates = estimates.filter((e) => e.status === "APPROVED")

  // Calculate total potential revenue from pending estimates
  const pendingRevenue = pendingEstimates.reduce((sum, e) => sum + (e.total || 0), 0)
  const approvedRevenue = approvedEstimates.reduce((sum, e) => sum + (e.total || 0), 0)

  const isLoading = leadsLoading || estimatesLoading || jobsLoading

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sales Dashboard"
        description="Track leads, estimates, and sales performance"
      />

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">New Leads</CardTitle>
            <Users className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{newLeads.length}</div>
            <p className="text-xs text-muted-foreground">Awaiting first contact</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pending Estimates</CardTitle>
            <FileText className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingEstimates.length}</div>
            <p className="text-xs text-muted-foreground">
              ${pendingRevenue.toLocaleString()} potential
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Approved This Week</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{approvedEstimates.length}</div>
            <p className="text-xs text-muted-foreground">
              ${approvedRevenue.toLocaleString()} value
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${(stats?.total_revenue || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">From completed jobs</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* New Leads to Contact */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Leads to Contact
            </CardTitle>
            <Button variant="outline" size="sm" asChild>
              <Link to="/leads/new">Add Lead</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : newLeads.length === 0 ? (
              <p className="text-muted-foreground">No new leads</p>
            ) : (
              <div className="space-y-4">
                {newLeads.slice(0, 5).map((lead) => (
                  <div
                    key={lead.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div>
                      <Link
                        to={`/leads/${lead.id}`}
                        className="font-medium hover:underline"
                      >
                        {lead.first_name} {lead.last_name}
                      </Link>
                      <p className="text-sm text-muted-foreground">{lead.phone}</p>
                      {lead.source && (
                        <p className="text-xs text-muted-foreground">
                          Source: {lead.source}
                        </p>
                      )}
                    </div>
                    <Badge variant="outline" className="text-blue-500 border-blue-500">
                      New
                    </Badge>
                  </div>
                ))}
                {newLeads.length > 5 && (
                  <Button variant="link" className="w-full" asChild>
                    <Link to="/leads?status=NEW">View all {newLeads.length} leads</Link>
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Qualified Leads */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-green-500" />
              Qualified Leads
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : qualifiedLeads.length === 0 ? (
              <p className="text-muted-foreground">No qualified leads</p>
            ) : (
              <div className="space-y-4">
                {qualifiedLeads.slice(0, 5).map((lead) => (
                  <div
                    key={lead.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div>
                      <Link
                        to={`/leads/${lead.id}`}
                        className="font-medium hover:underline"
                      >
                        {lead.first_name} {lead.last_name}
                      </Link>
                      <p className="text-sm text-muted-foreground">
                        {lead.vehicle_year} {lead.vehicle_make} {lead.vehicle_model}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/estimates/new?lead_id=${lead.id}`}>
                        Create Estimate
                      </Link>
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pending Estimates */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-yellow-500" />
              Pending Estimates
            </CardTitle>
            <Button variant="outline" size="sm" asChild>
              <Link to="/estimates/new">New Estimate</Link>
            </Button>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : pendingEstimates.length === 0 ? (
              <p className="text-muted-foreground">No pending estimates</p>
            ) : (
              <div className="space-y-4">
                {pendingEstimates.slice(0, 5).map((estimate) => (
                  <div
                    key={estimate.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div>
                      <Link
                        to={`/estimates/${estimate.id}`}
                        className="font-medium hover:underline"
                      >
                        {estimate.estimate_number}
                      </Link>
                      <p className="text-sm text-muted-foreground">
                        {estimate.customer_name}
                      </p>
                      <p className="text-sm font-medium text-green-600">
                        ${estimate.total?.toLocaleString() || "0"}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={
                        estimate.status === "SENT"
                          ? "text-blue-500 border-blue-500"
                          : "text-gray-500 border-gray-500"
                      }
                    >
                      {estimate.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recently Approved */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5 text-green-500" />
              Recently Approved
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-muted-foreground">Loading...</p>
            ) : approvedEstimates.length === 0 ? (
              <p className="text-muted-foreground">No approved estimates yet</p>
            ) : (
              <div className="space-y-4">
                {approvedEstimates.slice(0, 5).map((estimate) => (
                  <div
                    key={estimate.id}
                    className="flex items-center justify-between p-3 border rounded-lg bg-green-50 dark:bg-green-950"
                  >
                    <div>
                      <Link
                        to={`/estimates/${estimate.id}`}
                        className="font-medium hover:underline"
                      >
                        {estimate.estimate_number}
                      </Link>
                      <p className="text-sm text-muted-foreground">
                        {estimate.customer_name}
                      </p>
                    </div>
                    <span className="font-semibold text-green-600">
                      ${estimate.total?.toLocaleString() || "0"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button asChild>
              <Link to="/leads/new">
                <Users className="h-4 w-4 mr-2" />
                Add New Lead
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/estimates/new">
                <FileText className="h-4 w-4 mr-2" />
                Create Estimate
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/customers/new">
                <Users className="h-4 w-4 mr-2" />
                Add Customer
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/jobs/new">
                <Calendar className="h-4 w-4 mr-2" />
                Schedule Job
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
