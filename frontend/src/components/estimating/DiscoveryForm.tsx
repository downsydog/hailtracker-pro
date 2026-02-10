/**
 * Discovery Form Component
 * For logging discoveries during repair work
 * Supports photo capture and pre-defined discovery types
 */

import { useState, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
// Select imports available for future use
// import {
//   Select,
//   SelectContent,
//   SelectItem,
//   SelectTrigger,
//   SelectValue,
// } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Camera, Plus, Clock, DollarSign, AlertCircle, X, Image } from 'lucide-react'
import { cn } from '@/lib/utils'

// Discovery types with defaults
export const DISCOVERY_TYPES = [
  {
    type: 'hidden_damage',
    label: 'Hidden Damage',
    description: 'Damage not visible during initial inspection',
    typical_time: 0.5,
    typical_cost: 75
  },
  {
    type: 'access_obstruction',
    label: 'Access Obstruction',
    description: 'Obstruction requiring additional R&I',
    typical_time: 0.25,
    typical_cost: 35
  },
  {
    type: 'additional_ri',
    label: 'Additional R&I',
    description: 'Additional removal/installation needed',
    typical_time: 0.5,
    typical_cost: 50
  },
  {
    type: 'material_issue',
    label: 'Material Issue',
    description: 'Aluminum, HSS, or other material concerns',
    typical_time: 0.5,
    typical_cost: 75
  },
  {
    type: 'headliner_drop',
    label: 'Headliner Drop',
    description: 'Full headliner removal required',
    typical_time: 1.5,
    typical_cost: 150
  },
  {
    type: 'wiring_disconnect',
    label: 'Wiring Disconnect',
    description: 'Electrical disconnection required',
    typical_time: 0.25,
    typical_cost: 35
  },
  {
    type: 'adhesive_removal',
    label: 'Adhesive Removal',
    description: 'Bonded parts requiring adhesive removal',
    typical_time: 0.33,
    typical_cost: 40
  },
  {
    type: 'other',
    label: 'Other',
    description: 'Other discovery requiring supplement',
    typical_time: 0.25,
    typical_cost: 25
  }
]

interface DiscoveryFormData {
  discovery_type: string
  description: string
  additional_time_hours: number
  additional_cost: number
  photo_base64: string | null
  panel_name?: string
}

interface DiscoveryFormProps {
  panelName?: string
  onSubmit: (data: DiscoveryFormData) => void
  onCancel?: () => void
  isSubmitting?: boolean
}

export function DiscoveryForm({
  panelName,
  onSubmit,
  onCancel,
  isSubmitting = false
}: DiscoveryFormProps) {
  const [discoveryType, setDiscoveryType] = useState<string>('')
  const [description, setDescription] = useState('')
  const [additionalTime, setAdditionalTime] = useState('')
  const [additionalCost, setAdditionalCost] = useState('')
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Selected type info available via: DISCOVERY_TYPES.find(t => t.type === discoveryType)

  // Handle type selection - auto-fill defaults
  const handleTypeSelect = (type: string) => {
    setDiscoveryType(type)
    const typeInfo = DISCOVERY_TYPES.find(t => t.type === type)
    if (typeInfo) {
      setAdditionalTime(typeInfo.typical_time.toString())
      setAdditionalCost(typeInfo.typical_cost.toString())
      if (!description && typeInfo.description) {
        setDescription(typeInfo.description)
      }
    }
  }

  // Handle photo capture/upload
  const handlePhotoCapture = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const base64 = event.target?.result as string
      setPhotoPreview(base64)
    }
    reader.readAsDataURL(file)
  }, [])

  // Clear photo
  const clearPhoto = () => {
    setPhotoPreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Handle submit
  const handleSubmit = () => {
    if (!discoveryType) return

    onSubmit({
      discovery_type: discoveryType,
      description,
      additional_time_hours: parseFloat(additionalTime) || 0,
      additional_cost: parseFloat(additionalCost) || 0,
      photo_base64: photoPreview,
      panel_name: panelName
    })
  }

  // Quick add buttons for common discoveries
  const QuickAddButton = ({ type }: { type: typeof DISCOVERY_TYPES[0] }) => (
    <button
      type="button"
      onClick={() => {
        handleTypeSelect(type.type)
      }}
      className={cn(
        'p-3 rounded-lg border-2 text-left transition-all',
        'hover:border-primary/50 hover:bg-accent/50',
        discoveryType === type.type && 'border-primary bg-primary/5'
      )}
    >
      <p className="text-sm font-medium">{type.label}</p>
      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
        <Clock className="h-3 w-3" />
        <span>{type.typical_time}h</span>
        <DollarSign className="h-3 w-3 ml-1" />
        <span>${type.typical_cost}</span>
      </div>
    </button>
  )

  return (
    <div className="space-y-4">
      {panelName && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle className="h-4 w-4" />
          <span>Logging discovery on <strong>{panelName}</strong></span>
        </div>
      )}

      {/* Quick type selection */}
      <div>
        <Label className="text-xs text-muted-foreground">DISCOVERY TYPE</Label>
        <div className="grid grid-cols-2 gap-2 mt-2">
          {DISCOVERY_TYPES.slice(0, 6).map(type => (
            <QuickAddButton key={type.type} type={type} />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2 mt-2">
          {DISCOVERY_TYPES.slice(6).map(type => (
            <QuickAddButton key={type.type} type={type} />
          ))}
        </div>
      </div>

      {/* Description */}
      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what was discovered..."
          rows={3}
        />
      </div>

      {/* Time and Cost */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="time">Additional Time (hours)</Label>
          <Input
            id="time"
            type="number"
            step="0.1"
            min="0"
            value={additionalTime}
            onChange={(e) => setAdditionalTime(e.target.value)}
            placeholder="0.5"
          />
        </div>
        <div>
          <Label htmlFor="cost">Additional Cost ($)</Label>
          <Input
            id="cost"
            type="number"
            step="5"
            min="0"
            value={additionalCost}
            onChange={(e) => setAdditionalCost(e.target.value)}
            placeholder="75"
          />
        </div>
      </div>

      {/* Photo capture */}
      <div>
        <Label>Photo Evidence</Label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handlePhotoCapture}
          className="hidden"
        />

        {photoPreview ? (
          <div className="relative mt-2">
            <img
              src={photoPreview}
              alt="Discovery photo"
              className="w-full h-32 object-cover rounded-lg"
            />
            <Button
              variant="destructive"
              size="icon"
              className="absolute top-2 right-2 h-6 w-6"
              onClick={clearPhoto}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <Button
            variant="outline"
            className="w-full mt-2"
            onClick={() => fileInputRef.current?.click()}
          >
            <Camera className="h-4 w-4 mr-2" />
            Take Photo
          </Button>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2 pt-2">
        {onCancel && (
          <Button variant="outline" className="flex-1" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button
          className="flex-1"
          onClick={handleSubmit}
          disabled={!discoveryType || isSubmitting}
        >
          {isSubmitting ? 'Saving...' : 'Save Discovery'}
        </Button>
      </div>
    </div>
  )
}

// Discovery Dialog wrapper
interface DiscoveryDialogProps {
  panelName?: string
  onSubmit: (data: DiscoveryFormData) => void
  trigger?: React.ReactNode
  isSubmitting?: boolean
}

export function DiscoveryDialog({
  panelName,
  onSubmit,
  trigger,
  isSubmitting
}: DiscoveryDialogProps) {
  const [open, setOpen] = useState(false)

  const handleSubmit = (data: DiscoveryFormData) => {
    onSubmit(data)
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline">
            <Plus className="h-4 w-4 mr-2" />
            Add Discovery
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-500" />
            Log Discovery
          </DialogTitle>
        </DialogHeader>
        <DiscoveryForm
          panelName={panelName}
          onSubmit={handleSubmit}
          onCancel={() => setOpen(false)}
          isSubmitting={isSubmitting}
        />
      </DialogContent>
    </Dialog>
  )
}

// Discovery list item
interface DiscoveryItemProps {
  discovery: {
    id: number
    discovery_type: string
    description?: string
    additional_time_hours: number
    additional_cost: number
    photo_url?: string
    panel_name?: string
    narrative?: string
    created_at: string
  }
  onRemove?: (id: number) => void
}

export function DiscoveryItem({ discovery, onRemove }: DiscoveryItemProps) {
  const typeInfo = DISCOVERY_TYPES.find(t => t.type === discovery.discovery_type)

  return (
    <Card className="bg-orange-50 border-orange-200">
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-orange-500" />
              <span className="font-medium text-sm">
                {typeInfo?.label || discovery.discovery_type}
              </span>
              {discovery.panel_name && (
                <Badge variant="outline" className="text-xs">
                  {discovery.panel_name}
                </Badge>
              )}
            </div>
            {discovery.description && (
              <p className="text-sm text-muted-foreground mt-1">
                {discovery.description}
              </p>
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {discovery.additional_time_hours}h
              </span>
              <span className="font-medium text-orange-600">
                +${discovery.additional_cost}
              </span>
              {discovery.photo_url && (
                <span className="flex items-center gap-1">
                  <Image className="h-3 w-3" />
                  Photo
                </span>
              )}
            </div>
          </div>
          {onRemove && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground"
              onClick={() => onRemove(discovery.id)}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
