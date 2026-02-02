import * as React from "react"
import { kioskApi, KioskQueueItem } from "@/api/kiosk"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Car, Clock, User, Bell } from "lucide-react"

export function KioskQueuePage() {
  const [queue, setQueue] = React.useState<KioskQueueItem[]>([])
  const [averageWait, setAverageWait] = React.useState(15)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const fetchQueue = async () => {
      try {
        const result = await kioskApi.getQueue()
        setQueue(result.queue)
        setAverageWait(result.average_wait)
      } catch {
        // Demo data
        setQueue([
          {
            position: 1,
            job_number: "JOB-2025-097",
            customer_name: "John S.",
            vehicle: "2023 Toyota Camry",
            status: "in_progress",
            estimated_time: "Now",
          },
          {
            position: 2,
            job_number: "JOB-2025-098",
            customer_name: "Sarah M.",
            vehicle: "2022 Honda Accord",
            status: "waiting",
            estimated_time: "~5 min",
          },
          {
            position: 3,
            job_number: "JOB-2025-099",
            customer_name: "Mike D.",
            vehicle: "2024 Ford F-150",
            status: "waiting",
            estimated_time: "~10 min",
          },
          {
            position: 4,
            job_number: "JOB-2025-100",
            customer_name: "Lisa R.",
            vehicle: "2021 BMW X5",
            status: "waiting",
            estimated_time: "~15 min",
          },
        ])
        // Now serving is determined from queue items with status "in_progress"
      } finally {
        setLoading(false)
      }
    }

    fetchQueue()
    const interval = setInterval(fetchQueue, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-white"></div>
      </div>
    )
  }

  const currentItem = queue.find((q) => q.status === "in_progress")
  const waitingItems = queue.filter((q) => q.status === "waiting")

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8 text-white">
          <h1 className="text-4xl font-bold mb-2">Service Queue</h1>
          <p className="text-blue-200">
            Average wait time: {averageWait} minutes
          </p>
        </div>

        {/* Now Serving */}
        {currentItem && (
          <Card className="mb-6 border-4 border-green-400 bg-green-50">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-green-700">
                <Bell className="h-6 w-6 animate-pulse" />
                Now Serving
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
                    <User className="h-8 w-8 text-green-600" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-800">
                      {currentItem.customer_name}
                    </p>
                    <p className="text-green-600">{currentItem.vehicle}</p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge className="text-lg px-4 py-2 bg-green-500">
                    {currentItem.job_number}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Queue List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Waiting ({waitingItems.length})
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {waitingItems.length > 0 ? (
              <div className="divide-y">
                {waitingItems.map((item) => (
                  <div
                    key={item.job_number}
                    className="flex items-center justify-between p-4"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-xl font-bold text-blue-600">
                        {item.position}
                      </div>
                      <div>
                        <p className="font-semibold">{item.customer_name}</p>
                        <p className="text-sm text-muted-foreground flex items-center gap-1">
                          <Car className="h-4 w-4" />
                          {item.vehicle}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant="outline">{item.job_number}</Badge>
                      <p className="text-sm text-muted-foreground mt-1">
                        {item.estimated_time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center">
                <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <p className="font-medium">No one waiting</p>
                <p className="text-sm text-muted-foreground">
                  Check in at the kiosk to get started
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Footer Info */}
        <div className="mt-6 text-center text-blue-200 text-sm">
          <p>Queue updates automatically every 10 seconds</p>
        </div>
      </div>
    </div>
  )
}
