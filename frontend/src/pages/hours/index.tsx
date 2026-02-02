import { useState, useEffect } from "react"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  Clock,
  Coffee,
  Play,
  Square,
  Calendar,
  Timer,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
} from "lucide-react"
import api from "@/api/client"

interface TimeStatus {
  status: "clocked_out" | "clocked_in" | "on_break"
  clock_in_time: string | null
  clock_out_time: string | null
  total_hours: number
  break_hours: number
  job_hours: number
}

interface DailyTotal {
  date: string
  day_name: string
  hours: number
  is_complete: boolean
}

interface WeekSummary {
  week_start: string
  week_end: string
  daily_totals: DailyTotal[]
  total_hours: number
  total_break_hours: number
  total_job_hours: number
  job_breakdown: Array<{
    job_id: number
    job_number: string
    customer_name: string
    vehicle: string
    total_hours: number
  }>
}

interface TimeEntry {
  id: number
  entry_type: string
  entry_time: string
  job_id?: number
  hours?: number
  description?: string
}

export function HoursPage() {
  const [status, setStatus] = useState<TimeStatus>({
    status: "clocked_out",
    clock_in_time: null,
    clock_out_time: null,
    total_hours: 0,
    break_hours: 0,
    job_hours: 0,
  })
  const [weekSummary, setWeekSummary] = useState<WeekSummary | null>(null)
  const [entries, setEntries] = useState<TimeEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [weekOffset, setWeekOffset] = useState(0)

  // Update current time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const fetchData = async () => {
    try {
      // Fetch today's status
      const todayResponse = await api.get("/api/tech/time/today")
      if (todayResponse.data) {
        setStatus(todayResponse.data)
        setEntries(todayResponse.data.entries || [])
      }

      // Fetch week summary
      const weekResponse = await api.get(`/api/tech/time/week?offset=${weekOffset}`)
      if (weekResponse.data) {
        setWeekSummary(weekResponse.data)
      }
    } catch (error) {
      console.log("Using demo data for hours page")
      // Demo data
      setStatus({
        status: "clocked_in",
        clock_in_time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
        clock_out_time: null,
        total_hours: 4.25,
        break_hours: 0.5,
        job_hours: 3.5,
      })
      setEntries([
        { id: 1, entry_type: "clock_in", entry_time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString() },
        { id: 2, entry_type: "break_start", entry_time: new Date(Date.now() - 2.5 * 60 * 60 * 1000).toISOString() },
        { id: 3, entry_type: "break_end", entry_time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), hours: 0.5 },
        { id: 4, entry_type: "job_time", entry_time: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), job_id: 101, hours: 2, description: "Hood and fender repair" },
      ])
      setWeekSummary({
        week_start: "2025-01-20",
        week_end: "2025-01-26",
        daily_totals: [
          { date: "2025-01-20", day_name: "Monday", hours: 8.5, is_complete: true },
          { date: "2025-01-21", day_name: "Tuesday", hours: 8.0, is_complete: true },
          { date: "2025-01-22", day_name: "Wednesday", hours: 7.5, is_complete: true },
          { date: "2025-01-23", day_name: "Thursday", hours: 4.25, is_complete: false },
          { date: "2025-01-24", day_name: "Friday", hours: 0, is_complete: false },
          { date: "2025-01-25", day_name: "Saturday", hours: 0, is_complete: false },
          { date: "2025-01-26", day_name: "Sunday", hours: 0, is_complete: false },
        ],
        total_hours: 28.25,
        total_break_hours: 2.5,
        total_job_hours: 25,
        job_breakdown: [
          { job_id: 101, job_number: "JOB-00101", customer_name: "John Smith", vehicle: "2023 Toyota Camry", total_hours: 8.5 },
          { job_id: 102, job_number: "JOB-00102", customer_name: "Sarah Johnson", vehicle: "2022 Honda Accord", total_hours: 6.0 },
          { job_id: 103, job_number: "JOB-00103", customer_name: "Mike Davis", vehicle: "2024 Ford F-150", total_hours: 10.5 },
        ],
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [weekOffset])

  const handleClockIn = async () => {
    setActionLoading(true)
    try {
      await api.post("/api/tech/time/clock-in")
      fetchData()
    } catch (error) {
      // Demo mode - simulate clock in
      setStatus((prev) => ({
        ...prev,
        status: "clocked_in",
        clock_in_time: new Date().toISOString(),
      }))
    } finally {
      setActionLoading(false)
    }
  }

  const handleClockOut = async () => {
    setActionLoading(true)
    try {
      await api.post("/api/tech/time/clock-out")
      fetchData()
    } catch (error) {
      // Demo mode - simulate clock out
      setStatus((prev) => ({
        ...prev,
        status: "clocked_out",
        clock_out_time: new Date().toISOString(),
      }))
    } finally {
      setActionLoading(false)
    }
  }

  const handleStartBreak = async () => {
    setActionLoading(true)
    try {
      await api.post("/api/tech/time/break/start")
      fetchData()
    } catch (error) {
      // Demo mode
      setStatus((prev) => ({ ...prev, status: "on_break" }))
    } finally {
      setActionLoading(false)
    }
  }

  const handleEndBreak = async () => {
    setActionLoading(true)
    try {
      await api.post("/api/tech/time/break/end")
      fetchData()
    } catch (error) {
      // Demo mode
      setStatus((prev) => ({ ...prev, status: "clocked_in" }))
    } finally {
      setActionLoading(false)
    }
  }

  const formatTime = (isoString: string | null) => {
    if (!isoString) return "--:--"
    return new Date(isoString).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    })
  }

  const formatHours = (hours: number) => {
    const h = Math.floor(hours)
    const m = Math.round((hours - h) * 60)
    return `${h}h ${m}m`
  }

  const getStatusBadge = () => {
    switch (status.status) {
      case "clocked_in":
        return <Badge className="bg-green-500">Clocked In</Badge>
      case "on_break":
        return <Badge className="bg-yellow-500">On Break</Badge>
      case "clocked_out":
        return <Badge variant="secondary">Clocked Out</Badge>
    }
  }

  const getEntryTypeIcon = (type: string) => {
    switch (type) {
      case "clock_in":
        return <Play className="h-4 w-4 text-green-500" />
      case "clock_out":
        return <Square className="h-4 w-4 text-red-500" />
      case "break_start":
        return <Coffee className="h-4 w-4 text-yellow-500" />
      case "break_end":
        return <Coffee className="h-4 w-4 text-green-500" />
      case "job_time":
        return <Briefcase className="h-4 w-4 text-blue-500" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const getEntryTypeLabel = (type: string) => {
    switch (type) {
      case "clock_in":
        return "Clocked In"
      case "clock_out":
        return "Clocked Out"
      case "break_start":
        return "Break Started"
      case "break_end":
        return "Break Ended"
      case "job_time":
        return "Job Time Logged"
      default:
        return type
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const targetHours = 40
  const weekProgress = weekSummary ? (weekSummary.total_hours / targetHours) * 100 : 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Time Tracking"
        description="Track your work hours, breaks, and job time"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Clock & Today */}
        <div className="space-y-6">
          {/* Current Time & Status */}
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-5xl font-bold tabular-nums">
                  {currentTime.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {currentTime.toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                  })}
                </p>
                <div className="mt-4">
                  {getStatusBadge()}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Clock Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {status.status === "clocked_out" ? (
                <Button
                  className="w-full h-14 text-lg"
                  onClick={handleClockIn}
                  disabled={actionLoading}
                >
                  <Play className="h-5 w-5 mr-2" />
                  Clock In
                </Button>
              ) : (
                <>
                  {status.status === "clocked_in" ? (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={handleStartBreak}
                      disabled={actionLoading}
                    >
                      <Coffee className="h-4 w-4 mr-2" />
                      Start Break
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={handleEndBreak}
                      disabled={actionLoading}
                    >
                      <Coffee className="h-4 w-4 mr-2" />
                      End Break
                    </Button>
                  )}
                  <Button
                    variant="destructive"
                    className="w-full h-14 text-lg"
                    onClick={handleClockOut}
                    disabled={actionLoading}
                  >
                    <Square className="h-5 w-5 mr-2" />
                    Clock Out
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* Today's Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                Today
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-muted rounded-lg">
                  <p className="text-2xl font-bold">{formatTime(status.clock_in_time)}</p>
                  <p className="text-xs text-muted-foreground">Clock In</p>
                </div>
                <div className="text-center p-3 bg-muted rounded-lg">
                  <p className="text-2xl font-bold">{formatTime(status.clock_out_time)}</p>
                  <p className="text-xs text-muted-foreground">Clock Out</p>
                </div>
              </div>
              <Separator />
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hours Worked</span>
                  <span className="font-semibold">{formatHours(status.total_hours)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Break Time</span>
                  <span className="font-semibold">{formatHours(status.break_hours)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Job Time</span>
                  <span className="font-semibold">{formatHours(status.job_hours)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Middle Column - Week Summary */}
        <div className="space-y-6">
          {/* Week Navigation */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-base">Week Summary</CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setWeekOffset(weekOffset - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setWeekOffset(0)}
                  disabled={weekOffset === 0}
                >
                  This Week
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setWeekOffset(weekOffset + 1)}
                  disabled={weekOffset >= 0}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {weekSummary && (
                <>
                  <div className="text-center">
                    <p className="text-4xl font-bold">{formatHours(weekSummary.total_hours)}</p>
                    <p className="text-sm text-muted-foreground">of {targetHours}h target</p>
                    <Progress value={weekProgress} className="mt-2" />
                  </div>
                  <Separator />
                  <div className="space-y-2">
                    {weekSummary.daily_totals.map((day) => (
                      <div
                        key={day.date}
                        className="flex items-center justify-between p-2 rounded hover:bg-muted/50"
                      >
                        <div className="flex items-center gap-2">
                          {day.is_complete && (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          )}
                          <span className={day.hours === 0 ? "text-muted-foreground" : ""}>
                            {day.day_name}
                          </span>
                        </div>
                        <span className={`font-mono ${day.hours === 0 ? "text-muted-foreground" : "font-medium"}`}>
                          {day.hours > 0 ? formatHours(day.hours) : "--"}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Job Breakdown */}
          {weekSummary && weekSummary.job_breakdown.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Time by Job</CardTitle>
                <CardDescription>Hours logged to jobs this week</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y">
                  {weekSummary.job_breakdown.map((job) => (
                    <div key={job.job_id} className="flex items-center justify-between p-4">
                      <div className="min-w-0">
                        <p className="font-medium truncate">{job.customer_name}</p>
                        <p className="text-sm text-muted-foreground truncate">
                          {job.vehicle}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {job.job_number}
                        </p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="font-semibold">{formatHours(job.total_hours)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Today's Entries */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Timer className="h-4 w-4" />
                Today's Activity
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {entries.length > 0 ? (
                <div className="divide-y">
                  {entries.map((entry) => (
                    <div key={entry.id} className="flex items-start gap-3 p-4">
                      <div className="mt-0.5">
                        {getEntryTypeIcon(entry.entry_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium">{getEntryTypeLabel(entry.entry_type)}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatTime(entry.entry_time)}
                        </p>
                        {entry.description && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {entry.description}
                          </p>
                        )}
                      </div>
                      {entry.hours && (
                        <Badge variant="outline">{formatHours(entry.hours)}</Badge>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center">
                  <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                  <p className="font-medium">No activity today</p>
                  <p className="text-sm text-muted-foreground">
                    Clock in to start tracking your time
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Today</p>
                <p className="text-2xl font-bold">{formatHours(status.total_hours)}</p>
              </div>
              <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                <Clock className="h-5 w-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">This Week</p>
                <p className="text-2xl font-bold">
                  {weekSummary ? formatHours(weekSummary.total_hours) : "--"}
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                <Calendar className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Break Time</p>
                <p className="text-2xl font-bold">
                  {weekSummary ? formatHours(weekSummary.total_break_hours) : "--"}
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-yellow-100 flex items-center justify-center">
                <Coffee className="h-5 w-5 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Job Hours</p>
                <p className="text-2xl font-bold">
                  {weekSummary ? formatHours(weekSummary.total_job_hours) : "--"}
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-purple-100 flex items-center justify-center">
                <Briefcase className="h-5 w-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
