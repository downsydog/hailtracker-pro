import * as React from "react"
import { portalApi, PortalAppointment } from "@/api/portal"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Calendar,
  Clock,
  MapPin,
  CheckCircle,
  AlertCircle,
} from "lucide-react"

const appointmentTypeLabels: Record<string, string> = {
  drop_off: "Vehicle Drop-off",
  pick_up: "Vehicle Pick-up",
  check_in: "Check-in",
  inspection: "Inspection",
}

const statusColors: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-800",
  confirmed: "bg-green-100 text-green-800",
  completed: "bg-gray-100 text-gray-800",
  cancelled: "bg-red-100 text-red-800",
}

export function PortalAppointmentsPage() {
  const [appointments, setAppointments] = React.useState<PortalAppointment[]>([])
  const [loading, setLoading] = React.useState(true)
  const [rescheduleOpen, setRescheduleOpen] = React.useState(false)
  const [selectedApt, setSelectedApt] = React.useState<PortalAppointment | null>(null)
  const [rescheduleData, setRescheduleData] = React.useState({
    preferred_date: "",
    preferred_time: "",
    reason: "",
  })

  React.useEffect(() => {
    const fetchAppointments = async () => {
      try {
        const result = await portalApi.getAppointments()
        setAppointments(result.appointments)
      } catch {
        // Demo data
        setAppointments([
          {
            id: 1,
            job_id: 1,
            type: "pick_up",
            scheduled_at: "2025-01-28T14:00:00",
            location: "Main Shop - 123 Repair Lane",
            notes: "Please bring ID and insurance card",
            status: "scheduled",
          },
          {
            id: 2,
            job_id: 1,
            type: "drop_off",
            scheduled_at: "2025-01-20T09:00:00",
            location: "Main Shop - 123 Repair Lane",
            status: "completed",
          },
        ])
      } finally {
        setLoading(false)
      }
    }
    fetchAppointments()
  }, [])

  const handleReschedule = async () => {
    if (!selectedApt) return

    try {
      await portalApi.requestReschedule(selectedApt.id, rescheduleData)
      setRescheduleOpen(false)
      setRescheduleData({ preferred_date: "", preferred_time: "", reason: "" })
      // Show success message
    } catch (error) {
      console.error("Failed to request reschedule:", error)
    }
  }

  const upcomingAppointments = appointments.filter(
    (a) => !["completed", "cancelled"].includes(a.status)
  )
  const pastAppointments = appointments.filter(
    (a) => ["completed", "cancelled"].includes(a.status)
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Appointments</h1>
          <p className="text-muted-foreground">
            View and manage your scheduled appointments
          </p>
        </div>
      </div>

      {/* Upcoming Appointments */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Upcoming</h2>
        {upcomingAppointments.length > 0 ? (
          <div className="space-y-4">
            {upcomingAppointments.map((apt) => (
              <Card key={apt.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Calendar className="h-6 w-6 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold">
                          {appointmentTypeLabels[apt.type] || apt.type}
                        </h3>
                        <div className="mt-2 space-y-1 text-sm text-muted-foreground">
                          <p className="flex items-center gap-2">
                            <Clock className="h-4 w-4" />
                            {new Date(apt.scheduled_at).toLocaleDateString()} at{" "}
                            {new Date(apt.scheduled_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                          {apt.location && (
                            <p className="flex items-center gap-2">
                              <MapPin className="h-4 w-4" />
                              {apt.location}
                            </p>
                          )}
                          {apt.notes && (
                            <p className="flex items-center gap-2">
                              <AlertCircle className="h-4 w-4" />
                              {apt.notes}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge className={statusColors[apt.status]}>
                        {apt.status}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedApt(apt)
                          setRescheduleOpen(true)
                        }}
                      >
                        Request Reschedule
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
              <h3 className="font-medium mb-1">No Upcoming Appointments</h3>
              <p className="text-sm text-muted-foreground">
                You'll see your scheduled appointments here
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Past Appointments */}
      {pastAppointments.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Past Appointments</h2>
          <div className="space-y-4">
            {pastAppointments.map((apt) => (
              <Card key={apt.id} className="opacity-75">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-lg bg-gray-100 flex items-center justify-center">
                        {apt.status === "completed" ? (
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        ) : (
                          <AlertCircle className="h-5 w-5 text-red-600" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-medium">
                          {appointmentTypeLabels[apt.type] || apt.type}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {new Date(apt.scheduled_at).toLocaleDateString()} at{" "}
                          {new Date(apt.scheduled_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                    <Badge className={statusColors[apt.status]}>
                      {apt.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Reschedule Dialog */}
      <Dialog open={rescheduleOpen} onOpenChange={setRescheduleOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Reschedule</DialogTitle>
            <DialogDescription>
              Submit a reschedule request and we'll contact you to confirm.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="date">Preferred Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={rescheduleData.preferred_date}
                  onChange={(e) =>
                    setRescheduleData({ ...rescheduleData, preferred_date: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="time">Preferred Time</Label>
                <Input
                  id="time"
                  type="time"
                  value={rescheduleData.preferred_time}
                  onChange={(e) =>
                    setRescheduleData({ ...rescheduleData, preferred_time: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">Reason (optional)</Label>
              <Textarea
                id="reason"
                placeholder="Let us know why you need to reschedule..."
                value={rescheduleData.reason}
                onChange={(e) =>
                  setRescheduleData({ ...rescheduleData, reason: e.target.value })
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRescheduleOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleReschedule}>Submit Request</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
