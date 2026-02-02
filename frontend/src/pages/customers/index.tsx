import * as React from "react"
import { Link, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { DataTable, Column } from "@/components/app/data-table"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useCustomers } from "@/hooks/use-customers"
import { Customer } from "@/types"
import { Plus, Search, Phone, Mail } from "lucide-react"

export function CustomersPage() {
  const navigate = useNavigate()
  const [search, setSearch] = React.useState("")

  const { data, isLoading } = useCustomers({
    search: search || undefined,
  })

  const customers = data?.customers || []

  const columns: Column<Customer>[] = [
    {
      key: "name",
      header: "Name",
      render: (customer) => (
        <Link to={`/customers/${customer.id}`} className="font-medium hover:underline">
          {customer.first_name} {customer.last_name}
        </Link>
      ),
    },
    {
      key: "email",
      header: "Email",
      render: (customer) => (
        <span className="flex items-center gap-2">
          <Mail className="h-4 w-4 text-muted-foreground" />
          {customer.email || "—"}
        </span>
      ),
    },
    {
      key: "phone",
      header: "Phone",
      render: (customer) => (
        <span className="flex items-center gap-2">
          <Phone className="h-4 w-4 text-muted-foreground" />
          {customer.phone || "—"}
        </span>
      ),
    },
    {
      key: "jobs_count",
      header: "Jobs",
      render: (customer) => customer.jobs_count || 0,
    },
    {
      key: "created_at",
      header: "Customer Since",
      render: (customer) => new Date(customer.created_at).toLocaleDateString(),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customers"
        description="Manage your customer database."
        actions={[
          {
            label: "New Customer",
            onClick: () => navigate("/customers/new"),
            icon: Plus,
          },
        ]}
      />

      <Card>
        <CardContent className="pt-6">
          <div className="relative mb-6">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search customers..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 max-w-md"
            />
          </div>

          <DataTable
            columns={columns}
            data={customers}
            isLoading={isLoading}
            onRowClick={(customer) => navigate(`/customers/${customer.id}`)}
            emptyMessage="No customers found"
            keyExtractor={(customer) => customer.id}
          />
        </CardContent>
      </Card>
    </div>
  )
}
