import * as React from "react"
import { portalApi, PortalPayment, PortalInvoice } from "@/api/portal"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  CreditCard,
  DollarSign,
  Receipt,
  CheckCircle,
  Clock,
  AlertCircle,
} from "lucide-react"

const paymentStatusColors: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
  refunded: "bg-gray-100 text-gray-800",
}

const paymentMethodIcons: Record<string, React.ElementType> = {
  credit_card: CreditCard,
  debit_card: CreditCard,
  cash: DollarSign,
  check: Receipt,
}

export function PortalPaymentsPage() {
  const [payments, setPayments] = React.useState<PortalPayment[]>([])
  const [pendingInvoices, setPendingInvoices] = React.useState<PortalInvoice[]>([])
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await portalApi.getPaymentHistory()
        setPayments(result.payments)
      } catch {
        // Demo data
        setPayments([
          {
            id: 1,
            amount: 500,
            method: "credit_card",
            status: "completed",
            transaction_id: "TXN-12345",
            paid_at: "2025-01-21T10:30:00",
          },
          {
            id: 2,
            amount: 2950,
            method: "credit_card",
            status: "completed",
            transaction_id: "TXN-12346",
            paid_at: "2024-12-15T14:00:00",
          },
          {
            id: 3,
            amount: 750,
            method: "check",
            status: "completed",
            paid_at: "2024-11-20T09:00:00",
          },
        ])
        setPendingInvoices([
          {
            id: 1,
            invoice_number: "INV-2025-001",
            subtotal: 3200,
            tax: 250,
            total: 3450,
            amount_paid: 500,
            balance_due: 2950,
            status: "partial",
            due_date: "2025-02-01",
            items: [],
            payments: [],
            created_at: "2025-01-20",
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const totalPaid = payments
    .filter((p) => p.status === "completed")
    .reduce((sum, p) => sum + p.amount, 0)

  const totalPending = pendingInvoices.reduce((sum, i) => sum + i.balance_due, 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Payments</h1>
        <p className="text-muted-foreground">
          View your payment history and manage outstanding invoices
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Paid</p>
                <p className="text-2xl font-bold text-green-600">
                  ${totalPaid.toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-yellow-100 flex items-center justify-center">
                <Clock className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Balance Due</p>
                <p className="text-2xl font-bold text-yellow-600">
                  ${totalPending.toLocaleString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
                <Receipt className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Transactions</p>
                <p className="text-2xl font-bold">{payments.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Invoices */}
      {pendingInvoices.length > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              Outstanding Invoices
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {pendingInvoices.map((invoice) => (
              <div
                key={invoice.id}
                className="flex items-center justify-between p-4 bg-white rounded-lg border"
              >
                <div>
                  <h4 className="font-semibold">{invoice.invoice_number}</h4>
                  <p className="text-sm text-muted-foreground">
                    Due: {new Date(invoice.due_date!).toLocaleDateString()}
                  </p>
                  <div className="flex items-center gap-4 mt-2 text-sm">
                    <span>Total: ${invoice.total.toLocaleString()}</span>
                    <span>Paid: ${invoice.amount_paid.toLocaleString()}</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-yellow-700">
                    ${invoice.balance_due.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground mb-2">Balance Due</p>
                  <Button size="sm">
                    <CreditCard className="h-4 w-4 mr-2" />
                    Pay Now
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Payment History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Payment History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {payments.length > 0 ? (
            <div className="divide-y">
              {payments.map((payment) => {
                const Icon = paymentMethodIcons[payment.method] || DollarSign

                return (
                  <div
                    key={payment.id}
                    className="flex items-center justify-between p-4"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-full bg-gray-100 flex items-center justify-center">
                        <Icon className="h-5 w-5 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium">
                          ${payment.amount.toLocaleString()}
                        </p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className="capitalize">
                            {payment.method.replace("_", " ")}
                          </span>
                          {payment.transaction_id && (
                            <>
                              <span>•</span>
                              <span>{payment.transaction_id}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge className={paymentStatusColors[payment.status]}>
                        {payment.status}
                      </Badge>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(payment.paid_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="py-12 text-center">
              <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <h3 className="font-medium mb-1">No Payment History</h3>
              <p className="text-sm text-muted-foreground">
                Your payment transactions will appear here
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Methods */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Accepted Payment Methods</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="flex items-center gap-2 p-3 border rounded-lg">
              <CreditCard className="h-5 w-5 text-blue-600" />
              <span className="text-sm">Credit Card</span>
            </div>
            <div className="flex items-center gap-2 p-3 border rounded-lg">
              <CreditCard className="h-5 w-5 text-green-600" />
              <span className="text-sm">Debit Card</span>
            </div>
            <div className="flex items-center gap-2 p-3 border rounded-lg">
              <DollarSign className="h-5 w-5 text-gray-600" />
              <span className="text-sm">Cash</span>
            </div>
            <div className="flex items-center gap-2 p-3 border rounded-lg">
              <Receipt className="h-5 w-5 text-purple-600" />
              <span className="text-sm">Check</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Questions about billing? Contact us at (555) 123-4567
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
