import { useState } from 'react'
import { Calendar, Clock, MapPin, User, ChevronLeft, ChevronRight } from 'lucide-react'

const mockEvents = [
  { id: 1, title: 'Roof Inspection', customer: 'John Smith', time: '9:00 AM', address: '123 Oak St', type: 'inspection' },
  { id: 2, title: 'Install Start', customer: 'Sarah Johnson', time: '10:30 AM', address: '456 Elm Ave', type: 'job' },
  { id: 3, title: 'Estimate Visit', customer: 'Mike Williams', time: '2:00 PM', address: '789 Pine Rd', type: 'estimate' },
  { id: 4, title: 'Final Walkthrough', customer: 'Lisa Brown', time: '4:00 PM', address: '321 Cedar Ln', type: 'inspection' },
]

const typeColors: Record<string, string> = {
  inspection: 'border-l-blue-500 bg-blue-50',
  job: 'border-l-green-500 bg-green-50',
  estimate: 'border-l-purple-500 bg-purple-50',
}

export function SchedulePage() {
  const [selectedDate, setSelectedDate] = useState(new Date())

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
  }

  const prevDay = () => {
    setSelectedDate(new Date(selectedDate.setDate(selectedDate.getDate() - 1)))
  }

  const nextDay = () => {
    setSelectedDate(new Date(selectedDate.setDate(selectedDate.getDate() + 1)))
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Schedule</h1>
          <p className="text-muted-foreground">Manage appointments and job schedules</p>
        </div>
      </div>

      {/* Date Navigation */}
      <div className="flex items-center gap-4 mb-6 bg-card rounded-lg border p-4">
        <button onClick={prevDay} className="p-2 hover:bg-accent rounded-md">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <div className="flex-1 text-center">
          <p className="text-lg font-semibold">{formatDate(selectedDate)}</p>
        </div>
        <button onClick={nextDay} className="p-2 hover:bg-accent rounded-md">
          <ChevronRight className="h-5 w-5" />
        </button>
        <button
          onClick={() => setSelectedDate(new Date())}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          Today
        </button>
      </div>

      {/* Schedule Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Day View */}
        <div className="bg-card rounded-lg border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Today's Schedule</h2>
          </div>
          <div className="p-4 space-y-3">
            {mockEvents.map((event) => (
              <div
                key={event.id}
                className={`p-4 rounded-md border-l-4 ${typeColors[event.type]}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold">{event.title}</span>
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {event.time}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground space-y-1">
                  <div className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {event.customer}
                  </div>
                  <div className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {event.address}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Mini Calendar */}
        <div className="bg-card rounded-lg border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Calendar</h2>
          </div>
          <div className="p-4">
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              <div className="text-center">
                <Calendar className="h-12 w-12 mx-auto mb-2" />
                <p>Full calendar view coming soon</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
