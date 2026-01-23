import { Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
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
  ClipboardList,
  Clock,
  Route,
  Target,
  Trophy,
  MessageSquare,
  Ban,
  Eye,
} from "lucide-react"

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  badge?: number
}

interface NavSection {
  title?: string
  items: NavItem[]
}

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
    title: "Maps",
    items: [
      { label: "Hail Map", href: "/hail-map", icon: CloudSun },
      { label: "Fleet Map", href: "/fleet", icon: Map },
    ],
  },
  {
    title: "Dashboards",
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
  },
  {
    title: "Reports & Admin",
    items: [
      { label: "Reports", href: "/reports", icon: BarChart3 },
      { label: "Notifications", href: "/notifications", icon: Bell },
      { label: "Users", href: "/admin/users", icon: UserCog },
      { label: "Settings", href: "/admin/settings", icon: Settings },
    ],
  },
]

interface SidebarContentProps {
  onItemClick?: () => void
}

export function SidebarContent({ onItemClick }: SidebarContentProps) {
  const location = useLocation()

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
        {navigation.map((section, sectionIndex) => (
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
      </nav>
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
