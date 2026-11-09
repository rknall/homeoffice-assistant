// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Mail } from 'lucide-react'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'
import type { EmailReportState } from './useEmailReport'

/** Dialog that previews and sends the expense report by email. */
export function EmailReportModal({ email }: { email: EmailReportState }) {
  return (
    <Modal isOpen={email.isOpen} onClose={email.close} title="Email Expense Report" size="lg">
      <div className="space-y-4">
        {/* Template Selection */}
        {email.isLoadingTemplates ? (
          <div className="flex items-center gap-2 py-4">
            <Spinner size="sm" />
            <span className="text-sm text-gray-500">Loading templates...</span>
          </div>
        ) : email.templates.length === 0 ? (
          <Alert variant="warning">
            No email templates found. Please configure a template in Settings or Company settings.
          </Alert>
        ) : (
          <Select
            label="Email Template"
            value={email.selectedTemplateId || ''}
            onChange={(e) => email.changeTemplate(e.target.value)}
            options={email.templates.map((t) => ({
              value: t.id,
              label: `${t.name}${t.company_id ? '' : ' (Global)'}${t.is_default ? ' - Default' : ''}`,
            }))}
          />
        )}

        {/* Preview */}
        {email.selectedTemplateId && (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
              <p className="text-sm font-medium text-gray-700">Preview</p>
            </div>
            <div className="p-4 max-h-64 overflow-y-auto">
              {email.isLoadingPreview ? (
                <div className="flex items-center justify-center py-4">
                  <Spinner size="sm" />
                </div>
              ) : email.preview ? (
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Subject</p>
                    <p className="text-gray-900">{email.preview.subject}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase mb-1">Body</p>
                    <div
                      className="text-sm text-gray-700 prose prose-sm max-w-none"
                      // biome-ignore lint/security/noDangerouslySetInnerHtml: Email templates contain trusted, server-rendered HTML
                      // biome-ignore lint/style/useNamingConvention: __html is required by React when setting inner HTML
                      dangerouslySetInnerHTML={{ __html: email.preview.body_html }}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}

        <Input
          label="Recipient Email (optional)"
          type="email"
          value={email.emailAddress}
          onChange={(e) => email.setEmailAddress(e.target.value)}
          description="Leave empty to use company's expense recipient email"
        />

        {email.result && (
          <Alert variant={email.result.success ? 'success' : 'error'}>{email.result.message}</Alert>
        )}
        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={email.close}>
            Cancel
          </Button>
          <Button
            onClick={email.send}
            isLoading={email.isSending}
            disabled={email.templates.length === 0 || !email.selectedTemplateId}
          >
            <Mail className="h-4 w-4 mr-2" />
            Send Report
          </Button>
        </div>
      </div>
    </Modal>
  )
}
