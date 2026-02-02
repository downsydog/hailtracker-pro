import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scheduleApi, SchedulingToken } from '@/api/schedule'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import {
  Link2,
  Plus,
  Copy,
  Check,
  Clock,
  Users,
  ExternalLink,
} from 'lucide-react'

const APPOINTMENT_TYPES = [
  { value: 'DROP_OFF', label: 'Drop Off' },
  { value: 'INSPECTION', label: 'Inspection' },
  { value: 'PICKUP', label: 'Pickup' },
  { value: 'ESTIMATE', label: 'Estimate' },
]

export function SchedulingTokensPage() {
  const [showCreateDialog, setShowCreateDialog] = React.useState(false)
  const [copiedToken, setCopiedToken] = React.useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['scheduling-tokens'],
    queryFn: scheduleApi.getSchedulingTokens,
  })

  const createMutation = useMutation({
    mutationFn: scheduleApi.createSchedulingToken,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduling-tokens'] })
      setShowCreateDialog(false)
    },
  })

  const handleCreateToken = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      appointment_type: formData.get('appointment_type') as string || 'DROP_OFF',
      expires_hours: parseInt(formData.get('expires_hours') as string) || 168,
      max_uses: parseInt(formData.get('max_uses') as string) || 1,
    })
  }

  const copyToClipboard = async (url: string, tokenId: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopiedToken(tokenId)
      setTimeout(() => setCopiedToken(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const tokens = data?.tokens || []
  const activeTokens = tokens.filter((t: SchedulingToken) => t.is_active)
  const expiredTokens = tokens.filter((t: SchedulingToken) => !t.is_active)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Self-Scheduling Links</h1>
          <p className="text-muted-foreground">
            Create scheduling links for customers to book appointments
          </p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Link
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Scheduling Link</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateToken} className="space-y-4">
              <div>
                <Label htmlFor="appointment_type">Appointment Type</Label>
                <Select name="appointment_type" defaultValue="DROP_OFF">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {APPOINTMENT_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="expires_hours">Expires In (hours)</Label>
                  <Input
                    id="expires_hours"
                    name="expires_hours"
                    type="number"
                    defaultValue={168}
                    min={1}
                    max={720}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    168 hours = 1 week
                  </p>
                </div>
                <div>
                  <Label htmlFor="max_uses">Max Uses</Label>
                  <Input
                    id="max_uses"
                    name="max_uses"
                    type="number"
                    defaultValue={1}
                    min={1}
                    max={100}
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateDialog(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Link'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Links</CardTitle>
            <Link2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeTokens.length}</div>
            <p className="text-xs text-muted-foreground">Ready to share</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Uses</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tokens.reduce((sum: number, t: SchedulingToken) => sum + t.times_used, 0)}
            </div>
            <p className="text-xs text-muted-foreground">Appointments booked</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Expired</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{expiredTokens.length}</div>
            <p className="text-xs text-muted-foreground">No longer active</p>
          </CardContent>
        </Card>
      </div>

      {/* Active Tokens */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Active Links</h2>
        {activeTokens.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Link2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium">No active links</h3>
              <p className="text-muted-foreground">
                Create a scheduling link to share with customers
              </p>
              <Button className="mt-4" onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Link
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {activeTokens.map((token: SchedulingToken) => {
              const schedulingUrl = `${window.location.origin}/schedule/${token.token}`
              return (
                <Card key={token.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline">
                            {APPOINTMENT_TYPES.find((t) => t.value === token.appointment_type)?.label || token.appointment_type}
                          </Badge>
                          <Badge variant="secondary">
                            {token.times_used}/{token.max_uses} uses
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground font-mono truncate max-w-md">
                          {schedulingUrl}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Expires: {new Date(token.expires_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(schedulingUrl, token.token)}
                        >
                          {copiedToken === token.token ? (
                            <>
                              <Check className="h-4 w-4 mr-1 text-green-500" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="h-4 w-4 mr-1" />
                              Copy
                            </>
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          asChild
                        >
                          <a href={schedulingUrl} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      {/* Expired Tokens */}
      {expiredTokens.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Expired Links</h2>
          <div className="space-y-3">
            {expiredTokens.map((token: SchedulingToken) => (
              <Card key={token.id} className="opacity-60">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline">
                          {APPOINTMENT_TYPES.find((t) => t.value === token.appointment_type)?.label || token.appointment_type}
                        </Badge>
                        <Badge variant="secondary">
                          {token.times_used} uses
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Expired: {new Date(token.expires_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
