import * as React from "react"
import { useNavigate } from "react-router-dom"
import { usePortal } from "@/contexts/portal-context"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Car, Lock, AlertCircle, Phone, Mail } from "lucide-react"

export function PortalLoginPage() {
  const { login, isAuthenticated, isLoading } = usePortal()
  const navigate = useNavigate()
  const [accessCode, setAccessCode] = React.useState("")
  const [identifier, setIdentifier] = React.useState("")
  const [error, setError] = React.useState("")
  const [submitting, setSubmitting] = React.useState(false)

  // Redirect if already authenticated
  React.useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate("/portal")
    }
  }, [isLoading, isAuthenticated, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSubmitting(true)

    if (!accessCode.trim()) {
      setError("Please enter your access code")
      setSubmitting(false)
      return
    }

    const success = await login(accessCode.trim(), identifier.trim() || undefined)

    if (success) {
      navigate("/portal")
    } else {
      setError("Invalid access code or identifier. Please try again.")
    }
    setSubmitting(false)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
            <Car className="h-8 w-8 text-blue-600" />
          </div>
          <CardTitle className="text-2xl">Customer Portal</CardTitle>
          <CardDescription>
            Enter your access code to view your repair status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 rounded-lg">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="accessCode">
                <Lock className="h-4 w-4 inline mr-2" />
                Access Code
              </Label>
              <Input
                id="accessCode"
                type="text"
                placeholder="Enter your 6-digit code"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
                maxLength={10}
                className="text-center text-2xl tracking-widest font-mono"
                autoComplete="off"
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                You received this code when you dropped off your vehicle
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="identifier" className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <Phone className="h-4 w-4" />
                  <span>/</span>
                  <Mail className="h-4 w-4" />
                </div>
                Phone or Email (optional)
              </Label>
              <Input
                id="identifier"
                type="text"
                placeholder="Phone number or email"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Additional verification for your security
              </p>
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Verifying...
                </>
              ) : (
                "Access My Portal"
              )}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t text-center">
            <p className="text-sm text-muted-foreground mb-2">
              Don't have an access code?
            </p>
            <p className="text-sm">
              Contact us at{" "}
              <a href="tel:555-123-4567" className="text-blue-600 font-medium">
                (555) 123-4567
              </a>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
