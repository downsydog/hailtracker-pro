import { useState } from "react"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useJobs } from "@/hooks/use-jobs"
import { Job } from "@/types"
import { Link } from "react-router-dom"
import { ChevronLeft, ChevronRight } from "lucide-react"

export function SchedulePage() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const { data } = useJobs({ status: "SCHEDULED" })

  const scheduledJobs = (data?.jobs || []).filter(
    (job: Job) => job.scheduled_drop_off || job.scheduled_date
  )

  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDay = firstDay.getDay()

    return { daysInMonth, startingDay, year, month }
  }

  const { daysInMonth, startingDay, year, month } = getDaysInMonth(currentDate)

  const getJobsForDate = (day: number) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`
    return scheduledJobs.filter((job: Job) => {
      const schedDate = job.scheduled_drop_off || job.scheduled_date
      return schedDate?.startsWith(dateStr)
    })
  }

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1))
  }

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1))
  }

  const today = new Date()
  const isToday = (day: number) =>
    today.getFullYear() === year &&
    today.getMonth() === month &&
    today.getDate() === day

  const monthName = currentDate.toLocaleString("default", { month: "long" })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Schedule"
        description="View and manage job appointments."
      />

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-6">
            <Button variant="outline" size="icon" onClick={prevMonth}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-xl font-semibold">
              {monthName} {year}
            </h2>
            <Button variant="outline" size="icon" onClick={nextMonth}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>

          <div className="grid grid-cols-7 gap-1">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div
                key={day}
                className="p-2 text-center text-sm font-medium text-muted-foreground"
              >
                {day}
              </div>
            ))}

            {Array.from({ length: startingDay }).map((_, i) => (
              <div key={`empty-${i}`} className="p-2" />
            ))}

            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1
              const dayJobs = getJobsForDate(day)

              return (
                <div
                  key={day}
                  className={`min-h-24 p-2 border rounded-lg ${
                    isToday(day) ? "bg-primary/5 border-primary" : "border-border"
                  }`}
                >
                  <div
                    className={`text-sm font-medium mb-1 ${
                      isToday(day) ? "text-primary" : ""
                    }`}
                  >
                    {day}
                  </div>
                  <div className="space-y-1">
                    {dayJobs.slice(0, 2).map((job: Job) => (
                      <Link
                        key={job.id}
                        to={`/jobs/${job.id}`}
                        className="block"
                      >
                        <Badge
                          variant="secondary"
                          className="w-full justify-start text-xs truncate"
                        >
                          {job.job_number}
                        </Badge>
                      </Link>
                    ))}
                    {dayJobs.length > 2 && (
                      <span className="text-xs text-muted-foreground">
                        +{dayJobs.length - 2} more
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
