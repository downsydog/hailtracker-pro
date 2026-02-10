import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
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
import {
  useInvoices,
  useIssueInvoice,
  Invoice,
  InvoiceStatus,
  PayerType,
  invoiceStatusColors,
  invoiceStatusLabels,
  payerTypeLabels,
  allocationTypeLabels,
  allocationTypeColors,
  AllocationType,
} from "@/hooks/use-invoices"
import {
  Plus,
  Search,
  FileText,
  Send,
  DollarSign,
  AlertCircle,
  CheckCircle,
  Loader2,
  Download,
  ChevronDown,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import {
  useExportInvoicesCSV,
  useExportPaymentsCSV,
  getDefaultDateRange,
} from "@/hooks/use-exports"

export function InvoicesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [payerFilter, setPayerFilter] = useState<string>("all")

  // Export state
  const defaultDates = getDefaultDateRange()
  const [exportStartDate, setExportStartDate] = useState(defaultDates.start)
  const [exportEndDate, setExportEndDate] = useState(defaultDates.end)

  // Export hooks
  const exportInvoices = useExportInvoicesCSV()
  const exportPayments = useExportPaymentsCSV()

  // Fetch invoices using new hooks
  const { data, isLoading } = useInvoices({
    status: statusFilter !== "all" ? (statusFilter as InvoiceStatus) : undefined,
    payer_type: payerFilter !== "all" ? (payerFilter as PayerType) : undefined,
    page,
    per_page: 20,
  })

  // Issue invoice mutation
  const issueInvoice = useIssueInvoice()

  const invoices = data?.invoices || []
  const totalPages = data?.pages || 1

  // Calculate stats from loaded invoices
  const stats = {
    draft_count: invoices.filter(i => i.status === 'draft').length,
    issued_count: invoices.filter(i => i.status === 'issued').length,
    overdue_count: invoices.filter(i => i.is_overdue).length,
    paid_count: invoices.filter(i => i.status === 'paid').length,
    total_outstanding: invoices.reduce((sum, i) => sum + (i.balance_due || 0), 0),
  }

  const formatCurrency = (amount: number | null) => {
    if (amount == null) return "$0.00"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  // Client-side search filtering
  const filteredInvoices = invoices.filter((inv) => {
    if (!search) return true
    const searchLower = search.toLowerCase()
    return (
      inv.invoice_number?.toLowerCase().includes(searchLower) ||
      inv.payer_name?.toLowerCase().includes(searchLower) ||
      inv.estimate?.customer_name?.toLowerCase().includes(searchLower) ||
      inv.estimate?.vehicle_display?.toLowerCase().includes(searchLower)
    )
  })

  const handleIssue = async (invoice: Invoice) => {
    await issueInvoice.mutateAsync(invoice.id)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <PageHeader
          title="Invoices"
          description="Manage customer invoices and payments"
        />
        <div className="flex items-center gap-2">
          {/* Export Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Export
                <ChevronDown className="h-4 w-4 ml-2" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-72">
              <div className="p-3 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Start Date</Label>
                    <Input
                      type="date"
                      value={exportStartDate}
                      onChange={(e) => setExportStartDate(e.target.value)}
                      className="h-8"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">End Date</Label>
                    <Input
                      type="date"
                      value={exportEndDate}
                      onChange={(e) => setExportEndDate(e.target.value)}
                      className="h-8"
                    />
                  </div>
                </div>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => exportInvoices.mutate({
                  start: exportStartDate,
                  end: exportEndDate,
                  status: statusFilter !== 'all' ? statusFilter : undefined,
                  payer_type: payerFilter !== 'all' ? payerFilter : undefined,
                })}
                disabled={exportInvoices.isPending}
                className="cursor-pointer"
              >
                {exportInvoices.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <FileText className="h-4 w-4 mr-2" />
                )}
                Export Invoices CSV
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => exportPayments.mutate({
                  start: exportStartDate,
                  end: exportEndDate,
                  payer_type: payerFilter !== 'all' ? payerFilter : undefined,
                })}
                disabled={exportPayments.isPending}
                className="cursor-pointer"
              >
                {exportPayments.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <DollarSign className="h-4 w-4 mr-2" />
                )}
                Export Payments CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button asChild>
            <Link to="/invoices/new">
              <Plus className="h-4 w-4 mr-2" />
              New Invoice
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Draft</CardTitle>
            <FileText className="h-4 w-4 text-gray-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.draft_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Issued</CardTitle>
            <Send className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.issued_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Overdue</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {stats.overdue_count}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Paid</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats.paid_count}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Outstanding Summary */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Total Outstanding
              </p>
              <p className="text-3xl font-bold">
                {formatCurrency(stats.total_outstanding)}
              </p>
            </div>
            <DollarSign className="h-12 w-12 text-blue-500 opacity-50" />
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search invoices..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="issued">Issued</SelectItem>
            <SelectItem value="partial_paid">Partial Paid</SelectItem>
            <SelectItem value="paid">Paid</SelectItem>
            <SelectItem value="void">Void</SelectItem>
          </SelectContent>
        </Select>
        <Select value={payerFilter} onValueChange={setPayerFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by payer" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Payers</SelectItem>
            <SelectItem value="customer">Customer</SelectItem>
            <SelectItem value="insurer">Insurance</SelectItem>
            <SelectItem value="dealership">Dealership</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Invoices Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Payer</TableHead>
                <TableHead>Customer / Vehicle</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Paid</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead>Issued</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                    Loading invoices...
                  </TableCell>
                </TableRow>
              ) : filteredInvoices.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    <FileText className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                    <p className="text-muted-foreground">No invoices found</p>
                    <Button asChild variant="link" className="mt-2">
                      <Link to="/invoices/new">Create your first invoice</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ) : (
                filteredInvoices.map((invoice) => (
                  <TableRow
                    key={invoice.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => navigate(`/invoices/${invoice.id}`)}
                  >
                    <TableCell>
                      <span className="font-medium text-primary">
                        {invoice.invoice_number}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge className={invoiceStatusColors[invoice.status]}>
                        {invoiceStatusLabels[invoice.status]}
                      </Badge>
                      {invoice.is_overdue && invoice.status !== 'paid' && invoice.status !== 'void' && (
                        <Badge variant="destructive" className="ml-1 text-xs">
                          Overdue
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <Badge variant="outline">
                          {payerTypeLabels[invoice.payer_type]}
                        </Badge>
                        {invoice.allocation_type && invoice.allocation_type !== 'other' && (
                          <Badge className={`text-xs ${allocationTypeColors[invoice.allocation_type as AllocationType]}`}>
                            {allocationTypeLabels[invoice.allocation_type as AllocationType]}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">
                          {invoice.payer_name || invoice.estimate?.customer_name || "—"}
                        </p>
                        {invoice.estimate?.vehicle_display && (
                          <p className="text-sm text-muted-foreground">
                            {invoice.estimate.vehicle_display}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(invoice.total)}
                    </TableCell>
                    <TableCell className="text-right text-green-600">
                      {formatCurrency(invoice.amount_paid)}
                    </TableCell>
                    <TableCell className="text-right">
                      {invoice.balance_due > 0 ? (
                        <span className="text-red-600 font-medium">
                          {formatCurrency(invoice.balance_due)}
                        </span>
                      ) : (
                        <span className="text-green-600">Paid</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {invoice.issued_at
                        ? new Date(invoice.issued_at).toLocaleDateString()
                        : "—"}
                    </TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/invoices/${invoice.id}`)}
                        >
                          View
                        </Button>
                        {invoice.status === "draft" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleIssue(invoice)}
                            disabled={issueInvoice.isPending}
                          >
                            {issueInvoice.isPending ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <>
                                <Send className="h-3 w-3 mr-1" />
                                Issue
                              </>
                            )}
                          </Button>
                        )}
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
