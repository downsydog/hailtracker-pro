import * as React from "react"
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom"
import { usePortal } from "@/contexts/portal-context"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  Home,
  Car,
  FileText,
  MessageSquare,
  Calendar,
  Shield,
  Image,
  CreditCard,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
} from "lucide-react"

const navItems = [
  { label: "Dashboard", href: "/portal", icon: Home },
  { label: "My Jobs", href: "/portal/jobs", icon: Car },
  { label: "Documents", href: "/portal/documents", icon: FileText },
  { label: "Messages", href: "/portal/messages", icon: MessageSquare },
  { label: "Appointments", href: "/portal/appointments", icon: Calendar },
  { label: "Insurance", href: "/portal/insurance", icon: Shield },
  { label: "Photos", href: "/portal/photos", icon: Image },
  { label: "Payments", href: "/portal/payments", icon: CreditCard },
  { label: "Settings", href: "/portal/settings", icon: Settings },
]

export function PortalLayout() {
  const { customer, isLoading, logout } = usePortal()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)

  // Redirect to login if not authenticated
  React.useEffect(() => {
    if (!isLoading && !customer) {
      navigate("/portal/login")
    }
  }, [isLoading, customer, navigate])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!customer) {
    return null
  }

  const handleLogout = async () => {
    await logout()
    navigate("/portal/login")
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <button
                className="lg:hidden p-2 -ml-2"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? (
                  <X className="h-6 w-6" />
                ) : (
                  <Menu className="h-6 w-6" />
                )}
              </button>
              <Link to="/portal" className="flex items-center gap-2">
                <Car className="h-8 w-8 text-blue-600" />
                <span className="font-bold text-xl hidden sm:block">Customer Portal</span>
              </Link>
            </div>

            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <span className="absolute top-0 right-0 h-2 w-2 bg-red-500 rounded-full"></span>
              </Button>
              <div className="hidden sm:flex items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  Welcome, {customer.first_name}
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4 mr-2" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar - Desktop */}
        <aside className="hidden lg:block w-64 bg-white border-r min-h-[calc(100vh-4rem)] sticky top-16">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setMobileMenuOpen(false)}>
            <aside
              className="absolute left-0 top-16 w-64 bg-white h-[calc(100vh-4rem)] shadow-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <nav className="p-4 space-y-1">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <Link
                      key={item.href}
                      to={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                        isActive
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-700 hover:bg-gray-100"
                      )}
                    >
                      <item.icon className="h-5 w-5" />
                      {item.label}
                    </Link>
                  )
                })}
              </nav>
            </aside>
          </div>
        )}

        {/* Main Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="max-w-6xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
