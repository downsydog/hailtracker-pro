import * as React from "react"
import { useNavigate, useParams } from "react-router-dom"
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
import { useLead, useCreateLead, useUpdateLead } from "@/hooks/use-leads"
import { ArrowLeft, Save } from "lucide-react"

export function LeadFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id && id !== "new"

  const { data: lead, isLoading } = useLead(isEdit ? Number(id) : 0)
  const createLead = useCreateLead()
  const updateLead = useUpdateLead()

  const [formData, setFormData] = React.useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    source: "WEBSITE",
    status: "NEW",
    temperature: "WARM",
    vehicle_year: "",
    vehicle_make: "",
    vehicle_model: "",
    damage_type: "HAIL",
    damage_description: "",
    estimated_repair_cost: "",
    notes: "",
  })

  React.useEffect(() => {
    if (lead && isEdit) {
      setFormData({
        first_name: lead.first_name || "",
        last_name: lead.last_name || "",
        email: lead.email || "",
        phone: lead.phone || "",
        source: lead.source || "WEBSITE",
        status: lead.status || "NEW",
        temperature: lead.temperature || "WARM",
        vehicle_year: lead.vehicle_year?.toString() || "",
        vehicle_make: lead.vehicle_make || "",
        vehicle_model: lead.vehicle_model || "",
        damage_type: lead.damage_type || "HAIL",
        damage_description: lead.damage_description || "",
        estimated_repair_cost: lead.estimated_repair_cost?.toString() || "",
        notes: "",
      })
    }
  }, [lead, isEdit])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const data = {
      first_name: formData.first_name,
      last_name: formData.last_name,
      email: formData.email || undefined,
      phone: formData.phone || undefined,
      source: formData.source,
      status: formData.status,
      temperature: formData.temperature,
      vehicle_year: formData.vehicle_year ? Number(formData.vehicle_year) : undefined,
      vehicle_make: formData.vehicle_make || undefined,
      vehicle_model: formData.vehicle_model || undefined,
      damage_type: formData.damage_type || undefined,
      damage_description: formData.damage_description || undefined,
      estimated_repair_cost: formData.estimated_repair_cost
        ? Number(formData.estimated_repair_cost)
        : undefined,
    }

    try {
      if (isEdit) {
        await updateLead.mutateAsync({ id: Number(id), data })
        navigate(`/leads/${id}`)
      } else {
        const result = await createLead.mutateAsync(data)
        navigate(`/leads/${(result as { id?: number }).id || ""}`)
      }
    } catch (error) {
      console.error("Failed to save lead:", error)
    }
  }

  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 40 }, (_, i) => currentYear - i)

  if (isEdit && isLoading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/leads")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEdit ? "Edit Lead" : "New Lead"}
          description={
            isEdit ? `Editing ${lead?.first_name} ${lead?.last_name}` : "Add a new lead"
          }
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name">First Name *</Label>
                  <Input
                    id="first_name"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name">Last Name *</Label>
                  <Input
                    id="last_name"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="email@example.com"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="(555) 123-4567"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Lead Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="source">Source</Label>
                <Select
                  value={formData.source}
                  onValueChange={(value) => setFormData({ ...formData, source: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="WEBSITE">Website</SelectItem>
                    <SelectItem value="PHONE">Phone Call</SelectItem>
                    <SelectItem value="WALK_IN">Walk-in</SelectItem>
                    <SelectItem value="REFERRAL">Referral</SelectItem>
                    <SelectItem value="GOOGLE">Google</SelectItem>
                    <SelectItem value="FACEBOOK">Facebook</SelectItem>
                    <SelectItem value="OTHER">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Select
                  value={formData.status}
                  onValueChange={(value) => setFormData({ ...formData, status: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NEW">New</SelectItem>
                    <SelectItem value="CONTACTED">Contacted</SelectItem>
                    <SelectItem value="QUALIFIED">Qualified</SelectItem>
                    <SelectItem value="LOST">Lost</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="temperature">Temperature</Label>
                <Select
                  value={formData.temperature}
                  onValueChange={(value) => setFormData({ ...formData, temperature: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="HOT">Hot</SelectItem>
                    <SelectItem value="WARM">Warm</SelectItem>
                    <SelectItem value="COLD">Cold</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Vehicle Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="vehicle_year">Year</Label>
                <Select
                  value={formData.vehicle_year}
                  onValueChange={(value) => setFormData({ ...formData, vehicle_year: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select year" />
                  </SelectTrigger>
                  <SelectContent>
                    {years.map((year) => (
                      <SelectItem key={year} value={year.toString()}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="vehicle_make">Make</Label>
                <Input
                  id="vehicle_make"
                  value={formData.vehicle_make}
                  onChange={(e) => setFormData({ ...formData, vehicle_make: e.target.value })}
                  placeholder="Toyota, Ford, Honda..."
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="vehicle_model">Model</Label>
                <Input
                  id="vehicle_model"
                  value={formData.vehicle_model}
                  onChange={(e) => setFormData({ ...formData, vehicle_model: e.target.value })}
                  placeholder="Camry, F-150, Civic..."
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Damage Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="damage_type">Damage Type</Label>
                <Select
                  value={formData.damage_type}
                  onValueChange={(value) => setFormData({ ...formData, damage_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="HAIL">Hail Damage</SelectItem>
                    <SelectItem value="DENT">Dent Repair</SelectItem>
                    <SelectItem value="COLLISION">Collision</SelectItem>
                    <SelectItem value="OTHER">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="damage_description">Description</Label>
                <Textarea
                  id="damage_description"
                  value={formData.damage_description}
                  onChange={(e) =>
                    setFormData({ ...formData, damage_description: e.target.value })
                  }
                  placeholder="Describe the damage..."
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="estimated_repair_cost">Estimated Cost ($)</Label>
                <Input
                  id="estimated_repair_cost"
                  type="number"
                  value={formData.estimated_repair_cost}
                  onChange={(e) =>
                    setFormData({ ...formData, estimated_repair_cost: e.target.value })
                  }
                  placeholder="2500"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end gap-4 mt-6">
          <Button type="button" variant="outline" onClick={() => navigate("/leads")}>
            Cancel
          </Button>
          <Button type="submit" disabled={createLead.isPending || updateLead.isPending}>
            <Save className="h-4 w-4 mr-2" />
            {isEdit ? "Save Changes" : "Create Lead"}
          </Button>
        </div>
      </form>
    </div>
  )
}
