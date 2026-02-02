import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portalApi, DigitalFlyer, PersonalizedFlyer, FlyerAnalytics } from '@/api/portal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  FileImage,
  Download,
  Share2,
  Eye,
  MousePointer,
  TrendingUp,
  Copy,
  Check,
  ExternalLink,
} from 'lucide-react'

const FLYER_TYPE_COLORS: Record<string, string> = {
  HAIL_EVENT: 'bg-blue-500',
  SEASONAL: 'bg-green-500',
  PROMOTION: 'bg-purple-500',
}

export function PortalFlyersPage() {
  const [copiedId, setCopiedId] = React.useState<number | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['portal-flyers'],
    queryFn: portalApi.getFlyers,
  })

  const { data: analytics } = useQuery({
    queryKey: ['portal-flyer-analytics'],
    queryFn: portalApi.getFlyerAnalytics,
  })

  const generateMutation = useMutation({
    mutationFn: portalApi.generateFlyer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-flyers'] })
    },
  })

  const handleCopyLink = (flyerUrl: string, id: number) => {
    navigator.clipboard.writeText(flyerUrl)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const flyers = data?.flyers || []
  const personalizedFlyers = data?.personalized || []
  const stats: FlyerAnalytics = analytics || {
    total_views: 0,
    total_clicks: 0,
    flyers_shared: 0,
    leads_generated: 0,
    by_flyer: [],
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
        <h1 className="text-2xl font-bold">Digital Flyers</h1>
        <p className="text-muted-foreground">Share personalized flyers to earn referral rewards</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Flyers Shared</CardTitle>
            <Share2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.flyers_shared}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Views</CardTitle>
            <Eye className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_views}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Clicks</CardTitle>
            <MousePointer className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_clicks}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Leads Generated</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.leads_generated}</div>
          </CardContent>
        </Card>
      </div>

      {/* Your Personalized Flyers */}
      {personalizedFlyers.length > 0 && (
        <>
          <h2 className="text-lg font-semibold">Your Personalized Flyers</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {personalizedFlyers.map((flyer: PersonalizedFlyer) => (
              <Card key={flyer.id}>
                <CardContent className="p-4">
                  <div className="aspect-[3/4] bg-gray-100 rounded-lg mb-4 flex items-center justify-center">
                    <img
                      src={flyer.flyer_url}
                      alt="Flyer preview"
                      className="max-w-full max-h-full object-contain rounded-lg"
                      onError={(e) => {
                        e.currentTarget.src = ''
                        e.currentTarget.parentElement!.innerHTML = '<div class="text-muted-foreground">Preview not available</div>'
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-sm text-muted-foreground mb-3">
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {flyer.views} views
                    </span>
                    <span className="flex items-center gap-1">
                      <MousePointer className="h-3 w-3" />
                      {flyer.clicks} clicks
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleCopyLink(flyer.flyer_url, flyer.id)}
                    >
                      {copiedId === flyer.id ? <Check className="h-4 w-4 mr-1" /> : <Copy className="h-4 w-4 mr-1" />}
                      {copiedId === flyer.id ? 'Copied!' : 'Copy Link'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(flyer.flyer_url, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Available Flyer Templates */}
      <h2 className="text-lg font-semibold">Available Flyer Templates</h2>
      {flyers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileImage className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No flyers available</h3>
            <p className="text-muted-foreground">Check back later for new flyer templates</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {flyers.map((flyer: DigitalFlyer) => (
            <Card key={flyer.id} className="overflow-hidden">
              <div className="aspect-[3/4] bg-gray-100 flex items-center justify-center">
                {flyer.thumbnail_url ? (
                  <img
                    src={flyer.thumbnail_url}
                    alt={flyer.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <FileImage className="h-16 w-16 text-muted-foreground" />
                )}
              </div>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium">{flyer.name}</h3>
                  <Badge className={FLYER_TYPE_COLORS[flyer.type]}>{flyer.type}</Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-4">{flyer.description}</p>
                <Button
                  className="w-full"
                  onClick={() => generateMutation.mutate(flyer.id)}
                  disabled={generateMutation.isPending}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {generateMutation.isPending ? 'Generating...' : 'Generate My Flyer'}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
