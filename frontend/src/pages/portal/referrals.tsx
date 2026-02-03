import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portalApi, Referral, ReferralStats } from '@/api/portal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Users,
  Share2,
  DollarSign,
  Copy,
  Check,
  Gift,
  TrendingUp,
  UserPlus,
  Mail,
  Phone,
} from 'lucide-react'

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'bg-yellow-500',
  CONTACTED: 'bg-blue-500',
  CONVERTED: 'bg-green-500',
  EXPIRED: 'bg-gray-500',
}

export function PortalReferralsPage() {
  const [showNewReferral, setShowNewReferral] = React.useState(false)
  const [copied, setCopied] = React.useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['portal-referrals'],
    queryFn: portalApi.getReferrals,
  })

  const createMutation = useMutation({
    mutationFn: portalApi.createReferral,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-referrals'] })
      setShowNewReferral(false)
    },
  })

  const handleCreateReferral = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    createMutation.mutate({
      referred_name: formData.get('name') as string,
      referred_email: formData.get('email') as string || undefined,
      referred_phone: formData.get('phone') as string || undefined,
      notes: formData.get('notes') as string || undefined,
    })
  }

  const handleCopyLink = () => {
    if (data?.stats?.share_url) {
      navigator.clipboard.writeText(data.stats.share_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const referrals = data?.referrals || []
  const stats: ReferralStats = data?.stats || {
    total_referrals: 0,
    converted_referrals: 0,
    pending_rewards: 0,
    total_earned: 0,
    conversion_rate: 0,
    share_url: '',
    referral_code: '',
  }

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
      <div>
        <h1 className="text-2xl font-bold">Referral Program</h1>
        <p className="text-muted-foreground">Earn rewards by referring friends and family</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Referrals</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_referrals}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Converted</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.converted_referrals}</div>
            <p className="text-xs text-muted-foreground">{stats.conversion_rate}% rate</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Rewards</CardTitle>
            <Gift className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">${stats.pending_rewards}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Earned</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${stats.total_earned}</div>
          </CardContent>
        </Card>
      </div>

      {/* Share Link */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            Your Referral Link
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={stats.share_url || 'Loading...'}
              readOnly
              className="font-mono text-sm"
            />
            <Button onClick={handleCopyLink} variant="outline">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Share this link with friends. When they complete a repair, you both earn rewards!
          </p>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Your Referrals</h2>
        <Dialog open={showNewReferral} onOpenChange={setShowNewReferral}>
          <DialogTrigger asChild>
            <Button>
              <UserPlus className="h-4 w-4 mr-2" />
              Refer Someone
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Refer a Friend</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateReferral} className="space-y-4">
              <div>
                <Label htmlFor="name">Name *</Label>
                <Input id="name" name="name" required placeholder="John Smith" />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" name="email" type="email" placeholder="john@example.com" />
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input id="phone" name="phone" placeholder="(555) 123-4567" />
              </div>
              <div>
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" name="notes" placeholder="How do you know them?" />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setShowNewReferral(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Submitting...' : 'Submit Referral'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Referrals List */}
      {referrals.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No referrals yet</h3>
            <p className="text-muted-foreground">Share your link or submit a referral to get started</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {referrals.map((referral: Referral) => (
            <Card key={referral.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="font-medium">{referral.referred_name}</p>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      {referral.referred_email && (
                        <span className="flex items-center gap-1">
                          <Mail className="h-3 w-3" />
                          {referral.referred_email}
                        </span>
                      )}
                      {referral.referred_phone && (
                        <span className="flex items-center gap-1">
                          <Phone className="h-3 w-3" />
                          {referral.referred_phone}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {referral.reward_amount && referral.reward_status === 'APPROVED' && (
                      <span className="text-green-600 font-medium">${referral.reward_amount} earned</span>
                    )}
                    <Badge className={STATUS_COLORS[referral.status]}>{referral.status}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
