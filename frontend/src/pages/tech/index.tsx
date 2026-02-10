/**
 * Tech Dashboard - "My Day" view with assigned jobs and blocker flagging.
 *
 * Features:
 * - Today / This Week / Unscheduled sections
 * - Flag Issue button for reporting blockers
 * - Uses canonical WorkflowService via useJobWorkflow hook
 */
import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Wrench,
  Calendar,
  Clock,
  CheckCircle,
  ChevronRight,
  Loader2,
  PlayCircle,
  AlertTriangle,
  CalendarDays,
  CalendarClock,
  Building2,
  Truck,
} from "lucide-react"
import { useMyJobs, useUpdateJobStatus, useFlagJobIssue, useCheckInJob, JOB_ISSUE_TYPES, JobIssueType, JobCheckInLocation } from '@/hooks/use-jobs'
import { useAuth } from '@/contexts/auth-context'
import { Job } from '@/types'

// Job status colors - matches WorkflowCard
const jobStatusColors: Record<string, string> = {
  scheduled: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-700',
}

// Helper to check if a date is today (local time)
function isToday(dateStr: string | null | undefined): boolean {
  if (!dateStr) return false
  const date = new Date(dateStr)
  const today = new Date()
  return (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  )
}

// Helper to check if a date is within the next N days
function isWithinDays(dateStr: string | null | undefined, days: number): boolean {
  if (!dateStr) return false
  const date = new Date(dateStr)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const future = new Date(today)
  future.setDate(future.getDate() + days)
  return date >= today && date <= future
}

export function TechDashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data, isLoading } = useMyJobs()
  const updateJobStatus = useUpdateJobStatus()
  const flagJobIssue = useFlagJobIssue()
  const checkInJob = useCheckInJob()

  // Flag Issue modal state
  const [flagModalOpen, setFlagModalOpen] = useState(false)
  const [flagJobId, setFlagJobId] = useState<number | null>(null)
  const [flagIssueType, setFlagIssueType] = useState<JobIssueType>('other')
  const [flagNotes, setFlagNotes] = useState('')
  // Parts fields for waiting_on_parts (Stage 5O)
  const [flagPartsOrdered, setFlagPartsOrdered] = useState(false)
  const [flagVendor, setFlagVendor] = useState('')
  const [flagPoNumber, setFlagPoNumber] = useState('')
  const [flagEta, setFlagEta] = useState('')

  // Start Job modal state
  const [startModalOpen, setStartModalOpen] = useState(false)
  const [startJobId, setStartJobId] = useState<number | null>(null)
  const [startLocation, setStartLocation] = useState<JobCheckInLocation>(null)
  const [startNotes, setStartNotes] = useState('')

  const jobs = data?.jobs || []

  // Categorize jobs by date (client-side grouping)
  const { todayJobs, weekJobs, unscheduledJobs, inProgressJobs, completedJobs } = useMemo(() => {
    const today: Job[] = []
    const week: Job[] = []
    const unscheduled: Job[] = []
    const inProgress: Job[] = []
    const completed: Job[] = []

    for (const job of jobs) {
      if (job.status === 'completed') {
        completed.push(job)
      } else if (job.status === 'in_progress') {
        inProgress.push(job)
      } else if (job.status === 'scheduled') {
        if (isToday(job.scheduled_date)) {
          today.push(job)
        } else if (isWithinDays(job.scheduled_date, 7)) {
          week.push(job)
        } else if (!job.scheduled_date) {
          unscheduled.push(job)
        } else {
          // Future beyond 7 days - put in week section
          week.push(job)
        }
      }
    }

    return {
      todayJobs: today,
      weekJobs: week,
      unscheduledJobs: unscheduled,
      inProgressJobs: inProgress,
      completedJobs: completed,
    }
  }, [jobs])

  // Open Start Job modal
  const openStartModal = (jobId: number) => {
    setStartJobId(jobId)
    setStartLocation(null)
    setStartNotes('')
    setStartModalOpen(true)
  }

  // Handle Start Job submission (status update + check-in)
  const handleStartJobSubmit = async () => {
    if (!startJobId) return
    // First update status to in_progress
    await updateJobStatus.mutateAsync({ id: startJobId, status: 'in_progress' })
    // Then check-in with location (if provided)
    await checkInJob.mutateAsync({
      id: startJobId,
      location: startLocation,
      notes: startNotes,
    })
    setStartModalOpen(false)
    setStartJobId(null)
  }

  const handleCompleteJob = async (jobId: number) => {
    await updateJobStatus.mutateAsync({ id: jobId, status: 'completed' })
  }

  const openFlagModal = (jobId: number) => {
    setFlagJobId(jobId)
    setFlagIssueType('other')
    setFlagNotes('')
    // Reset parts fields
    setFlagPartsOrdered(false)
    setFlagVendor('')
    setFlagPoNumber('')
    setFlagEta('')
    setFlagModalOpen(true)
  }

  const handleFlagIssue = async () => {
    if (!flagJobId) return
    await flagJobIssue.mutateAsync({
      id: flagJobId,
      issueType: flagIssueType,
      notes: flagNotes,
      // Include parts data if waiting_on_parts
      parts: flagIssueType === 'waiting_on_parts' ? {
        partsOrdered: flagPartsOrdered,
        vendor: flagVendor,
        poNumber: flagPoNumber,
        eta: flagEta,
      } : undefined,
    })
    setFlagModalOpen(false)
    setFlagJobId(null)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Day"
        description={`Welcome back, ${user?.name || 'Technician'}!`}
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className={todayJobs.length > 0 ? 'border-blue-200' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Today</CardTitle>
            <Calendar className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold">{todayJobs.length}</p>
                <p className="text-xs text-muted-foreground">Jobs scheduled today</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card className={inProgressJobs.length > 0 ? 'border-amber-200' : ''}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Wrench className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold">{inProgressJobs.length}</p>
                <p className="text-xs text-muted-foreground">Currently working</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">This Week</CardTitle>
            <CalendarDays className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold">{weekJobs.length}</p>
                <p className="text-xs text-muted-foreground">Upcoming jobs</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <>
                <p className="text-2xl font-bold text-green-600">{completedJobs.length}</p>
                <p className="text-xs text-muted-foreground">Jobs finished</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* In Progress Jobs - Priority */}
      {inProgressJobs.length > 0 && (
        <Card className="border-amber-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <PlayCircle className="h-5 w-5 text-amber-500" />
              Currently In Progress
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {inProgressJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onStart={() => {}}
                onComplete={() => handleCompleteJob(job.id)}
                onFlagIssue={() => openFlagModal(job.id)}
                onNavigate={() => navigate(`/jobs/${job.id}`)}
                isPending={updateJobStatus.isPending}
                showComplete
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Today's Jobs */}
      <Card className={todayJobs.length > 0 ? 'border-blue-200' : ''}>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Calendar className="h-5 w-5 text-blue-500" />
            Today
            {todayJobs.length > 0 && (
              <Badge variant="secondary">{todayJobs.length}</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : todayJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No jobs scheduled for today</p>
            </div>
          ) : (
            <div className="space-y-3">
              {todayJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onStart={() => openStartModal(job.id)}
                  onComplete={() => handleCompleteJob(job.id)}
                  onFlagIssue={() => openFlagModal(job.id)}
                  onNavigate={() => navigate(`/jobs/${job.id}`)}
                  isPending={updateJobStatus.isPending || checkInJob.isPending}
                  showStart
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* This Week */}
      {weekJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CalendarDays className="h-5 w-5 text-purple-500" />
              This Week
              <Badge variant="secondary">{weekJobs.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {weekJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onStart={() => openStartModal(job.id)}
                onComplete={() => handleCompleteJob(job.id)}
                onFlagIssue={() => openFlagModal(job.id)}
                onNavigate={() => navigate(`/jobs/${job.id}`)}
                isPending={updateJobStatus.isPending || checkInJob.isPending}
                showStart
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Unscheduled */}
      {unscheduledJobs.length > 0 && (
        <Card className="border-orange-200">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CalendarClock className="h-5 w-5 text-orange-500" />
              Unscheduled
              <Badge variant="secondary" className="bg-orange-100 text-orange-700">
                {unscheduledJobs.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {unscheduledJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onStart={() => openStartModal(job.id)}
                onComplete={() => handleCompleteJob(job.id)}
                onFlagIssue={() => openFlagModal(job.id)}
                onNavigate={() => navigate(`/jobs/${job.id}`)}
                isPending={updateJobStatus.isPending || checkInJob.isPending}
                showStart
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Flag Issue Modal */}
      <Dialog open={flagModalOpen} onOpenChange={setFlagModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Flag Issue
            </DialogTitle>
            <DialogDescription>
              Report a blocker or issue with this job. The office will be notified.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="issue-type">Issue Type</Label>
              <Select
                value={flagIssueType}
                onValueChange={(v) => setFlagIssueType(v as JobIssueType)}
              >
                <SelectTrigger id="issue-type">
                  <SelectValue placeholder="Select issue type" />
                </SelectTrigger>
                <SelectContent>
                  {JOB_ISSUE_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Parts fields for waiting_on_parts (Stage 5O) */}
            {flagIssueType === 'waiting_on_parts' && (
              <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="vendor" className="text-xs">Vendor (optional)</Label>
                    <Input
                      id="vendor"
                      placeholder="e.g., AutoZone"
                      value={flagVendor}
                      onChange={(e) => setFlagVendor(e.target.value)}
                      className="h-8"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="po-number" className="text-xs">PO # (optional)</Label>
                    <Input
                      id="po-number"
                      placeholder="e.g., PO-12345"
                      value={flagPoNumber}
                      onChange={(e) => setFlagPoNumber(e.target.value)}
                      className="h-8"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="eta" className="text-xs">Expected Arrival (optional)</Label>
                  <Input
                    id="eta"
                    type="date"
                    value={flagEta}
                    onChange={(e) => setFlagEta(e.target.value)}
                    className="h-8"
                  />
                </div>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={flagPartsOrdered}
                    onChange={(e) => setFlagPartsOrdered(e.target.checked)}
                    className="rounded"
                  />
                  Parts already ordered
                </label>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                placeholder="Describe the issue..."
                value={flagNotes}
                onChange={(e) => setFlagNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFlagModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleFlagIssue}
              disabled={flagJobIssue.isPending}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {flagJobIssue.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <AlertTriangle className="h-4 w-4 mr-2" />
              )}
              Flag Issue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Start Job Modal */}
      <Dialog open={startModalOpen} onOpenChange={setStartModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5 text-green-500" />
              Start Job
            </DialogTitle>
            <DialogDescription>
              Record your location before starting the job.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Location (optional)</Label>
              <div className="grid grid-cols-2 gap-3">
                <Button
                  type="button"
                  variant={startLocation === 'shop' ? 'default' : 'outline'}
                  className={startLocation === 'shop' ? 'bg-blue-600 hover:bg-blue-700' : ''}
                  onClick={() => setStartLocation(startLocation === 'shop' ? null : 'shop')}
                >
                  <Building2 className="h-4 w-4 mr-2" />
                  Shop
                </Button>
                <Button
                  type="button"
                  variant={startLocation === 'field' ? 'default' : 'outline'}
                  className={startLocation === 'field' ? 'bg-green-600 hover:bg-green-700' : ''}
                  onClick={() => setStartLocation(startLocation === 'field' ? null : 'field')}
                >
                  <Truck className="h-4 w-4 mr-2" />
                  Field
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="start-notes">Notes (optional)</Label>
              <Textarea
                id="start-notes"
                placeholder="Any notes about the job start..."
                value={startNotes}
                onChange={(e) => setStartNotes(e.target.value)}
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStartModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleStartJobSubmit}
              disabled={updateJobStatus.isPending || checkInJob.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {(updateJobStatus.isPending || checkInJob.isPending) ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <PlayCircle className="h-4 w-4 mr-2" />
              )}
              Start Job
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ============================================================================
// JOB CARD COMPONENT
// ============================================================================
interface JobCardProps {
  job: Job
  onStart: () => void
  onComplete: () => void
  onFlagIssue: () => void
  onNavigate: () => void
  isPending: boolean
  showStart?: boolean
  showComplete?: boolean
}

function JobCard({
  job,
  onStart,
  onComplete,
  onFlagIssue,
  onNavigate,
  isPending,
  showStart,
  showComplete,
}: JobCardProps) {
  const statusColor = job.status === 'in_progress'
    ? 'bg-amber-50/50 hover:bg-amber-50'
    : 'hover:bg-muted/50'

  return (
    <div
      className={`flex items-center justify-between p-4 border rounded-lg cursor-pointer ${statusColor}`}
      onClick={onNavigate}
    >
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold">{job.job_number}</span>
          <Badge className={jobStatusColors[job.status] || 'bg-gray-100'}>
            {job.status.replace('_', ' ')}
          </Badge>
          {job.scheduled_date && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {new Date(job.scheduled_date).toLocaleDateString()}
            </span>
          )}
        </div>
        <p className="text-sm text-muted-foreground">{job.customer_name}</p>
        <p className="text-xs text-muted-foreground">
          {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
        </p>
        {job.estimate_id && (
          <p className="text-xs text-blue-600 mt-1">
            Est: #{job.estimate_id}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
        {/* Flag Issue Button */}
        <Button
          size="sm"
          variant="ghost"
          className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
          onClick={onFlagIssue}
        >
          <AlertTriangle className="h-4 w-4" />
        </Button>

        {/* Action Buttons */}
        {showStart && job.status === 'scheduled' && (
          <Button
            size="sm"
            variant="outline"
            onClick={onStart}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <PlayCircle className="h-4 w-4 mr-1" />
                Start
              </>
            )}
          </Button>
        )}
        {showComplete && job.status === 'in_progress' && (
          <Button
            size="sm"
            onClick={onComplete}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-1" />
                Complete
              </>
            )}
          </Button>
        )}
        <ChevronRight className="h-5 w-5 text-muted-foreground" />
      </div>
    </div>
  )
}
