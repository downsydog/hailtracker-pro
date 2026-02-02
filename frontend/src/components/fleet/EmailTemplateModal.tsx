import { useState, useEffect } from 'react'
import { emailTemplatesApi } from '../../api/fleet'

interface EmailTemplate {
  key: string
  name: string
  subject_preview?: string
  follow_up_days?: number
}

interface Business {
  id: number
  name?: string
  company_name?: string
  city?: string
  state?: string
  phone?: string
  email?: string
  website?: string
  category?: string
  estimated_vehicles?: number
  hail_date?: string
  hail_size?: number
}

interface EmailTemplateModalProps {
  business: Business
  onClose: () => void
  onSent?: () => void
}

export function EmailTemplateModal({ business, onClose, onSent }: EmailTemplateModalProps) {
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(true)
  const [copying, setCopying] = useState(false)

  useEffect(() => {
    loadTemplates()
  }, [])

  useEffect(() => {
    if (business.id) {
      loadTemplateForBusiness()
    }
  }, [business.id])

  const loadTemplates = async () => {
    try {
      const data = await emailTemplatesApi.listTemplates()
      setTemplates(data.templates || [])
    } catch (error) {
      console.error('Failed to load templates:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTemplateForBusiness = async () => {
    try {
      const data = await emailTemplatesApi.getTemplateForBusiness(business.id)
      setSelectedTemplate(data.template_key || '')
      if (data.template) {
        setSubject(data.template.subject || '')
        setBody(data.template.body || '')
      }
    } catch (error) {
      console.error('Failed to load template for business:', error)
    }
  }

  const handleTemplateChange = async (templateKey: string) => {
    setSelectedTemplate(templateKey)

    try {
      const data = await emailTemplatesApi.getTemplate(templateKey, {
        company_name: business.name || business.company_name || '',
        city: business.city || '',
        state: business.state || '',
        estimated_vehicles: String(business.estimated_vehicles || ''),
        hail_date: business.hail_date || '',
      })
      if (data.template) {
        setSubject(data.template.subject || '')
        setBody(data.template.body || '')
      }
    } catch (error) {
      console.error('Failed to load template:', error)
    }
  }

  const handleCopyToClipboard = async () => {
    setCopying(true)
    const fullEmail = `Subject: ${subject}\n\n${body}`

    try {
      await navigator.clipboard.writeText(fullEmail)
      setTimeout(() => setCopying(false), 1500)
    } catch (error) {
      alert('Failed to copy. Please select and copy manually.')
      setCopying(false)
    }
  }

  const handleOpenInEmail = () => {
    const mailtoLink = `mailto:${business.email || ''}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    window.open(mailtoLink)
    onSent?.()
  }

  const handleOpenGmail = () => {
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${business.email || ''}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    window.open(gmailUrl, '_blank')
    onSent?.()
  }

  const companyName = business.name || business.company_name || 'Unknown'

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-purple-50 flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              📧 Email Template
            </h2>
            <div className="text-sm text-gray-600 mt-1">
              To: {companyName}
              {business.email && <span className="text-blue-600 ml-2">&lt;{business.email}&gt;</span>}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Template Selector */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Template
            </label>
            <select
              value={selectedTemplate}
              onChange={(e) => handleTemplateChange(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a template...</option>
              {templates.map(t => (
                <option key={t.key} value={t.key}>
                  {t.name}
                  {t.follow_up_days && ` (follow up: ${t.follow_up_days} days)`}
                </option>
              ))}
            </select>
          </div>

          {/* Subject Line */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Subject
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Email subject..."
            />
          </div>

          {/* Email Body */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Message
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={14}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Email body..."
            />
          </div>

          {/* Business Info Card */}
          <div className="bg-gray-50 rounded-lg p-3 text-sm">
            <div className="font-medium text-gray-700 mb-2">📋 Business Details</div>
            <div className="grid grid-cols-2 gap-2 text-gray-600">
              <div>📍 {business.city}, {business.state}</div>
              <div>🏷️ {business.category?.replace(/_/g, ' ')}</div>
              {business.estimated_vehicles && (
                <div>🚗 ~{business.estimated_vehicles} vehicles</div>
              )}
              {business.phone && (
                <div>📞 {business.phone}</div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t bg-gray-50 flex flex-wrap gap-2">
          <button
            onClick={handleCopyToClipboard}
            className={`flex-1 py-2.5 rounded-lg font-medium transition-all ${
              copying
                ? 'bg-green-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {copying ? '✓ Copied!' : '📋 Copy to Clipboard'}
          </button>

          <button
            onClick={handleOpenInEmail}
            className="flex-1 bg-blue-500 text-white py-2.5 rounded-lg font-medium hover:bg-blue-600 transition-all"
          >
            📧 Open in Email App
          </button>

          <button
            onClick={handleOpenGmail}
            className="flex-1 bg-red-500 text-white py-2.5 rounded-lg font-medium hover:bg-red-600 transition-all"
          >
            <span className="mr-1">✉️</span> Open in Gmail
          </button>
        </div>
      </div>
    </div>
  )
}
