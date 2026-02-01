import * as React from "react"
import { useParams, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft } from "lucide-react"

export function LeadFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEditing = !!id

  const [formData, setFormData] = React.useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    source: "",
    vehicle_year: "",
    vehicle_make: "",
    vehicle_model: "",
    damage_type: "",
    damage_description: "",
    notes: "",
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    navigate("/leads")
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/leads")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEditing ? "Edit Lead" : "New Lead"}
          description={isEditing ? `Editing lead #${id}` : "Add a new lead"}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="first_name">First Name</Label>
                <Input
                  id="first_name"
                  name="first_name"
                  value={formData.first_name}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name">Last Name</Label>
                <Input
                  id="last_name"
                  name="last_name"
                  value={formData.last_name}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source">Lead Source</Label>
                <select
                  id="source"
                  name="source"
                  value={formData.source}
                  onChange={handleChange}
                  className="w-full p-2 border rounded-md"
                >
                  <option value="">Select source</option>
                  <option value="WEBSITE">Website</option>
                  <option value="REFERRAL">Referral</option>
                  <option value="CANVASSING">Canvassing</option>
                  <option value="SOCIAL">Social Media</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="vehicle_year">Vehicle Year</Label>
                <Input
                  id="vehicle_year"
                  name="vehicle_year"
                  type="number"
                  value={formData.vehicle_year}
                  onChange={handleChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vehicle_make">Vehicle Make</Label>
                <Input
                  id="vehicle_make"
                  name="vehicle_make"
                  value={formData.vehicle_make}
                  onChange={handleChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vehicle_model">Vehicle Model</Label>
                <Input
                  id="vehicle_model"
                  name="vehicle_model"
                  value={formData.vehicle_model}
                  onChange={handleChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="damage_type">Damage Type</Label>
                <select
                  id="damage_type"
                  name="damage_type"
                  value={formData.damage_type}
                  onChange={handleChange}
                  className="w-full p-2 border rounded-md"
                >
                  <option value="">Select type</option>
                  <option value="HAIL">Hail Damage</option>
                  <option value="DENT">Dent</option>
                  <option value="DING">Door Ding</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="damage_description">Damage Description</Label>
              <Textarea
                id="damage_description"
                name="damage_description"
                value={formData.damage_description}
                onChange={handleChange}
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                rows={3}
              />
            </div>

            <div className="flex gap-4">
              <Button type="submit">
                {isEditing ? "Update Lead" : "Create Lead"}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate("/leads")}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}
