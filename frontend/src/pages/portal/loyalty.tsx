import * as React from 'react'
import { useQuery } from '@tanstack/react-query'
import { portalApi, LoyaltyData, LoyaltyReward, PointHistory } from '@/api/portal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Star,
  Gift,
  Trophy,
  TrendingUp,
  Clock,
  Check,
  Sparkles,
} from 'lucide-react'

const TIER_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  BRONZE: { bg: 'bg-amber-100', text: 'text-amber-700', icon: 'text-amber-500' },
  SILVER: { bg: 'bg-gray-100', text: 'text-gray-700', icon: 'text-gray-500' },
  GOLD: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: 'text-yellow-500' },
  PLATINUM: { bg: 'bg-purple-100', text: 'text-purple-700', icon: 'text-purple-500' },
}

const POINT_TYPE_ICONS: Record<string, React.ReactNode> = {
  EARNED: <TrendingUp className="h-4 w-4 text-green-500" />,
  REDEEMED: <Gift className="h-4 w-4 text-blue-500" />,
  BONUS: <Sparkles className="h-4 w-4 text-purple-500" />,
}

export function PortalLoyaltyPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['portal-loyalty'],
    queryFn: portalApi.getLoyalty,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const loyalty: LoyaltyData = data || {
    points: 0,
    tier: 'BRONZE',
    tier_progress: 0,
    next_tier_points: 500,
    lifetime_points: 0,
    available_rewards: [],
    point_history: [],
  }

  const tierStyle = TIER_COLORS[loyalty.tier] || TIER_COLORS.BRONZE

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Loyalty Rewards</h1>
        <p className="text-muted-foreground">Earn points and redeem rewards</p>
      </div>

      {/* Points & Tier Card */}
      <Card className={`${tierStyle.bg} border-2`}>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Trophy className={`h-8 w-8 ${tierStyle.icon}`} />
                <div>
                  <p className={`text-sm font-medium ${tierStyle.text}`}>{loyalty.tier} Member</p>
                  <p className="text-3xl font-bold">{loyalty.points.toLocaleString()} pts</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Lifetime: {loyalty.lifetime_points.toLocaleString()} points earned
              </p>
            </div>
            <div className="text-right">
              <Star className={`h-16 w-16 ${tierStyle.icon}`} />
            </div>
          </div>

          {/* Tier Progress */}
          {loyalty.tier !== 'PLATINUM' && (
            <div className="mt-6">
              <div className="flex justify-between text-sm mb-2">
                <span>Progress to next tier</span>
                <span>{loyalty.next_tier_points - loyalty.points} points to go</span>
              </div>
              <Progress value={loyalty.tier_progress} className="h-2" />
            </div>
          )}
        </CardContent>
      </Card>

      {/* How to Earn */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            How to Earn Points
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-start gap-3 p-4 bg-green-50 rounded-lg">
              <Check className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium">Complete a Repair</p>
                <p className="text-sm text-muted-foreground">Earn 100 pts per service</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 bg-blue-50 rounded-lg">
              <Gift className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <p className="font-medium">Refer a Friend</p>
                <p className="text-sm text-muted-foreground">Earn 250 pts per referral</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 bg-purple-50 rounded-lg">
              <Star className="h-5 w-5 text-purple-600 mt-0.5" />
              <div>
                <p className="font-medium">Leave a Review</p>
                <p className="text-sm text-muted-foreground">Earn 50 pts per review</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Available Rewards */}
      <h2 className="text-lg font-semibold">Available Rewards</h2>
      {loyalty.available_rewards.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Gift className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No rewards available</h3>
            <p className="text-muted-foreground">Earn more points to unlock rewards</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {loyalty.available_rewards.map((reward: LoyaltyReward) => {
            const canRedeem = loyalty.points >= reward.points_required
            return (
              <Card key={reward.id} className={!canRedeem ? 'opacity-60' : ''}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <Gift className="h-8 w-8 text-primary" />
                    <Badge variant="outline">{reward.type}</Badge>
                  </div>
                  <h3 className="font-medium mb-1">{reward.name}</h3>
                  <p className="text-sm text-muted-foreground mb-4">{reward.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="font-bold">{reward.points_required} pts</span>
                    <Button disabled={!canRedeem} size="sm">
                      {canRedeem ? 'Redeem' : 'Not Enough Points'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Points History */}
      <h2 className="text-lg font-semibold">Points History</h2>
      {loyalty.point_history.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <Clock className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-muted-foreground">No point history yet</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {loyalty.point_history.map((entry: PointHistory) => (
                <div key={entry.id} className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    {POINT_TYPE_ICONS[entry.type]}
                    <div>
                      <p className="font-medium">{entry.description}</p>
                      <p className="text-sm text-muted-foreground">{entry.created_at}</p>
                    </div>
                  </div>
                  <span className={`font-bold ${entry.points > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.points > 0 ? '+' : ''}{entry.points} pts
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
