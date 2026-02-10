import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
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
import {
  useInvoice,
  useIssueInvoice,
  useVoidInvoice,
  useAddPayment,
  useAddLineItem,
  useRemoveLineItem,
  invoiceStatusColors,
  invoiceStatusLabels,
  payerTypeLabels,
  paymentMethodLabels,
  lineItemCategoryLabels,
  allocationTypeLabels,
  allocationTypeColors,
  PaymentMethod,
  LineItemCategory,
  AllocationType,
} from "@/hooks/use-invoices"
import {
  ArrowLeft,
  Send,
  Printer,
  DollarSign,
  Trash2,
  User,
  Car,
  Calendar,
  FileText,
  Ban,
  Plus,
  Loader2,
  ExternalLink,
  Download,
} from "lucide-react"
import { useDownloadPaymentReceipt } from "@/hooks/use-exports"

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const invoiceId = id ? parseInt(id) : null

  // State for modals
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [showLineItemModal, setShowLineItemModal] = useState(false)

  // Payment form state
  const [paymentAmount, setPaymentAmount] = useState("")
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("check")
  const [paymentReference, setPaymentReference] = useState("")
  const [paymentNotes, setPaymentNotes] = useState("")

  // Line item form state
  const [lineItemCategory, setLineItemCategory] = useState<LineItemCategory>("pdr")
  const [lineItemDescription, setLineItemDescription] = useState("")
  const [lineItemQuantity, setLineItemQuantity] = useState("1")
  const [lineItemPrice, setLineItemPrice] = useState("")

  // Hooks
  const { data: invoice, isLoading, refetch } = useInvoice(invoiceId)
  const issueInvoice = useIssueInvoice()
  const voidInvoice = useVoidInvoice()
  const addPayment = useAddPayment()
  const addLineItem = useAddLineItem()
  const removeLineItem = useRemoveLineItem()
  const downloadReceipt = useDownloadPaymentReceipt()

  const formatCurrency = (amount: number | null) => {
    if (amount == null) return "$0.00"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  const handleIssue = async () => {
    if (!invoice) return
    await issueInvoice.mutateAsync(invoice.id)
    refetch()
  }

  const handleVoid = async () => {
    if (!invoice) return
    await voidInvoice.mutateAsync(invoice.id)
    refetch()
  }

  const handleAddPayment = async () => {
    if (!invoice || !paymentAmount) return
    await addPayment.mutateAsync({
      invoiceId: invoice.id,
      params: {
        amount: parseFloat(paymentAmount),
        method: paymentMethod,
        reference: paymentReference || undefined,
        notes: paymentNotes || undefined,
      },
    })
    setShowPaymentModal(false)
    setPaymentAmount("")
    setPaymentMethod("check")
    setPaymentReference("")
    setPaymentNotes("")
    refetch()
  }

  const handleAddLineItem = async () => {
    if (!invoice || !lineItemDescription || !lineItemPrice) return
    await addLineItem.mutateAsync({
      invoiceId: invoice.id,
      params: {
        category: lineItemCategory,
        description: lineItemDescription,
        quantity: parseFloat(lineItemQuantity) || 1,
        unit_price: parseFloat(lineItemPrice),
      },
    })
    setShowLineItemModal(false)
    setLineItemCategory("pdr")
    setLineItemDescription("")
    setLineItemQuantity("1")
    setLineItemPrice("")
    refetch()
  }

  const handleRemoveLineItem = async (lineItemId: number) => {
    if (!invoice) return
    await removeLineItem.mutateAsync({
      invoiceId: invoice.id,
      lineItemId,
    })
    refetch()
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

  const canIssue = invoice.status === "draft"
  const canVoid = invoice.status === "draft" || invoice.status === "issued"
  const canAddPayment = invoice.status === "issued" || invoice.status === "partial_paid"
  const canEditLineItems = invoice.status === "draft"

  return (
    <div className="space-y-6">
      {/* Header */}
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
              <Badge className={invoiceStatusColors[invoice.status]}>
                {invoiceStatusLabels[invoice.status]}
              </Badge>
              {invoice.allocation_type && invoice.allocation_type !== 'other' && (
                <Badge className={allocationTypeColors[invoice.allocation_type as AllocationType]}>
                  {allocationTypeLabels[invoice.allocation_type as AllocationType]}
                </Badge>
              )}
              {invoice.is_overdue && invoice.status !== 'paid' && invoice.status !== 'void' && (
                <Badge variant="destructive">Overdue</Badge>
              )}
            </div>
            <p className="text-muted-foreground">
              {payerTypeLabels[invoice.payer_type]} Invoice
              {invoice.payer_name && ` for ${invoice.payer_name}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {canIssue && (
            <Button
              onClick={handleIssue}
              disabled={issueInvoice.isPending}
            >
              {issueInvoice.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Issue Invoice
            </Button>
          )}
          {canVoid && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline">
                  <Ban className="h-4 w-4 mr-2" />
                  Void
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Void Invoice?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will void the invoice. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleVoid}
                    className="bg-destructive text-destructive-foreground"
                  >
                    Void Invoice
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
          <Button variant="outline">
            <Printer className="h-4 w-4 mr-2" />
            Print
          </Button>
          {canAddPayment && invoice.balance_due > 0 && (
            <Button onClick={() => setShowPaymentModal(true)}>
              <DollarSign className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Header Info */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold mb-2">Bill To:</h3>
                  <p className="font-medium">{invoice.payer_name || invoice.estimate?.customer_name || "—"}</p>
                  {invoice.estimate && (
                    <p className="text-muted-foreground mt-1">
                      {invoice.estimate.vehicle_display}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <div className="space-y-1">
                    <p>
                      <span className="text-muted-foreground">Created:</span>{" "}
                      {new Date(invoice.created_at).toLocaleDateString()}
                    </p>
                    {invoice.issued_at && (
                      <p>
                        <span className="text-muted-foreground">Issued:</span>{" "}
                        {new Date(invoice.issued_at).toLocaleDateString()}
                      </p>
                    )}
                    {invoice.due_at && (
                      <p>
                        <span className="text-muted-foreground">Due:</span>{" "}
                        {new Date(invoice.due_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Line Items</CardTitle>
              {canEditLineItems && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowLineItemModal(true)}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add Item
                </Button>
              )}
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Category</th>
                    <th className="text-left py-2">Description</th>
                    <th className="text-right py-2 w-16">Qty</th>
                    <th className="text-right py-2 w-28">Price</th>
                    <th className="text-right py-2 w-28">Total</th>
                    {canEditLineItems && <th className="w-12"></th>}
                  </tr>
                </thead>
                <tbody>
                  {invoice.line_items && invoice.line_items.length > 0 ? (
                    invoice.line_items.map((item) => (
                      <tr key={item.id} className="border-b">
                        <td className="py-3">
                          <Badge variant="outline" className="text-xs">
                            {lineItemCategoryLabels[item.category]}
                          </Badge>
                        </td>
                        <td className="py-3">{item.description}</td>
                        <td className="text-right py-3">{item.quantity}</td>
                        <td className="text-right py-3">
                          {formatCurrency(item.unit_price)}
                        </td>
                        <td className="text-right py-3 font-medium">
                          {formatCurrency(item.total)}
                        </td>
                        {canEditLineItems && (
                          <td className="py-3">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => handleRemoveLineItem(item.id)}
                              disabled={removeLineItem.isPending}
                            >
                              <Trash2 className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </td>
                        )}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={canEditLineItems ? 6 : 5} className="py-8 text-center text-muted-foreground">
                        No line items yet
                      </td>
                    </tr>
                  )}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={canEditLineItems ? 4 : 3} className="text-right py-3 font-medium">
                      Subtotal
                    </td>
                    <td className="text-right py-3" colSpan={canEditLineItems ? 2 : 1}>
                      {formatCurrency(invoice.subtotal)}
                    </td>
                  </tr>
                  {invoice.tax_total > 0 && (
                    <tr>
                      <td colSpan={canEditLineItems ? 4 : 3} className="text-right py-2">
                        Tax ({(invoice.tax_rate * 100).toFixed(2)}%)
                      </td>
                      <td className="text-right py-2" colSpan={canEditLineItems ? 2 : 1}>
                        {formatCurrency(invoice.tax_total)}
                      </td>
                    </tr>
                  )}
                  <tr className="border-t-2">
                    <td colSpan={canEditLineItems ? 4 : 3} className="text-right py-3 font-bold text-lg">
                      Total
                    </td>
                    <td className="text-right py-3 font-bold text-lg" colSpan={canEditLineItems ? 2 : 1}>
                      {formatCurrency(invoice.total)}
                    </td>
                  </tr>
                  {invoice.amount_paid > 0 && (
                    <>
                      <tr>
                        <td colSpan={canEditLineItems ? 4 : 3} className="text-right py-2 text-green-600">
                          Amount Paid
                        </td>
                        <td className="text-right py-2 text-green-600" colSpan={canEditLineItems ? 2 : 1}>
                          -{formatCurrency(invoice.amount_paid)}
                        </td>
                      </tr>
                      <tr className="border-t">
                        <td colSpan={canEditLineItems ? 4 : 3} className="text-right py-3 font-bold text-lg">
                          Balance Due
                        </td>
                        <td
                          className={`text-right py-3 font-bold text-lg ${
                            invoice.balance_due > 0 ? "text-red-600" : "text-green-600"
                          }`}
                          colSpan={canEditLineItems ? 2 : 1}
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
          {invoice.payments && invoice.payments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Payment History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {invoice.payments.map((payment) => (
                    <div
                      key={payment.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium">
                          {formatCurrency(payment.amount)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {paymentMethodLabels[payment.method]}
                          {payment.reference && ` - ${payment.reference}`}
                          {" "}&bull;{" "}
                          {new Date(payment.received_at).toLocaleDateString()}
                        </p>
                        {payment.notes && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {payment.notes}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => downloadReceipt.mutate({
                            invoiceId: invoice.id,
                            paymentId: payment.id,
                            invoiceNumber: invoice.invoice_number
                          })}
                          disabled={downloadReceipt.isPending}
                        >
                          {downloadReceipt.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Download className="h-3 w-3 mr-1" />
                          )}
                          Receipt
                        </Button>
                        <Badge variant="outline" className="bg-green-50">
                          Received
                        </Badge>
                      </div>
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
                  <p className="text-sm text-muted-foreground">Payer</p>
                  <p className="font-medium">
                    {invoice.payer_name || invoice.estimate?.customer_name || "—"}
                  </p>
                </div>
              </div>
              {invoice.estimate_id && (
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Estimate</p>
                    <Link
                      to={`/estimates/${invoice.estimate_id}`}
                      className="font-medium hover:underline flex items-center gap-1"
                    >
                      {invoice.estimate?.estimate_number || `#${invoice.estimate_id}`}
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              )}
              {invoice.job_id && (
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Job</p>
                    <Link
                      to={`/jobs/${invoice.job_id}`}
                      className="font-medium hover:underline flex items-center gap-1"
                    >
                      Job #{invoice.job_id}
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              )}
              {invoice.estimate?.vehicle_display && (
                <div className="flex items-center gap-3">
                  <Car className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Vehicle</p>
                    <p className="font-medium">{invoice.estimate.vehicle_display}</p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="font-medium">
                    {new Date(invoice.created_at).toLocaleDateString()}
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
              {invoice.balance_due <= 0 && invoice.status === 'paid' && (
                <Badge className="mt-2 bg-green-600">Paid in Full</Badge>
              )}
              {invoice.status === 'void' && (
                <Badge className="mt-2" variant="secondary">Voided</Badge>
              )}
            </CardContent>
          </Card>

          {/* Add Payment CTA */}
          {canAddPayment && invoice.balance_due > 0 && (
            <Button
              className="w-full"
              size="lg"
              onClick={() => setShowPaymentModal(true)}
            >
              <DollarSign className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          )}
        </div>
      </div>

      {/* Add Payment Modal */}
      <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Payment</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="amount">Amount</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  placeholder={invoice?.balance_due.toFixed(2)}
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  className="pl-7"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Balance due: {formatCurrency(invoice?.balance_due || 0)}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="method">Payment Method</Label>
              <Select value={paymentMethod} onValueChange={(v) => setPaymentMethod(v as PaymentMethod)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="check">Check</SelectItem>
                  <SelectItem value="card">Card</SelectItem>
                  <SelectItem value="ach">ACH</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reference">Reference # (optional)</Label>
              <Input
                id="reference"
                placeholder="Check number, transaction ID, etc."
                value={paymentReference}
                onChange={(e) => setPaymentReference(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                placeholder="Payment notes..."
                value={paymentNotes}
                onChange={(e) => setPaymentNotes(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPaymentModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddPayment}
              disabled={!paymentAmount || addPayment.isPending}
            >
              {addPayment.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Record Payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Line Item Modal */}
      <Dialog open={showLineItemModal} onOpenChange={setShowLineItemModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Line Item</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select value={lineItemCategory} onValueChange={(v) => setLineItemCategory(v as LineItemCategory)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdr">PDR Labor</SelectItem>
                  <SelectItem value="ri">R&I Labor</SelectItem>
                  <SelectItem value="materials">Materials</SelectItem>
                  <SelectItem value="parts">Parts</SelectItem>
                  <SelectItem value="sublet">Sublet</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                placeholder="Line item description"
                value={lineItemDescription}
                onChange={(e) => setLineItemDescription(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="quantity">Quantity</Label>
                <Input
                  id="quantity"
                  type="number"
                  step="0.01"
                  value={lineItemQuantity}
                  onChange={(e) => setLineItemQuantity(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="unit_price">Unit Price</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                  <Input
                    id="unit_price"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={lineItemPrice}
                    onChange={(e) => setLineItemPrice(e.target.value)}
                    className="pl-7"
                  />
                </div>
              </div>
            </div>
            {lineItemQuantity && lineItemPrice && (
              <div className="text-right text-sm">
                <span className="text-muted-foreground">Total: </span>
                <span className="font-medium">
                  {formatCurrency(parseFloat(lineItemQuantity || "1") * parseFloat(lineItemPrice || "0"))}
                </span>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLineItemModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddLineItem}
              disabled={!lineItemDescription || !lineItemPrice || addLineItem.isPending}
            >
              {addLineItem.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Add Item
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
