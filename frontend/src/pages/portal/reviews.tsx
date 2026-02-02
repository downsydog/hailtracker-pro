import * as React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portalApi, Review, PendingReview } from '@/api/portal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Star,
  MessageSquare,
  ThumbsUp,
  AlertCircle,
} from 'lucide-react'

export function PortalReviewsPage() {
  const [selectedJob, setSelectedJob] = React.useState<PendingReview | null>(null)
  const [rating, setRating] = React.useState(5)
  const [hoverRating, setHoverRating] = React.useState(0)
  const [comment, setComment] = React.useState('')
  const [wouldRecommend, setWouldRecommend] = React.useState(true)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['portal-reviews'],
    queryFn: portalApi.getReviews,
  })

  const submitMutation = useMutation({
    mutationFn: ({ jobId, data }: { jobId: number; data: { rating: number; comment?: string; would_recommend: boolean } }) =>
      portalApi.submitReview(jobId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portal-reviews'] })
      setSelectedJob(null)
      setRating(5)
      setComment('')
      setWouldRecommend(true)
    },
  })

  const handleSubmitReview = () => {
    if (selectedJob) {
      submitMutation.mutate({
        jobId: selectedJob.job_id,
        data: {
          rating,
          comment: comment || undefined,
          would_recommend: wouldRecommend,
        },
      })
    }
  }

  const reviews = data?.reviews || []
  const pendingReviews = data?.pending_reviews || []

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
        <h1 className="text-2xl font-bold">Reviews</h1>
        <p className="text-muted-foreground">Share your experience and help others</p>
      </div>

      {/* Pending Reviews */}
      {pendingReviews.length > 0 && (
        <>
          <Card className="border-yellow-200 bg-yellow-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-yellow-800">
                <AlertCircle className="h-5 w-5" />
                Reviews Needed ({pendingReviews.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-yellow-700 mb-4">
                Your feedback helps us improve! Earn 50 loyalty points for each review.
              </p>
              <div className="space-y-3">
                {pendingReviews.map((pending: PendingReview) => (
                  <div
                    key={pending.job_id}
                    className="flex items-center justify-between p-3 bg-white rounded-lg"
                  >
                    <div>
                      <p className="font-medium">{pending.vehicle}</p>
                      <p className="text-sm text-muted-foreground">
                        Job #{pending.job_number} - Completed {pending.completed_at}
                      </p>
                    </div>
                    <Button onClick={() => setSelectedJob(pending)}>
                      <Star className="h-4 w-4 mr-2" />
                      Leave Review
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Past Reviews */}
      <h2 className="text-lg font-semibold">Your Reviews</h2>
      {reviews.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No reviews yet</h3>
            <p className="text-muted-foreground">Complete a service to leave a review</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {reviews.map((review: Review) => (
            <Card key={review.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={`h-5 w-5 ${
                          star <= review.rating
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    {review.would_recommend && (
                      <Badge variant="outline" className="text-green-600">
                        <ThumbsUp className="h-3 w-3 mr-1" />
                        Recommends
                      </Badge>
                    )}
                    <span className="text-sm text-muted-foreground">{review.created_at}</span>
                  </div>
                </div>

                {review.comment && (
                  <p className="text-muted-foreground mb-3">{review.comment}</p>
                )}

                {review.response && (
                  <div className="bg-muted p-3 rounded-lg mt-3">
                    <p className="text-sm font-medium mb-1">Business Response:</p>
                    <p className="text-sm text-muted-foreground">{review.response}</p>
                    {review.response_at && (
                      <p className="text-xs text-muted-foreground mt-1">{review.response_at}</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Review Dialog */}
      <Dialog open={!!selectedJob} onOpenChange={() => setSelectedJob(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Leave a Review</DialogTitle>
          </DialogHeader>

          {selectedJob && (
            <div className="space-y-6">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">{selectedJob.vehicle}</p>
                <p className="text-sm text-muted-foreground">Job #{selectedJob.job_number}</p>
              </div>

              {/* Star Rating */}
              <div>
                <Label>Your Rating</Label>
                <div className="flex items-center gap-2 mt-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      className="focus:outline-none"
                      onMouseEnter={() => setHoverRating(star)}
                      onMouseLeave={() => setHoverRating(0)}
                      onClick={() => setRating(star)}
                    >
                      <Star
                        className={`h-8 w-8 transition-colors ${
                          star <= (hoverRating || rating)
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-300 hover:text-yellow-200'
                        }`}
                      />
                    </button>
                  ))}
                  <span className="ml-2 text-lg font-medium">{rating}/5</span>
                </div>
              </div>

              {/* Comment */}
              <div>
                <Label htmlFor="comment">Your Feedback (Optional)</Label>
                <Textarea
                  id="comment"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Tell us about your experience..."
                  className="mt-2"
                  rows={4}
                />
              </div>

              {/* Would Recommend */}
              <div className="flex items-center justify-between">
                <div>
                  <Label>Would you recommend us?</Label>
                  <p className="text-sm text-muted-foreground">To friends and family</p>
                </div>
                <Switch
                  checked={wouldRecommend}
                  onCheckedChange={setWouldRecommend}
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setSelectedJob(null)}>
                  Cancel
                </Button>
                <Button onClick={handleSubmitReview} disabled={submitMutation.isPending}>
                  {submitMutation.isPending ? 'Submitting...' : 'Submit Review'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
