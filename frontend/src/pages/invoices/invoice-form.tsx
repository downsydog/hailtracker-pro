import { useState, useEffect } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { useQuery, useMutation } from "@tanstack/react-query"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
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
import { invoicesApi, InvoiceCreateData } from "@/api/invoices"
import { jobsApi } from "@/api/jobs"
import { ArrowLeft, Plus, Trash2 } from "lucide-react"

interface LineItem {
  description: string
  quantity: number
  unit_price: number
}

export function InvoiceFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [formData, setFormData] = useState({
    job_id: "",
    customer_id: "",
    invoice_date: new Date().toISOString().split("T")[0],
    due_date: "",
    tax_rate: 0,
    notes: "",
  })

  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: "", quantity: 1, unit_price: 0 },
  ])

  // Fetch jobs for dropdown using typed API
  const { data: jobsData } = useQuery({
    queryKey: ["jobs-select"],
    queryFn: () => jobsApi.list({ per_page: 100 }),
  })

  // Fetch invoice if editing using typed API
  const { data: invoiceData } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => invoicesApi.getInvoice(Number(id)),
    enabled: isEdit,
  })

  const invoice = invoiceData?.invoice
  const invoiceItems = invoiceData?.items || []

  // Populate form when editing
  useEffect(() => {
    if (invoice) {
      setFormData({
        job_id: invoice.job_id?.toString() || "",
        customer_id: invoice.customer_id?.toString() || "",
        invoice_date: invoice.issue_date || "",
        due_date: invoice.due_date || "",
        tax_rate: invoice.tax_rate || 0,
        notes: invoice.notes || "",
      })
      if (invoiceItems.length > 0) {
        setLineItems(invoiceItems.map(item => ({
          description: item.description,
          quantity: item.quantity,
          unit_price: item.unit_price,
        })))
      }
    }
  }, [invoice, invoiceItems])

  // Create invoice using typed API
  const createInvoice = useMutation({
    mutationFn: (data: InvoiceCreateData) => invoicesApi.createInvoice(data),
    onSuccess: (response) => {
      navigate(`/invoices/${response.invoice_id}`)
    },
  })

  // Update invoice using typed API
  const updateInvoice = useMutation({
    mutationFn: (data: Partial<InvoiceCreateData>) => invoicesApi.updateInvoice(Number(id), data),
    onSuccess: () => {
      navigate(`/invoices/${id}`)
    },
  })

  const jobs = jobsData?.jobs || []

  // Calculate totals
  const subtotal = lineItems.reduce(
    (sum, item) => sum + item.quantity * item.unit_price,
    0
  )
  const taxAmount = subtotal * (formData.tax_rate / 100)
  const total = subtotal + taxAmount

  const handleJobChange = (jobId: string) => {
    const job = jobs.find((j) => j.id.toString() === jobId)
    setFormData((prev) => ({
      ...prev,
      job_id: jobId,
      customer_id: job?.customer_id?.toString() || "",
    }))
  }

  const addLineItem = () => {
    setLineItems([...lineItems, { description: "", quantity: 1, unit_price: 0 }])
  }

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index))
    }
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: any) => {
    const updated = [...lineItems]
    updated[index] = { ...updated[index], [field]: value }
    setLineItems(updated)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const data: InvoiceCreateData = {
      job_id: parseInt(formData.job_id),
      customer_id: parseInt(formData.customer_id),
      issue_date: formData.invoice_date,
      due_date: formData.due_date || undefined,
      tax_rate: formData.tax_rate,
      items: lineItems.filter((item) => item.description.trim()),
      notes: formData.notes,
    }

    if (isEdit) {
      updateInvoice.mutate(data)
    } else {
      createInvoice.mutate(data)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/invoices">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader
          title={isEdit ? "Edit Invoice" : "New Invoice"}
          description={
            isEdit ? "Update invoice details" : "Create a new invoice"
          }
        />
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Basic Info */}
            <Card>
              <CardHeader>
                <CardTitle>Invoice Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="job_id">Job *</Label>
                    <Select
                      value={formData.job_id}
                      onValueChange={handleJobChange}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select a job" />
                      </SelectTrigger>
                      <SelectContent>
                        {jobs.map((job) => (
                          <SelectItem key={job.id} value={job.id.toString()}>
                            {job.job_number} - {job.customer_name} (
                            {job.vehicle_year} {job.vehicle_make})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invoice_date">Invoice Date *</Label>
                    <Input
                      id="invoice_date"
                      type="date"
                      value={formData.invoice_date}
                      onChange={(e) =>
                        setFormData({ ...formData, invoice_date: e.target.value })
                      }
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="due_date">Due Date</Label>
                    <Input
                      id="due_date"
                      type="date"
                      value={formData.due_date}
                      onChange={(e) =>
                        setFormData({ ...formData, due_date: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tax_rate">Tax Rate (%)</Label>
                    <Input
                      id="tax_rate"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={formData.tax_rate}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          tax_rate: parseFloat(e.target.value) || 0,
                        })
                      }
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Line Items */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Line Items</CardTitle>
                  <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                    <Plus className="h-4 w-4 mr-1" />
                    Add Item
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-12 gap-2 text-sm font-medium text-muted-foreground">
                    <div className="col-span-6">Description</div>
                    <div className="col-span-2 text-right">Qty</div>
                    <div className="col-span-2 text-right">Price</div>
                    <div className="col-span-1 text-right">Total</div>
                    <div className="col-span-1"></div>
                  </div>

                  {lineItems.map((item, index) => (
                    <div key={index} className="grid grid-cols-12 gap-2 items-center">
                      <div className="col-span-6">
                        <Input
                          placeholder="Description"
                          value={item.description}
                          onChange={(e) =>
                            updateLineItem(index, "description", e.target.value)
                          }
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          min="1"
                          value={item.quantity}
                          onChange={(e) =>
                            updateLineItem(
                              index,
                              "quantity",
                              parseInt(e.target.value) || 1
                            )
                          }
                          className="text-right"
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={item.unit_price}
                          onChange={(e) =>
                            updateLineItem(
                              index,
                              "unit_price",
                              parseFloat(e.target.value) || 0
                            )
                          }
                          className="text-right"
                        />
                      </div>
                      <div className="col-span-1 text-right font-medium">
                        {formatCurrency(item.quantity * item.unit_price)}
                      </div>
                      <div className="col-span-1 text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          onClick={() => removeLineItem(index)}
                          disabled={lineItems.length === 1}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  placeholder="Additional notes or terms..."
                  value={formData.notes}
                  onChange={(e) =>
                    setFormData({ ...formData, notes: e.target.value })
                  }
                  rows={4}
                />
              </CardContent>
            </Card>
          </div>

          {/* Summary Sidebar */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span>{formatCurrency(subtotal)}</span>
                </div>
                {formData.tax_rate > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Tax ({formData.tax_rate}%)
                    </span>
                    <span>{formatCurrency(taxAmount)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t pt-4">
                  <span className="font-semibold text-lg">Total</span>
                  <span className="font-bold text-lg">{formatCurrency(total)}</span>
                </div>
              </CardContent>
            </Card>

            <div className="flex flex-col gap-2">
              <Button
                type="submit"
                disabled={
                  createInvoice.isPending ||
                  updateInvoice.isPending ||
                  !formData.job_id
                }
              >
                {createInvoice.isPending || updateInvoice.isPending
                  ? "Saving..."
                  : isEdit
                  ? "Update Invoice"
                  : "Create Invoice"}
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to="/invoices">Cancel</Link>
              </Button>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
