/**
 * Create Share Link Modal
 *
 * Modal for generating a shareable link to an estimate.
 * Allows configuration of expiration and permissions.
 */

import { useState, useEffect } from 'react'
import { Loader2, Link2, Copy, Check, ExternalLink, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useCreateShareLink } from '@/hooks/use-pdr-estimates'

interface CreateShareLinkModalProps {
  open: boolean
  onClose: () => void
  estimateId: number
  estimateNumber?: string
  vehicleInfo?: string
}

export function CreateShareLinkModal({
  open,
  onClose,
  estimateId,
  estimateNumber,
  vehicleInfo
}: CreateShareLinkModalProps) {
  const createShareLink = useCreateShareLink()

  // Form state
  const [expiresInDays, setExpiresInDays] = useState(14)
  const [allowPhotosheet, setAllowPhotosheet] = useState(true)
  const [allowDisputePack, setAllowDisputePack] = useState(true)
  const [allowSupplements, setAllowSupplements] = useState(true)

  // Result state
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setExpiresInDays(14)
      setAllowPhotosheet(true)
      setAllowDisputePack(true)
      setAllowSupplements(true)
      setShareUrl(null)
      setExpiresAt(null)
      setCopied(false)
    }
  }, [open])

  const handleCreate = async () => {
    try {
      const result = await createShareLink.mutateAsync({
        estimateId,
        expiresInDays,
        allowPhotosheet,
        allowDisputePack,
        allowSupplements
      })

      setShareUrl(result.url)
      setExpiresAt(result.expires_at)
    } catch (error) {
      console.error('Failed to create share link:', error)
    }
  }

  const handleCopy = async () => {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.error('Copy failed:', e)
    }
  }

  const handleOpenLink = () => {
    if (shareUrl) {
      window.open(shareUrl, '_blank')
    }
  }

  const handleClose = () => {
    if (!createShareLink.isPending) {
      onClose()
    }
  }

  const expiresDate = expiresAt ? new Date(expiresAt) : null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            Create Share Link
          </DialogTitle>
        </DialogHeader>

        {shareUrl ? (
          // Success state - show the link
          <div className="py-4 space-y-4">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-3">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <p className="font-medium text-lg mb-1">Share Link Created</p>
              {estimateNumber && (
                <p className="text-sm text-muted-foreground">
                  {estimateNumber} - {vehicleInfo}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Share URL</Label>
              <div className="flex gap-2">
                <Input
                  value={shareUrl}
                  readOnly
                  className="font-mono text-xs"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleCopy}
                  title="Copy to clipboard"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {expiresDate && (
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Expires {expiresDate.toLocaleDateString()} at{' '}
                {expiresDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
              </p>
            )}

            <div className="flex gap-2 pt-2">
              <Button variant="outline" className="flex-1" onClick={handleOpenLink}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Open Link
              </Button>
              <Button className="flex-1" onClick={handleCopy}>
                {copied ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy Link
                  </>
                )}
              </Button>
            </div>
          </div>
        ) : (
          // Form state
          <div className="py-4 space-y-4">
            {/* Expiration */}
            <div className="space-y-2">
              <Label htmlFor="expires">Link Expiration (days)</Label>
              <Input
                id="expires"
                type="number"
                min={1}
                max={90}
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(parseInt(e.target.value) || 14)}
                className="w-32"
              />
              <p className="text-xs text-muted-foreground">
                Link will expire after {expiresInDays} day{expiresInDays !== 1 ? 's' : ''}
              </p>
            </div>

            {/* Permissions */}
            <div className="space-y-3">
              <Label>Permissions</Label>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Estimate PDF</p>
                  <p className="text-xs text-muted-foreground">Always included</p>
                </div>
                <Switch checked disabled />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Photo Sheet</p>
                  <p className="text-xs text-muted-foreground">Photo documentation PDF</p>
                </div>
                <Switch
                  checked={allowPhotosheet}
                  onCheckedChange={setAllowPhotosheet}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Dispute Pack</p>
                  <p className="text-xs text-muted-foreground">Complete ZIP bundle</p>
                </div>
                <Switch
                  checked={allowDisputePack}
                  onCheckedChange={setAllowDisputePack}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Supplements</p>
                  <p className="text-xs text-muted-foreground">Supplement PDFs if any</p>
                </div>
                <Switch
                  checked={allowSupplements}
                  onCheckedChange={setAllowSupplements}
                />
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          {shareUrl ? (
            <Button variant="outline" onClick={handleClose}>
              Done
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={createShareLink.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={createShareLink.isPending}
              >
                {createShareLink.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Link2 className="h-4 w-4 mr-2" />
                    Create Link
                  </>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default CreateShareLinkModal
