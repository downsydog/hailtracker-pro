import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import { useAuth } from "@/contexts/auth-context"
import {
  LayoutDashboard,
  Briefcase,
  Users,
  Car,
  FileText,
  UserPlus,
  BarChart3,
  Settings,
  Bell,
  Calendar,
  UserCog,
  Wrench,
  TrendingUp,
  CloudSun,
  LucideIcon,
  DollarSign,
  Shield,
  Map,
  Search,
  ClipboardList,
  Clock,
  Route,
  Target,
  Trophy,
  MessageSquare,
  Ban,
  Eye,
  Building2,
  Upload,
  MapPin,
  Key,
  ExternalLink,
  Monitor,
  User,
  ChevronRight,
} from "lucide-react"

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  badge?: number
  external?: boolean
}

interface NavSection {
  title?: string
  items: NavItem[]
  roles?: string[] // If specified, only show to these roles
  permissions?: string[] // If specified, only show to users with any of these permissions
}

// Main navigation sections
const navigation: NavSection[] = [
  {
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
      { label: "Jobs", href: "/jobs", icon: Briefcase },
      { label: "Customers", href: "/customers", icon: Users },
      { label: "Vehicles", href: "/vehicles", icon: Car },
      { label: "Leads", href: "/leads", icon: UserPlus },
      { label: "Estimates", href: "/estimates", icon: FileText },
      { label: "Invoices", href: "/invoices", icon: DollarSign },
      { label: "Claims", href: "/claims", icon: Shield },
      { label: "Schedule", href: "/schedule", icon: Calendar },
    ],
  },
  {
    title: "Maps & Weather",
    items: [
      { label: "Hail Map", href: "/hail-map", icon: CloudSun },
      { label: "Hail Lookup", href: "/hail-lookup", icon: Search },
      { label: "Fleet Map", href: "/fleet", icon: Map },
    ],
  },
  {
    title: "Role Dashboards",
    items: [
      { label: "Tech", href: "/tech", icon: Wrench },
      { label: "Sales", href: "/sales", icon: TrendingUp },
      { label: "Estimator", href: "/estimator", icon: ClipboardList },
      { label: "Hours", href: "/hours", icon: Clock },
    ],
  },
  {
    title: "Sales Tools",
    items: [
      { label: "My Route", href: "/sales/routes", icon: Route },
      { label: "Field Leads", href: "/sales/field-leads", icon: Target },
      { label: "Competitors", href: "/sales/competitors", icon: Eye },
      { label: "Leaderboard", href: "/sales/leaderboard", icon: Trophy },
      { label: "Scripts", href: "/sales/scripts", icon: MessageSquare },
      { label: "DNK List", href: "/sales/dnk", icon: Ban },
    ],
    roles: ["admin", "manager", "sales"],
  },
  {
    title: "Dealership Portal",
    items: [
      { label: "Overview", href: "/dealership", icon: Building2 },
      { label: "Vehicles", href: "/dealership/vehicles", icon: Car },
      { label: "Batch Upload", href: "/dealership/upload", icon: Upload },
      { label: "Locations", href: "/dealership/locations", icon: MapPin },
      { label: "API Settings", href: "/dealership/api", icon: Key },
    ],
    roles: ["admin", "manager", "dealership"],
    permissions: ["dealership_access"],
  },
  {
    title: "Reports & Admin",
    items: [
      { label: "Reports", href: "/reports", icon: BarChart3 },
      { label: "Notifications", href: "/notifications", icon: Bell },
      { label: "Users", href: "/admin/users", icon: UserCog },
      { label: "Settings", href: "/admin/settings", icon: Settings },
    ],
    roles: ["admin", "manager"],
  },
]

// Portal quick-switch links
const portalLinks: NavItem[] = [
  { label: "Customer Portal", href: "/portal", icon: User, external: true },
  { label: "Kiosk Mode", href: "/kiosk", icon: Monitor, external: true },
  { label: "Dealership", href: "/dealership", icon: Building2 },
]

interface SidebarContentProps {
  onItemClick?: () => void
}

export function SidebarContent({ onItemClick }: SidebarContentProps) {
  const location = useLocation()
  const { user } = useAuth()

  // Check if user has access to a section based on roles/permissions
  const hasAccess = (section: NavSection): boolean => {
    // If no role/permission restrictions, show to everyone
    if (!section.roles && !section.permissions) {
      return true
    }

    // For demo mode (no user), show everything
    if (!user) {
      return true
    }

    // Check role match
    if (section.roles && section.roles.includes(user.role)) {
      return true
    }

    // Check permission match
    if (section.permissions && user.permissions) {
      return section.permissions.some((p) => user.permissions.includes(p))
    }

    return false
  }

  return (
    <>
      <div className="flex items-center h-16 px-6 border-b">
        <Link to="/" className="flex items-center gap-2" onClick={onItemClick}>
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">HT</span>
          </div>
          <span className="font-semibold text-lg">HailTracker</span>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        {navigation.filter(hasAccess).map((section, sectionIndex) => (
          <div key={sectionIndex} className="px-3 mb-6">
            {section.title && (
              <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {section.title}
              </h3>
            )}
            <div className="space-y-1">
              {section.items.map((item) => {
                const isActive = location.pathname === item.href ||
                  (item.href !== "/" && location.pathname.startsWith(item.href))

                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    onClick={onItemClick}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.label}
                    {item.badge !== undefined && item.badge > 0 && (
                      <span className="ml-auto bg-primary-foreground text-primary text-xs font-medium px-2 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}

        {/* Portal Quick Switch */}
        <div className="px-3 mb-6 border-t pt-4">
          <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Quick Switch
          </h3>
          <div className="space-y-1">
            {portalLinks.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                onClick={onItemClick}
                target={item.external ? "_blank" : undefined}
                rel={item.external ? "noopener noreferrer" : undefined}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                  "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
                {item.external && (
                  <ExternalLink className="h-3 w-3 ml-auto opacity-50" />
                )}
                {!item.external && (
                  <ChevronRight className="h-4 w-4 ml-auto opacity-50" />
                )}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* User Info at bottom */}
      {user && (
        <div className="border-t p-4">
          <Link
            to="/profile"
            onClick={onItemClick}
            className="flex items-center gap-3 px-2 py-2 rounded-md hover:bg-muted transition-colors"
          >
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user.name?.charAt(0)?.toUpperCase() || user.username?.charAt(0)?.toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.name || user.username}</p>
              <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
            </div>
          </Link>
        </div>
      )}
    </>
  )
}

export function Sidebar() {
  return (
    <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 bg-card border-r">
      <SidebarContent />
    </aside>
  )
}
