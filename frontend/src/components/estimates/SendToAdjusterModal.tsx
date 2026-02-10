/**
 * Send to Adjuster Modal
 *
 * Allows sending estimate package (PDF + Photo Sheet) via email.
 */

import { useState, useEffect } from 'react'
import { Loader2, Send, Mail, AlertCircle, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useSendEstimatePackage } from '@/hooks/use-pdr-estimates'

interface SendToAdjusterModalProps {
  open: boolean
  onClose: () => void
  estimateId: number
  estimateNumber?: string
  vehicleInfo?: string  // e.g., "2024 Ford F-150"
  customerName?: string
}

export function SendToAdjusterModal({
  open,
  onClose,
  estimateId,
  estimateNumber,
  vehicleInfo,
  customerName
}: SendToAdjusterModalProps) {
  const sendPackage = useSendEstimatePackage()

  // Form state
  const [to, setTo] = useState('')
  const [cc, setCc] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')

  // Result state
  const [sendResult, setSendResult] = useState<'success' | 'error' | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  // Generate defaults when modal opens
  useEffect(() => {
    if (open) {
      // Reset form
      setTo('')
      setCc('')
      setSendResult(null)
      setErrorMessage('')

      // Generate default subject
      const estNum = estimateNumber || `EST-${estimateId}`
      const vehicle = vehicleInfo || 'Vehicle'
      setSubject(`Estimate ${estNum} — ${vehicle}`)

      // Generate default message
      setMessage(`Hello,

Please find attached the PDR estimate and photo documentation for:

Vehicle: ${vehicleInfo || 'N/A'}
Estimate #: ${estNum}
${customerName ? `Customer: ${customerName}` : ''}

The attached documents include:
- Detailed estimate with panel breakdown and pricing
- Photo sheet with damage documentation

Please review and let us know if you have any questions.

Thank you`)
    }
  }, [open, estimateId, estimateNumber, vehicleInfo, customerName])

  const handleSend = async () => {
    if (!to.trim()) return

    setSendResult(null)
    setErrorMessage('')

    // Parse CC emails
    const ccList = cc
      .split(',')
      .map(e => e.trim())
      .filter(e => e.length > 0)

    try {
      const result = await sendPackage.mutateAsync({
        estimateId,
        to: to.trim(),
        cc: ccList.length > 0 ? ccList : undefined,
        subject: subject.trim() || undefined,
        message: message.trim() || undefined
      })

      if (result.status === 'sent') {
        setSendResult('success')
        // Auto-close after success
        setTimeout(() => {
          onClose()
        }, 1500)
      } else {
        setSendResult('error')
        setErrorMessage(result.error || 'Failed to send email')
      }
    } catch (error) {
      setSendResult('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to send email')
    }
  }

  const handleClose = () => {
    if (!sendPackage.isPending) {
      onClose()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Send to Adjuster
          </DialogTitle>
        </DialogHeader>

        {sendResult === 'success' ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <CheckCircle className="h-12 w-12 text-green-500" />
            <p className="text-lg font-medium text-green-700">Email Sent Successfully</p>
            <p className="text-sm text-muted-foreground">
              Estimate package sent to {to}
            </p>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {/* To field */}
            <div className="space-y-2">
              <Label htmlFor="to">To (Adjuster Email) *</Label>
              <Input
                id="to"
                type="email"
                placeholder="adjuster@insurance.com"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                disabled={sendPackage.isPending}
              />
            </div>

            {/* CC field */}
            <div className="space-y-2">
              <Label htmlFor="cc">CC (optional)</Label>
              <Input
                id="cc"
                type="text"
                placeholder="manager@shop.com, customer@email.com"
                value={cc}
                onChange={(e) => setCc(e.target.value)}
                disabled={sendPackage.isPending}
              />
              <p className="text-xs text-muted-foreground">
                Separate multiple emails with commas
              </p>
            </div>

            {/* Subject field */}
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                disabled={sendPackage.isPending}
              />
            </div>

            {/* Message field */}
            <div className="space-y-2">
              <Label htmlFor="message">Message</Label>
              <Textarea
                id="message"
                rows={6}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                disabled={sendPackage.isPending}
                className="resize-none"
              />
            </div>

            {/* Attachments info */}
            <div className="bg-muted/50 rounded-md p-3 text-sm">
              <p className="font-medium mb-1">Attachments:</p>
              <ul className="text-muted-foreground space-y-1">
                <li>• Estimate PDF (detailed breakdown)</li>
                <li>• Photo Sheet PDF (damage documentation)</li>
              </ul>
            </div>

            {/* Error message */}
            {sendResult === 'error' && (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-md p-3">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <p className="text-sm">{errorMessage}</p>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {sendResult !== 'success' && (
            <>
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={sendPackage.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSend}
                disabled={!to.trim() || sendPackage.isPending}
              >
                {sendPackage.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Send Email
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

export default SendToAdjusterModal
