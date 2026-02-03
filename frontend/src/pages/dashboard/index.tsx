import { CloudRain, Users, Briefcase, DollarSign } from 'lucide-react'

const stats = [
  { label: 'Active Leads', value: '47', icon: Users, change: '+12%' },
  { label: 'Open Jobs', value: '23', icon: Briefcase, change: '+5%' },
  { label: 'Hail Events (7d)', value: '8', icon: CloudRain, change: '+3' },
  { label: 'Revenue (MTD)', value: '$127,450', icon: DollarSign, change: '+18%' },
]

export function DashboardPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Here's what's happening.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="p-4 bg-card rounded-lg border">
              <div className="flex items-center justify-between mb-2">
                <Icon className="h-5 w-5 text-muted-foreground" />
                <span className="text-xs text-green-600 font-medium">{stat.change}</span>
              </div>
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </div>
          )
        })}
      </div>

      {/* Activity Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">Recent Hail Events</h2>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3 p-2 hover:bg-accent rounded-md">
                <CloudRain className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="font-medium">Hail Event #{i}</p>
                  <p className="text-sm text-muted-foreground">Dallas, TX - 1.5" diameter</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
          <div className="space-y-3">
            {[
              'New lead assigned: John Smith',
              'Job #1234 marked complete',
              'Estimate approved: $12,450',
              'Fleet vehicle checked in'
            ].map((activity, i) => (
              <div key={i} className="flex items-center gap-3 p-2 hover:bg-accent rounded-md">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <p className="text-sm">{activity}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
