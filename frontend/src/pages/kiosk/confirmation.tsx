import * as React from "react"
import { useSearchParams, useNavigate } from "react-router-dom"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle, Clock, QrCode, Home, Copy, Check } from "lucide-react"

export function KioskConfirmationPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [copied, setCopied] = React.useState(false)

  const jobNumber = searchParams.get("job") || "JOB-2025-001"
  const queuePosition = searchParams.get("position") || "3"
  const accessCode = searchParams.get("code") || "ABC123"

  const handleCopyCode = () => {
    navigator.clipboard.writeText(accessCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Auto-redirect after 30 seconds
  React.useEffect(() => {
    const timer = setTimeout(() => {
      navigate("/kiosk")
    }, 30000)
    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <Card className="shadow-2xl text-center">
      <CardContent className="pt-12 pb-8 px-8">
        {/* Success Icon */}
        <div className="mb-8">
          <div className="h-24 w-24 mx-auto rounded-full bg-green-100 flex items-center justify-center animate-pulse">
            <CheckCircle className="h-14 w-14 text-green-600" />
          </div>
        </div>

        {/* Success Message */}
        <h1 className="text-3xl font-bold mb-2">You're Checked In!</h1>
        <p className="text-xl text-muted-foreground mb-8">
          Thank you for choosing us for your repair
        </p>

        {/* Job Info Card */}
        <div className="bg-blue-50 rounded-xl p-6 mb-8">
          <p className="text-sm text-blue-600 font-medium mb-1">Your Job Number</p>
          <p className="text-3xl font-bold text-blue-700">{jobNumber}</p>
        </div>

        {/* Queue Position */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="bg-gray-50 rounded-xl p-4">
            <Clock className="h-8 w-8 mx-auto text-gray-600 mb-2" />
            <p className="text-sm text-muted-foreground">Queue Position</p>
            <p className="text-2xl font-bold">#{queuePosition}</p>
          </div>
          <div className="bg-gray-50 rounded-xl p-4">
            <QrCode className="h-8 w-8 mx-auto text-gray-600 mb-2" />
            <p className="text-sm text-muted-foreground">Estimated Wait</p>
            <p className="text-2xl font-bold">~15 min</p>
          </div>
        </div>

        {/* Access Code */}
        <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl p-6 mb-8 text-white">
          <p className="text-sm text-purple-200 mb-2">Your Portal Access Code</p>
          <div className="flex items-center justify-center gap-3">
            <p className="text-4xl font-mono font-bold tracking-wider">
              {accessCode}
            </p>
            <Button
              variant="ghost"
              size="icon"
              className="text-white hover:bg-white/20"
              onClick={handleCopyCode}
            >
              {copied ? (
                <Check className="h-5 w-5" />
              ) : (
                <Copy className="h-5 w-5" />
              )}
            </Button>
          </div>
          <p className="text-sm text-purple-200 mt-2">
            Use this code to track your repair online
          </p>
        </div>

        {/* Instructions */}
        <div className="text-left bg-gray-50 rounded-xl p-6 mb-8">
          <h3 className="font-semibold mb-3">What's Next?</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="h-5 w-5 rounded-full bg-blue-100 text-blue-600 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                1
              </span>
              <span>Please have a seat in our waiting area</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="h-5 w-5 rounded-full bg-blue-100 text-blue-600 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                2
              </span>
              <span>A service advisor will call you shortly</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="h-5 w-5 rounded-full bg-blue-100 text-blue-600 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                3
              </span>
              <span>Track your repair progress at hailtracker.com/portal</span>
            </li>
          </ul>
        </div>

        {/* Return Button */}
        <Button
          variant="outline"
          size="lg"
          className="w-full h-14"
          onClick={() => navigate("/kiosk")}
        >
          <Home className="h-5 w-5 mr-2" />
          Return to Start
        </Button>

        <p className="text-xs text-muted-foreground mt-4">
          This screen will reset automatically in 30 seconds
        </p>
      </CardContent>
    </Card>
  )
}
