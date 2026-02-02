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
import { useJob, useCreateJob, useUpdateJob } from "@/hooks/use-jobs"
import { useCustomers } from "@/hooks/use-customers"
import { useVehicles } from "@/hooks/use-vehicles"
import { ArrowLeft, Save } from "lucide-react"

export function JobFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = !!id && id !== "new"

  const { data: job, isLoading: jobLoading } = useJob(isEdit ? Number(id) : 0)
  const { data: customersData } = useCustomers({ per_page: 100 })
  const { data: vehiclesData } = useVehicles({ per_page: 100 })

  const createJob = useCreateJob()
  const updateJob = useUpdateJob()

  const [formData, setFormData] = React.useState({
    customer_id: "",
    vehicle_id: "",
    damage_type: "HAIL",
    damage_description: "",
    insurance_company: "",
    claim_number: "",
    deductible: "",
    scheduled_drop_off: "",
    notes: "",
  })

  React.useEffect(() => {
    if (job && isEdit) {
      setFormData({
        customer_id: job.customer_id?.toString() || "",
        vehicle_id: job.vehicle_id?.toString() || "",
        damage_type: job.damage_type || "HAIL",
        damage_description: job.tech_notes || "",
        insurance_company: job.insurance_company || "",
        claim_number: job.claim_number || "",
        deductible: job.deductible?.toString() || "",
        scheduled_drop_off: job.scheduled_drop_off?.split("T")[0] || "",
        notes: job.notes || "",
      })
    }
  }, [job, isEdit])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const data = {
      customer_id: formData.customer_id ? Number(formData.customer_id) : undefined,
      vehicle_id: formData.vehicle_id ? Number(formData.vehicle_id) : undefined,
      damage_type: formData.damage_type,
      damage_description: formData.damage_description || undefined,
      insurance_company: formData.insurance_company || undefined,
      claim_number: formData.claim_number || undefined,
      deductible: formData.deductible ? Number(formData.deductible) : undefined,
      scheduled_drop_off: formData.scheduled_drop_off || undefined,
      notes: formData.notes || undefined,
    }

    try {
      if (isEdit) {
        await updateJob.mutateAsync({ id: Number(id), data })
        navigate(`/jobs/${id}`)
      } else {
        const result = await createJob.mutateAsync(data)
        navigate(`/jobs/${result.job_id || ""}`)
      }
    } catch (error) {
      console.error("Failed to save job:", error)
    }
  }

  const customers = customersData?.customers || []
  const vehicles = vehiclesData?.vehicles || []

  // Filter vehicles by selected customer
  const filteredVehicles = formData.customer_id
    ? vehicles.filter((v) => v.customer_id === Number(formData.customer_id))
    : vehicles

  if (isEdit && jobLoading) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/jobs")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEdit ? "Edit Job" : "New Job"}
          description={isEdit ? `Editing job ${job?.job_number}` : "Create a new repair job"}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Customer & Vehicle</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="customer_id">Customer *</Label>
                <Select
                  value={formData.customer_id}
                  onValueChange={(value) =>
                    setFormData({ ...formData, customer_id: value, vehicle_id: "" })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id.toString()}>
                        {customer.first_name} {customer.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="vehicle_id">Vehicle</Label>
                <Select
                  value={formData.vehicle_id}
                  onValueChange={(value) => setFormData({ ...formData, vehicle_id: value })}
                  disabled={!formData.customer_id && filteredVehicles.length === 0}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select vehicle" />
                  </SelectTrigger>
                  <SelectContent>
                    {filteredVehicles.map((vehicle) => (
                      <SelectItem key={vehicle.id} value={vehicle.id.toString()}>
                        {vehicle.year} {vehicle.make} {vehicle.model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="scheduled_drop_off">Scheduled Drop-off</Label>
                <Input
                  id="scheduled_drop_off"
                  type="date"
                  value={formData.scheduled_drop_off}
                  onChange={(e) =>
                    setFormData({ ...formData, scheduled_drop_off: e.target.value })
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Job Details</CardTitle>
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
                <Label htmlFor="damage_description">Damage Description</Label>
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
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Insurance Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="insurance_company">Insurance Company</Label>
                <Input
                  id="insurance_company"
                  value={formData.insurance_company}
                  onChange={(e) =>
                    setFormData({ ...formData, insurance_company: e.target.value })
                  }
                  placeholder="State Farm, Allstate, etc."
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="claim_number">Claim Number</Label>
                <Input
                  id="claim_number"
                  value={formData.claim_number}
                  onChange={(e) =>
                    setFormData({ ...formData, claim_number: e.target.value })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="deductible">Deductible ($)</Label>
                <Input
                  id="deductible"
                  type="number"
                  value={formData.deductible}
                  onChange={(e) =>
                    setFormData({ ...formData, deductible: e.target.value })
                  }
                  placeholder="500"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Additional notes..."
                rows={6}
              />
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end gap-4 mt-6">
          <Button type="button" variant="outline" onClick={() => navigate("/jobs")}>
            Cancel
          </Button>
          <Button type="submit" disabled={createJob.isPending || updateJob.isPending}>
            <Save className="h-4 w-4 mr-2" />
            {isEdit ? "Save Changes" : "Create Job"}
          </Button>
        </div>
      </form>
    </div>
  )
}
