import * as React from "react"
import { useSearchParams } from "react-router-dom"
import { portalApi, InsuranceStatus, PortalJob } from "@/api/portal"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Shield,
  CheckCircle,
  Clock,
  AlertCircle,
  Phone,
  Mail,
  User,
  FileText,
} from "lucide-react"

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  submitted: "bg-blue-100 text-blue-800",
  approved: "bg-green-100 text-green-800",
  denied: "bg-red-100 text-red-800",
  supplement_needed: "bg-orange-100 text-orange-800",
}

const statusIcons: Record<string, React.ElementType> = {
  pending: Clock,
  submitted: FileText,
  approved: CheckCircle,
  denied: AlertCircle,
  supplement_needed: AlertCircle,
}

export function PortalInsurancePage() {
  const [searchParams] = useSearchParams()
  const jobIdParam = searchParams.get("job_id")
  const [jobs, setJobs] = React.useState<PortalJob[]>([])
  const [selectedJob, setSelectedJob] = React.useState<string>(jobIdParam || "")
  const [insurance, setInsurance] = React.useState<InsuranceStatus | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const fetchJobs = async () => {
      try {
        const result = await portalApi.getJobs()
        setJobs(result.jobs)
        if (!selectedJob && result.jobs.length > 0) {
          setSelectedJob(result.jobs[0].id.toString())
        }
      } catch {
        // Demo data
        setJobs([
          {
            id: 1,
            job_number: "JOB-2025-001",
            vehicle_year: 2023,
            vehicle_make: "Toyota",
            vehicle_model: "Camry",
            status: "IN_PROGRESS",
            status_label: "In Progress",
            photos_count: 12,
            documents_count: 3,
            messages_count: 5,
            created_at: "2025-01-20",
            updated_at: "2025-01-23",
          },
        ])
        if (!selectedJob) {
          setSelectedJob("1")
        }
      }
    }
    fetchJobs()
  }, [])

  React.useEffect(() => {
    const fetchInsurance = async () => {
      if (!selectedJob) return
      setLoading(true)
      try {
        const result = await portalApi.getInsuranceStatus(Number(selectedJob))
        setInsurance(result)
      } catch {
        // Demo data
        setInsurance({
          claim_number: "CLM-2025-45678",
          insurance_company: "State Farm Insurance",
          adjuster_name: "Sarah Williams",
          adjuster_phone: "(555) 987-6543",
          adjuster_email: "sarah.williams@statefarm.example.com",
          status: "approved",
          status_label: "Approved",
          deductible: 500,
          approved_amount: 3450,
          supplements: [
            {
              id: 1,
              amount: 750,
              reason: "Additional hidden damage found on roof rails",
              status: "pending",
              submitted_at: "2025-01-22",
            },
          ],
          timeline: [
            {
              id: 1,
              type: "submitted",
              title: "Claim Submitted",
              description: "Initial claim filed with insurance company",
              timestamp: "2025-01-20T10:00:00",
              color: "blue",
            },
            {
              id: 2,
              type: "review",
              title: "Under Review",
              description: "Insurance adjuster assigned to claim",
              timestamp: "2025-01-21T09:00:00",
              color: "yellow",
            },
            {
              id: 3,
              type: "approved",
              title: "Claim Approved",
              description: "Initial claim approved for $3,450",
              timestamp: "2025-01-21T16:00:00",
              color: "green",
            },
            {
              id: 4,
              type: "supplement",
              title: "Supplement Submitted",
              description: "Additional damage supplement submitted for $750",
              timestamp: "2025-01-22T11:00:00",
              color: "blue",
            },
          ],
        })
      } finally {
        setLoading(false)
      }
    }
    fetchInsurance()
  }, [selectedJob])

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const StatusIcon = insurance ? statusIcons[insurance.status] || Shield : Shield

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Insurance Status</h1>
        <p className="text-muted-foreground">
          Track your insurance claim progress
        </p>
      </div>

      {/* Job Selector */}
      {jobs.length > 1 && (
        <Select value={selectedJob} onValueChange={setSelectedJob}>
          <SelectTrigger className="w-full sm:w-[300px]">
            <SelectValue placeholder="Select a job" />
          </SelectTrigger>
          <SelectContent>
            {jobs.map((job) => (
              <SelectItem key={job.id} value={job.id.toString()}>
                {job.job_number} - {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {insurance ? (
        <>
          {/* Status Card */}
          <Card className={`border-2 ${
            insurance.status === "approved" ? "border-green-200 bg-green-50" :
            insurance.status === "pending" ? "border-yellow-200 bg-yellow-50" :
            insurance.status === "denied" ? "border-red-200 bg-red-50" :
            "border-blue-200 bg-blue-50"
          }`}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <div className={`h-16 w-16 rounded-full flex items-center justify-center ${
                    insurance.status === "approved" ? "bg-green-100" :
                    insurance.status === "pending" ? "bg-yellow-100" :
                    insurance.status === "denied" ? "bg-red-100" :
                    "bg-blue-100"
                  }`}>
                    <StatusIcon className={`h-8 w-8 ${
                      insurance.status === "approved" ? "text-green-600" :
                      insurance.status === "pending" ? "text-yellow-600" :
                      insurance.status === "denied" ? "text-red-600" :
                      "text-blue-600"
                    }`} />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold">{insurance.status_label}</h2>
                    <p className="text-muted-foreground">
                      Claim #{insurance.claim_number}
                    </p>
                  </div>
                </div>
                {insurance.approved_amount && (
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Approved Amount</p>
                    <p className="text-2xl font-bold text-green-600">
                      ${insurance.approved_amount.toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Details Grid */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Insurance Company */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Insurance Company</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-blue-600" />
                  <span className="font-medium">{insurance.insurance_company}</span>
                </div>
                {insurance.deductible && (
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <span className="text-sm">Your Deductible</span>
                    <span className="font-bold">${insurance.deductible.toLocaleString()}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Adjuster Contact */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Insurance Adjuster</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {insurance.adjuster_name && (
                  <div className="flex items-center gap-3">
                    <User className="h-5 w-5 text-muted-foreground" />
                    <span>{insurance.adjuster_name}</span>
                  </div>
                )}
                {insurance.adjuster_phone && (
                  <a
                    href={`tel:${insurance.adjuster_phone}`}
                    className="flex items-center gap-3 text-blue-600 hover:underline"
                  >
                    <Phone className="h-5 w-5" />
                    <span>{insurance.adjuster_phone}</span>
                  </a>
                )}
                {insurance.adjuster_email && (
                  <a
                    href={`mailto:${insurance.adjuster_email}`}
                    className="flex items-center gap-3 text-blue-600 hover:underline"
                  >
                    <Mail className="h-5 w-5" />
                    <span className="truncate">{insurance.adjuster_email}</span>
                  </a>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Supplements */}
          {(insurance.supplements?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Supplements</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {insurance.supplements?.map((supp) => (
                  <div
                    key={supp.id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium">${supp.amount.toLocaleString()}</p>
                      <p className="text-sm text-muted-foreground">{supp.reason}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Submitted: {supp.submitted_at ? new Date(supp.submitted_at).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                    <Badge className={statusColors[supp.status]}>
                      {supp.status}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Claim Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-0">
                {insurance.timeline?.map((event, index) => (
                  <div key={event.id ?? index} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
                        event.color === "green" ? "bg-green-100 text-green-600" :
                        event.color === "blue" ? "bg-blue-100 text-blue-600" :
                        event.color === "yellow" ? "bg-yellow-100 text-yellow-600" :
                        event.color === "red" ? "bg-red-100 text-red-600" :
                        "bg-gray-100 text-gray-600"
                      }`}>
                        <CheckCircle className="h-5 w-5" />
                      </div>
                      {index < (insurance.timeline?.length ?? 0) - 1 && (
                        <div className="flex-1 w-px bg-gray-200 my-2"></div>
                      )}
                    </div>
                    <div className="pb-6 flex-1">
                      <h4 className="font-medium">{event.title}</h4>
                      {event.description && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {event.description}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-2">
                        {event.timestamp ? new Date(event.timestamp).toLocaleDateString() : 'N/A'} at{" "}
                        {event.timestamp ? new Date(event.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        }) : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
            <h3 className="font-medium mb-1">No Insurance Information</h3>
            <p className="text-sm text-muted-foreground">
              Insurance claim details will appear here once submitted
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
