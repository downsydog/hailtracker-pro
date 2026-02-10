/**
 * Shared Estimate Portal Page
 *
 * Public page for viewing and downloading shared estimate documents.
 * Accessed via share token - no authentication required.
 * Supports customer signature capture when signing permission is enabled.
 */

import { useState, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  FileText,
  Image,
  Archive,
  Download,
  Loader2,
  AlertCircle,
  Clock,
  Car,
  CheckCircle,
  PenLine
} from 'lucide-react'
import {
  useSharedEstimate,
  downloadSharedEstimatePDF,
  downloadSharedPhotoSheet,
  downloadSharedDisputePack,
  downloadSharedSupplementPDF,
  useSignEstimateViaPortal
} from '@/hooks/use-pdr-estimates'
import { SignatureCapture, SignatureDisplay, SignatureCaptureRef } from '@/components/estimates'

export function SharedEstimate() {
  const { token } = useParams<{ token: string }>()
  const { data, isLoading, error, refetch } = useSharedEstimate(token || null)
  const signMutation = useSignEstimateViaPortal()

  // Signature capture ref
  const signatureRef = useRef<SignatureCaptureRef>(null)

  // Download states
  const [downloadingPDF, setDownloadingPDF] = useState(false)
  const [downloadingPhotoSheet, setDownloadingPhotoSheet] = useState(false)
  const [downloadingDisputePack, setDownloadingDisputePack] = useState(false)
  const [downloadingSupplements, setDownloadingSupplements] = useState<Set<number>>(new Set())
  const [downloadError, setDownloadError] = useState<string | null>(null)

  // Signature states
  const [signedByName, setSignedByName] = useState('')
  const [signatureError, setSignatureError] = useState<string | null>(null)
  const [signatureSuccess, setSignatureSuccess] = useState(false)

  const handleSubmitSignature = async () => {
    if (!token || !signatureRef.current) return

    // Validate name
    if (!signedByName.trim()) {
      setSignatureError('Please enter your name')
      return
    }

    // Validate signature
    if (signatureRef.current.isEmpty()) {
      setSignatureError('Please sign above before submitting')
      return
    }

    const signatureBase64 = signatureRef.current.toDataURL()
    if (!signatureBase64) {
      setSignatureError('Failed to capture signature')
      return
    }

    setSignatureError(null)

    try {
      await signMutation.mutateAsync({
        token,
        signatureBase64,
        signedByName: signedByName.trim()
      })
      setSignatureSuccess(true)
      // Refetch to get updated status
      refetch()
    } catch (e) {
      setSignatureError(e instanceof Error ? e.message : 'Signing failed')
    }
  }

  const handleDownloadPDF = async () => {
    if (!token) return
    setDownloadingPDF(true)
    setDownloadError(null)
    try {
      await downloadSharedEstimatePDF(token)
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setDownloadingPDF(false)
    }
  }

  const handleDownloadPhotoSheet = async () => {
    if (!token) return
    setDownloadingPhotoSheet(true)
    setDownloadError(null)
    try {
      await downloadSharedPhotoSheet(token)
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setDownloadingPhotoSheet(false)
    }
  }

  const handleDownloadDisputePack = async () => {
    if (!token) return
    setDownloadingDisputePack(true)
    setDownloadError(null)
    try {
      await downloadSharedDisputePack(token)
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setDownloadingDisputePack(false)
    }
  }

  const handleDownloadSupplement = async (supplementId: number) => {
    if (!token) return
    setDownloadingSupplements(prev => new Set(prev).add(supplementId))
    setDownloadError(null)
    try {
      await downloadSharedSupplementPDF(token, supplementId)
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : 'Download failed')
    } finally {
      setDownloadingSupplements(prev => {
        const next = new Set(prev)
        next.delete(supplementId)
        return next
      })
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-4" />
          <p className="text-muted-foreground">Loading estimate...</p>
        </div>
      </div>
    )
  }

  // Error state (expired or invalid token)
  if (error) {
    const isExpired = error.message.toLowerCase().includes('expired')
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-8 pb-8 text-center">
            <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
              isExpired ? 'bg-amber-100' : 'bg-red-100'
            }`}>
              {isExpired ? (
                <Clock className="h-8 w-8 text-amber-600" />
              ) : (
                <AlertCircle className="h-8 w-8 text-red-600" />
              )}
            </div>
            <h2 className="text-xl font-bold mb-2">
              {isExpired ? 'Link Expired' : 'Invalid Link'}
            </h2>
            <p className="text-muted-foreground mb-6">
              {isExpired
                ? 'This share link has expired. Please request a new link from the estimate owner.'
                : 'This share link is invalid or has been revoked.'}
            </p>
            <p className="text-sm text-muted-foreground">
              If you believe this is an error, please contact the person who shared this link.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const { estimate, permissions, supplements, expires_at } = data
  const expiresDate = new Date(expires_at)
  const vehicleInfo = `${estimate.vehicle_year} ${estimate.vehicle_make} ${estimate.vehicle_model}`

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
              <Car className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Estimate {estimate.estimate_number}</h1>
              <p className="text-muted-foreground">{vehicleInfo}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        {/* Download error */}
        {downloadError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
            <p className="text-red-700">{downloadError}</p>
            <button
              onClick={() => setDownloadError(null)}
              className="ml-auto text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Main Downloads */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Available Downloads</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Estimate PDF */}
            {permissions.estimate_pdf && (
              <Button
                variant="outline"
                className="w-full justify-start h-auto py-4"
                onClick={handleDownloadPDF}
                disabled={downloadingPDF}
              >
                {downloadingPDF ? (
                  <Loader2 className="h-5 w-5 mr-3 animate-spin" />
                ) : (
                  <FileText className="h-5 w-5 mr-3 text-blue-600" />
                )}
                <div className="text-left">
                  <div className="font-medium">Estimate PDF</div>
                  <div className="text-sm text-muted-foreground">
                    Complete estimate with panel details and pricing
                  </div>
                </div>
                <Download className="h-4 w-4 ml-auto" />
              </Button>
            )}

            {/* Photo Sheet */}
            {permissions.photosheet && (
              <Button
                variant="outline"
                className="w-full justify-start h-auto py-4"
                onClick={handleDownloadPhotoSheet}
                disabled={downloadingPhotoSheet}
              >
                {downloadingPhotoSheet ? (
                  <Loader2 className="h-5 w-5 mr-3 animate-spin" />
                ) : (
                  <Image className="h-5 w-5 mr-3 text-green-600" />
                )}
                <div className="text-left">
                  <div className="font-medium">Photo Sheet</div>
                  <div className="text-sm text-muted-foreground">
                    Photo documentation of damage
                  </div>
                </div>
                <Download className="h-4 w-4 ml-auto" />
              </Button>
            )}

            {/* Dispute Pack */}
            {permissions.dispute_pack && (
              <Button
                variant="outline"
                className="w-full justify-start h-auto py-4"
                onClick={handleDownloadDisputePack}
                disabled={downloadingDisputePack}
              >
                {downloadingDisputePack ? (
                  <Loader2 className="h-5 w-5 mr-3 animate-spin" />
                ) : (
                  <Archive className="h-5 w-5 mr-3 text-purple-600" />
                )}
                <div className="text-left">
                  <div className="font-medium">Dispute Pack (ZIP)</div>
                  <div className="text-sm text-muted-foreground">
                    Complete bundle with all documents
                  </div>
                </div>
                <Download className="h-4 w-4 ml-auto" />
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Customer Authorization Section */}
        {permissions.signing && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <PenLine className="h-5 w-5" />
                Customer Authorization
              </CardTitle>
              <CardDescription>
                {estimate.is_customer_authorized
                  ? 'You have authorized this estimate'
                  : 'Please review the estimate and sign below to authorize repairs'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Already authorized */}
              {estimate.is_customer_authorized ? (
                <SignatureDisplay
                  signedByName={estimate.signed_by_name || undefined}
                  signedAt={estimate.signed_at || undefined}
                />
              ) : signatureSuccess ? (
                /* Just authorized successfully */
                <div className="p-6 bg-green-50 border border-green-200 rounded-lg text-center">
                  <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-3" />
                  <h3 className="font-semibold text-green-800 mb-1">Thank You!</h3>
                  <p className="text-green-700">
                    Your authorization has been recorded successfully.
                  </p>
                </div>
              ) : (
                /* Signature capture form */
                <div className="space-y-4">
                  {/* Signature error */}
                  {signatureError && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                      <p className="text-sm text-red-700">{signatureError}</p>
                    </div>
                  )}

                  {/* Name input */}
                  <div>
                    <Label htmlFor="signed-by-name">Full Name</Label>
                    <Input
                      id="signed-by-name"
                      type="text"
                      placeholder="Enter your full name"
                      value={signedByName}
                      onChange={(e) => setSignedByName(e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  {/* Signature pad */}
                  <div>
                    <Label>Signature</Label>
                    <div className="mt-1">
                      <SignatureCapture
                        ref={signatureRef}
                        width={360}
                        height={150}
                        placeholder="Sign here"
                      />
                    </div>
                  </div>

                  {/* Submit button */}
                  <Button
                    onClick={handleSubmitSignature}
                    disabled={signMutation.isPending}
                    className="w-full"
                  >
                    {signMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Authorizing...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Authorize Repairs
                      </>
                    )}
                  </Button>

                  <p className="text-xs text-muted-foreground text-center">
                    By signing, you authorize the repair work described in this estimate.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Supplements */}
        {permissions.supplements && supplements.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Supplements</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {supplements.map((supp) => {
                const isDownloading = downloadingSupplements.has(supp.id)
                const createdDate = supp.created_at
                  ? new Date(supp.created_at).toLocaleDateString()
                  : 'Unknown'

                return (
                  <Button
                    key={supp.id}
                    variant="outline"
                    className="w-full justify-start h-auto py-4"
                    onClick={() => handleDownloadSupplement(supp.id)}
                    disabled={isDownloading}
                  >
                    {isDownloading ? (
                      <Loader2 className="h-5 w-5 mr-3 animate-spin" />
                    ) : (
                      <FileText className="h-5 w-5 mr-3 text-orange-600" />
                    )}
                    <div className="text-left flex-1">
                      <div className="font-medium flex items-center gap-2">
                        Supplement #{supp.supplement_number}
                        {supp.status === 'approved' && (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {createdDate}
                        {supp.delta_amount !== null && (
                          <span className="ml-2 text-orange-600 font-medium">
                            +${supp.delta_amount.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                    <Download className="h-4 w-4" />
                  </Button>
                )
              })}
            </CardContent>
          </Card>
        )}

        {/* Expiration notice */}
        <div className="text-center text-sm text-muted-foreground">
          <Clock className="h-4 w-4 inline-block mr-1" />
          This link expires on {expiresDate.toLocaleDateString()} at{' '}
          {expiresDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-12 py-6 text-center text-sm text-muted-foreground">
        Powered by HailTracker Pro
      </footer>
    </div>
  )
}

export default SharedEstimate
