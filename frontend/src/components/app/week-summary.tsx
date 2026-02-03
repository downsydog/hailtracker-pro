import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useWeekTime, formatHoursMinutes } from "@/hooks/use-time-tracking"
import { BarChart3 } from "lucide-react"

export function WeekSummary() {
  const { data, isLoading, error } = useWeekTime()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-5 w-5" />
            Hours This Week
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (error || !data?.success) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-5 w-5" />
            Hours This Week
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">Unable to load week data</p>
        </CardContent>
      </Card>
    )
  }

  const { week } = data
  const maxHours = Math.max(...(week?.days?.map((d) => d.hours) || [8]), 8)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Hours This Week
          </span>
          <span className="text-2xl font-bold text-primary">
            {formatHoursMinutes(week?.total_hours || 0)}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Daily bars */}
        <div className="flex items-end justify-between gap-1 h-24">
          {week?.days?.map((day) => {
            const heightPercent = (day.hours / maxHours) * 100
            const isToday = new Date().toDateString() === new Date(day.date).toDateString()

            return (
              <div
                key={day.date}
                className="flex-1 flex flex-col items-center gap-1"
              >
                <div
                  className="w-full relative rounded-t"
                  style={{ height: "80px" }}
                >
                  <div
                    className={`absolute bottom-0 w-full rounded-t transition-all ${
                      isToday
                        ? "bg-primary"
                        : day.hours > 0
                        ? "bg-primary/60"
                        : "bg-muted"
                    }`}
                    style={{
                      height: `${Math.max(heightPercent, day.hours > 0 ? 10 : 5)}%`,
                    }}
                  />
                </div>
                <div className="text-center">
                  <p
                    className={`text-xs font-medium ${
                      isToday ? "text-primary" : "text-muted-foreground"
                    }`}
                  >
                    {day.day_name.slice(0, 3)}
                  </p>
                  {day.hours > 0 && (
                    <p className="text-xs text-muted-foreground">
                      {day.hours.toFixed(1)}h
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Break time if any */}
        {(week?.break_hours || 0) > 0 && (
          <p className="text-xs text-muted-foreground mt-3 text-center">
            Break time: {formatHoursMinutes(week?.break_hours || 0)}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
