// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useMemo, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { api, errorMessage } from '@/api/client'
import { ContactTypeSelect } from '@/components/ContactTypeSelect'
import { EmailTemplatePreview } from '@/components/settings/EmailTemplatePreview'
import { EmailTemplateVariables } from '@/components/settings/EmailTemplateVariables'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import type { ContactType, EmailTemplate, TemplatePreviewResponse, TemplateReason } from '@/types'

const templateSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  reason: z.string().min(1, 'Reason is required'),
  subject: z.string().min(1, 'Subject is required').max(500),
  body_html: z.string().min(1, 'HTML body is required'),
  body_text: z.string().min(1, 'Plain text body is required'),
  is_default: z.boolean().optional(),
  contact_types: z.array(z.string()),
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
  const [showPrefillPrompt, setShowPrefillPrompt] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    control,
    formState: { errors },
  } = useForm<TemplateForm>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      reason: 'expense_report',
      is_default: false,
      contact_types: [],
    },
  })

  const watchSubject = watch('subject')
  const watchBodyHtml = watch('body_html')
  const watchBodyText = watch('body_text')
  const watchReason = watch('reason')

  // Find the current reason's variables
  const currentReason = useMemo(
    () => reasons.find((r) => r.reason === watchReason),
    [reasons, watchReason],
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
          contact_types: template.contact_types || [],
        })
        setShowPrefillPrompt(false)
      } else {
        reset({
          name: '',
          reason: 'expense_report',
          subject: '',
          body_html: '',
          body_text: '',
          is_default: false,
          contact_types: ['billing'], // Default to billing for expense report templates
        })
        // Show prefill prompt for new templates
        setShowPrefillPrompt(true)
      }
      setPreview(null)
      setActiveTab('edit')
    }
  }, [isOpen, template, reset])

  const loadDefaultContent = async () => {
    try {
      const defaultContent = await api.get<{
        name: string
        subject: string
        body_html: string
        body_text: string
      }>(`/email-templates/default-content/${watchReason}`)
      reset({
        name: `${defaultContent.name} (Copy)`,
        reason: watchReason,
        subject: defaultContent.subject,
        body_html: defaultContent.body_html,
        body_text: defaultContent.body_text,
        is_default: false,
        contact_types: watchReason === 'expense_report' ? ['billing'] : [],
      })
      setShowPrefillPrompt(false)
    } catch (e) {
      setError(errorMessage(e, 'Failed to load default template content'))
    }
  }

  const skipPrefill = () => {
    setShowPrefillPrompt(false)
  }

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
        contact_types: data.contact_types as ContactType[],
      }

      if (template) {
        await api.put(`/email-templates/${template.id}`, payload)
      } else {
        await api.post('/email-templates', payload)
      }
      onSaved()
    } catch (e) {
      setError(errorMessage(e, 'Failed to save template'))
    } finally {
      setIsSaving(false)
    }
  }

  const reasonOptions = reasons.map((r) => ({
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

          {error && (
            <Alert variant="error" className="mb-4">
              {error}
            </Alert>
          )}

          {showPrefillPrompt && !template && (
            <Alert variant="info" className="mb-4">
              <div className="flex items-center justify-between">
                <span>Would you like to start with the default template?</span>
                <div className="flex gap-2 ml-4">
                  <Button size="sm" onClick={loadDefaultContent}>
                    Use Default
                  </Button>
                  <Button size="sm" variant="secondary" onClick={skipPrefill}>
                    Start Empty
                  </Button>
                </div>
              </div>
            </Alert>
          )}

          {activeTab === 'edit' ? (
            <form onSubmit={handleSubmit(onSubmit)} className="flex-1 flex flex-col space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input label="Template Name" {...register('name')} error={errors.name?.message} />
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
                <label htmlFor="body_html" className="block text-sm font-medium text-gray-700 mb-1">
                  HTML Body
                </label>
                <textarea
                  id="body_html"
                  {...register('body_html')}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm resize-none"
                  placeholder="<p>Dear {{company.recipient_name}},</p>..."
                />
                {errors.body_html && (
                  <p className="mt-1 text-sm text-red-600">{errors.body_html.message}</p>
                )}
              </div>

              <div className="flex-1 flex flex-col min-h-0">
                <label htmlFor="body_text" className="block text-sm font-medium text-gray-700 mb-1">
                  Plain Text Body
                </label>
                <textarea
                  id="body_text"
                  {...register('body_text')}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono text-sm resize-none"
                  placeholder="Dear {{company.recipient_name}},..."
                />
                {errors.body_text && (
                  <p className="mt-1 text-sm text-red-600">{errors.body_text.message}</p>
                )}
              </div>

              <Controller
                name="contact_types"
                control={control}
                render={({ field }) => (
                  <ContactTypeSelect
                    label="Send to Contact Types"
                    value={field.value as ContactType[]}
                    onChange={field.onChange}
                    error={errors.contact_types?.message}
                  />
                )}
              />
              <p className="text-xs text-gray-500 -mt-2">
                When sending emails, recipients will be automatically selected from contacts with
                these types.
              </p>

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
              <EmailTemplatePreview isLoading={isLoadingPreview} preview={preview} />
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

        <EmailTemplateVariables reason={currentReason} />
      </div>
    </Modal>
  )
}
