import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { EmailTemplate, TemplatePreviewResponse } from '@/types'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'

interface EmailTemplateSelectorProps {
  companyId: string | null
  eventId: string
  onTemplateChange: (templateId: string | null) => void
}

export function EmailTemplateSelector({
  companyId,
  eventId,
  onTemplateChange,
}: EmailTemplateSelectorProps) {
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const [preview, setPreview] = useState<TemplatePreviewResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)

  // Fetch available templates
  useEffect(() => {
    const fetchTemplates = async () => {
      setIsLoading(true)
      try {
        const params = new URLSearchParams({ reason: 'expense_report' })
        if (companyId) {
          params.append('company_id', companyId)
        }
        const data = await api.get<EmailTemplate[]>(`/email-templates?${params.toString()}`)
        setTemplates(data)

        // Find and select the default template
        const defaultTemplate = data.find(t =>
          // Prefer company-specific default
          t.company_id === companyId && t.is_default
        ) || data.find(t =>
          // Fall back to global default
          t.company_id === null && t.is_default
        ) || data[0]

        if (defaultTemplate) {
          setSelectedTemplateId(defaultTemplate.id)
          onTemplateChange(defaultTemplate.id)
        }
      } catch {
        setTemplates([])
      } finally {
        setIsLoading(false)
      }
    }

    fetchTemplates()
  }, [companyId, onTemplateChange])

  // Fetch preview when template changes
  useEffect(() => {
    if (!selectedTemplateId) {
      setPreview(null)
      return
    }

    const selectedTemplate = templates.find(t => t.id === selectedTemplateId)
    if (!selectedTemplate) {
      setPreview(null)
      return
    }

    const fetchPreview = async () => {
      setIsLoadingPreview(true)
      try {
        const result = await api.post<TemplatePreviewResponse>('/email-templates/preview', {
          subject: selectedTemplate.subject,
          body_html: selectedTemplate.body_html,
          body_text: selectedTemplate.body_text,
          reason: selectedTemplate.reason,
          event_id: eventId,
        })
        setPreview(result)
      } catch {
        setPreview(null)
      } finally {
        setIsLoadingPreview(false)
      }
    }

    fetchPreview()
  }, [selectedTemplateId, templates, eventId])

  const handleTemplateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newId = e.target.value
    setSelectedTemplateId(newId)
    onTemplateChange(newId || null)
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-4">
        <Spinner size="sm" />
        <span className="text-sm text-gray-500">Loading templates...</span>
      </div>
    )
  }

  if (templates.length === 0) {
    return (
      <div className="py-4 text-sm text-amber-600">
        No email templates found. Please configure a template in Settings.
      </div>
    )
  }

  const templateOptions = templates.map(t => ({
    value: t.id,
    label: `${t.name}${t.company_id ? '' : ' (Global)'}${t.is_default ? ' - Default' : ''}`,
  }))

  return (
    <div className="space-y-4">
      <Select
        label="Email Template"
        value={selectedTemplateId}
        onChange={handleTemplateChange}
        options={templateOptions}
      />

      {/* Preview */}
      {selectedTemplateId && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
            <p className="text-sm font-medium text-gray-700">Preview</p>
          </div>
          <div className="p-4">
            {isLoadingPreview ? (
              <div className="flex items-center justify-center py-8">
                <Spinner size="sm" />
              </div>
            ) : preview ? (
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">Subject</p>
                  <p className="text-gray-900">{preview.subject}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-1">Body</p>
                  <div
                    className="text-sm text-gray-700 prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: preview.body_html }}
                  />
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500 text-center py-4">
                Select a template to see preview
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
