import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
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
import { useLogTime } from "@/hooks/use-time-tracking"
import { Clock } from "lucide-react"

interface Job {
  id: number
  job_number: string
  customer_name?: string
  vehicle_year?: number
  vehicle_make?: string
  vehicle_model?: string
}

interface LogTimeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  jobs: Job[]
  preselectedJobId?: number
}

export function LogTimeDialog({
  open,
  onOpenChange,
  jobs,
  preselectedJobId,
}: LogTimeDialogProps) {
  const logTime = useLogTime()

  const [selectedJobId, setSelectedJobId] = React.useState<string>(
    preselectedJobId?.toString() || ""
  )
  const [hours, setHours] = React.useState("")
  const [minutes, setMinutes] = React.useState("")
  const [description, setDescription] = React.useState("")

  // Reset form when dialog opens
  React.useEffect(() => {
    if (open) {
      setSelectedJobId(preselectedJobId?.toString() || "")
      setHours("")
      setMinutes("")
      setDescription("")
    }
  }, [open, preselectedJobId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!selectedJobId) return

    const totalHours = (parseFloat(hours) || 0) + (parseFloat(minutes) || 0) / 60

    if (totalHours <= 0) return

    try {
      await logTime.mutateAsync({
        job_id: parseInt(selectedJobId),
        hours: totalHours,
        description: description || undefined,
      })
      onOpenChange(false)
    } catch (error) {
      console.error("Failed to log time:", error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Log Time to Job
          </DialogTitle>
          <DialogDescription>
            Record hours worked on a specific job.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="job">Select Job</Label>
            <Select value={selectedJobId} onValueChange={setSelectedJobId}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a job..." />
              </SelectTrigger>
              <SelectContent>
                {jobs.map((job) => (
                  <SelectItem key={job.id} value={job.id.toString()}>
                    {job.job_number} - {job.vehicle_year} {job.vehicle_make} {job.vehicle_model}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Time Spent</Label>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <Input
                  type="number"
                  min="0"
                  max="24"
                  placeholder="0"
                  value={hours}
                  onChange={(e) => setHours(e.target.value)}
                />
                <p className="text-xs text-muted-foreground mt-1">Hours</p>
              </div>
              <span className="text-muted-foreground">:</span>
              <div className="flex-1">
                <Input
                  type="number"
                  min="0"
                  max="59"
                  step="15"
                  placeholder="0"
                  value={minutes}
                  onChange={(e) => setMinutes(e.target.value)}
                />
                <p className="text-xs text-muted-foreground mt-1">Minutes</p>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Work Description (optional)</Label>
            <Textarea
              id="description"
              placeholder="What did you work on?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!selectedJobId || logTime.isPending}
            >
              {logTime.isPending ? "Logging..." : "Log Time"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
