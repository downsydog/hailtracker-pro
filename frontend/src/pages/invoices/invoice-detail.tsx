import { useParams, Link, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { invoicesApi, InvoiceLineItem, InvoicePayment } from "@/api/invoices"
import {
  ArrowLeft,
  Send,
  Printer,
  DollarSign,
  Pencil,
  Trash2,
  User,
  Car,
  Calendar,
  FileText,
} from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

// Extended invoice detail type (standalone to avoid extending conflicts)
interface InvoiceDetail {
  id: number
  invoice_number: string
  job_id?: number
  customer_id: number
  customer_name: string
  customer_email?: string
  customer_phone?: string
  address_line1?: string
  city?: string
  state?: string
  zip_code?: string
  vehicle_info?: string
  status: string
  issue_date: string
  due_date: string
  subtotal: number
  tax_rate: number
  tax_amount: number
  discount_amount: number
  total: number
  amount_paid: number
  balance_due: number
  notes?: string
  payment_terms?: string
  job_number?: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
  line_items?: InvoiceLineItem[]
  invoice_date?: string
  sent_date?: string
  paid_date?: string
  payments?: InvoicePayment[]
  created_at: string
  updated_at: string
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  sent: "bg-blue-100 text-blue-800",
  viewed: "bg-purple-100 text-purple-800",
  partial_paid: "bg-yellow-100 text-yellow-800",
  paid: "bg-green-100 text-green-800",
  overdue: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
  refunded: "bg-orange-100 text-orange-800",
}

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Fetch invoice using typed API
  const { data: invoiceData, isLoading } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => invoicesApi.getInvoice(Number(id)),
  })

  const invoice = invoiceData?.invoice as InvoiceDetail | undefined
  const lineItems = invoiceData?.items || []
  const payments = invoiceData?.payments || []

  // Send invoice using typed API
  const sendInvoice = useMutation({
    mutationFn: () => invoicesApi.sendInvoice(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice", id] })
    },
  })

  // Delete invoice using typed API
  const deleteInvoice = useMutation({
    mutationFn: () => invoicesApi.deleteInvoice(Number(id)),
    onSuccess: () => {
      navigate("/invoices")
    },
  })

  const formatCurrency = (amount: number | null) => {
    if (amount == null) return "$0.00"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!invoice) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
        <p className="text-muted-foreground">Invoice not found</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/invoices">Back to invoices</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/invoices">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{invoice.invoice_number}</h1>
              <Badge className={STATUS_COLORS[invoice.status]}>
                {invoice.status?.replace(/_/g, " ")}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              Invoice for {invoice.customer_name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {invoice.status === "draft" && (
            <>
              <Button
                variant="outline"
                onClick={() => sendInvoice.mutate()}
                disabled={sendInvoice.isPending}
              >
                <Send className="h-4 w-4 mr-2" />
                Send Invoice
              </Button>
              <Button variant="outline" asChild>
                <Link to={`/invoices/${id}/edit`}>
                  <Pencil className="h-4 w-4 mr-2" />
                  Edit
                </Link>
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" size="icon">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete Invoice?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete this invoice. This action
                      cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => deleteInvoice.mutate()}
                      className="bg-destructive text-destructive-foreground"
                    >
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </>
          )}
          <Button variant="outline">
            <Printer className="h-4 w-4 mr-2" />
            Print
          </Button>
          {invoice.balance_due > 0 && (
            <Button>
              <DollarSign className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Invoice Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Header */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold mb-2">Bill To:</h3>
                  <p className="font-medium">{invoice.customer_name}</p>
                  {invoice.address_line1 && <p>{invoice.address_line1}</p>}
                  {invoice.city && (
                    <p>
                      {invoice.city}, {invoice.state} {invoice.zip_code}
                    </p>
                  )}
                  {invoice.customer_email && (
                    <p className="text-muted-foreground">
                      {invoice.customer_email}
                    </p>
                  )}
                  {invoice.customer_phone && (
                    <p className="text-muted-foreground">
                      {invoice.customer_phone}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <div className="space-y-1">
                    <p>
                      <span className="text-muted-foreground">Invoice Date:</span>{" "}
                      {invoice.invoice_date
                        ? new Date(invoice.invoice_date).toLocaleDateString()
                        : "—"}
                    </p>
                    <p>
                      <span className="text-muted-foreground">Due Date:</span>{" "}
                      {invoice.due_date
                        ? new Date(invoice.due_date).toLocaleDateString()
                        : "—"}
                    </p>
                    {invoice.sent_date && (
                      <p>
                        <span className="text-muted-foreground">Sent:</span>{" "}
                        {new Date(invoice.sent_date).toLocaleDateString()}
                      </p>
                    )}
                    {invoice.paid_date && (
                      <p>
                        <span className="text-muted-foreground">Paid:</span>{" "}
                        {new Date(invoice.paid_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card>
            <CardHeader>
              <CardTitle>Line Items</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Description</th>
                    <th className="text-right py-2 w-20">Qty</th>
                    <th className="text-right py-2 w-28">Price</th>
                    <th className="text-right py-2 w-28">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((item, index) => (
                    <tr key={index} className="border-b">
                      <td className="py-3">{item.description}</td>
                      <td className="text-right py-3">{item.quantity}</td>
                      <td className="text-right py-3">
                        {formatCurrency(item.unit_price)}
                      </td>
                      <td className="text-right py-3 font-medium">
                        {formatCurrency(item.total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={3} className="text-right py-3 font-medium">
                      Subtotal
                    </td>
                    <td className="text-right py-3">
                      {formatCurrency(invoice.subtotal)}
                    </td>
                  </tr>
                  {invoice.tax_amount > 0 && (
                    <tr>
                      <td colSpan={3} className="text-right py-2">
                        Tax
                      </td>
                      <td className="text-right py-2">
                        {formatCurrency(invoice.tax_amount)}
                      </td>
                    </tr>
                  )}
                  <tr className="border-t-2">
                    <td colSpan={3} className="text-right py-3 font-bold text-lg">
                      Total
                    </td>
                    <td className="text-right py-3 font-bold text-lg">
                      {formatCurrency(invoice.total)}
                    </td>
                  </tr>
                  {invoice.amount_paid > 0 && (
                    <>
                      <tr>
                        <td colSpan={3} className="text-right py-2 text-green-600">
                          Amount Paid
                        </td>
                        <td className="text-right py-2 text-green-600">
                          -{formatCurrency(invoice.amount_paid)}
                        </td>
                      </tr>
                      <tr className="border-t">
                        <td
                          colSpan={3}
                          className="text-right py-3 font-bold text-lg"
                        >
                          Balance Due
                        </td>
                        <td
                          className={`text-right py-3 font-bold text-lg ${
                            invoice.balance_due > 0
                              ? "text-red-600"
                              : "text-green-600"
                          }`}
                        >
                          {formatCurrency(invoice.balance_due)}
                        </td>
                      </tr>
                    </>
                  )}
                </tfoot>
              </table>
            </CardContent>
          </Card>

          {/* Notes */}
          {invoice.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{invoice.notes}</p>
              </CardContent>
            </Card>
          )}

          {/* Payments */}
          {payments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Payment History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {payments.map((payment) => (
                    <div
                      key={payment.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium">
                          {formatCurrency(payment.amount)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {payment.payment_method} •{" "}
                          {new Date(payment.payment_date).toLocaleDateString()}
                        </p>
                      </div>
                      <Badge variant="outline" className="bg-green-50">
                        Received
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Customer</p>
                  <Link
                    to={`/customers/${invoice.customer_id}`}
                    className="font-medium hover:underline"
                  >
                    {invoice.customer_name}
                  </Link>
                </div>
              </div>
              {invoice.job_id && (
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Job</p>
                    <Link
                      to={`/jobs/${invoice.job_id}`}
                      className="font-medium hover:underline"
                    >
                      {invoice.job_number}
                    </Link>
                  </div>
                </div>
              )}
              {invoice.vehicle_year && (
                <div className="flex items-center gap-3">
                  <Car className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Vehicle</p>
                    <p className="font-medium">
                      {invoice.vehicle_year} {invoice.vehicle_make}{" "}
                      {invoice.vehicle_model}
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="font-medium">
                    {invoice.invoice_date
                      ? new Date(invoice.invoice_date).toLocaleDateString()
                      : "—"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Balance Summary */}
          <Card
            className={
              invoice.balance_due > 0
                ? "bg-red-50 dark:bg-red-950"
                : "bg-green-50 dark:bg-green-950"
            }
          >
            <CardContent className="pt-6 text-center">
              <p className="text-sm font-medium text-muted-foreground mb-1">
                Balance Due
              </p>
              <p
                className={`text-3xl font-bold ${
                  invoice.balance_due > 0 ? "text-red-600" : "text-green-600"
                }`}
              >
                {formatCurrency(invoice.balance_due)}
              </p>
              {invoice.balance_due <= 0 && (
                <Badge className="mt-2 bg-green-600">Paid in Full</Badge>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
