import { useState, useEffect } from 'react'
import { callScriptsApi, CallScript } from '../../api/fleet'

interface ScriptListItem {
  key: string
  name: string
  category: string
}

interface Business {
  id: number
  name?: string
  company_name?: string
  address?: string
  city?: string
  state?: string
  phone?: string
  website?: string
  category?: string
  estimated_vehicles?: number
  hail_date?: string
  lead_id?: number
}

interface CallScriptModalProps {
  business: Business
  onClose: () => void
  onLogCall?: (outcome: string, notes: string) => void
}

const CALL_OUTCOMES = [
  { value: 'APPOINTMENT_SET', label: '✅ Appointment Set', color: 'bg-green-500' },
  { value: 'CALLBACK_SCHEDULED', label: '📅 Callback Scheduled', color: 'bg-blue-500' },
  { value: 'SENT_INFO', label: '📧 Sent Info/Email', color: 'bg-purple-500' },
  { value: 'INTERESTED', label: '👍 Interested - Follow Up', color: 'bg-teal-500' },
  { value: 'NOT_INTERESTED', label: '❌ Not Interested', color: 'bg-red-500' },
  { value: 'NO_ANSWER', label: '📵 No Answer', color: 'bg-gray-500' },
  { value: 'LEFT_VOICEMAIL', label: '📝 Left Voicemail', color: 'bg-yellow-500' },
  { value: 'WRONG_NUMBER', label: '🚫 Wrong Number', color: 'bg-gray-400' },
  { value: 'GATEKEEPER', label: '🚧 Gatekeeper - Try Again', color: 'bg-orange-500' },
]

export function CallScriptModal({ business, onClose, onLogCall }: CallScriptModalProps) {
  const [scripts, setScripts] = useState<ScriptListItem[]>([])
  const [selectedScript, setSelectedScript] = useState<string>('')
  const [scriptContent, setScriptContent] = useState<string>('')
  const [loading, setLoading] = useState(true)

  // Call logging state
  const [callOutcome, setCallOutcome] = useState<string>('')
  const [callNotes, setCallNotes] = useState<string>('')
  const [showLogSection, setShowLogSection] = useState(false)

  useEffect(() => {
    loadScripts()
  }, [])

  useEffect(() => {
    if (business.id) {
      loadScriptForBusiness()
    }
  }, [business.id])

  const loadScripts = async () => {
    try {
      const data = await callScriptsApi.listScripts()
      setScripts(data.scripts || [])
    } catch (error) {
      console.error('Failed to load scripts:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadScriptForBusiness = async () => {
    try {
      const data = await callScriptsApi.getScriptForBusiness(business.id)
      setSelectedScript(data.script_key || '')
      if (data.script) {
        setScriptContent(data.script.script || '')
      }
    } catch (error) {
      console.error('Failed to load script for business:', error)
    }
  }

  const handleScriptChange = async (scriptKey: string) => {
    setSelectedScript(scriptKey)

    try {
      const data = await callScriptsApi.getScript(scriptKey, {
        company_name: business.name || business.company_name || '',
        city: business.city || '',
        address: business.address || '',
        hail_date: business.hail_date || '',
      })
      if (data.script) {
        setScriptContent(data.script.script || '')
      }
    } catch (error) {
      console.error('Failed to load script:', error)
    }
  }

  const handleLogCall = () => {
    if (!callOutcome) {
      alert('Please select a call outcome')
      return
    }

    onLogCall?.(callOutcome, callNotes)
    onClose()
  }

  // Parse markdown-like formatting in script
  const formatScript = (text: string) => {
    if (!text) return null

    return text.split('\n').map((line, i) => {
      // Bold headers **text**
      if (line.startsWith('**') && line.includes('**')) {
        const content = line.replace(/\*\*/g, '')
        return (
          <div key={i} className="font-bold text-blue-800 mt-4 mb-2 bg-blue-50 px-2 py-1 rounded">
            {content}
          </div>
        )
      }
      // Quotes/speaking parts
      if (line.startsWith('"')) {
        return (
          <div key={i} className="bg-green-50 border-l-4 border-green-400 pl-3 py-1 my-1 italic text-gray-700">
            {line}
          </div>
        )
      }
      // Bullet points
      if (line.startsWith('•') || line.startsWith('-')) {
        return (
          <div key={i} className="ml-4 text-gray-600">
            {line}
          </div>
        )
      }
      // Arrows/tips
      if (line.startsWith('→')) {
        return (
          <div key={i} className="ml-4 text-blue-600 italic">
            {line}
          </div>
        )
      }
      // Horizontal rules
      if (line.startsWith('---')) {
        return <hr key={i} className="my-3 border-gray-200" />
      }
      // Empty lines
      if (!line.trim()) {
        return <div key={i} className="h-2"></div>
      }
      // Regular text
      return (
        <div key={i} className="text-gray-700">
          {line}
        </div>
      )
    })
  }

  const companyName = business.name || business.company_name || 'Unknown'

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b bg-gradient-to-r from-green-50 to-teal-50 flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              📞 Call Script
            </h2>
            <div className="text-sm text-gray-600 mt-1">
              {companyName}
              {business.phone && (
                <span className="ml-2 font-mono text-green-600">{business.phone}</span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Main Content - Split View */}
        <div className="flex-1 flex overflow-hidden">
          {/* Script Panel */}
          <div className="flex-1 p-4 overflow-y-auto border-r">
            {/* Script Selector */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Script Type
              </label>
              <select
                value={selectedScript}
                onChange={(e) => handleScriptChange(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500 focus:border-green-500"
              >
                <option value="">Select a script...</option>
                {scripts.map(s => (
                  <option key={s.key} value={s.key}>
                    {s.name} ({s.category})
                  </option>
                ))}
              </select>
            </div>

            {/* Script Content */}
            <div className="bg-gray-50 rounded-lg p-4 text-sm leading-relaxed min-h-[300px]">
              {scriptContent ? (
                formatScript(scriptContent)
              ) : (
                <div className="text-gray-400 text-center py-8">
                  Select a script to begin
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Info & Logging */}
          <div className="w-80 p-4 bg-gray-50 overflow-y-auto">
            {/* Quick Info */}
            <div className="bg-white rounded-lg p-3 mb-4 shadow-sm">
              <div className="font-medium text-gray-700 mb-2">📋 Quick Info</div>
              <div className="space-y-1 text-sm text-gray-600">
                <div>🏢 {companyName}</div>
                {business.address && <div>📍 {business.address}</div>}
                <div>📍 {business.city}, {business.state}</div>
                {business.category && (
                  <div>🏷️ {business.category.replace(/_/g, ' ')}</div>
                )}
                {business.estimated_vehicles && (
                  <div>🚗 ~{business.estimated_vehicles} vehicles</div>
                )}
              </div>
            </div>

            {/* Call Button */}
            {business.phone && (
              <a
                href={`tel:${business.phone}`}
                onClick={() => setShowLogSection(true)}
                className="block w-full bg-green-500 text-white py-3 rounded-lg font-bold text-center hover:bg-green-600 transition-all mb-4"
              >
                📞 Call {business.phone}
              </a>
            )}

            {/* Call Logging Section */}
            <div className={`transition-all ${showLogSection || !business.phone ? 'opacity-100' : 'opacity-50'}`}>
              <div className="font-medium text-gray-700 mb-2">📝 Log This Call</div>

              {/* Outcome Buttons */}
              <div className="space-y-2 mb-4">
                {CALL_OUTCOMES.map(outcome => (
                  <button
                    key={outcome.value}
                    onClick={() => setCallOutcome(outcome.value)}
                    className={`w-full py-2 px-3 rounded-lg text-sm text-left transition-all ${
                      callOutcome === outcome.value
                        ? `${outcome.color} text-white shadow-md`
                        : 'bg-white border border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    {outcome.label}
                  </button>
                ))}
              </div>

              {/* Notes */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={callNotes}
                  onChange={(e) => setCallNotes(e.target.value)}
                  rows={4}
                  placeholder="What did you discuss? Decision maker name? Follow-up needed?"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500"
                />
              </div>

              {/* Save Button */}
              <button
                onClick={handleLogCall}
                disabled={!callOutcome}
                className={`w-full py-2.5 rounded-lg font-medium transition-all ${
                  callOutcome
                    ? 'bg-blue-500 text-white hover:bg-blue-600'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                💾 Save & Close
              </button>
            </div>

            {/* Quick Actions */}
            <div className="mt-4 pt-4 border-t space-y-2">
              <button
                onClick={() => window.open(`https://www.google.com/maps/search/${encodeURIComponent(
                  `${business.address || ''} ${business.city} ${business.state}`
                )}`, '_blank')}
                className="w-full py-2 bg-white border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
              >
                🗺️ View on Map
              </button>
              {business.website && (
                <button
                  onClick={() => window.open(business.website, '_blank')}
                  className="w-full py-2 bg-white border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
                >
                  🌐 Visit Website
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
