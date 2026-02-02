import { useParams, useNavigate } from "react-router-dom"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useLead, useConvertLead, useDeleteLead } from "@/hooks/use-leads"
import {
  ArrowLeft,
  Edit,
  Trash2,
  User,
  Car,
  FileText,
  UserCheck,
  Phone,
  Mail,
} from "lucide-react"

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  NEW: "default",
  CONTACTED: "secondary",
  QUALIFIED: "default",
  CONVERTED: "outline",
  LOST: "destructive",
}

const temperatureColors: Record<string, string> = {
  HOT: "text-red-500",
  WARM: "text-orange-500",
  COLD: "text-blue-500",
}

export function LeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: lead, isLoading } = useLead(Number(id))
  const convertLead = useConvertLead()
  const deleteLead = useDeleteLead()

  const handleConvert = async () => {
    if (confirm("Convert this lead to a customer?")) {
      try {
        const result = await convertLead.mutateAsync(Number(id))
        navigate(`/customers/${result.customer_id}`)
      } catch (error) {
        console.error("Failed to convert lead:", error)
      }
    }
  }

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this lead?")) {
      try {
        await deleteLead.mutateAsync(Number(id))
        navigate("/leads")
      } catch (error) {
        console.error("Failed to delete lead:", error)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  if (!lead) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Lead not found</h2>
        <Button variant="link" onClick={() => navigate("/leads")}>
          Back to leads
        </Button>
      </div>
    )
  }

  const displayName =
    lead.display_name || lead.name || `${lead.first_name} ${lead.last_name}`.trim()
  const canConvert = lead.status !== "CONVERTED" && lead.status !== "LOST"

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/leads")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <PageHeader
            title={displayName}
            description={`Lead created on ${new Date(lead.created_at).toLocaleDateString()}`}
          />
        </div>
        <div className="flex gap-2">
          {canConvert && (
            <Button onClick={handleConvert} disabled={convertLead.isPending}>
              <UserCheck className="h-4 w-4 mr-2" />
              Convert to Customer
            </Button>
          )}
          <Button variant="outline" onClick={() => navigate(`/leads/${id}/edit`)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Contact Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Name</p>
              <p className="font-medium">{displayName}</p>
            </div>
            {lead.email && (
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <a href={`mailto:${lead.email}`} className="hover:underline">
                  {lead.email}
                </a>
              </div>
            )}
            {lead.phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <a href={`tel:${lead.phone}`} className="hover:underline">
                  {lead.phone}
                </a>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Lead Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <Badge variant={statusColors[lead.status] || "outline"}>{lead.status}</Badge>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Temperature</p>
              <p className={`font-medium ${temperatureColors[lead.temperature] || ""}`}>
                {lead.temperature}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Source</p>
              <p className="font-medium">{lead.source}</p>
            </div>
            {lead.score !== undefined && (
              <div>
                <p className="text-sm text-muted-foreground">Lead Score</p>
                <p className="font-medium">{lead.score}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Car className="h-5 w-5" />
              Vehicle Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {lead.vehicle_year || lead.vehicle_make || lead.vehicle_model ? (
              <>
                <div>
                  <p className="text-sm text-muted-foreground">Vehicle</p>
                  <p className="font-medium">
                    {[lead.vehicle_year, lead.vehicle_make, lead.vehicle_model]
                      .filter(Boolean)
                      .join(" ")}
                  </p>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground">No vehicle information</p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Damage Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-sm text-muted-foreground">Damage Type</p>
                <p className="font-medium">{lead.damage_type || "Not specified"}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Estimated Cost</p>
                <p className="font-medium">
                  {lead.estimated_repair_cost
                    ? `$${lead.estimated_repair_cost.toLocaleString()}`
                    : "Not estimated"}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Description</p>
                <p className="font-medium">{lead.damage_description || "Not specified"}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
