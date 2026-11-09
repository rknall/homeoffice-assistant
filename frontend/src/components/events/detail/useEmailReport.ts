// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useState } from 'react'
import { api, errorMessage } from '@/api/client'
import type { EmailTemplate, Event, TemplatePreviewResponse } from '@/types'

/** State and actions of the "Email Expense Report" dialog. */
export function useEmailReport(
  id: string | undefined,
  event: Event | null,
  reportExpenseIds: string[] | null,
) {
  const [isOpen, setIsOpen] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [emailAddress, setEmailAddress] = useState('')
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [preview, setPreview] = useState<TemplatePreviewResponse | null>(null)
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)

  const loadPreview = async (template: EmailTemplate) => {
    if (!id) return
    setIsLoadingPreview(true)
    try {
      const response = await api.post<TemplatePreviewResponse>('/email-templates/preview', {
        subject: template.subject,
        body_html: template.body_html,
        body_text: template.body_text,
        reason: template.reason,
        event_id: id,
        expense_ids: reportExpenseIds,
      })
      setPreview(response)
    } catch {
      setPreview(null)
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const open = async () => {
    setEmailAddress('')
    setResult(null)
    setSelectedTemplateId(null)
    setPreview(null)
    setIsOpen(true)

    // Fetch available templates
    setIsLoadingTemplates(true)
    try {
      const params = new URLSearchParams({ reason: 'expense_report' })
      if (event?.company_id) {
        params.append('company_id', event.company_id)
      }
      const loaded = await api.get<EmailTemplate[]>(`/email-templates?${params.toString()}`)
      setTemplates(loaded)

      // Auto-select default template
      const defaultTemplate =
        loaded.find((t) => t.company_id === event?.company_id && t.is_default) ||
        loaded.find((t) => t.company_id === null && t.is_default) ||
        loaded[0]

      if (defaultTemplate) {
        setSelectedTemplateId(defaultTemplate.id)
        loadPreview(defaultTemplate)
      }
    } catch {
      setTemplates([])
    } finally {
      setIsLoadingTemplates(false)
    }
  }

  const close = () => {
    setIsOpen(false)
    setResult(null)
  }

  const changeTemplate = (templateId: string) => {
    setSelectedTemplateId(templateId)
    const template = templates.find((t) => t.id === templateId)
    if (template) {
      loadPreview(template)
    } else {
      setPreview(null)
    }
  }

  const send = async () => {
    if (!id) return
    setIsSending(true)
    setResult(null)
    try {
      const response = await api.post<{ success: boolean; message: string }>(
        `/events/${id}/expense-report/send`,
        {
          recipient_emails: emailAddress ? [emailAddress] : null,
          template_id: selectedTemplateId,
          expense_ids: reportExpenseIds,
        },
      )
      setResult(response)
      if (response.success) {
        setTimeout(() => {
          setIsOpen(false)
        }, 2000)
      }
    } catch (e) {
      setResult({ success: false, message: errorMessage(e, 'Failed to send report') })
    } finally {
      setIsSending(false)
    }
  }

  return {
    isOpen,
    isSending,
    emailAddress,
    setEmailAddress,
    result,
    selectedTemplateId,
    templates,
    preview,
    isLoadingTemplates,
    isLoadingPreview,
    open,
    close,
    changeTemplate,
    send,
  }
}

export type EmailReportState = ReturnType<typeof useEmailReport>
