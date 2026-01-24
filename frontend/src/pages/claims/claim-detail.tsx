import { useParams, Link, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { claimsApi } from "@/api/claims"
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Shield,
  Phone,
  Mail,
  Calendar,
  DollarSign,
  User,
  Car,
  FileText,
  Clock,
} from "lucide-react"
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

// Local claim type for this page's extended fields
interface Claim {
  id: number
  claim_number: string
  insurance_company: string
  policy_number: string
  status: string
  adjuster_name: string
  adjuster_email: string
  adjuster_phone: string
  adjuster_extension: string
  claim_date: string
  submitted_date: string
  adjuster_scheduled_date: string
  adjuster_inspection_date: string
  approval_date: string
  payment_received_date: string
  claimed_amount: number
  approved_amount: number
  supplement_amount: number
  deductible: number
  payment_received: number
  notes: string
  adjuster_notes: string
  last_contact_date: string
  last_contact_method: string
  next_follow_up_date: string
  follow_up_count: number
  job_id: number
  job_number: string
  customer_id: number
  customer_name: string
  customer_phone: string
  customer_email: string
  vehicle_year: number
  vehicle_make: string
  vehicle_model: string
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-800",
  submitted: "bg-blue-100 text-blue-800",
  in_review: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  paid: "bg-emerald-100 text-emerald-800",
  closed: "bg-gray-100 text-gray-800",
}

export function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Fetch claim using typed API
  const { data: claimData, isLoading } = useQuery({
    queryKey: ["claim", id],
    queryFn: () => claimsApi.getClaim(Number(id)),
  })

  // Cast to local type for extended fields
  const claim = claimData?.claim as Claim | undefined

  // Delete claim using typed API
  const deleteClaim = useMutation({
    mutationFn: () => claimsApi.deleteClaim(Number(id)),
    onSuccess: () => {
      navigate("/claims")
    },
  })

  // Update status using typed API
  const updateStatus = useMutation({
    mutationFn: (status: 'pending' | 'submitted' | 'in_review' | 'approved' | 'denied' | 'paid' | 'closed') =>
      claimsApi.updateStatus(Number(id), status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["claim", id] })
    },
  })

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return "$0.00"
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!claim) {
    return (
      <div className="text-center py-12">
        <Shield className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
        <p className="text-muted-foreground">Claim not found</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/claims">Back to claims</Link>
        </Button>
      </div>
    )
  }

  const statusLabel = claim.status?.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/claims">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{claim.claim_number}</h1>
              <Badge className={STATUS_COLORS[claim.status] || "bg-gray-100 text-gray-800"}>
                {statusLabel}
              </Badge>
            </div>
            <p className="text-muted-foreground">{claim.insurance_company}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to={`/claims/${id}/edit`}>
              <Pencil className="h-4 w-4 mr-2" />
              Edit
            </Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="icon">
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Claim?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently delete this claim record.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => deleteClaim.mutate()}
                  className="bg-destructive text-destructive-foreground"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Insurance & Adjuster Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Insurance Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold mb-3">Insurance Company</h3>
                  <p className="text-lg">{claim.insurance_company}</p>
                  {claim.policy_number && (
                    <p className="text-muted-foreground">
                      Policy: {claim.policy_number}
                    </p>
                  )}
                </div>
                <div>
                  <h3 className="font-semibold mb-3">Adjuster</h3>
                  {claim.adjuster_name ? (
                    <div className="space-y-1">
                      <p className="text-lg">{claim.adjuster_name}</p>
                      {claim.adjuster_phone && (
                        <a
                          href={`tel:${claim.adjuster_phone}${claim.adjuster_extension ? `,${claim.adjuster_extension}` : ""}`}
                          className="flex items-center gap-2 text-muted-foreground hover:text-primary"
                        >
                          <Phone className="h-4 w-4" />
                          {claim.adjuster_phone}
                          {claim.adjuster_extension && ` ext. ${claim.adjuster_extension}`}
                        </a>
                      )}
                      {claim.adjuster_email && (
                        <a
                          href={`mailto:${claim.adjuster_email}`}
                          className="flex items-center gap-2 text-muted-foreground hover:text-primary"
                        >
                          <Mail className="h-4 w-4" />
                          {claim.adjuster_email}
                        </a>
                      )}
                    </div>
                  ) : (
                    <p className="text-muted-foreground">Not assigned yet</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Financial Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5" />
                Financial Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">Claimed</p>
                  <p className="text-xl font-bold">
                    {formatCurrency(claim.claimed_amount)}
                  </p>
                </div>
                <div className="p-4 bg-green-50 dark:bg-green-950 rounded-lg">
                  <p className="text-sm text-muted-foreground">Approved</p>
                  <p className="text-xl font-bold text-green-600">
                    {formatCurrency(claim.approved_amount)}
                  </p>
                </div>
                <div className="p-4 bg-orange-50 dark:bg-orange-950 rounded-lg">
                  <p className="text-sm text-muted-foreground">Deductible</p>
                  <p className="text-xl font-bold text-orange-600">
                    {formatCurrency(claim.deductible)}
                  </p>
                </div>
                <div className="p-4 bg-emerald-50 dark:bg-emerald-950 rounded-lg">
                  <p className="text-sm text-muted-foreground">Received</p>
                  <p className="text-xl font-bold text-emerald-600">
                    {formatCurrency(claim.payment_received)}
                  </p>
                </div>
              </div>
              {claim.supplement_amount && claim.supplement_amount > 0 && (
                <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg">
                  <p className="text-sm text-muted-foreground">Supplement Amount</p>
                  <p className="text-xl font-bold text-blue-600">
                    {formatCurrency(claim.supplement_amount)}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {claim.claim_date && (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <div>
                      <p className="font-medium">Claim Filed</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(claim.claim_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {claim.submitted_date && (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-purple-500" />
                    <div>
                      <p className="font-medium">Submitted to Insurance</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(claim.submitted_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {claim.adjuster_scheduled_date && (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <div>
                      <p className="font-medium">Adjuster Scheduled</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(claim.adjuster_scheduled_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {claim.adjuster_inspection_date && (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-indigo-500" />
                    <div>
                      <p className="font-medium">Inspection Completed</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(claim.adjuster_inspection_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {claim.approval_date && (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <div>
                      <p className="font-medium">Approved</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(claim.approval_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
                {claim.payment_received_date && (
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 rounded-full bg-emerald-500" />
                    <div>
                      <p className="font-medium">Payment Received</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(claim.payment_received_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          {(claim.notes || claim.adjuster_notes) && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {claim.notes && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">
                      Internal Notes
                    </p>
                    <p className="whitespace-pre-wrap">{claim.notes}</p>
                  </div>
                )}
                {claim.adjuster_notes && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">
                      Adjuster Notes
                    </p>
                    <p className="whitespace-pre-wrap">{claim.adjuster_notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Update Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {claim.status === "pending" && (
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => updateStatus.mutate("submitted")}
                >
                  Submit to Insurance
                </Button>
              )}
              {claim.status === "submitted" && (
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => updateStatus.mutate("in_review")}
                >
                  Mark as In Review
                </Button>
              )}
              {claim.status === "in_review" && (
                <>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-green-600"
                    onClick={() => updateStatus.mutate("approved")}
                  >
                    Mark as Approved
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-red-600"
                    onClick={() => updateStatus.mutate("denied")}
                  >
                    Mark as Denied
                  </Button>
                </>
              )}
              {claim.status === "approved" && (
                <Button
                  variant="outline"
                  className="w-full justify-start text-emerald-600"
                  onClick={() => updateStatus.mutate("paid")}
                >
                  Mark as Paid
                </Button>
              )}
              {claim.status === "paid" && (
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => updateStatus.mutate("closed")}
                >
                  Close Claim
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Follow-up Info */}
          {claim.next_follow_up_date && (
            <Card className="bg-yellow-50 dark:bg-yellow-950">
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-4 w-4 text-yellow-600" />
                  <span className="font-medium text-yellow-800 dark:text-yellow-200">
                    Next Follow-up
                  </span>
                </div>
                <p className="text-lg font-bold">
                  {new Date(claim.next_follow_up_date).toLocaleDateString()}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {claim.follow_up_count} follow-ups so far
                </p>
              </CardContent>
            </Card>
          )}

          {/* Related Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Related</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {claim.customer_id && (
                <div className="flex items-center gap-3">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Customer</p>
                    <Link
                      to={`/customers/${claim.customer_id}`}
                      className="font-medium hover:underline"
                    >
                      {claim.customer_name}
                    </Link>
                  </div>
                </div>
              )}
              {claim.job_id && (
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Job</p>
                    <Link
                      to={`/jobs/${claim.job_id}`}
                      className="font-medium hover:underline"
                    >
                      {claim.job_number}
                    </Link>
                  </div>
                </div>
              )}
              {claim.vehicle_year && (
                <div className="flex items-center gap-3">
                  <Car className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Vehicle</p>
                    <p className="font-medium">
                      {claim.vehicle_year} {claim.vehicle_make} {claim.vehicle_model}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
