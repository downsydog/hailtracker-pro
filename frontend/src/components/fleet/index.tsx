import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface Business {
  id: number
  name: string
  city?: string
  state?: string
  phone?: string
  email?: string
  website?: string
  category?: string
  estimated_vehicles?: number
  hail_date?: string
  hail_size?: number
  address?: string
}

interface EmailTemplateModalProps {
  business: Business
  onClose: () => void
  onSent?: () => void
}

export function EmailTemplateModal({ business, onClose, onSent }: EmailTemplateModalProps) {
  const [subject, setSubject] = React.useState(
    `Hail Damage Repair Services for ${business.name}`
  )
  const [body, setBody] = React.useState(
    `Dear ${business.name},\n\nWe noticed your area was recently affected by a hail storm${business.hail_date ? ` on ${business.hail_date}` : ''}${business.hail_size ? ` with ${business.hail_size}" hail` : ''}.\n\nWith an estimated ${business.estimated_vehicles || 'fleet'} vehicles, we'd love to help you get your fleet back in shape.\n\nWould you be available for a quick call to discuss our mobile PDR services?\n\nBest regards`
  )

  const handleSend = () => {
    // Open email client
    const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    window.open(mailtoLink)
    onSent?.()
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Email Template - {business.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Subject</Label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
          </div>
          <div>
            <Label>Body</Label>
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={10}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSend}>Open in Email Client</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface CallScriptModalProps {
  business: Business
  onClose: () => void
  onLogCall?: (outcome: string, notes: string) => Promise<void>
}

export function CallScriptModal({ business, onClose, onLogCall }: CallScriptModalProps) {
  const [outcome, setOutcome] = React.useState("")
  const [notes, setNotes] = React.useState("")

  const script = `Hi, this is [Your Name] from [Company].

I'm calling because we noticed your area was recently hit by a hail storm${business.hail_date ? ` on ${business.hail_date}` : ''}.

We specialize in mobile paintless dent repair for commercial fleets, and with your ${business.estimated_vehicles || 'fleet'} vehicles at ${business.name}, we could come to your location and get your fleet looking new again.

Do you have a few minutes to discuss how we can help?`

  const handleLog = async () => {
    if (onLogCall) {
      await onLogCall(outcome, notes)
    }
    onClose()
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Call Script - {business.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="p-4 bg-muted rounded-lg">
            <pre className="whitespace-pre-wrap text-sm">{script}</pre>
          </div>
          {business.phone && (
            <div className="flex items-center gap-2">
              <span className="font-medium">Phone:</span>
              <a href={`tel:${business.phone}`} className="text-blue-600 hover:underline">
                {business.phone}
              </a>
            </div>
          )}
          <div>
            <Label>Call Outcome</Label>
            <select
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
              className="w-full p-2 border rounded-md"
            >
              <option value="">Select outcome...</option>
              <option value="connected">Connected - Interested</option>
              <option value="callback">Callback Scheduled</option>
              <option value="not_interested">Not Interested</option>
              <option value="no_answer">No Answer</option>
              <option value="wrong_number">Wrong Number</option>
            </select>
          </div>
          <div>
            <Label>Notes</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes from the call..."
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleLog} disabled={!outcome}>Log Call</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
