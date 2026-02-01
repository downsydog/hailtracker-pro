import * as React from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, Plus, Trash2 } from "lucide-react"

interface LineItem {
  id: number
  service_type: string
  description: string
  quantity: number
  unit_price: number
}

export function EstimateFormPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const isEditing = !!id

  const [formData, setFormData] = React.useState({
    customer_id: searchParams.get("customer_id") || "",
    vehicle_id: "",
    notes: "",
  })

  const [lineItems, setLineItems] = React.useState<LineItem[]>([
    { id: 1, service_type: "PDR", description: "", quantity: 1, unit_price: 0 },
  ])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleLineItemChange = (id: number, field: keyof LineItem, value: string | number) => {
    setLineItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, [field]: value } : item
      )
    )
  }

  const addLineItem = () => {
    setLineItems((prev) => [
      ...prev,
      { id: Date.now(), service_type: "PDR", description: "", quantity: 1, unit_price: 0 },
    ])
  }

  const removeLineItem = (id: number) => {
    setLineItems((prev) => prev.filter((item) => item.id !== id))
  }

  const subtotal = lineItems.reduce((sum, item) => sum + item.quantity * item.unit_price, 0)
  const tax = subtotal * 0.08
  const total = subtotal + tax

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    navigate("/estimates")
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/estimates")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEditing ? "Edit Estimate" : "New Estimate"}
          description={isEditing ? `Editing estimate #${id}` : "Create a new estimate"}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Customer & Vehicle</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="customer_id">Customer ID</Label>
                  <Input
                    id="customer_id"
                    name="customer_id"
                    type="number"
                    value={formData.customer_id}
                    onChange={handleChange}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vehicle_id">Vehicle ID</Label>
                  <Input
                    id="vehicle_id"
                    name="vehicle_id"
                    type="number"
                    value={formData.vehicle_id}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Line Items</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                <Plus className="h-4 w-4 mr-2" />
                Add Item
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {lineItems.map((item) => (
                  <div key={item.id} className="grid gap-4 md:grid-cols-5 items-end">
                    <div className="space-y-2">
                      <Label>Service Type</Label>
                      <select
                        value={item.service_type}
                        onChange={(e) => handleLineItemChange(item.id, "service_type", e.target.value)}
                        className="w-full p-2 border rounded-md"
                      >
                        <option value="PDR">PDR</option>
                        <option value="PAINT">Paint</option>
                        <option value="POLISH">Polish</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label>Description</Label>
                      <Input
                        value={item.description}
                        onChange={(e) => handleLineItemChange(item.id, "description", e.target.value)}
                        placeholder="Description"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Unit Price</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => handleLineItemChange(item.id, "unit_price", Number(e.target.value))}
                      />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeLineItem(item.id)}
                      disabled={lineItems.length === 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex justify-end">
                <div className="text-right space-y-1">
                  <p>Subtotal: ${subtotal.toFixed(2)}</p>
                  <p>Tax (8%): ${tax.toFixed(2)}</p>
                  <p className="text-xl font-bold">Total: ${total.toFixed(2)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                placeholder="Additional notes..."
                rows={3}
              />
            </CardContent>
          </Card>

          <div className="flex gap-4">
            <Button type="submit">
              {isEditing ? "Update Estimate" : "Create Estimate"}
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate("/estimates")}>
              Cancel
            </Button>
          </div>
        </div>
      </form>
    </div>
  )
}
