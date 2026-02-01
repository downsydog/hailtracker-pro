import * as React from "react"
import { PageHeader } from "@/components/app/page-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Target,
  CheckSquare,
  DollarSign,
  TrendingUp,
  Plus,
  Filter,
  MoreHorizontal,
} from "lucide-react"

export function CRMDashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="CRM Dashboard"
        description="Manage deals, tasks, and customer relationships"
      >
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Deal
        </Button>
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Open Deals</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">12</p>
            <p className="text-xs text-muted-foreground">5 closing this week</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Tasks Due</CardTitle>
            <CheckSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">8</p>
            <p className="text-xs text-muted-foreground">3 overdue</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">$45,200</p>
            <p className="text-xs text-muted-foreground">Weighted: $28,500</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">68%</p>
            <p className="text-xs text-muted-foreground">Up 5% this month</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center py-8">
            No recent activity
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

export function CRMDealsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Deals"
        description="Track and manage your sales deals"
      >
        <Button variant="outline">
          <Filter className="h-4 w-4 mr-2" />
          Filter
        </Button>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Deal
        </Button>
      </PageHeader>

      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No deals found. Create your first deal to get started.
        </CardContent>
      </Card>
    </div>
  )
}

export function CRMTasksPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Tasks"
        description="Manage your CRM tasks and follow-ups"
      >
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Task
        </Button>
      </PageHeader>

      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No tasks found
        </CardContent>
      </Card>
    </div>
  )
}

export function CRMPipelinePage() {
  const stages = ["Lead", "Qualified", "Proposal", "Negotiation", "Closed Won"]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline"
        description="Visual pipeline view of your deals"
      />

      <div className="flex gap-4 overflow-x-auto pb-4">
        {stages.map((stage) => (
          <div key={stage} className="flex-shrink-0 w-72">
            <div className="bg-muted p-3 rounded-t-lg font-medium flex items-center justify-between">
              {stage}
              <Badge variant="secondary">0</Badge>
            </div>
            <div className="border border-t-0 rounded-b-lg min-h-[400px] p-2 bg-muted/20">
              <p className="text-sm text-muted-foreground text-center py-8">
                No deals in this stage
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
