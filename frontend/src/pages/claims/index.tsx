import { useState } from "react"
import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { claimsApi } from "@/api/claims"
import {
  Plus,
  Search,
  Shield,
  Clock,
  CheckCircle,
  DollarSign,
  Phone,
} from "lucide-react"

// Local claim type for list view
interface Claim {
  id: number
  claim_number: string
  insurance_company: string
  status: string
  adjuster_name?: string
  adjuster_phone?: string
  claimed_amount?: number
  approved_amount?: number
  job_number?: string
  customer_name: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
  next_follow_up_date?: string
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-800",
  submitted: "bg-blue-100 text-blue-800",
  in_review: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  paid: "bg-emerald-100 text-emerald-800",
  closed: "bg-gray-100 text-gray-800",
}

export function ClaimsPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  // Fetch claims using typed API
  const { data, isLoading } = useQuery({
    queryKey: ["claims", page, statusFilter],
    queryFn: () =>
      claimsApi.getClaims({
        page,
        per_page: 20,
        status: statusFilter !== "all" ? statusFilter : undefined,
      }),
  })

  // Fetch claim stats
  const { data: statsData } = useQuery({
    queryKey: ["claims-stats"],
    queryFn: () => claimsApi.getStats(),
  })

  const claims = (data?.claims || []) as Claim[]
  const totalPages = data?.total ? Math.ceil(data.total / 20) : 1
  const stats = {
    submitted_count: statsData?.total_pending || 0,
    pending_adjuster_count: statsData?.total_in_review || 0,
    approved_count: statsData?.total_approved || 0,
    paid_count: 0,
    total_approved: statsData?.total_value_pending || 0,
    total_received: 0,
  }

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return "$0.00"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  const filteredClaims = claims.filter((claim) => {
    if (!search) return true
    const searchLower = search.toLowerCase()
    return (
      claim.claim_number?.toLowerCase().includes(searchLower) ||
      claim.customer_name?.toLowerCase().includes(searchLower) ||
      claim.insurance_company?.toLowerCase().includes(searchLower) ||
      claim.job_number?.toLowerCase().includes(searchLower)
    )
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Insurance Claims"
          description="Track and manage insurance claims"
        />
        <Button asChild>
          <Link to="/claims/new">
            <Plus className="h-4 w-4 mr-2" />
            New Claim
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Filed</CardTitle>
            <Shield className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.submitted_count || 0}</div>
            <p className="text-xs text-muted-foreground">Awaiting response</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">In Review</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {stats.pending_adjuster_count || 0}
            </div>
            <p className="text-xs text-muted-foreground">Need follow-up</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Approved</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats.approved_count || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats.total_approved || 0)} approved
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Paid</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600">
              {stats.paid_count || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(stats.total_received || 0)} received
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search claims..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="submitted">Submitted</SelectItem>
            <SelectItem value="in_review">In Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="denied">Denied</SelectItem>
            <SelectItem value="paid">Paid</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Claims Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Claim #</TableHead>
                <TableHead>Insurance</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Vehicle</TableHead>
                <TableHead>Adjuster</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Claimed</TableHead>
                <TableHead className="text-right">Approved</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    Loading claims...
                  </TableCell>
                </TableRow>
              ) : filteredClaims.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    <Shield className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                    <p className="text-muted-foreground">No claims found</p>
                    <Button asChild variant="link" className="mt-2">
                      <Link to="/claims/new">File a new claim</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ) : (
                filteredClaims.map((claim) => (
                  <TableRow key={claim.id}>
                    <TableCell>
                      <Link
                        to={`/claims/${claim.id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {claim.claim_number}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{claim.insurance_company}</div>
                    </TableCell>
                    <TableCell>
                      <div>{claim.customer_name || "—"}</div>
                      {claim.job_number && (
                        <Link
                          to={`/jobs/${claim.job_number}`}
                          className="text-xs text-muted-foreground hover:underline"
                        >
                          {claim.job_number}
                        </Link>
                      )}
                    </TableCell>
                    <TableCell>
                      {claim.vehicle_year ? (
                        <span className="text-sm">
                          {claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {claim.adjuster_name ? (
                        <div>
                          <div className="font-medium text-sm">{claim.adjuster_name}</div>
                          {claim.adjuster_phone && (
                            <a
                              href={`tel:${claim.adjuster_phone}`}
                              className="text-xs text-muted-foreground hover:underline flex items-center gap-1"
                            >
                              <Phone className="h-3 w-3" />
                              {claim.adjuster_phone}
                            </a>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">Not assigned</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[claim.status] || "bg-gray-100"}>
                        {claim.status?.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                      </Badge>
                      {claim.next_follow_up_date && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Follow-up: {new Date(claim.next_follow_up_date).toLocaleDateString()}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(claim.claimed_amount ?? 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {claim.approved_amount ? (
                        <span className="text-green-600 font-medium">
                          {formatCurrency(claim.approved_amount)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" asChild>
                          <Link to={`/claims/${claim.id}`}>View</Link>
                        </Button>
                        <Button variant="outline" size="sm" asChild>
                          <Link to={`/claims/${claim.id}/edit`}>Edit</Link>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="flex items-center px-4 text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}
