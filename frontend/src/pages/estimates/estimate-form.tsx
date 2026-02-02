import * as React from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
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
import { useEstimate, useCreateEstimate, useUpdateEstimate } from "@/hooks/use-estimates"
import { useJobs } from "@/hooks/use-jobs"
import { ArrowLeft, Save, Plus, Trash2, ClipboardList } from "lucide-react"

interface LineItem {
  id?: number
  service_type: string
  description: string
  quantity: number
  unit_price: number
}

// Estimate templates with pre-filled line items
const ESTIMATE_TEMPLATES = {
  HAIL_BASIC: {
    name: "Hail - Basic",
    items: [
      { service_type: "PDR", description: "Hood - PDR dent repair", quantity: 1, unit_price: 350 },
      { service_type: "PDR", description: "Roof - PDR dent repair", quantity: 1, unit_price: 450 },
      { service_type: "PDR", description: "Trunk/Deck lid - PDR dent repair", quantity: 1, unit_price: 300 },
    ],
  },
  HAIL_SEVERE: {
    name: "Hail - Severe",
    items: [
      { service_type: "PDR", description: "Hood - PDR dent repair (severe)", quantity: 1, unit_price: 650 },
      { service_type: "PDR", description: "Roof - PDR dent repair (severe)", quantity: 1, unit_price: 850 },
      { service_type: "PDR", description: "Trunk/Deck lid - PDR dent repair (severe)", quantity: 1, unit_price: 550 },
      { service_type: "PDR", description: "Left fender - PDR dent repair", quantity: 1, unit_price: 350 },
      { service_type: "PDR", description: "Right fender - PDR dent repair", quantity: 1, unit_price: 350 },
      { service_type: "PDR", description: "Left door - PDR dent repair", quantity: 2, unit_price: 275 },
      { service_type: "PDR", description: "Right door - PDR dent repair", quantity: 2, unit_price: 275 },
    ],
  },
  DOOR_DING: {
    name: "Door Ding",
    items: [
      { service_type: "PDR", description: "Door ding repair - single panel", quantity: 1, unit_price: 125 },
    ],
  },
  CUSTOM: {
    name: "Custom",
    items: [
      { service_type: "PDR", description: "", quantity: 1, unit_price: 0 },
    ],
  },
}

export function EstimateFormPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEdit = !!id && id !== "new"

  const { data: estimate, isLoading } = useEstimate(isEdit ? Number(id) : 0)
  const { data: jobsData } = useJobs({ per_page: 100 })
  const createEstimate = useCreateEstimate()
  const updateEstimate = useUpdateEstimate()

  const [formData, setFormData] = React.useState({
    job_id: searchParams.get("job_id") || "",
    notes: "",
    tax_rate: "8.25",
  })

  const [lineItems, setLineItems] = React.useState<LineItem[]>([
    { service_type: "PDR", description: "", quantity: 1, unit_price: 0 },
  ])

  const [selectedTemplate, setSelectedTemplate] = React.useState<string>("")

  const applyTemplate = (templateKey: string) => {
    const template = ESTIMATE_TEMPLATES[templateKey as keyof typeof ESTIMATE_TEMPLATES]
    if (template) {
      setLineItems(template.items.map((item) => ({ ...item })))
      setSelectedTemplate(templateKey)
    }
  }

  React.useEffect(() => {
    if (estimate && isEdit) {
      setFormData({
        job_id: (estimate as { job_id?: number }).job_id?.toString() || "",
        notes: "",
        tax_rate: "8.25",
      })
      if ((estimate as { items?: LineItem[] }).items?.length) {
        setLineItems((estimate as { items: LineItem[] }).items)
      }
    }
  }, [estimate, isEdit])

  const addLineItem = () => {
    setLineItems([
      ...lineItems,
      { service_type: "PDR", description: "", quantity: 1, unit_price: 0 },
    ])
  }

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index))
    }
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: string | number) => {
    const updated = [...lineItems]
    updated[index] = { ...updated[index], [field]: value }
    setLineItems(updated)
  }

  const subtotal = lineItems.reduce((sum, item) => sum + item.quantity * item.unit_price, 0)
  const tax = subtotal * (parseFloat(formData.tax_rate) / 100)
  const total = subtotal + tax

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const data = {
      job_id: formData.job_id ? Number(formData.job_id) : undefined,
      subtotal,
      tax,
      total,
      items: lineItems,
    }

    try {
      if (isEdit) {
        await updateEstimate.mutateAsync({ id: Number(id), data })
        navigate(`/estimates/${id}`)
      } else {
        const result = await createEstimate.mutateAsync(data)
        navigate(`/estimates/${(result as { id?: number }).id || ""}`)
      }
    } catch (error) {
      console.error("Failed to save estimate:", error)
    }
  }

  const jobs = jobsData?.jobs || []

  if (isEdit && isLoading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/estimates")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEdit ? "Edit Estimate" : "New Estimate"}
          description={
            isEdit ? `Editing ${estimate?.estimate_number}` : "Create a new repair estimate"
          }
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Job Selection</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="job_id">Associated Job</Label>
                <Select
                  value={formData.job_id}
                  onValueChange={(value) => setFormData({ ...formData, job_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a job" />
                  </SelectTrigger>
                  <SelectContent>
                    {jobs.map((job) => (
                      <SelectItem key={job.id} value={job.id.toString()}>
                        {job.job_number} - {job.customer_name} ({job.vehicle_year}{" "}
                        {job.vehicle_make} {job.vehicle_model})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Line Items</CardTitle>
              <div className="flex items-center gap-2">
                <Select value={selectedTemplate} onValueChange={applyTemplate}>
                  <SelectTrigger className="w-[180px]">
                    <ClipboardList className="h-4 w-4 mr-2" />
                    <SelectValue placeholder="Use Template" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(ESTIMATE_TEMPLATES).map(([key, template]) => (
                      <SelectItem key={key} value={key}>
                        {template.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Item
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {lineItems.map((item, index) => (
                  <div
                    key={index}
                    className="grid grid-cols-12 gap-4 items-end p-4 border rounded-lg"
                  >
                    <div className="col-span-2 space-y-2">
                      <Label>Service Type</Label>
                      <Select
                        value={item.service_type}
                        onValueChange={(value) => updateLineItem(index, "service_type", value)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="PDR">PDR</SelectItem>
                          <SelectItem value="PAINT">Paint</SelectItem>
                          <SelectItem value="BODY">Body Work</SelectItem>
                          <SelectItem value="PARTS">Parts</SelectItem>
                          <SelectItem value="LABOR">Labor</SelectItem>
                          <SelectItem value="OTHER">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="col-span-5 space-y-2">
                      <Label>Description</Label>
                      <Input
                        value={item.description}
                        onChange={(e) => updateLineItem(index, "description", e.target.value)}
                        placeholder="Service description"
                      />
                    </div>

                    <div className="col-span-1 space-y-2">
                      <Label>Qty</Label>
                      <Input
                        type="number"
                        min="1"
                        value={item.quantity}
                        onChange={(e) =>
                          updateLineItem(index, "quantity", parseInt(e.target.value) || 1)
                        }
                      />
                    </div>

                    <div className="col-span-2 space-y-2">
                      <Label>Unit Price</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) =>
                          updateLineItem(index, "unit_price", parseFloat(e.target.value) || 0)
                        }
                        placeholder="0.00"
                      />
                    </div>

                    <div className="col-span-1 space-y-2">
                      <Label>Total</Label>
                      <p className="py-2 font-medium">
                        ${(item.quantity * item.unit_price).toFixed(2)}
                      </p>
                    </div>

                    <div className="col-span-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeLineItem(index)}
                        disabled={lineItems.length === 1}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex justify-end">
                <div className="w-64 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Subtotal:</span>
                    <span>${subtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">
                      Tax ({formData.tax_rate}%):
                    </span>
                    <span>${tax.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-lg border-t pt-2">
                    <span>Total:</span>
                    <span>${total.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Additional Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Notes for the estimate..."
                rows={4}
              />
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end gap-4 mt-6">
          <Button type="button" variant="outline" onClick={() => navigate("/estimates")}>
            Cancel
          </Button>
          <Button type="submit" disabled={createEstimate.isPending || updateEstimate.isPending}>
            <Save className="h-4 w-4 mr-2" />
            {isEdit ? "Save Changes" : "Create Estimate"}
          </Button>
        </div>
      </form>
    </div>
  )
}
