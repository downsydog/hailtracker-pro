import * as React from "react"
import { useParams, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useJob, useCreateJob, useUpdateJob } from "@/hooks/use-jobs"
import { ArrowLeft } from "lucide-react"

export function JobFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEditing = !!id

  const { data: existingJob, isLoading } = useJob(Number(id))
  const createJob = useCreateJob()
  const updateJob = useUpdateJob()

  const [formData, setFormData] = React.useState({
    customer_id: "",
    vehicle_id: "",
    damage_type: "",
    scheduled_date: "",
    estimated_completion: "",
    tech_id: "",
    total: "",
    insurance_company: "",
    claim_number: "",
    deductible: "",
    notes: "",
    tech_notes: "",
    internal_notes: "",
  })

  React.useEffect(() => {
    if (existingJob) {
      setFormData({
        customer_id: String(existingJob.customer_id || ""),
        vehicle_id: String(existingJob.vehicle_id || ""),
        damage_type: existingJob.damage_type || "",
        scheduled_date: existingJob.scheduled_date?.split("T")[0] || "",
        estimated_completion: existingJob.estimated_completion?.split("T")[0] || "",
        tech_id: String(existingJob.tech_id || ""),
        total: String(existingJob.total || ""),
        insurance_company: existingJob.insurance_company || "",
        claim_number: existingJob.claim_number || "",
        deductible: String(existingJob.deductible || ""),
        notes: existingJob.notes || "",
        tech_notes: existingJob.tech_notes || "",
        internal_notes: existingJob.internal_notes || "",
      })
    }
  }, [existingJob])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const data = {
      customer_id: Number(formData.customer_id) || undefined,
      vehicle_id: Number(formData.vehicle_id) || undefined,
      damage_type: formData.damage_type || undefined,
      scheduled_date: formData.scheduled_date || undefined,
      estimated_completion: formData.estimated_completion || undefined,
      tech_id: Number(formData.tech_id) || undefined,
      total: Number(formData.total) || undefined,
      insurance_company: formData.insurance_company || undefined,
      claim_number: formData.claim_number || undefined,
      deductible: Number(formData.deductible) || undefined,
      notes: formData.notes || undefined,
      tech_notes: formData.tech_notes || undefined,
      internal_notes: formData.internal_notes || undefined,
    }

    if (isEditing) {
      await updateJob.mutateAsync({ id: Number(id), data })
      navigate(`/jobs/${id}`)
    } else {
      const result = await createJob.mutateAsync(data)
      navigate(`/jobs/${result.job_id}`)
    }
  }

  if (isLoading && isEditing) {
    return <div>Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/jobs")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={isEditing ? "Edit Job" : "New Job"}
          description={isEditing ? `Editing job ${existingJob?.job_number}` : "Create a new job"}
        />
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardContent className="pt-6 space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="customer_id">Customer ID</Label>
                <Input
                  id="customer_id"
                  name="customer_id"
                  type="number"
                  value={formData.customer_id}
                  onChange={handleChange}
                  placeholder="Enter customer ID"
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
                  placeholder="Enter vehicle ID"
                  required
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
                  <option value="">Select damage type</option>
                  <option value="HAIL">Hail Damage</option>
                  <option value="DENT">Dent</option>
                  <option value="DING">Door Ding</option>
                  <option value="CREASE">Crease</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="tech_id">Technician ID</Label>
                <Input
                  id="tech_id"
                  name="tech_id"
                  type="number"
                  value={formData.tech_id}
                  onChange={handleChange}
                  placeholder="Assign to technician"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="scheduled_date">Scheduled Date</Label>
                <Input
                  id="scheduled_date"
                  name="scheduled_date"
                  type="date"
                  value={formData.scheduled_date}
                  onChange={handleChange}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="estimated_completion">Est. Completion</Label>
                <Input
                  id="estimated_completion"
                  name="estimated_completion"
                  type="date"
                  value={formData.estimated_completion}
                  onChange={handleChange}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="total">Total ($)</Label>
                <Input
                  id="total"
                  name="total"
                  type="number"
                  step="0.01"
                  value={formData.total}
                  onChange={handleChange}
                  placeholder="0.00"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="deductible">Deductible ($)</Label>
                <Input
                  id="deductible"
                  name="deductible"
                  type="number"
                  step="0.01"
                  value={formData.deductible}
                  onChange={handleChange}
                  placeholder="0.00"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="insurance_company">Insurance Company</Label>
                <Input
                  id="insurance_company"
                  name="insurance_company"
                  value={formData.insurance_company}
                  onChange={handleChange}
                  placeholder="Insurance company name"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="claim_number">Claim Number</Label>
                <Input
                  id="claim_number"
                  name="claim_number"
                  value={formData.claim_number}
                  onChange={handleChange}
                  placeholder="Insurance claim number"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Customer Notes</Label>
              <Textarea
                id="notes"
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                placeholder="Notes visible to customer"
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tech_notes">Tech Notes</Label>
              <Textarea
                id="tech_notes"
                name="tech_notes"
                value={formData.tech_notes}
                onChange={handleChange}
                placeholder="Notes for technician"
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="internal_notes">Internal Notes</Label>
              <Textarea
                id="internal_notes"
                name="internal_notes"
                value={formData.internal_notes}
                onChange={handleChange}
                placeholder="Internal notes (not visible to customer)"
                rows={3}
              />
            </div>

            <div className="flex gap-4">
              <Button
                type="submit"
                disabled={createJob.isPending || updateJob.isPending}
              >
                {isEditing ? "Update Job" : "Create Job"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate("/jobs")}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}
