import * as React from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useTimeStatus,
  useClockIn,
  useClockOut,
  useStartBreak,
  useEndBreak,
  formatHoursMinutes,
  formatTime,
  getElapsedTime,
} from "@/hooks/use-time-tracking"
import {
  Clock,
  LogIn,
  LogOut,
  Coffee,
  Play,
  Timer,
} from "lucide-react"

export function TimeStatusBanner() {
  const { data, isLoading, error } = useTimeStatus()
  const clockIn = useClockIn()
  const clockOut = useClockOut()
  const startBreak = useStartBreak()
  const endBreak = useEndBreak()

  // Force re-render every minute when clocked in to update elapsed time display
  const [, setTick] = React.useState(0)

  React.useEffect(() => {
    if (!data?.status?.is_clocked_in) return

    const interval = setInterval(() => setTick((t) => t + 1), 60000)
    return () => clearInterval(interval)
  }, [data?.status?.is_clocked_in])

  if (isLoading) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
      </Card>
    )
  }

  if (error || !data?.success) {
    return (
      <Card className="p-4 bg-yellow-50 dark:bg-yellow-950 border-yellow-200">
        <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-300">
          <Clock className="h-5 w-5" />
          <span>Time tracking unavailable</span>
        </div>
      </Card>
    )
  }

  const { status, today } = data
  const isClockedIn = status?.is_clocked_in
  const isOnBreak = status?.is_on_break

  // Not clocked in
  if (!isClockedIn) {
    return (
      <Card className="p-4 bg-slate-50 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-slate-200 dark:bg-slate-800">
              <Clock className="h-6 w-6 text-slate-500" />
            </div>
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-300">
                Not Clocked In
              </p>
              <p className="text-sm text-muted-foreground">
                Ready to start your day?
              </p>
            </div>
          </div>
          <Button
            onClick={() => clockIn.mutate({})}
            disabled={clockIn.isPending}
            className="bg-green-600 hover:bg-green-700"
          >
            <LogIn className="h-4 w-4 mr-2" />
            Clock In
          </Button>
        </div>
      </Card>
    )
  }

  // On break
  if (isOnBreak) {
    return (
      <Card className="p-4 bg-amber-50 dark:bg-amber-950 border-amber-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-amber-200 dark:bg-amber-800 animate-pulse">
              <Coffee className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="font-semibold text-amber-700 dark:text-amber-300">
                On Break
              </p>
              <p className="text-sm text-amber-600 dark:text-amber-400">
                Clocked in at {status.clock_in_time ? formatTime(status.clock_in_time) : '--'} |
                Break started {status.current_break_start ? getElapsedTime(status.current_break_start) : ''} ago
              </p>
            </div>
          </div>
          <Button
            onClick={() => endBreak.mutate()}
            disabled={endBreak.isPending}
            variant="outline"
            className="border-amber-300 text-amber-700 hover:bg-amber-100"
          >
            <Play className="h-4 w-4 mr-2" />
            End Break
          </Button>
        </div>
      </Card>
    )
  }

  // Clocked in and working
  return (
    <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-green-200 dark:bg-green-800">
            <Timer className="h-6 w-6 text-green-600" />
          </div>
          <div>
            <p className="font-semibold text-green-700 dark:text-green-300">
              Clocked In - Working
            </p>
            <p className="text-sm text-green-600 dark:text-green-400">
              Since {status.clock_in_time ? formatTime(status.clock_in_time) : '--'} |
              Today: {formatHoursMinutes(today?.total_hours || status.total_hours_today || 0)}
              {(today?.break_minutes || status.break_minutes_today || 0) > 0 &&
                ` (${Math.round((today?.break_minutes || status.break_minutes_today || 0))}m break)`
              }
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => startBreak.mutate()}
            disabled={startBreak.isPending}
            variant="outline"
            className="border-amber-300 text-amber-700 hover:bg-amber-50"
          >
            <Coffee className="h-4 w-4 mr-2" />
            Break
          </Button>
          <Button
            onClick={() => clockOut.mutate({})}
            disabled={clockOut.isPending}
            variant="outline"
            className="border-red-300 text-red-700 hover:bg-red-50"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Clock Out
          </Button>
        </div>
      </div>
    </Card>
  )
}
