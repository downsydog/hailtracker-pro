import { Link, Outlet, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import {
  Building2,
  Car,
  Upload,
  MapPin,
  BarChart3,
  Key,
} from "lucide-react"

const navItems = [
  { label: "Dashboard", href: "/dealership", icon: BarChart3 },
  { label: "Vehicles", href: "/dealership/vehicles", icon: Car },
  { label: "Batch Upload", href: "/dealership/upload", icon: Upload },
  { label: "Locations", href: "/dealership/locations", icon: MapPin },
  { label: "API Settings", href: "/dealership/api", icon: Key },
]

export function DealershipLayout() {
  const location = useLocation()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center">
          <Building2 className="h-6 w-6 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Dealership Portal</h1>
          <p className="text-muted-foreground">Manage your fleet and repair requests</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex gap-1 p-1 bg-muted rounded-lg overflow-x-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href ||
            (item.href !== "/dealership" && location.pathname.startsWith(item.href))

          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap",
                isActive
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-background/50"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Content */}
      <Outlet />
    </div>
  )
}
