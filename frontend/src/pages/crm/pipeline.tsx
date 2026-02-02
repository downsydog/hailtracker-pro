import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { crmApi, Deal, PipelineStage } from '@/api/crm'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DollarSign,
  User,
  ChevronRight,
  GripVertical,
} from 'lucide-react'

const STAGES = [
  { value: 'LEAD', label: 'Lead', color: 'bg-gray-100 border-gray-300' },
  { value: 'CONTACTED', label: 'Contacted', color: 'bg-blue-50 border-blue-300' },
  { value: 'QUALIFIED', label: 'Qualified', color: 'bg-yellow-50 border-yellow-300' },
  { value: 'PROPOSAL', label: 'Proposal', color: 'bg-purple-50 border-purple-300' },
  { value: 'NEGOTIATION', label: 'Negotiation', color: 'bg-orange-50 border-orange-300' },
  { value: 'CLOSED_WON', label: 'Won', color: 'bg-green-50 border-green-300' },
  { value: 'CLOSED_LOST', label: 'Lost', color: 'bg-red-50 border-red-300' },
]

export function CRMPipelinePage() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['crm-pipeline'],
    queryFn: crmApi.getPipeline,
  })

  const updateStageMutation = useMutation({
    mutationFn: ({ dealId, stage }: { dealId: number; stage: string }) =>
      crmApi.updateDealStage(dealId, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm-pipeline'] })
    },
  })

  const pipeline = data?.pipeline || []

  // Group deals by stage
  const dealsByStage = React.useMemo(() => {
    const grouped: Record<string, Deal[]> = {}
    STAGES.forEach(s => {
      grouped[s.value] = []
    })

    pipeline.forEach((stage: PipelineStage) => {
      if (grouped[stage.stage]) {
        grouped[stage.stage] = stage.deals || []
      }
    })

    return grouped
  }, [pipeline])

  // Calculate stage totals
  const stageTotals = React.useMemo(() => {
    const totals: Record<string, { count: number; value: number }> = {}
    STAGES.forEach(s => {
      const deals = dealsByStage[s.value] || []
      totals[s.value] = {
        count: deals.length,
        value: deals.reduce((sum, d) => sum + (d.value || 0), 0),
      }
    })
    return totals
  }, [dealsByStage])

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
          <h1 className="text-2xl font-bold">Sales Pipeline</h1>
          <p className="text-muted-foreground">Drag and drop deals between stages</p>
        </div>
        <Button asChild>
          <Link to="/crm/deals/new">New Deal</Link>
        </Button>
      </div>

      {/* Pipeline Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map(stage => {
          const deals = dealsByStage[stage.value] || []
          const totals = stageTotals[stage.value]

          return (
            <div key={stage.value} className="flex-shrink-0 w-72">
              <Card className={`${stage.color} border-2`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center justify-between">
                    <span>{stage.label}</span>
                    <Badge variant="secondary">{totals.count}</Badge>
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">
                    ${totals.value.toLocaleString()} total
                  </p>
                </CardHeader>
                <CardContent className="space-y-2 min-h-[400px]">
                  {deals.map((deal: Deal) => (
                    <Card
                      key={deal.id}
                      className="bg-white cursor-pointer hover:shadow-md transition-shadow"
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData('dealId', deal.id.toString())
                      }}
                    >
                      <CardContent className="p-3">
                        <div className="flex items-start gap-2">
                          <GripVertical className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                          <div className="flex-1 min-w-0">
                            <Link
                              to={`/crm/deals/${deal.id}`}
                              className="font-medium text-sm hover:text-primary truncate block"
                            >
                              {deal.title}
                            </Link>
                            {deal.contact_name && (
                              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                                <User className="h-3 w-3" />
                                {deal.contact_name}
                              </p>
                            )}
                            <p className="text-sm font-semibold mt-2 flex items-center gap-1">
                              <DollarSign className="h-3 w-3" />
                              {deal.value?.toLocaleString() || 0}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}

                  {/* Drop Zone */}
                  <div
                    className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center text-sm text-muted-foreground min-h-[60px] flex items-center justify-center"
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.currentTarget.classList.add('border-primary', 'bg-primary/5')
                    }}
                    onDragLeave={(e) => {
                      e.currentTarget.classList.remove('border-primary', 'bg-primary/5')
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      e.currentTarget.classList.remove('border-primary', 'bg-primary/5')
                      const dealId = parseInt(e.dataTransfer.getData('dealId'))
                      if (dealId) {
                        updateStageMutation.mutate({ dealId, stage: stage.value })
                      }
                    }}
                  >
                    Drop here
                  </div>
                </CardContent>
              </Card>
            </div>
          )
        })}
      </div>

      {/* Stage Navigation (for mobile) */}
      <div className="md:hidden flex overflow-x-auto gap-2 pb-2">
        {STAGES.map((stage, index) => (
          <React.Fragment key={stage.value}>
            <Badge variant="outline" className="flex-shrink-0">
              {stage.label} ({stageTotals[stage.value].count})
            </Badge>
            {index < STAGES.length - 1 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}
