import { Link } from "react-router-dom"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Car, UserPlus, Clock, ArrowRight } from "lucide-react"

export function KioskWelcomePage() {
  return (
    <div className="text-center">
      {/* Welcome Message */}
      <div className="mb-8 text-white">
        <h1 className="text-4xl font-bold mb-4">Welcome!</h1>
        <p className="text-xl text-blue-200">
          Self-Service Vehicle Check-In
        </p>
      </div>

      {/* Main Action Card */}
      <Card className="shadow-2xl mb-8">
        <CardContent className="pt-8 pb-8 px-8">
          <div className="mb-6">
            <div className="h-20 w-20 mx-auto rounded-full bg-blue-100 flex items-center justify-center">
              <Car className="h-10 w-10 text-blue-600" />
            </div>
          </div>

          <h2 className="text-2xl font-bold mb-2">Ready to Check In?</h2>
          <p className="text-muted-foreground mb-8">
            Start your vehicle check-in process in just a few simple steps
          </p>

          <Button
            asChild
            size="lg"
            className="w-full h-16 text-xl bg-blue-600 hover:bg-blue-700"
          >
            <Link to="/kiosk/check-in">
              <UserPlus className="h-6 w-6 mr-3" />
              Start Check-In
              <ArrowRight className="h-6 w-6 ml-3" />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Info Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-white/10 border-white/20 text-white">
          <CardContent className="pt-6 pb-4">
            <div className="text-3xl mb-2">1</div>
            <p className="text-sm text-blue-200">Enter your phone number</p>
          </CardContent>
        </Card>
        <Card className="bg-white/10 border-white/20 text-white">
          <CardContent className="pt-6 pb-4">
            <div className="text-3xl mb-2">2</div>
            <p className="text-sm text-blue-200">Verify your information</p>
          </CardContent>
        </Card>
        <Card className="bg-white/10 border-white/20 text-white">
          <CardContent className="pt-6 pb-4">
            <div className="text-3xl mb-2">3</div>
            <p className="text-sm text-blue-200">Describe the damage</p>
          </CardContent>
        </Card>
      </div>

      {/* Current Wait Time */}
      <Card className="mt-8 bg-white/10 border-white/20">
        <CardContent className="py-4 flex items-center justify-center gap-3 text-white">
          <Clock className="h-5 w-5 text-blue-300" />
          <span>Current estimated wait time: </span>
          <span className="font-bold text-lg">~10 minutes</span>
        </CardContent>
      </Card>
    </div>
  )
}
