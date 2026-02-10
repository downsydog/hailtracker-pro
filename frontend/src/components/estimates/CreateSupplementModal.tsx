/**
 * Create Supplement Modal
 *
 * Allows creating a new supplement based on changes since a baseline version.
 */

import { useState, useEffect } from 'react'
import { Loader2, FileText, AlertCircle, CheckCircle, Plus, Shield, Copy, Check, Package } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
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
  DialogFooter,
} from '@/components/ui/dialog'
import {
  useEstimateVersions,
  useCreateEstimateVersion,
  useCreateSupplement,
  DISCOVERY_TYPES,
  EstimateVersion,
  EstimateSupplement
} from '@/hooks/use-pdr-estimates'
import { useEstimateRI } from '@/hooks/use-ri'
import { useEstimatePartsRequests } from '@/hooks/use-jobs'

interface CreateSupplementModalProps {
  open: boolean
  onClose: () => void
  estimateId: number
  currentEstimateData: Record<string, unknown>
  onSupplementCreated?: (supplement: EstimateSupplement) => void
}

export function CreateSupplementModal({
  open,
  onClose,
  estimateId,
  currentEstimateData,
  onSupplementCreated
}: CreateSupplementModalProps) {
  // Hooks
  const { data: versionsData, isLoading: versionsLoading } = useEstimateVersions(estimateId)
  const createVersion = useCreateEstimateVersion()
  const createSupplement = useCreateSupplement()

  // Stage 7B: R&I data for denial ammo
  const { data: estimateRiData } = useEstimateRI(estimateId)
  const denialPack = estimateRiData?.ri_denial_pack
  const hasDenialAmmo = !!(denialPack?.copy_blocks?.full)

  // Stage 7C: Parts requests for context
  const { data: partsData } = useEstimatePartsRequests(estimateId)
  const partsRequests = partsData?.requests || []
  const hasPartsRequests = partsRequests.length > 0
  const openPartsCount = partsRequests.filter((p: { parts_status?: string }) =>
    p.parts_status && !['received', 'installed', 'cancelled'].includes(p.parts_status)
  ).length

  // Form state
  const [selectedVersionId, setSelectedVersionId] = useState<string>('')
  const [discoveryType, setDiscoveryType] = useState<string>('hidden_damage')
  const [summary, setSummary] = useState('')
  const [attachDenialAmmo, setAttachDenialAmmo] = useState(false)
  const [attachPartsContext, setAttachPartsContext] = useState(false)
  const [ammocopied, setAmmoCopied] = useState(false)

  // Result state
  const [createdSupplement, setCreatedSupplement] = useState<EstimateSupplement | null>(null)
  const [error, setError] = useState('')

  const versions = versionsData?.versions || []

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      setSelectedVersionId('')
      setDiscoveryType('hidden_damage')
      setSummary('')
      setAttachDenialAmmo(false)
      setAttachPartsContext(false)
      setAmmoCopied(false)
      setCreatedSupplement(null)
      setError('')
    }
  }, [open])

  // Auto-select first version if available
  useEffect(() => {
    if (versions.length > 0 && !selectedVersionId) {
      setSelectedVersionId(versions[0].id.toString())
    }
  }, [versions, selectedVersionId])

  const handleCreateBaseline = async () => {
    try {
      const result = await createVersion.mutateAsync({
        estimateId,
        snapshot: currentEstimateData,
        description: 'Baseline for supplement'
      })
      setSelectedVersionId(result.version.id.toString())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create baseline')
    }
  }

  const handleCreate = async () => {
    if (!selectedVersionId) {
      setError('Please select a baseline version')
      return
    }

    setError('')

    // Build summary with denial ammo and parts context if toggled
    let finalSummary = summary.trim()
    if (attachDenialAmmo && denialPack?.copy_blocks?.full) {
      finalSummary = finalSummary
        ? `${finalSummary}\n\n---\n\n${denialPack.copy_blocks.full}`
        : denialPack.copy_blocks.full
    }

    // Stage 7C: Append parts context if toggled
    if (attachPartsContext && partsRequests.length > 0) {
      const partsLines = ['PARTS STATUS:']
      const openParts = partsRequests.filter((p: { parts_status?: string }) =>
        p.parts_status && !['received', 'installed', 'cancelled'].includes(p.parts_status)
      )
      for (const part of openParts.slice(0, 5)) {
        const p = part as { part_name?: string; vendor?: string; eta?: string; parts_status?: string }
        partsLines.push(`• ${p.part_name || 'Part'} - ${p.vendor || 'TBD'} - ETA: ${p.eta || 'TBD'} - Status: ${p.parts_status || 'pending'}`)
      }
      if (openParts.length > 5) {
        partsLines.push(`  ...and ${openParts.length - 5} more open requests`)
      }
      const partsBlock = partsLines.join('\n')
      finalSummary = finalSummary
        ? `${finalSummary}\n\n---\n\n${partsBlock}`
        : partsBlock
    }

    try {
      const result = await createSupplement.mutateAsync({
        estimateId,
        baselineVersionId: parseInt(selectedVersionId),
        currentState: currentEstimateData,
        discoveryType,
        summary: finalSummary || undefined
      })

      setCreatedSupplement(result.supplement)
      onSupplementCreated?.(result.supplement)

      // Auto-close after success
      setTimeout(() => {
        onClose()
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create supplement')
    }
  }

  const handleClose = () => {
    if (!createSupplement.isPending && !createVersion.isPending) {
      onClose()
    }
  }

  const isProcessing = createSupplement.isPending || createVersion.isPending

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Create Supplement
          </DialogTitle>
        </DialogHeader>

        {createdSupplement ? (
          <div className="py-8 flex flex-col items-center gap-3">
            <CheckCircle className="h-12 w-12 text-green-500" />
            <p className="text-lg font-medium text-green-700">Supplement Created</p>
            <p className="text-sm text-muted-foreground">
              Supplement #{createdSupplement.supplement_number} created successfully
            </p>
            {createdSupplement.delta_amount !== null && (
              <p className="text-lg font-bold">
                Delta: {createdSupplement.delta_amount >= 0 ? '+' : ''}${createdSupplement.delta_amount.toFixed(2)}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {/* Baseline version selection */}
            <div className="space-y-2">
              <Label>Baseline Version</Label>
              {versionsLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading versions...
                </div>
              ) : versions.length === 0 ? (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    No baseline versions exist. Create one to capture the current state before creating a supplement.
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCreateBaseline}
                    disabled={createVersion.isPending}
                  >
                    {createVersion.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Baseline Now
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Select value={selectedVersionId} onValueChange={setSelectedVersionId}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select baseline version" />
                    </SelectTrigger>
                    <SelectContent>
                      {versions.map((v: EstimateVersion) => (
                        <SelectItem key={v.id} value={v.id.toString()}>
                          Version {v.version_number}
                          {v.description && ` - ${v.description}`}
                          {' '}({new Date(v.created_at).toLocaleDateString()})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleCreateBaseline}
                    disabled={createVersion.isPending}
                    title="Create new baseline"
                  >
                    {createVersion.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              )}
            </div>

            {/* Discovery type */}
            <div className="space-y-2">
              <Label>Discovery Type</Label>
              <Select value={discoveryType} onValueChange={setDiscoveryType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DISCOVERY_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Select the reason for the additional charges
              </p>
            </div>

            {/* Summary */}
            <div className="space-y-2">
              <Label>Summary (optional)</Label>
              <Textarea
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="Brief description of the additional damage found..."
                rows={3}
                disabled={isProcessing}
                className="resize-none"
              />
            </div>

            {/* Stage 7B: Denial Ammo Toggle */}
            {hasDenialAmmo && (
              <div className="space-y-3 bg-blue-50 rounded-lg p-3 border border-blue-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-blue-600" />
                    <Label htmlFor="attach-ammo" className="text-sm font-medium text-blue-900">
                      Attach Denial Ammo
                    </Label>
                  </div>
                  <Switch
                    id="attach-ammo"
                    checked={attachDenialAmmo}
                    onCheckedChange={setAttachDenialAmmo}
                    disabled={isProcessing}
                  />
                </div>
                {attachDenialAmmo && (
                  <div className="space-y-2">
                    <p className="text-xs text-blue-700">
                      R&I justification will be appended to the supplement narrative.
                    </p>
                    <div className="bg-white rounded border p-2 text-xs max-h-24 overflow-y-auto text-muted-foreground">
                      {denialPack?.copy_blocks?.short || 'R&I justification details...'}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => {
                        if (denialPack?.copy_blocks?.full) {
                          navigator.clipboard.writeText(denialPack.copy_blocks.full)
                          setAmmoCopied(true)
                          setTimeout(() => setAmmoCopied(false), 2000)
                        }
                      }}
                    >
                      {ammocopied ? (
                        <>
                          <Check className="h-3 w-3 mr-1" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3 mr-1" />
                          Copy Full Text
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Stage 7C: Parts Context Toggle */}
            {hasPartsRequests && (
              <div className="space-y-3 bg-amber-50 rounded-lg p-3 border border-amber-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-amber-600" />
                    <Label htmlFor="attach-parts" className="text-sm font-medium text-amber-900">
                      Attach Parts Context
                    </Label>
                    {openPartsCount > 0 && (
                      <span className="text-xs bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded">
                        {openPartsCount} open
                      </span>
                    )}
                  </div>
                  <Switch
                    id="attach-parts"
                    checked={attachPartsContext}
                    onCheckedChange={setAttachPartsContext}
                    disabled={isProcessing}
                  />
                </div>
                {attachPartsContext && (
                  <div className="space-y-2">
                    <p className="text-xs text-amber-700">
                      Parts request status will be appended to the supplement narrative.
                    </p>
                    <div className="bg-white rounded border p-2 text-xs max-h-24 overflow-y-auto text-muted-foreground">
                      {partsRequests.slice(0, 3).map((p: { id?: number; part_name?: string; vendor?: string; parts_status?: string }, idx: number) => (
                        <div key={p.id || idx} className="flex justify-between py-0.5">
                          <span>{p.part_name || 'Part'}</span>
                          <span className="text-amber-600">{p.vendor || 'TBD'} • {p.parts_status || 'pending'}</span>
                        </div>
                      ))}
                      {partsRequests.length > 3 && (
                        <div className="text-center text-amber-500 pt-1">
                          +{partsRequests.length - 3} more
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Info box */}
            <div className="bg-muted/50 rounded-md p-3 text-sm">
              <p className="font-medium mb-1">What happens next:</p>
              <ul className="text-muted-foreground space-y-1">
                <li>• System will compute diff between baseline and current state</li>
                <li>• A narrative will be generated explaining the changes</li>
                <li>• You can download or send the supplement PDF</li>
              </ul>
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 text-red-600 bg-red-50 rounded-md p-3">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {!createdSupplement && (
            <>
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={isProcessing}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!selectedVersionId || isProcessing}
              >
                {createSupplement.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 mr-2" />
                    Create Supplement
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

export default CreateSupplementModal
