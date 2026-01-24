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
import { claimsApi } from "@/api/claims"
import { jobsApi } from "@/api/jobs"
import { ArrowLeft } from "lucide-react"

// Local claim type for form handling
interface ClaimFormData {
  claim_number: string
  insurance_company: string
  policy_number: string
  adjuster_name: string
  adjuster_email: string
  adjuster_phone: string
  adjuster_extension: string
  status: string
  claim_date: string
  adjuster_scheduled_date: string
  claimed_amount: string
  deductible: string
  approved_amount: string
  payment_received: string
  notes: string
  adjuster_notes: string
  next_follow_up_date: string
  job_id: string
}

const INSURANCE_COMPANIES = [
  "State Farm",
  "GEICO",
  "Progressive",
  "Allstate",
  "USAA",
  "Liberty Mutual",
  "Farmers",
  "Nationwide",
  "Travelers",
  "American Family",
  "Auto-Owners",
  "Erie Insurance",
  "Other",
]

const CLAIM_STATUSES = [
  "pending",
  "submitted",
  "in_review",
  "approved",
  "denied",
  "paid",
  "closed",
]

export function ClaimFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [formData, setFormData] = useState<ClaimFormData>({
    claim_number: "",
    insurance_company: "",
    policy_number: "",
    adjuster_name: "",
    adjuster_email: "",
    adjuster_phone: "",
    adjuster_extension: "",
    status: "pending",
    claim_date: new Date().toISOString().split("T")[0],
    adjuster_scheduled_date: "",
    claimed_amount: "",
    deductible: "",
    approved_amount: "",
    payment_received: "",
    notes: "",
    adjuster_notes: "",
    next_follow_up_date: "",
    job_id: "",
  })

  // Fetch jobs for dropdown using typed API
  const { data: jobsData } = useQuery({
    queryKey: ["jobs-select"],
    queryFn: () => jobsApi.list({ per_page: 100 }),
  })

  // Fetch claim if editing using typed API
  const { data: claimData } = useQuery({
    queryKey: ["claim", id],
    queryFn: () => claimsApi.getClaim(Number(id)),
    enabled: isEdit,
  })

  // Cast to any since the claim type may have more fields than the API type
  const claim = claimData?.claim as Record<string, unknown> | undefined

  // Populate form when editing
  useEffect(() => {
    if (claim) {
      setFormData({
        claim_number: String(claim.claim_number || ""),
        insurance_company: String(claim.insurance_company || ""),
        policy_number: String(claim.policy_number || ""),
        adjuster_name: String(claim.adjuster_name || ""),
        adjuster_email: String(claim.adjuster_email || ""),
        adjuster_phone: String(claim.adjuster_phone || ""),
        adjuster_extension: String(claim.adjuster_extension || ""),
        status: String(claim.status || "pending"),
        claim_date: String(claim.claim_date || ""),
        adjuster_scheduled_date: String(claim.adjuster_scheduled_date || ""),
        claimed_amount: claim.claimed_amount ? String(claim.claimed_amount) : "",
        deductible: claim.deductible ? String(claim.deductible) : "",
        approved_amount: claim.approved_amount ? String(claim.approved_amount) : "",
        payment_received: claim.payment_received ? String(claim.payment_received) : "",
        notes: String(claim.notes || ""),
        adjuster_notes: String(claim.adjuster_notes || ""),
        next_follow_up_date: String(claim.next_follow_up_date || ""),
        job_id: claim.job_id ? String(claim.job_id) : "",
      })
    }
  }, [claim])

  // Create claim using typed API
  const createClaim = useMutation({
    mutationFn: (data: Record<string, unknown>) => claimsApi.createClaim(data as any),
    onSuccess: (response) => {
      navigate(`/claims/${response.claim_id}`)
    },
  })

  // Update claim using typed API
  const updateClaim = useMutation({
    mutationFn: (data: Record<string, unknown>) => claimsApi.updateClaim(Number(id), data as any),
    onSuccess: () => {
      navigate(`/claims/${id}`)
    },
  })

  const jobs = jobsData?.jobs || []

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const data: Record<string, unknown> = {
      ...formData,
      claimed_amount: formData.claimed_amount
        ? parseFloat(formData.claimed_amount)
        : undefined,
      deductible: formData.deductible ? parseFloat(formData.deductible) : 0,
      approved_amount: formData.approved_amount
        ? parseFloat(formData.approved_amount)
        : undefined,
      payment_received: formData.payment_received
        ? parseFloat(formData.payment_received)
        : undefined,
      job_id: formData.job_id ? parseInt(formData.job_id) : undefined,
    }

    if (isEdit) {
      updateClaim.mutate(data)
    } else {
      createClaim.mutate(data)
    }
  }

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/claims">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <PageHeader
          title={isEdit ? "Edit Claim" : "New Claim"}
          description={
            isEdit ? "Update claim details" : "File a new insurance claim"
          }
        />
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Insurance Info */}
          <Card>
            <CardHeader>
              <CardTitle>Insurance Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="insurance_company">Insurance Company *</Label>
                  <Select
                    value={formData.insurance_company}
                    onValueChange={(v) => handleChange("insurance_company", v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select company" />
                    </SelectTrigger>
                    <SelectContent>
                      {INSURANCE_COMPANIES.map((company) => (
                        <SelectItem key={company} value={company}>
                          {company}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="claim_number">Claim Number</Label>
                  <Input
                    id="claim_number"
                    value={formData.claim_number}
                    onChange={(e) => handleChange("claim_number", e.target.value)}
                    placeholder="Auto-generated if blank"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="policy_number">Policy Number</Label>
                  <Input
                    id="policy_number"
                    value={formData.policy_number}
                    onChange={(e) => handleChange("policy_number", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="claim_date">Claim Date</Label>
                  <Input
                    id="claim_date"
                    type="date"
                    value={formData.claim_date}
                    onChange={(e) => handleChange("claim_date", e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="job_id">Related Job</Label>
                <Select
                  value={formData.job_id}
                  onValueChange={(v) => handleChange("job_id", v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a job (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {jobs.map((job) => (
                      <SelectItem key={job.id} value={job.id.toString()}>
                        {job.job_number} - {job.customer_name} ({job.vehicle_year}{" "}
                        {job.vehicle_make})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Adjuster Info */}
          <Card>
            <CardHeader>
              <CardTitle>Adjuster Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="adjuster_name">Adjuster Name</Label>
                <Input
                  id="adjuster_name"
                  value={formData.adjuster_name}
                  onChange={(e) => handleChange("adjuster_name", e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="adjuster_phone">Phone</Label>
                  <Input
                    id="adjuster_phone"
                    type="tel"
                    value={formData.adjuster_phone}
                    onChange={(e) => handleChange("adjuster_phone", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="adjuster_extension">Extension</Label>
                  <Input
                    id="adjuster_extension"
                    value={formData.adjuster_extension}
                    onChange={(e) =>
                      handleChange("adjuster_extension", e.target.value)
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="adjuster_email">Email</Label>
                <Input
                  id="adjuster_email"
                  type="email"
                  value={formData.adjuster_email}
                  onChange={(e) => handleChange("adjuster_email", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="adjuster_scheduled_date">
                  Adjuster Scheduled Date
                </Label>
                <Input
                  id="adjuster_scheduled_date"
                  type="datetime-local"
                  value={formData.adjuster_scheduled_date}
                  onChange={(e) =>
                    handleChange("adjuster_scheduled_date", e.target.value)
                  }
                />
              </div>
            </CardContent>
          </Card>

          {/* Financial Info */}
          <Card>
            <CardHeader>
              <CardTitle>Financial Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="claimed_amount">Claimed Amount</Label>
                  <Input
                    id="claimed_amount"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.claimed_amount}
                    onChange={(e) => handleChange("claimed_amount", e.target.value)}
                    placeholder="0.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="deductible">Deductible</Label>
                  <Input
                    id="deductible"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.deductible}
                    onChange={(e) => handleChange("deductible", e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="approved_amount">Approved Amount</Label>
                  <Input
                    id="approved_amount"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.approved_amount}
                    onChange={(e) => handleChange("approved_amount", e.target.value)}
                    placeholder="0.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="payment_received">Payment Received</Label>
                  <Input
                    id="payment_received"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.payment_received}
                    onChange={(e) =>
                      handleChange("payment_received", e.target.value)
                    }
                    placeholder="0.00"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status & Follow-up */}
          <Card>
            <CardHeader>
              <CardTitle>Status & Follow-up</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Select
                  value={formData.status}
                  onValueChange={(v) => handleChange("status", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CLAIM_STATUSES.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="next_follow_up_date">Next Follow-up Date</Label>
                <Input
                  id="next_follow_up_date"
                  type="date"
                  value={formData.next_follow_up_date}
                  onChange={(e) =>
                    handleChange("next_follow_up_date", e.target.value)
                  }
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Notes */}
        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="notes">Internal Notes</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => handleChange("notes", e.target.value)}
                  rows={4}
                  placeholder="Notes for internal use..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="adjuster_notes">Adjuster Notes</Label>
                <Textarea
                  id="adjuster_notes"
                  value={formData.adjuster_notes}
                  onChange={(e) => handleChange("adjuster_notes", e.target.value)}
                  rows={4}
                  placeholder="Notes from adjuster communications..."
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" asChild>
            <Link to="/claims">Cancel</Link>
          </Button>
          <Button
            type="submit"
            disabled={
              createClaim.isPending ||
              updateClaim.isPending ||
              !formData.insurance_company
            }
          >
            {createClaim.isPending || updateClaim.isPending
              ? "Saving..."
              : isEdit
              ? "Update Claim"
              : "File Claim"}
          </Button>
        </div>
      </form>
    </div>
  )
}
