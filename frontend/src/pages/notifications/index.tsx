import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/app/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useAuth } from '@/contexts/auth-context'
import {
  useWorkInbox,
  useSendNudge,
  WorkInboxItem,
  getPriorityBadgeVariant,
  getSeverityBadgeVariant,
  getSeverityLabel,
  formatRelativeTime,
  formatAge,
} from '@/hooks/use-notifications'
import {
  Bell,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  FileText,
  FilePlus,
  Wrench,
  Receipt,
  Users,
  ChevronRight,
  RefreshCw,
  Lock,
  Activity,
  Inbox,
  User,
  Siren,
  Send,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'

type FilterTab = 'all' | 'attention' | 'activity' | 'escalations' | 'mine'

// Entity icon component
function EntityIcon({ entity }: { entity: WorkInboxItem['entity'] }) {
  const iconClass = 'h-4 w-4'
  switch (entity) {
    case 'estimate':
      return <FileText className={iconClass} />
    case 'supplement':
      return <FilePlus className={iconClass} />
    case 'job':
      return <Wrench className={iconClass} />
    case 'invoice':
      return <Receipt className={iconClass} />
    case 'lead':
      return <Users className={iconClass} />
    default:
      return <Bell className={iconClass} />
  }
}

// Priority indicator component
function PriorityIndicator({ score, severity }: { score: number; severity?: string }) {
  // For escalations, use severity-based colors
  if (severity === 'critical') {
    return <AlertCircle className="h-4 w-4 text-destructive" />
  }
  if (severity === 'high') {
    return <AlertTriangle className="h-4 w-4 text-amber-500" />
  }
  if (severity === 'warn') {
    return <Clock className="h-4 w-4 text-yellow-500" />
  }

  // Fallback to score-based
  if (score >= 80) {
    return <AlertCircle className="h-4 w-4 text-destructive" />
  }
  if (score >= 60) {
    return <AlertTriangle className="h-4 w-4 text-amber-500" />
  }
  return <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
}

// Summary card component
function SummaryCard({
  title,
  count,
  variant,
  icon: Icon,
}: {
  title: string
  count: number
  variant: 'destructive' | 'warning' | 'default'
  icon: React.ElementType
}) {
  const bgColor = variant === 'destructive'
    ? 'bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-900'
    : variant === 'warning'
    ? 'bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900'
    : 'bg-muted/50'

  const iconColor = variant === 'destructive'
    ? 'text-red-600 dark:text-red-400'
    : variant === 'warning'
    ? 'text-amber-600 dark:text-amber-400'
    : 'text-muted-foreground'

  return (
    <Card className={cn('border', bgColor)}>
      <CardContent className="flex items-center gap-3 py-4">
        <Icon className={cn('h-5 w-5', iconColor)} />
        <div>
          <p className="text-2xl font-bold">{count}</p>
          <p className="text-xs text-muted-foreground">{title}</p>
        </div>
      </CardContent>
    </Card>
  )
}

// Send Nudge Modal
function SendNudgeModal({
  open,
  onOpenChange,
  item,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  item: WorkInboxItem | null
}) {
  const [to, setTo] = useState('')
  const [toInternal, setToInternal] = useState(true)
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')

  const sendNudge = useSendNudge()

  // Reset form when item changes
  const alertType = item?.meta?.alert_type as string || ''
  const defaultSubject = item
    ? `[HailTracker] SLA Alert: ${alertType.replace(/_/g, ' ')} - ${item.title}`
    : ''
  const defaultMessage = item
    ? `This is an automated nudge for: ${item.title}\n\nAlert Type: ${alertType.replace(/_/g, ' ')}\n\nPlease review and take action.`
    : ''

  const handleSubmit = async () => {
    if (!item) return

    try {
      await sendNudge.mutateAsync({
        alert_type: alertType,
        entity: item.entity,
        entity_id: item.entity_id,
        to: toInternal ? undefined : to,
        to_internal: toInternal,
        subject: subject || defaultSubject,
        message: message || defaultMessage,
      })
      onOpenChange(false)
      // Reset form
      setTo('')
      setSubject('')
      setMessage('')
    } catch {
      // Error handled by mutation state
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Send Nudge</DialogTitle>
          <DialogDescription>
            Send an email notification about this SLA escalation.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Recipient</Label>
            <div className="flex items-center gap-2">
              <Button
                variant={toInternal ? 'default' : 'outline'}
                size="sm"
                onClick={() => setToInternal(true)}
              >
                Internal Team
              </Button>
              <Button
                variant={!toInternal ? 'default' : 'outline'}
                size="sm"
                onClick={() => setToInternal(false)}
              >
                Custom Email
              </Button>
            </div>
            {!toInternal && (
              <Input
                placeholder="recipient@example.com"
                value={to}
                onChange={(e) => setTo(e.target.value)}
              />
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="subject">Subject</Label>
            <Input
              id="subject"
              placeholder={defaultSubject}
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="message">Message</Label>
            <Textarea
              id="message"
              placeholder={defaultMessage}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={sendNudge.isPending}>
            {sendNudge.isPending ? 'Sending...' : 'Send Nudge'}
            <Send className="ml-2 h-4 w-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Feed item row component
function FeedItemRow({
  item,
  onNavigate,
  canPerformAction,
  canSendNudge,
  onSendNudge,
}: {
  item: WorkInboxItem
  onNavigate: (route: string) => void
  canPerformAction: boolean
  canSendNudge: boolean
  onSendNudge: (item: WorkInboxItem) => void
}) {
  const isEscalation = item.kind === 'escalation'
  const severity = item.meta?.severity as string | undefined
  const ageDays = item.meta?.age_days as number | undefined
  const ageHours = item.meta?.age_hours as number | undefined

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 border-b last:border-b-0 hover:bg-muted/30 transition-colors cursor-pointer',
        item.kind === 'attention' && 'bg-muted/10',
        isEscalation && severity === 'critical' && 'bg-red-50/50 dark:bg-red-950/10',
        isEscalation && severity === 'high' && 'bg-amber-50/50 dark:bg-amber-950/10'
      )}
      onClick={() => onNavigate(item.route)}
    >
      {/* Priority indicator */}
      <div className="mt-1 flex-shrink-0">
        <PriorityIndicator score={item.priority_score} severity={severity} />
      </div>

      {/* Entity icon */}
      <div className="mt-1 flex-shrink-0 text-muted-foreground">
        <EntityIcon entity={item.entity} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
          <span className="font-medium text-sm truncate">{item.title}</span>
          {isEscalation && severity && (
            <Badge
              variant={getSeverityBadgeVariant(severity)}
              className={cn(
                'text-xs',
                severity === 'high' && 'bg-amber-500 hover:bg-amber-600 text-white',
                severity === 'warn' && 'bg-yellow-500 hover:bg-yellow-600 text-white'
              )}
            >
              {getSeverityLabel(severity)}
            </Badge>
          )}
          {isEscalation && (ageDays || ageHours) && (
            <Badge variant="outline" className="text-xs">
              {formatAge(ageDays, ageHours)} old
            </Badge>
          )}
          {!isEscalation && item.priority_reason && (
            <Badge
              variant={getPriorityBadgeVariant(item.priority_score)}
              className={cn(
                'text-xs',
                item.priority_score >= 60 && item.priority_score < 80 && 'bg-amber-500 hover:bg-amber-600 text-white'
              )}
            >
              {item.priority_reason}
            </Badge>
          )}
          {item.kind === 'attention' && (
            <Badge variant="outline" className="text-xs">
              Action needed
            </Badge>
          )}
          {isEscalation && (
            <Badge variant="outline" className="text-xs border-orange-300 text-orange-700 dark:text-orange-400">
              SLA
            </Badge>
          )}
        </div>
        {item.subtitle && (
          <p className="text-sm text-muted-foreground truncate">{item.subtitle}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1">
          {formatRelativeTime(item.timestamp)}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {isEscalation && canSendNudge && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation()
                    onSendNudge(item)
                  }}
                >
                  <Send className="h-3 w-3 mr-1" />
                  Nudge
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Send a nudge email about this escalation</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        {item.primary_action && !isEscalation && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!canPerformAction}
                  onClick={(e) => {
                    e.stopPropagation()
                    if (canPerformAction) {
                      onNavigate(item.primary_action!.route)
                    }
                  }}
                >
                  {!canPerformAction && <Lock className="h-3 w-3 mr-1" />}
                  {item.primary_action.label}
                </Button>
              </TooltipTrigger>
              {!canPerformAction && (
                <TooltipContent>
                  <p>You don't have permission to perform this action</p>
                </TooltipContent>
              )}
            </Tooltip>
          </TooltipProvider>
        )}
        <ChevronRight className="h-4 w-4 text-muted-foreground" />
      </div>
    </div>
  )
}

export function NotificationsPage() {
  const navigate = useNavigate()
  const { user, permissions } = useAuth()
  const [activeTab, setActiveTab] = useState<FilterTab>('all')
  const [nudgeItem, setNudgeItem] = useState<WorkInboxItem | null>(null)

  // Determine if user should see "Mine" tab
  const userRole = user?.role || ''
  const isRestrictedRole = ['tech', 'technician', 'sales', 'salesman'].includes(userRole)
  const canSendNudge = ['owner', 'manager', 'desk'].includes(userRole)

  // Fetch work inbox - include escalations when on escalations tab or all
  const { feed, summary, escalationsSummary, isLoading, isFetching, refetch, lastUpdated } = useWorkInbox({
    limit: 100,
    assignedToMe: activeTab === 'mine',
    escalations: activeTab === 'escalations' || activeTab === 'all',
  })

  // Filter feed based on active tab
  const filteredFeed = feed.filter((item) => {
    switch (activeTab) {
      case 'attention':
        return item.kind === 'attention'
      case 'activity':
        return item.kind === 'activity'
      case 'escalations':
        return item.kind === 'escalation'
      case 'mine':
        // Backend already filters for assigned_to_me
        return true
      default:
        return true
    }
  })

  // Check if user can perform an action based on entity type
  const canPerformAction = (item: WorkInboxItem): boolean => {
    switch (item.entity) {
      case 'estimate':
        return permissions.canEditPricing || permissions.canSendEmail
      case 'job':
        return true // Jobs can typically be started/completed by anyone
      case 'invoice':
        return permissions.canManageSettings || userRole !== 'tech'
      case 'lead':
        return true
      default:
        return true
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-10 w-full" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Work Inbox"
        description={
          lastUpdated
            ? `Updated ${formatRelativeTime(lastUpdated.toISOString())}`
            : 'Your tasks and recent activity'
        }
      >
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={cn('h-4 w-4 mr-2', isFetching && 'animate-spin')} />
          Refresh
        </Button>
      </PageHeader>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <SummaryCard
          title="Critical"
          count={summary.critical}
          variant="destructive"
          icon={AlertCircle}
        />
        <SummaryCard
          title="High Priority"
          count={summary.high}
          variant="warning"
          icon={AlertTriangle}
        />
        <SummaryCard
          title="Standard"
          count={summary.standard}
          variant="default"
          icon={CheckCircle2}
        />
        {escalationsSummary.total > 0 && (
          <SummaryCard
            title="SLA Escalations"
            count={escalationsSummary.total}
            variant={escalationsSummary.critical > 0 ? 'destructive' : 'warning'}
            icon={Siren}
          />
        )}
      </div>

      {/* Filter Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as FilterTab)}>
        <TabsList>
          <TabsTrigger value="all" className="gap-2">
            <Inbox className="h-4 w-4" />
            All
            <Badge variant="secondary" className="ml-1 text-xs">
              {feed.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="attention" className="gap-2">
            <AlertCircle className="h-4 w-4" />
            Attention
            <Badge variant="secondary" className="ml-1 text-xs">
              {feed.filter((i) => i.kind === 'attention').length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="escalations" className="gap-2">
            <Siren className="h-4 w-4" />
            Escalations
            {escalationsSummary.total > 0 && (
              <Badge
                variant={escalationsSummary.critical > 0 ? 'destructive' : 'secondary'}
                className="ml-1 text-xs"
              >
                {escalationsSummary.total}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="activity" className="gap-2">
            <Activity className="h-4 w-4" />
            Activity
            <Badge variant="secondary" className="ml-1 text-xs">
              {feed.filter((i) => i.kind === 'activity').length}
            </Badge>
          </TabsTrigger>
          {isRestrictedRole && (
            <TabsTrigger value="mine" className="gap-2">
              <User className="h-4 w-4" />
              Mine
            </TabsTrigger>
          )}
        </TabsList>
      </Tabs>

      {/* Feed List */}
      {filteredFeed.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bell className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">All caught up!</h3>
            <p className="text-muted-foreground">
              {activeTab === 'attention'
                ? 'No items need your attention right now.'
                : activeTab === 'activity'
                ? 'No recent activity to show.'
                : activeTab === 'escalations'
                ? 'No SLA escalations to show.'
                : activeTab === 'mine'
                ? 'No items assigned to you.'
                : 'Your work inbox is empty.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {filteredFeed.length} item{filteredFeed.length !== 1 ? 's' : ''}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {filteredFeed.map((item) => (
              <FeedItemRow
                key={item.id}
                item={item}
                onNavigate={navigate}
                canPerformAction={canPerformAction(item)}
                canSendNudge={canSendNudge}
                onSendNudge={setNudgeItem}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Send Nudge Modal */}
      <SendNudgeModal
        open={nudgeItem !== null}
        onOpenChange={(open) => !open && setNudgeItem(null)}
        item={nudgeItem}
      />
    </div>
  )
}
