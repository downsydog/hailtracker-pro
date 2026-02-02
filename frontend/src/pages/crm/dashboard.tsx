import { } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { crmApi, Deal, CRMTask, Interaction } from '@/api/crm'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DollarSign,
  Target,
  CheckSquare,
  AlertTriangle,
  Phone,
  ArrowRight,
  Plus,
  TrendingUp,
  Calendar,
} from 'lucide-react'

const STAGE_COLORS: Record<string, string> = {
  LEAD: 'bg-gray-500',
  CONTACTED: 'bg-blue-500',
  QUALIFIED: 'bg-yellow-500',
  PROPOSAL: 'bg-purple-500',
  NEGOTIATION: 'bg-orange-500',
  CLOSED_WON: 'bg-green-500',
  CLOSED_LOST: 'bg-red-500',
}

export function CRMDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['crm-dashboard'],
    queryFn: crmApi.getDashboard,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const stats = data || {
    total_deals: 0,
    total_value: 0,
    deals_by_stage: {},
    recent_deals: [],
    overdue_tasks: [],
    upcoming_tasks: [],
    recent_interactions: [],
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">CRM Dashboard</h1>
          <p className="text-muted-foreground">Manage your sales pipeline and customer relationships</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/crm/tasks">
              <CheckSquare className="h-4 w-4 mr-2" />
              Tasks
            </Link>
          </Button>
          <Button asChild>
            <Link to="/crm/deals/new">
              <Plus className="h-4 w-4 mr-2" />
              New Deal
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Deals</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_deals}</div>
            <p className="text-xs text-muted-foreground">In pipeline</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${stats.total_value?.toLocaleString() || 0}
            </div>
            <p className="text-xs text-muted-foreground">Total potential revenue</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overdue Tasks</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {stats.overdue_tasks?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Need attention</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.recent_interactions?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Interactions today</p>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Pipeline Overview</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/crm/pipeline">
                View Full Pipeline <ArrowRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {Object.entries(stats.deals_by_stage || {}).map(([stage, count]) => (
              <div key={stage} className="flex-1 text-center">
                <div className={`h-2 rounded ${STAGE_COLORS[stage] || 'bg-gray-300'}`}></div>
                <p className="text-xs mt-1 font-medium">{stage.replace('_', ' ')}</p>
                <p className="text-lg font-bold">{count as number}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Deals */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Deals</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/crm/deals">View All</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {stats.recent_deals?.slice(0, 5).map((deal: Deal) => (
                <Link
                  key={deal.id}
                  to={`/crm/deals/${deal.id}`}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-muted"
                >
                  <div>
                    <p className="font-medium">{deal.title}</p>
                    <p className="text-sm text-muted-foreground">{deal.contact_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">${deal.value?.toLocaleString()}</p>
                    <Badge className={STAGE_COLORS[deal.stage]}>{deal.stage}</Badge>
                  </div>
                </Link>
              ))}
              {(!stats.recent_deals || stats.recent_deals.length === 0) && (
                <p className="text-center text-muted-foreground py-4">No deals yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Tasks */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Upcoming Tasks</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/crm/tasks">View All</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Overdue Tasks */}
              {stats.overdue_tasks?.slice(0, 3).map((task: CRMTask) => (
                <div key={task.id} className="flex items-center gap-3 p-3 rounded-lg bg-red-50 border border-red-200">
                  <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{task.title}</p>
                    <p className="text-sm text-red-600">Overdue: {task.due_date}</p>
                  </div>
                </div>
              ))}

              {/* Upcoming Tasks */}
              {stats.upcoming_tasks?.slice(0, 3).map((task: CRMTask) => (
                <div key={task.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted">
                  <Calendar className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{task.title}</p>
                    <p className="text-sm text-muted-foreground">Due: {task.due_date}</p>
                  </div>
                </div>
              ))}

              {(!stats.upcoming_tasks || stats.upcoming_tasks.length === 0) &&
               (!stats.overdue_tasks || stats.overdue_tasks.length === 0) && (
                <p className="text-center text-muted-foreground py-4">No tasks</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Interactions */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Interactions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {stats.recent_interactions?.slice(0, 5).map((interaction: Interaction) => (
              <div key={interaction.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-muted">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Phone className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">{interaction.contact_name || 'Unknown Contact'}</p>
                  <p className="text-sm text-muted-foreground">
                    {interaction.interaction_type} - {interaction.notes?.slice(0, 50)}...
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">{interaction.created_at}</p>
              </div>
            ))}
            {(!stats.recent_interactions || stats.recent_interactions.length === 0) && (
              <p className="text-center text-muted-foreground py-4">No recent interactions</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
