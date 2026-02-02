import * as React from "react"
import { Link, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useLeads, useConvertLead } from "@/hooks/use-leads"
import { Lead } from "@/types"
import { Plus, Search, UserCheck } from "lucide-react"

const statusOptions = [
  { value: "all", label: "All Statuses" },
  { value: "NEW", label: "New" },
  { value: "CONTACTED", label: "Contacted" },
  { value: "QUALIFIED", label: "Qualified" },
  { value: "CONVERTED", label: "Converted" },
  { value: "LOST", label: "Lost" },
]

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  NEW: "default",
  CONTACTED: "secondary",
  QUALIFIED: "default",
  CONVERTED: "outline",
  LOST: "destructive",
}

export function LeadsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = React.useState("")
  const [status, setStatus] = React.useState("all")
  const convertLead = useConvertLead()

  const { data, isLoading } = useLeads({
    search: search || undefined,
    status: status !== "all" ? status : undefined,
  })

  const leads = data?.leads || []

  const handleConvert = (e: React.MouseEvent, leadId: number) => {
    e.stopPropagation()
    if (confirm("Convert this lead to a customer?")) {
      convertLead.mutate(leadId)
    }
  }

  const columns: Column<Lead>[] = [
    {
      key: "name",
      header: "Name",
      render: (lead) => (
        <Link to={`/leads/${lead.id}`} className="font-medium hover:underline">
          {lead.display_name || lead.name || `${lead.first_name} ${lead.last_name}`.trim() || "—"}
        </Link>
      ),
    },
    {
      key: "email",
      header: "Email",
      render: (lead) => lead.email || "—",
    },
    {
      key: "phone",
      header: "Phone",
      render: (lead) => lead.phone || "—",
    },
    {
      key: "source",
      header: "Source",
      render: (lead) => lead.source || "—",
    },
    {
      key: "status",
      header: "Status",
      render: (lead) => (
        <Badge variant={statusColors[lead.status] || "outline"}>
          {lead.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (lead) =>
        lead.status !== "CONVERTED" && lead.status !== "LOST" ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => handleConvert(e, lead.id)}
            disabled={convertLead.isPending}
          >
            <UserCheck className="h-4 w-4 mr-1" />
            Convert
          </Button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Leads"
        description="Manage potential customers and conversions."
        actions={[
          {
            label: "New Lead",
            onClick: () => navigate("/leads/new"),
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
                placeholder="Search leads..."
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
            data={leads}
            isLoading={isLoading}
            onRowClick={(lead) => navigate(`/leads/${lead.id}`)}
            emptyMessage="No leads found"
            keyExtractor={(lead) => lead.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}
