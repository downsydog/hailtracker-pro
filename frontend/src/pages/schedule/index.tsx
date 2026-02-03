import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Calendar, Clock, MapPin, User, ChevronLeft, ChevronRight, Plus, Loader2 } from 'lucide-react'
import { scheduleApi, ScheduleSlot } from '@/api/schedule'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const typeColors: Record<string, string> = {
  available: 'border-l-gray-300 bg-gray-50',
  booked: 'border-l-green-500 bg-green-50',
  blocked: 'border-l-red-500 bg-red-50',
  inspection: 'border-l-blue-500 bg-blue-50',
  job: 'border-l-green-500 bg-green-50',
  estimate: 'border-l-purple-500 bg-purple-50',
  drop_off: 'border-l-amber-500 bg-amber-50',
  pickup: 'border-l-teal-500 bg-teal-50',
}

export function SchedulePage() {
  const [selectedDate, setSelectedDate] = useState(new Date())

  const formatDateForApi = (date: Date) => {
    return date.toISOString().split('T')[0]
  }

  const formatDateDisplay = (date: Date) => {
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['schedule', formatDateForApi(selectedDate)],
    queryFn: () => scheduleApi.getSchedule({ date: formatDateForApi(selectedDate) }),
  })

  const prevDay = () => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() - 1)
    setSelectedDate(newDate)
  }

  const nextDay = () => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() + 1)
    setSelectedDate(newDate)
  }

  const slots = data?.slots || []
  const bookedSlots = slots.filter(s => s.status === 'booked')

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Schedule</h1>
          <p className="text-muted-foreground">Manage appointments and job schedules</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Appointment
        </Button>
      </div>

      {/* Date Navigation */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Button variant="outline" size="icon" onClick={prevDay}>
              <ChevronLeft className="h-5 w-5" />
            </Button>
            <div className="flex-1 text-center">
              <p className="text-lg font-semibold">{formatDateDisplay(selectedDate)}</p>
            </div>
            <Button variant="outline" size="icon" onClick={nextDay}>
              <ChevronRight className="h-5 w-5" />
            </Button>
            <Button onClick={() => setSelectedDate(new Date())}>
              Today
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Schedule Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Day View */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Today's Schedule</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center h-48">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-48 text-muted-foreground">
                <p>Failed to load schedule</p>
              </div>
            ) : bookedSlots.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                <Calendar className="h-12 w-12 mb-2" />
                <p>No appointments scheduled</p>
              </div>
            ) : (
              <div className="space-y-3">
                {bookedSlots.map((slot: ScheduleSlot) => (
                  <div
                    key={slot.id}
                    className={`p-4 rounded-md border-l-4 ${typeColors[slot.status] || typeColors.booked}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">
                        {slot.job_number ? `Job #${slot.job_number}` : 'Appointment'}
                      </span>
                      <span className="text-sm text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {slot.time}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      {slot.customer_name && (
                        <div className="flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {slot.customer_name}
                        </div>
                      )}
                      {slot.vehicle_name && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {slot.vehicle_name}
                        </div>
                      )}
                      {slot.tech_name && (
                        <Badge variant="outline" className="mt-1">
                          Tech: {slot.tech_name}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Day Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-green-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-600">{bookedSlots.length}</p>
                <p className="text-sm text-green-700">Booked</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-gray-600">
                  {slots.filter(s => s.status === 'available').length}
                </p>
                <p className="text-sm text-gray-700">Available</p>
              </div>
              <div className="p-4 bg-red-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-600">
                  {slots.filter(s => s.status === 'blocked').length}
                </p>
                <p className="text-sm text-red-700">Blocked</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg text-center">
                <p className="text-2xl font-bold text-blue-600">{slots.length}</p>
                <p className="text-sm text-blue-700">Total Slots</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
