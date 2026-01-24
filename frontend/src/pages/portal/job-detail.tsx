import * as React from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { portalApi, PortalTimelineEvent } from "@/api/portal"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Car,
  ArrowLeft,
  Calendar,
  MessageSquare,
  FileText,
  Image,
  Wrench,
  CheckCircle,
  Clock,
  AlertCircle,
  Download,
  Shield,
  DollarSign,
} from "lucide-react"

const statusColors: Record<string, string> = {
  CHECKED_IN: "bg-yellow-100 text-yellow-800 border-yellow-200",
  IN_PROGRESS: "bg-blue-100 text-blue-800 border-blue-200",
  ON_HOLD: "bg-red-100 text-red-800 border-red-200",
  COMPLETED: "bg-green-100 text-green-800 border-green-200",
  READY_FOR_PICKUP: "bg-emerald-100 text-emerald-800 border-emerald-200",
}

const timelineIcons: Record<string, React.ElementType> = {
  check_in: Car,
  in_progress: Wrench,
  completed: CheckCircle,
  message: MessageSquare,
  document: FileText,
  photo: Image,
  payment: DollarSign,
  default: Clock,
}

function TimelineItem({ event }: { event: PortalTimelineEvent }) {
  const Icon = timelineIcons[event.type] || timelineIcons.default

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`h-10 w-10 rounded-full flex items-center justify-center ${
          event.color === "green" ? "bg-green-100 text-green-600" :
          event.color === "blue" ? "bg-blue-100 text-blue-600" :
          event.color === "yellow" ? "bg-yellow-100 text-yellow-600" :
          "bg-gray-100 text-gray-600"
        }`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 w-px bg-gray-200 my-2"></div>
      </div>
      <div className="pb-6 flex-1">
        <h4 className="font-medium">{event.title}</h4>
        {event.description && (
          <p className="text-sm text-muted-foreground mt-1">{event.description}</p>
        )}
        <p className="text-xs text-muted-foreground mt-2">
          {new Date(event.timestamp).toLocaleDateString()} at{" "}
          {new Date(event.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  )
}

export function PortalJobDetailPage() {
  const { id } = useParams<{ id: string }>()

  // Fetch job details from API
  const { data: job, isLoading, error } = useQuery({
    queryKey: ["portal-job", id],
    queryFn: () => portalApi.getJob(Number(id)),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
        <h2 className="text-xl font-semibold mb-2">Job Not Found</h2>
        <p className="text-muted-foreground mb-4">
          We couldn't find this job in your account.
        </p>
        <Button asChild>
          <Link to="/portal/jobs">Back to Jobs</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/portal/jobs">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold">
              {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
            </h1>
            <Badge className={statusColors[job.status] || "bg-gray-100"}>
              {job.status_label}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1">
            Job #{job.job_number} • {job.vehicle_color}
            {job.vehicle_vin && ` • VIN: ${job.vehicle_vin.slice(-6)}`}
          </p>
        </div>
      </div>

      {/* Progress Card */}
      {job.progress_percent !== undefined && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Wrench className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-blue-900">Repair Progress</span>
              </div>
              <span className="text-lg font-bold text-blue-700">{job.progress_percent}%</span>
            </div>
            <Progress value={job.progress_percent} className="h-3" />
            {job.estimated_completion && (
              <p className="text-sm text-blue-700 mt-2">
                <Calendar className="h-4 w-4 inline mr-1" />
                Estimated completion: {new Date(job.estimated_completion).toLocaleDateString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tech Info */}
      {job.tech_name && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-full bg-gray-200 flex items-center justify-center">
                <Wrench className="h-6 w-6 text-gray-600" />
              </div>
              <div>
                <p className="font-medium">{job.tech_name}</p>
                <p className="text-sm text-muted-foreground">Your Technician</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="timeline">
        <TabsList className="w-full sm:w-auto grid grid-cols-4 sm:flex">
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="photos">Photos</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="estimate">Estimate</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Job Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {job.timeline.length > 0 ? (
                <div className="space-y-0">
                  {job.timeline.map((event) => (
                    <TimelineItem key={event.id} event={event} />
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  No timeline events yet
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="photos" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Photos ({job.photos.length})</CardTitle>
              <Button variant="outline" size="sm" asChild>
                <Link to={`/portal/jobs/${id}/photos`}>View All</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {job.photos.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {job.photos.slice(0, 6).map((photo) => (
                    <div key={photo.id} className="relative group">
                      <div className="aspect-square rounded-lg overflow-hidden bg-gray-100 border">
                        <img
                          src={photo.url}
                          alt={photo.description || "Job photo"}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = "https://via.placeholder.com/200?text=Photo"
                          }}
                        />
                      </div>
                      <Badge className="absolute top-2 left-2 text-xs capitalize">
                        {photo.type}
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center">
                  <Image className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                  <p className="font-medium">No photos yet</p>
                  <p className="text-sm text-muted-foreground">
                    Photos will be added as work progresses
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documents" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Documents ({job.documents.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {job.documents.length > 0 ? (
                <div className="space-y-3">
                  {job.documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                          <FileText className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium">{doc.name}</p>
                          <p className="text-xs text-muted-foreground capitalize">
                            {doc.type} • {new Date(doc.created_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <Button variant="ghost" size="icon">
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                  <p className="font-medium">No documents yet</p>
                  <p className="text-sm text-muted-foreground">
                    Documents will appear here when available
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="estimate" className="mt-4">
          {job.estimate ? (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base">Estimate #{job.estimate.estimate_number}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Created {new Date(job.estimate.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge className={
                  job.estimate.status === "approved" ? "bg-green-100 text-green-800" :
                  job.estimate.status === "pending" ? "bg-yellow-100 text-yellow-800" :
                  "bg-gray-100"
                }>
                  {job.estimate.status}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {job.estimate.items.map((item) => (
                    <div key={item.id} className="flex justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="font-medium">{item.description}</p>
                        <p className="text-sm text-muted-foreground">
                          {item.service_type} • Qty: {item.quantity}
                        </p>
                      </div>
                      <p className="font-medium">${item.total.toFixed(2)}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 pt-4 border-t space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Subtotal</span>
                    <span>${job.estimate.subtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Tax</span>
                    <span>${job.estimate.tax.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-lg pt-2">
                    <span>Total</span>
                    <span>${job.estimate.total.toFixed(2)}</span>
                  </div>
                </div>

                {job.estimate.status === "pending" && (
                  <Button className="w-full mt-4">
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Approve Estimate
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <h3 className="font-medium mb-1">Estimate Not Ready</h3>
                <p className="text-sm text-muted-foreground">
                  Your estimate is being prepared and will appear here soon.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Quick Actions */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Button variant="outline" className="h-auto py-3 flex-col" asChild>
              <Link to={`/portal/messages?job_id=${id}`}>
                <MessageSquare className="h-5 w-5 mb-1" />
                <span className="text-xs">Message Shop</span>
              </Link>
            </Button>
            <Button variant="outline" className="h-auto py-3 flex-col" asChild>
              <Link to={`/portal/jobs/${id}/insurance`}>
                <Shield className="h-5 w-5 mb-1" />
                <span className="text-xs">Insurance</span>
              </Link>
            </Button>
            <Button variant="outline" className="h-auto py-3 flex-col" asChild>
              <Link to={`/portal/appointments?job_id=${id}`}>
                <Calendar className="h-5 w-5 mb-1" />
                <span className="text-xs">Appointments</span>
              </Link>
            </Button>
            <Button variant="outline" className="h-auto py-3 flex-col" asChild>
              <Link to={`/portal/jobs/${id}/payment`}>
                <DollarSign className="h-5 w-5 mb-1" />
                <span className="text-xs">Payment</span>
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
