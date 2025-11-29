import { useEffect, useState, useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '@/api/client'
import type { EmailTemplate, TemplateReason, TemplatePreviewResponse } from '@/types'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { Alert } from '@/components/ui/Alert'

const templateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  reason: z.string().min(1, 'Reason is required'),
  subject: z.string().min(1, 'Subject is required').max(500),
  body_html: z.string().min(1, 'HTML body is required'),
  body_text: z.string().min(1, 'Plain text body is required'),
  is_default: z.boolean().optional(),
})

type TemplateForm = z.infer<typeof templateSchema>

interface EmailTemplateEditorProps {
  isOpen: boolean
  onClose: () => void
  onSaved: () => void
  template: EmailTemplate | null
  companyId?: string
  reasons: TemplateReason[]
}

export function EmailTemplateEditor({
  isOpen,
  onClose,
  onSaved,
  template,
  companyId,
  reasons,
}: EmailTemplateEditorProps) {
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [preview, setPreview] = useState<TemplatePreviewResponse | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit')

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<TemplateForm>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      reason: 'expense_report',
      is_default: false,
    },
  })

  const watchSubject = watch('subject')
  const watchBodyHtml = watch('body_html')
  const watchBodyText = watch('body_text')
  const watchReason = watch('reason')

  // Find the current reason's variables
  const currentReason = useMemo(
    () => reasons.find(r => r.reason === watchReason),
    [reasons, watchReason]
  )

  // Reset form when template or modal state changes
  useEffect(() => {
    if (isOpen) {
      if (template) {
        reset({
          name: template.name,
          reason: template.reason,
          subject: template.subject,
          body_html: template.body_html,
          body_text: template.body_text,
          is_default: template.is_default,
        })
      } else {
        reset({
          name: '',
          reason: 'expense_report',
          subject: '',
          body_html: '',
          body_text: '',
          is_default: false,
        })
      }
      setPreview(null)
      setActiveTab('edit')
    }
  }, [isOpen, template, reset])

  // Debounced preview update
  useEffect(() => {
    if (!isOpen || !watchSubject || !watchBodyHtml || !watchBodyText) {
      setPreview(null)
      return
    }

    const timeoutId = setTimeout(async () => {
      setIsLoadingPreview(true)
      try {
        const result = await api.post<TemplatePreviewResponse>('/email-templates/preview', {
          subject: watchSubject,
          body_html: watchBodyHtml,
          body_text: watchBodyText,
          reason: watchReason,
        })
        setPreview(result)
      } catch {
        // Silently fail preview - user can still save
      } finally {
        setIsLoadingPreview(false)
      }
    }, 500)

    return () => clearTimeout(timeoutId)
  }, [isOpen, watchSubject, watchBodyHtml, watchBodyText, watchReason])

  const onSubmit = async (data: TemplateForm) => {
    setIsSaving(true)
    setError(null)
    try {
      const payload = {
        ...data,
        company_id: companyId || null,
      }

      if (template) {
        await api.put(`/email-templates/${template.id}`, payload)
      } else {
        await api.post('/email-templates', payload)
      }
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save template')
    } finally {
      setIsSaving(false)
    }
  }

  const insertVariable = (variable: string) => {
    // Get the active textarea and insert the variable at cursor
    const activeElement = document.activeElement as HTMLTextAreaElement | HTMLInputElement
    if (activeElement && (activeElement.tagName === 'TEXTAREA' || activeElement.tagName === 'INPUT')) {
      const start = activeElement.selectionStart || 0
      const end = activeElement.selectionEnd || 0
      const currentValue = activeElement.value
      const newValue = currentValue.substring(0, start) + variable + currentValue.substring(end)
      activeElement.value = newValue
      activeElement.setSelectionRange(start + variable.length, start + variable.length)
      activeElement.focus()

      // Trigger React's onChange
      const event = new Event('input', { bubbles: true })
      activeElement.dispatchEvent(event)
    }
  }

  const reasonOptions = reasons.map(r => ({
    value: r.reason,
    label: r.description,
  }))

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={template ? 'Edit Email Template' : 'Create Email Template'}
      size="4xl"
    >
      <div className="flex gap-6" style={{ minHeight: '600px' }}>
        {/* Left side - Editor */}
        <div className="flex-1 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-4">
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === 'edit'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('edit')}
            >
              Edit
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === 'preview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('preview')}
            >
              Preview
            </button>
          </div>

          {error && <Alert variant="error" className="mb-4">{error}</Alert>}

          {activeTab === 'edit' ? (
            <form onSubmit={handleSubmit(onSubmit)} className="flex-1 flex flex-col space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Template Name"
                  {...register('name')}
                  error={errors.name?.message}
                />
                <Select
                  label="Template Type"
                  options={reasonOptions}
                  {...register('reason')}
                  error={errors.reason?.message}
                />
              </div>

              <Input
                label="Subject"
                {...register('subject')}
                error={errors.subject?.message}
                description="Use {{variable}} syntax for dynamic content"
              />

              <div className="flex-1 flex flex-col min-h-0">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  HTML Body
                </label>
                <textarea
                  {...register('body_html')}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm resize-none"
                  placeholder="<p>Dear {{company.recipient_name}},</p>..."
                />
                {errors.body_html && (
                  <p className="mt-1 text-sm text-red-600">{errors.body_html.message}</p>
                )}
              </div>

              <div className="flex-1 flex flex-col min-h-0">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Plain Text Body
                </label>
                <textarea
                  {...register('body_text')}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm resize-none"
                  placeholder="Dear {{company.recipient_name}},..."
                />
                {errors.body_text && (
                  <p className="mt-1 text-sm text-red-600">{errors.body_text.message}</p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_default"
                  {...register('is_default')}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="is_default" className="text-sm text-gray-700">
                  Set as default template for this type
                  {companyId && ' (company-specific)'}
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <Button type="button" variant="secondary" onClick={onClose}>
                  Cancel
                </Button>
                <Button type="submit" isLoading={isSaving}>
                  {template ? 'Save Changes' : 'Create Template'}
                </Button>
              </div>
            </form>
          ) : (
            /* Preview Tab */
            <div className="flex-1 flex flex-col">
              {isLoadingPreview ? (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  Loading preview...
                </div>
              ) : preview ? (
                <div className="flex-1 flex flex-col overflow-auto">
                  <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm font-medium text-gray-500">Subject</p>
                    <p className="text-gray-900">{preview.subject}</p>
                  </div>
                  <div className="flex-1 border rounded-lg overflow-hidden">
                    <iframe
                      srcDoc={preview.body_html}
                      title="Email Preview"
                      className="w-full h-full bg-white"
                      style={{ minHeight: '300px' }}
                    />
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  Enter template content to see preview
                </div>
              )}
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 mt-4">
                <Button type="button" variant="secondary" onClick={onClose}>
                  Cancel
                </Button>
                <Button onClick={handleSubmit(onSubmit)} isLoading={isSaving}>
                  {template ? 'Save Changes' : 'Create Template'}
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Right side - Variables */}
        <div className="w-64 flex-shrink-0 border-l border-gray-200 pl-6">
          <h3 className="font-medium text-gray-900 mb-4">Available Variables</h3>
          {currentReason ? (
            <div className="space-y-3">
              {currentReason.variables.map((v) => (
                <div key={v.variable} className="text-sm">
                  <button
                    type="button"
                    onClick={() => insertVariable(v.variable)}
                    className="font-mono text-blue-600 hover:text-blue-800 cursor-pointer"
                    title={`Click to insert: ${v.variable}`}
                  >
                    {v.variable}
                  </button>
                  <p className="text-gray-500 text-xs">{v.description}</p>
                  <p className="text-gray-400 text-xs">e.g. {v.example}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Select a template type to see available variables
            </p>
          )}
        </div>
      </div>
    </Modal>
  )
}
