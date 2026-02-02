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
import { useEstimates } from "@/hooks/use-estimates"
import { Estimate } from "@/types"
import { Plus, Search } from "lucide-react"

const statusOptions = [
  { value: "all", label: "All Statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "SENT", label: "Sent" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
]

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  DRAFT: "secondary",
  SENT: "outline",
  APPROVED: "default",
  REJECTED: "destructive",
}

export function EstimatesPage() {
  const navigate = useNavigate()
  const [search, setSearch] = React.useState("")
  const [status, setStatus] = React.useState("all")

  const { data, isLoading } = useEstimates({
    search: search || undefined,
    status: status !== "all" ? status : undefined,
  })

  const estimates = data?.estimates || []

  const columns: Column<Estimate>[] = [
    {
      key: "estimate_number",
      header: "Estimate #",
      render: (estimate) => (
        <Link to={`/estimates/${estimate.id}`} className="font-medium hover:underline">
          {estimate.estimate_number}
        </Link>
      ),
    },
    {
      key: "customer_name",
      header: "Customer",
      render: (estimate) => estimate.customer_name || "—",
    },
    {
      key: "vehicle",
      header: "Vehicle",
      render: (estimate) =>
        estimate.vehicle_year
          ? `${estimate.vehicle_year} ${estimate.vehicle_make} ${estimate.vehicle_model}`
          : "—",
    },
    {
      key: "total",
      header: "Total",
      render: (estimate) => `$${(estimate.total || 0).toFixed(2)}`,
    },
    {
      key: "status",
      header: "Status",
      render: (estimate) => (
        <Badge variant={statusColors[estimate.status] || "outline"}>
          {estimate.status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Date",
      render: (estimate) => new Date(estimate.created_at).toLocaleDateString(),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Estimates"
        description="Create and manage repair estimates."
        actions={[
          {
            label: "New Estimate",
            onClick: () => navigate("/estimates/new"),
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
                placeholder="Search estimates..."
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
            data={estimates}
            isLoading={isLoading}
            onRowClick={(estimate) => navigate(`/estimates/${estimate.id}`)}
            emptyMessage="No estimates found"
            keyExtractor={(estimate) => estimate.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}
