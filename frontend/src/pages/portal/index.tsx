import * as React from "react"
import { Outlet, Link, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Home,
  Briefcase,
  MessageSquare,
  Calendar,
  FileText,
  Camera,
  CreditCard,
  Shield,
  Settings,
  LogOut,
  Users,
  Gift,
  Star,
} from "lucide-react"
import { usePortal } from "@/contexts/portal-context"

// Portal Layout
export function PortalLayout() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold">Customer Portal</h1>
          <Button variant="ghost" onClick={() => navigate("/portal/settings")}>
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </header>
      <nav className="bg-white border-b">
        <div className="container mx-auto px-4 flex overflow-x-auto gap-2 py-2">
          <Link to="/portal" className="px-3 py-2 text-sm hover:bg-gray-100 rounded whitespace-nowrap">Dashboard</Link>
          <Link to="/portal/jobs" className="px-3 py-2 text-sm hover:bg-gray-100 rounded whitespace-nowrap">My Jobs</Link>
          <Link to="/portal/messages" className="px-3 py-2 text-sm hover:bg-gray-100 rounded whitespace-nowrap">Messages</Link>
          <Link to="/portal/appointments" className="px-3 py-2 text-sm hover:bg-gray-100 rounded whitespace-nowrap">Appointments</Link>
          <Link to="/portal/documents" className="px-3 py-2 text-sm hover:bg-gray-100 rounded whitespace-nowrap">Documents</Link>
          <Link to="/portal/payments" className="px-3 py-2 text-sm hover:bg-gray-100 rounded whitespace-nowrap">Payments</Link>
        </div>
      </nav>
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

// Portal Login
export function PortalLoginPage() {
  const [email, setEmail] = React.useState("")
  const [code, setCode] = React.useState("")
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement portal auth
    navigate("/portal")
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Customer Portal Login</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email or Phone</label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Enter your email or phone"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Access Code</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full p-2 border rounded"
                placeholder="Enter your access code"
              />
            </div>
            <Button type="submit" className="w-full">Login</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Dashboard
export function PortalDashboardPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Welcome to Your Portal</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <Briefcase className="h-5 w-5" />
            <CardTitle>Active Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">1</p>
            <Link to="/portal/jobs" className="text-sm text-blue-600 hover:underline">View all jobs</Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            <CardTitle>Messages</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">0</p>
            <Link to="/portal/messages" className="text-sm text-blue-600 hover:underline">View messages</Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center gap-2">
            <Calendar className="h-5 w-5" />
            <CardTitle>Next Appointment</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No upcoming appointments</p>
            <Link to="/portal/appointments" className="text-sm text-blue-600 hover:underline">Schedule now</Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Portal Jobs
export function PortalJobsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">My Jobs</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No jobs found
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Job Detail
export function PortalJobDetailPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Job Details</h2>
      <Card>
        <CardContent className="py-8">
          Job information will appear here
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Messages
export function PortalMessagesPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Messages</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No messages
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Appointments
export function PortalAppointmentsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Appointments</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No upcoming appointments
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Documents
export function PortalDocumentsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Documents</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No documents available
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Photos
export function PortalPhotosPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Photos</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No photos available
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Payments
export function PortalPaymentsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Payments</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No payment history
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Insurance
export function PortalInsurancePage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Insurance Information</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No insurance claims
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Settings
export function PortalSettingsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Settings</h2>
      <Card>
        <CardContent className="py-8">
          <p>Manage your account settings here</p>
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Referrals
export function PortalReferralsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Referrals</h2>
      <Card>
        <CardContent className="py-8 text-center">
          <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Refer friends and earn rewards!</p>
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Flyers
export function PortalFlyersPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Promotional Flyers</h2>
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No flyers available
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Loyalty
export function PortalLoyaltyPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Loyalty Program</h2>
      <Card>
        <CardContent className="py-8 text-center">
          <Gift className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Join our loyalty program for exclusive rewards</p>
        </CardContent>
      </Card>
    </div>
  )
}

// Portal Reviews
export function PortalReviewsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Leave a Review</h2>
      <Card>
        <CardContent className="py-8 text-center">
          <Star className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">We appreciate your feedback!</p>
        </CardContent>
      </Card>
    </div>
  )
}
