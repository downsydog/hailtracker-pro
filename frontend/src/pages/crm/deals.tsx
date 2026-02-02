import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { crmApi, Deal } from '@/api/crm'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
  Search,
  DollarSign,
  User,
  Phone,
  Mail,
  Calendar,
} from 'lucide-react'

const STAGES = [
  { value: 'LEAD', label: 'Lead', color: 'bg-gray-500' },
  { value: 'CONTACTED', label: 'Contacted', color: 'bg-blue-500' },
  { value: 'QUALIFIED', label: 'Qualified', color: 'bg-yellow-500' },
  { value: 'PROPOSAL', label: 'Proposal', color: 'bg-purple-500' },
  { value: 'NEGOTIATION', label: 'Negotiation', color: 'bg-orange-500' },
  { value: 'CLOSED_WON', label: 'Closed Won', color: 'bg-green-500' },
  { value: 'CLOSED_LOST', label: 'Closed Lost', color: 'bg-red-500' },
]

export function CRMDealsPage() {
  const [search, setSearch] = React.useState('')
  const [stageFilter, setStageFilter] = React.useState<string>('all')
  const [showNewDeal, setShowNewDeal] = React.useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['crm-deals', { search, stage: stageFilter }],
    queryFn: () => crmApi.getDeals({
      search: search || undefined,
      stage: stageFilter !== 'all' ? stageFilter : undefined,
    }),
  })

  const createMutation = useMutation({
    mutationFn: crmApi.createDeal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm-deals'] })
      setShowNewDeal(false)
    },
  })

  const handleCreateDeal = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      title: formData.get('title') as string,
      value: parseFloat(formData.get('value') as string) || 0,
      stage: (formData.get('stage') as Deal['stage']) || 'LEAD',
      contact_name: formData.get('contact_name') as string,
      contact_email: formData.get('contact_email') as string,
      contact_phone: formData.get('contact_phone') as string,
      notes: formData.get('notes') as string,
    })
  }

  const deals = data?.deals || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Deals</h1>
          <p className="text-muted-foreground">Manage your sales opportunities</p>
        </div>
        <Dialog open={showNewDeal} onOpenChange={setShowNewDeal}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Deal
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Create New Deal</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateDeal} className="space-y-4">
              <div>
                <Label htmlFor="title">Deal Title</Label>
                <Input id="title" name="title" required placeholder="e.g., 2024 BMW X5 Hail Repair" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="value">Value ($)</Label>
                  <Input id="value" name="value" type="number" placeholder="0" />
                </div>
                <div>
                  <Label htmlFor="stage">Stage</Label>
                  <Select name="stage" defaultValue="LEAD">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STAGES.map(s => (
                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label htmlFor="contact_name">Contact Name</Label>
                <Input id="contact_name" name="contact_name" placeholder="John Smith" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="contact_email">Email</Label>
                  <Input id="contact_email" name="contact_email" type="email" placeholder="john@example.com" />
                </div>
                <div>
                  <Label htmlFor="contact_phone">Phone</Label>
                  <Input id="contact_phone" name="contact_phone" placeholder="(555) 123-4567" />
                </div>
              </div>
              <div>
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" name="notes" placeholder="Additional details..." />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowNewDeal(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create Deal'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search deals..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={stageFilter} onValueChange={setStageFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All Stages" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                {STAGES.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Deals List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : deals.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No deals found</h3>
            <p className="text-muted-foreground">Create your first deal to get started</p>
            <Button className="mt-4" onClick={() => setShowNewDeal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Deal
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {deals.map((deal: Deal) => {
            const stage = STAGES.find(s => s.value === deal.stage)
            return (
              <Card key={deal.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <Link
                        to={`/crm/deals/${deal.id}`}
                        className="text-lg font-semibold hover:text-primary"
                      >
                        {deal.title}
                      </Link>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {deal.contact_name && (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {deal.contact_name}
                          </span>
                        )}
                        {deal.contact_email && (
                          <span className="flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {deal.contact_email}
                          </span>
                        )}
                        {deal.contact_phone && (
                          <span className="flex items-center gap-1">
                            <Phone className="h-3 w-3" />
                            {deal.contact_phone}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-xl font-bold">${deal.value?.toLocaleString() || 0}</p>
                        {deal.expected_close_date && (
                          <p className="text-sm text-muted-foreground flex items-center justify-end gap-1">
                            <Calendar className="h-3 w-3" />
                            {deal.expected_close_date}
                          </p>
                        )}
                      </div>
                      <Badge className={stage?.color}>{stage?.label || deal.stage}</Badge>
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
