/**
 * Insurer Approval Modal
 *
 * Modal for recording insurer approval with partial approval support.
 * Captures approved amount, optional breakdown, and notes.
 */

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { Loader2, Lock, ChevronDown, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface InsurerApprovalModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (data: InsurerApprovalData) => Promise<void>
  estimateNumber: string
  requestedTotal: number
  isLoading?: boolean
}

export interface InsurerApprovalData {
  approved_total: number
  approved_labor?: number
  approved_ri?: number
  approved_materials?: number
  approved_tax?: number
  notes?: string
  reference?: string
}

export function InsurerApprovalModal({
  open,
  onOpenChange,
  onConfirm,
  estimateNumber,
  requestedTotal,
  isLoading = false
}: InsurerApprovalModalProps) {
  const [approvedTotal, setApprovedTotal] = useState(requestedTotal.toFixed(2))
  const [approvedLabor, setApprovedLabor] = useState('')
  const [approvedRi, setApprovedRi] = useState('')
  const [approvedMaterials, setApprovedMaterials] = useState('')
  const [approvedTax, setApprovedTax] = useState('')
  const [notes, setNotes] = useState('')
  const [reference, setReference] = useState('')
  const [showBreakdown, setShowBreakdown] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const parsedApprovedTotal = parseFloat(approvedTotal) || 0
  const shortPaid = requestedTotal - parsedApprovedTotal
  const hasPartialApproval = shortPaid > 0

  const handleSubmit = async () => {
    setError(null)

    if (!approvedTotal || isNaN(parseFloat(approvedTotal))) {
      setError('Please enter a valid approved amount')
      return
    }

    const total = parseFloat(approvedTotal)
    if (total < 0) {
      setError('Approved amount cannot be negative')
      return
    }

    const data: InsurerApprovalData = {
      approved_total: total,
      notes: notes || undefined,
      reference: reference || undefined
    }

    // Add breakdown if provided
    if (approvedLabor) data.approved_labor = parseFloat(approvedLabor)
    if (approvedRi) data.approved_ri = parseFloat(approvedRi)
    if (approvedMaterials) data.approved_materials = parseFloat(approvedMaterials)
    if (approvedTax) data.approved_tax = parseFloat(approvedTax)

    try {
      await onConfirm(data)
      // Reset form on success
      setApprovedTotal('')
      setApprovedLabor('')
      setApprovedRi('')
      setApprovedMaterials('')
      setApprovedTax('')
      setNotes('')
      setReference('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to record approval')
    }
  }

  const handleClose = () => {
    if (!isLoading) {
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Record Insurer Approval
          </DialogTitle>
          <DialogDescription>
            Recording insurer approval for estimate <strong>{estimateNumber}</strong>.
            This will lock the estimate - further changes will require supplements.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Error display */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Requested total (read-only) */}
          <div>
            <Label className="text-muted-foreground">Requested Total</Label>
            <div className="text-2xl font-bold">${requestedTotal.toFixed(2)}</div>
          </div>

          {/* Approved total (required) */}
          <div>
            <Label htmlFor="approved-total">
              Approved Total <span className="text-red-500">*</span>
            </Label>
            <div className="relative mt-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
              <Input
                id="approved-total"
                type="number"
                step="0.01"
                min="0"
                value={approvedTotal}
                onChange={(e) => setApprovedTotal(e.target.value)}
                className="pl-7"
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Short paid warning */}
          {hasPartialApproval && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center gap-2 text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-medium">Partial Approval</span>
              </div>
              <p className="text-sm text-amber-700 mt-1">
                Short paid by <strong>${shortPaid.toFixed(2)}</strong>
              </p>
            </div>
          )}

          {/* Optional breakdown */}
          <Collapsible open={showBreakdown} onOpenChange={setShowBreakdown}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between">
                <span>Optional Breakdown</span>
                <ChevronDown className={cn(
                  "h-4 w-4 transition-transform",
                  showBreakdown && "rotate-180"
                )} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-3 pt-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="approved-labor" className="text-sm">Labor</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <Input
                      id="approved-labor"
                      type="number"
                      step="0.01"
                      min="0"
                      value={approvedLabor}
                      onChange={(e) => setApprovedLabor(e.target.value)}
                      className="pl-5 h-9"
                      placeholder="0.00"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="approved-ri" className="text-sm">R&I</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <Input
                      id="approved-ri"
                      type="number"
                      step="0.01"
                      min="0"
                      value={approvedRi}
                      onChange={(e) => setApprovedRi(e.target.value)}
                      className="pl-5 h-9"
                      placeholder="0.00"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="approved-materials" className="text-sm">Materials</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <Input
                      id="approved-materials"
                      type="number"
                      step="0.01"
                      min="0"
                      value={approvedMaterials}
                      onChange={(e) => setApprovedMaterials(e.target.value)}
                      className="pl-5 h-9"
                      placeholder="0.00"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="approved-tax" className="text-sm">Tax</Label>
                  <div className="relative mt-1">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <Input
                      id="approved-tax"
                      type="number"
                      step="0.01"
                      min="0"
                      value={approvedTax}
                      onChange={(e) => setApprovedTax(e.target.value)}
                      className="pl-5 h-9"
                      placeholder="0.00"
                    />
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Adjuster reference */}
          <div>
            <Label htmlFor="reference">Adjuster Reference ID</Label>
            <Input
              id="reference"
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              className="mt-1"
              placeholder="e.g., ADJ-123456"
            />
          </div>

          {/* Notes */}
          <div>
            <Label htmlFor="notes">Approval Notes</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-1"
              placeholder="e.g., Approved excluding roof body line rate..."
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Recording...
              </>
            ) : (
              <>
                <Lock className="h-4 w-4 mr-2" />
                Record Approval & Lock
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default InsurerApprovalModal
