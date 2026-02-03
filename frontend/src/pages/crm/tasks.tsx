import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { crmApi, CRMTask } from '@/api/crm'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Plus,
  CheckSquare,
  AlertTriangle,
  Calendar,
  User,
} from 'lucide-react'

const PRIORITIES = [
  { value: 'LOW', label: 'Low', color: 'bg-gray-500' },
  { value: 'NORMAL', label: 'Normal', color: 'bg-blue-500' },
  { value: 'HIGH', label: 'High', color: 'bg-orange-500' },
  { value: 'URGENT', label: 'Urgent', color: 'bg-red-500' },
]

const STATUSES = [
  { value: 'PENDING', label: 'Pending' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

export function CRMTasksPage() {
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const [showNewTask, setShowNewTask] = React.useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['crm-tasks', { status: statusFilter }],
    queryFn: () => crmApi.getTasks({
      status: statusFilter !== 'all' ? statusFilter : undefined,
    }),
  })

  const { data: overdueData } = useQuery({
    queryKey: ['crm-tasks-overdue'],
    queryFn: crmApi.getOverdueTasks,
  })

  const createMutation = useMutation({
    mutationFn: crmApi.createTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm-tasks'] })
      setShowNewTask(false)
    },
  })

  const completeMutation = useMutation({
    mutationFn: crmApi.completeTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm-tasks'] })
    },
  })

  const handleCreateTask = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      title: formData.get('title') as string,
      description: formData.get('description') as string,
      due_date: formData.get('due_date') as string,
      priority: (formData.get('priority') as CRMTask['priority']) || 'NORMAL',
    })
  }

  const tasks = data?.tasks || []
  const overdueTasks = overdueData?.tasks || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tasks</h1>
          <p className="text-muted-foreground">Manage your CRM tasks and follow-ups</p>
        </div>
        <Dialog open={showNewTask} onOpenChange={setShowNewTask}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Task
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Task</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <Label htmlFor="title">Task Title</Label>
                <Input id="title" name="title" required placeholder="e.g., Follow up with customer" />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" name="description" placeholder="Task details..." />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="due_date">Due Date</Label>
                  <Input id="due_date" name="due_date" type="date" />
                </div>
                <div>
                  <Label htmlFor="priority">Priority</Label>
                  <Select name="priority" defaultValue="NORMAL">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PRIORITIES.map(p => (
                        <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowNewTask(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Task'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Overdue Alert */}
      {overdueTasks.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-red-700 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              {overdueTasks.length} Overdue Task{overdueTasks.length > 1 ? 's' : ''}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {overdueTasks.slice(0, 3).map((task: CRMTask) => (
                <div key={task.id} className="flex items-center justify-between p-2 bg-white rounded">
                  <span className="font-medium">{task.title}</span>
                  <span className="text-sm text-red-600">Due: {task.due_date}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                {STATUSES.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tasks List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : tasks.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No tasks found</h3>
            <p className="text-muted-foreground">Create your first task to get started</p>
            <Button className="mt-4" onClick={() => setShowNewTask(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Task
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {tasks.map((task: CRMTask) => {
            const priority = PRIORITIES.find(p => p.value === task.priority)
            const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'COMPLETED'

            return (
              <Card
                key={task.id}
                className={`${isOverdue ? 'border-red-200' : ''} ${task.status === 'COMPLETED' ? 'opacity-60' : ''}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    <Checkbox
                      checked={task.status === 'COMPLETED'}
                      onCheckedChange={() => {
                        if (task.status !== 'COMPLETED') {
                          completeMutation.mutate(task.id)
                        }
                      }}
                    />
                    <div className="flex-1">
                      <p className={`font-medium ${task.status === 'COMPLETED' ? 'line-through text-muted-foreground' : ''}`}>
                        {task.title}
                      </p>
                      {task.description && (
                        <p className="text-sm text-muted-foreground">{task.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        {task.due_date && (
                          <span className={`flex items-center gap-1 ${isOverdue ? 'text-red-600 font-medium' : ''}`}>
                            <Calendar className="h-3 w-3" />
                            {task.due_date}
                          </span>
                        )}
                        {task.assigned_to_name && (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {task.assigned_to_name}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={priority?.color}>{priority?.label}</Badge>
                      <Badge variant="outline">{task.status}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
