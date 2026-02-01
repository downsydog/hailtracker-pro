import * as React from "react"
import { Outlet, useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { CheckCircle, Clock, Users } from "lucide-react"

// Kiosk Layout
export function KioskLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center text-white mb-8">
          <h1 className="text-4xl font-bold">Welcome</h1>
          <p className="text-xl opacity-90">HailTracker Pro Check-In</p>
        </div>
        <Outlet />
      </div>
    </div>
  )
}

// Welcome Page
export function KioskWelcomePage() {
  const navigate = useNavigate()

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Customer Check-In</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-center text-muted-foreground">
            Please check in to let us know you've arrived
          </p>
          <Button
            className="w-full h-16 text-xl"
            onClick={() => navigate("/kiosk/check-in")}
          >
            Start Check-In
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

// Check-In Page
export function KioskCheckInPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = React.useState("")
  const [name, setName] = React.useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    navigate("/kiosk/confirmation")
  }

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Enter Your Information</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Phone Number</label>
              <Input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="(555) 123-4567"
                className="h-14 text-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="h-14 text-lg"
              />
            </div>
            <Button type="submit" className="w-full h-14 text-lg">
              Check In
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

// Confirmation Page
export function KioskConfirmationPage() {
  const navigate = useNavigate()

  React.useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/kiosk")
    }, 10000)
    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-md text-center">
        <CardContent className="py-12">
          <CheckCircle className="h-24 w-24 mx-auto text-green-500 mb-6" />
          <h2 className="text-3xl font-bold mb-2">You're Checked In!</h2>
          <p className="text-lg text-muted-foreground mb-6">
            A team member will be with you shortly.
          </p>
          <div className="flex items-center justify-center gap-2 text-muted-foreground">
            <Clock className="h-5 w-5" />
            <span>Estimated wait: 5-10 minutes</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Queue Display Page (for lobby screens)
export function KioskQueuePage() {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold">Customer Queue</h1>
      </div>
      <div className="max-w-4xl mx-auto">
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Users className="h-6 w-6" />
              Currently Waiting
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-400 text-center py-8">No customers waiting</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
