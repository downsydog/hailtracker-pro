import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, Calendar, CloudLightning, Car, MapPin } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { hailEventsApi, CalendarDay, CalendarDayEvent } from "@/api/weather"
import { cn } from "@/lib/utils"

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
]

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

const SEVERITY_COLORS = {
  SEVERE: { bg: "bg-red-500", text: "text-white", border: "border-red-600" },
  MODERATE: { bg: "bg-orange-500", text: "text-white", border: "border-orange-600" },
  MINOR: { bg: "bg-yellow-500", text: "text-black", border: "border-yellow-600" },
}

interface StormCalendarProps {
  onSelectEvent?: (event: CalendarDayEvent) => void
  className?: string
}

export function StormCalendar({ onSelectEvent, className }: StormCalendarProps) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1) // 1-indexed
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [viewMode, setViewMode] = useState<"month" | "year">("month")

  // Fetch calendar data for current month
  const { data: calendarData, isLoading } = useQuery({
    queryKey: ["storm-calendar", year, month],
    queryFn: () => hailEventsApi.getCalendar({ year, month }),
    enabled: viewMode === "month",
  })

  // Fetch year overview
  const { data: yearData, isLoading: yearLoading } = useQuery({
    queryKey: ["storm-calendar-year", year],
    queryFn: () => hailEventsApi.getCalendarYear({ year }),
    enabled: viewMode === "year",
  })

  const days = calendarData?.data?.days || {}
  const monthStats = calendarData?.data?.month_stats
  const months = yearData?.data?.months || {}
  const yearStats = yearData?.data?.year_stats

  // Generate calendar grid for month view
  const calendarGrid = useMemo(() => {
    const firstDayOfMonth = new Date(year, month - 1, 1)
    const lastDayOfMonth = new Date(year, month, 0)
    const startDay = firstDayOfMonth.getDay()
    const daysInMonth = lastDayOfMonth.getDate()

    const grid: (number | null)[] = []

    // Add empty cells for days before the 1st
    for (let i = 0; i < startDay; i++) {
      grid.push(null)
    }

    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      grid.push(day)
    }

    return grid
  }, [year, month])

  const navigateMonth = (delta: number) => {
    let newMonth = month + delta
    let newYear = year

    if (newMonth > 12) {
      newMonth = 1
      newYear++
    } else if (newMonth < 1) {
      newMonth = 12
      newYear--
    }

    setMonth(newMonth)
    setYear(newYear)
  }

  const goToToday = () => {
    setYear(now.getFullYear())
    setMonth(now.getMonth() + 1)
    setViewMode("month")
  }

  const handleDayClick = (day: number) => {
    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
    if (days[dateStr]) {
      setSelectedDate(dateStr)
      setSheetOpen(true)
    }
  }

  const handleMonthClick = (monthNum: number) => {
    setMonth(monthNum)
    setViewMode("month")
  }

  const getDayData = (day: number): CalendarDay | null => {
    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
    return days[dateStr] || null
  }

  const selectedDayData = selectedDate ? days[selectedDate] : null

  // Year selector options (last 15 years)
  const yearOptions = useMemo(() => {
    const years = []
    for (let y = now.getFullYear(); y >= 2011; y--) {
      years.push(y)
    }
    return years
  }, [])

  if (isLoading && viewMode === "month") {
    return (
      <Card className={className}>
        <CardHeader>
          <Skeleton className="h-8 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn("", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Storm Calendar</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Select value={viewMode} onValueChange={(v) => setViewMode(v as "month" | "year")}>
              <SelectTrigger className="w-24 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="month">Month</SelectItem>
                <SelectItem value="year">Year</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={goToToday}>
              Today
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-3">
          <Button variant="ghost" size="icon" onClick={() => viewMode === "month" ? navigateMonth(-1) : setYear(year - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div className="flex items-center gap-2">
            {viewMode === "month" && (
              <Select value={String(month)} onValueChange={(v) => setMonth(parseInt(v))}>
                <SelectTrigger className="w-32 h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MONTH_NAMES.map((name, idx) => (
                    <SelectItem key={idx} value={String(idx + 1)}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <Select value={String(year)} onValueChange={(v) => setYear(parseInt(v))}>
              <SelectTrigger className="w-24 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {yearOptions.map((y) => (
                  <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button variant="ghost" size="icon" onClick={() => viewMode === "month" ? navigateMonth(1) : setYear(year + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {viewMode === "month" ? (
          <>
            {/* Month Stats */}
            {monthStats && monthStats.total_events > 0 && (
              <div className="grid grid-cols-4 gap-2 mb-4 text-center text-sm">
                <div className="bg-muted rounded p-2">
                  <div className="font-bold text-lg">{monthStats.total_events}</div>
                  <div className="text-xs text-muted-foreground">Events</div>
                </div>
                <div className="bg-muted rounded p-2">
                  <div className="font-bold text-lg">{monthStats.storm_days}</div>
                  <div className="text-xs text-muted-foreground">Storm Days</div>
                </div>
                <div className="bg-muted rounded p-2">
                  <div className="font-bold text-lg">{monthStats.max_hail_size.toFixed(1)}"</div>
                  <div className="text-xs text-muted-foreground">Max Hail</div>
                </div>
                <div className="bg-muted rounded p-2">
                  <div className="font-bold text-lg">{(monthStats.total_vehicles / 1000).toFixed(0)}k</div>
                  <div className="text-xs text-muted-foreground">Vehicles</div>
                </div>
              </div>
            )}

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1">
              {/* Day headers */}
              {DAY_NAMES.map((name) => (
                <div key={name} className="text-center text-xs font-medium text-muted-foreground py-2">
                  {name}
                </div>
              ))}

              {/* Days */}
              {calendarGrid.map((day, idx) => {
                if (day === null) {
                  return <div key={`empty-${idx}`} className="h-12" />
                }

                const dayData = getDayData(day)
                const isToday = day === now.getDate() && month === now.getMonth() + 1 && year === now.getFullYear()
                const severity = dayData?.max_severity || ""
                const colors = SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS]

                return (
                  <button
                    key={day}
                    onClick={() => handleDayClick(day)}
                    className={cn(
                      "h-12 rounded-md text-sm relative transition-all",
                      isToday && "ring-2 ring-primary",
                      dayData ? `${colors?.bg} ${colors?.text} hover:opacity-80 cursor-pointer` : "hover:bg-muted",
                      !dayData && "text-muted-foreground"
                    )}
                  >
                    <span className="absolute top-1 left-2">{day}</span>
                    {dayData && (
                      <div className="absolute bottom-1 right-1 flex items-center gap-0.5">
                        <CloudLightning className="h-3 w-3" />
                        <span className="text-xs font-bold">{dayData.count}</span>
                      </div>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Legend */}
            <div className="flex items-center justify-center gap-4 mt-4 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-red-500" />
                <span>Severe (2"+)</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-orange-500" />
                <span>Moderate (1-2")</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-yellow-500" />
                <span>Minor (&lt;1")</span>
              </div>
            </div>
          </>
        ) : (
          /* Year View */
          <>
            {yearLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : (
              <>
                {/* Year Stats */}
                {yearStats && (
                  <div className="grid grid-cols-4 gap-2 mb-4 text-center text-sm">
                    <div className="bg-muted rounded p-2">
                      <div className="font-bold text-lg">{yearStats.total_events.toLocaleString()}</div>
                      <div className="text-xs text-muted-foreground">Total Events</div>
                    </div>
                    <div className="bg-muted rounded p-2">
                      <div className="font-bold text-lg">{yearStats.total_storm_days}</div>
                      <div className="text-xs text-muted-foreground">Storm Days</div>
                    </div>
                    <div className="bg-muted rounded p-2">
                      <div className="font-bold text-lg">{yearStats.max_hail_size.toFixed(1)}"</div>
                      <div className="text-xs text-muted-foreground">Max Hail</div>
                    </div>
                    <div className="bg-muted rounded p-2">
                      <div className="font-bold text-lg">
                        {yearStats.peak_month ? MONTH_NAMES[yearStats.peak_month - 1].slice(0, 3) : "-"}
                      </div>
                      <div className="text-xs text-muted-foreground">Peak Month</div>
                    </div>
                  </div>
                )}

                {/* Month Grid */}
                <div className="grid grid-cols-4 gap-2">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => {
                    const monthData = months[m]
                    const hasStorms = monthData?.total_events > 0
                    const intensity = monthData ? Math.min(1, monthData.total_events / 100) : 0

                    return (
                      <button
                        key={m}
                        onClick={() => handleMonthClick(m)}
                        className={cn(
                          "p-3 rounded-lg text-center transition-all hover:ring-2 hover:ring-primary",
                          hasStorms
                            ? monthData.severe_count > 0
                              ? "bg-red-500/80 text-white"
                              : monthData.moderate_count > 0
                              ? "bg-orange-500/80 text-white"
                              : "bg-yellow-500/80 text-black"
                            : "bg-muted"
                        )}
                        style={{
                          opacity: hasStorms ? 0.5 + intensity * 0.5 : 1,
                        }}
                      >
                        <div className="font-medium">{MONTH_NAMES[m - 1].slice(0, 3)}</div>
                        {monthData && monthData.total_events > 0 && (
                          <div className="text-xs mt-1">
                            {monthData.total_events} events
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
              </>
            )}
          </>
        )}
      </CardContent>

      {/* Day Detail Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[400px] sm:w-[450px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <CloudLightning className="h-5 w-5 text-orange-500" />
              Storms on {selectedDate}
            </SheetTitle>
          </SheetHeader>

          {selectedDayData && (
            <div className="mt-4 space-y-4">
              {/* Day Summary */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="bg-muted rounded p-2">
                  <div className="font-bold">{selectedDayData.count}</div>
                  <div className="text-xs text-muted-foreground">Storms</div>
                </div>
                <div className="bg-muted rounded p-2">
                  <div className="font-bold">{selectedDayData.max_hail_size.toFixed(2)}"</div>
                  <div className="text-xs text-muted-foreground">Max Hail</div>
                </div>
                <div className="bg-muted rounded p-2">
                  <div className="font-bold">{selectedDayData.total_vehicles.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">Vehicles</div>
                </div>
              </div>

              {/* Event List */}
              <div className="space-y-3">
                {selectedDayData.events.map((event) => (
                  <div
                    key={event.id}
                    className="p-3 rounded-lg border hover:border-primary cursor-pointer transition-colors"
                    onClick={() => {
                      onSelectEvent?.(event)
                      setSheetOpen(false)
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="font-medium text-sm">{event.event_name}</div>
                      <Badge
                        className={cn(
                          event.severity === "SEVERE" && "bg-red-100 text-red-700",
                          event.severity === "MODERATE" && "bg-orange-100 text-orange-700",
                          event.severity === "MINOR" && "bg-yellow-100 text-yellow-700"
                        )}
                      >
                        {event.hail_size.toFixed(2)}"
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                      {event.vehicles && (
                        <span className="flex items-center gap-1">
                          <Car className="h-3 w-3" />
                          {event.vehicles.toLocaleString()} vehicles
                        </span>
                      )}
                      {event.area_sqmi && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {event.area_sqmi.toFixed(0)} sq mi
                        </span>
                      )}
                    </div>
                    <div className="mt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full"
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelectEvent?.(event)
                          setSheetOpen(false)
                        }}
                      >
                        View on Map
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </Card>
  )
}
