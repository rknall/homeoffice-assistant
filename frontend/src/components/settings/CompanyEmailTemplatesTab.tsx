// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Pencil, Plus, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ContactTypeBadge } from '@/components/ContactTypeBadge'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { TabPanel } from '@/components/ui/Tabs'
import type { EmailTemplate } from '@/types'

interface CompanyEmailTemplatesTabProps {
  templates: EmailTemplate[]
  hasSmtpIntegration: boolean
  onAdd: () => void
  onEdit: (template: EmailTemplate) => void
  onDelete: (templateId: string) => void
}

export function CompanyEmailTemplatesTab({
  templates,
  hasSmtpIntegration,
  onAdd,
  onEdit,
  onDelete,
}: CompanyEmailTemplatesTabProps) {
  return (
    <TabPanel value="templates" className="bg-white rounded-b-lg shadow">
      {!hasSmtpIntegration && (
        <Alert variant="warning" className="m-6 mb-0">
          No email integration has been configured. Email templates cannot be used until you{' '}
          <Link to="/settings/integrations" className="font-medium underline hover:no-underline">
            configure an SMTP server
          </Link>
          .
        </Alert>
      )}
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Email Templates</h3>
        <Button onClick={onAdd}>
          <Plus className="h-4 w-4 mr-2" />
          Add Template
        </Button>
      </div>
      <div className="p-6">
        {templates.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No company-specific email templates. This company will use global templates.
          </p>
        ) : (
          <div className="divide-y divide-gray-200">
            {templates.map((template) => (
              <div key={template.id} className="flex items-center justify-between py-4">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-900">{template.name}</h4>
                  <p className="text-sm text-gray-500">
                    {template.reason === 'expense_report' && 'Expense Report'}
                    {template.is_default && ' (Default)'}
                  </p>
                  {template.contact_types && template.contact_types.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {template.contact_types.map((type) => (
                        <ContactTypeBadge key={type} type={type} size="sm" />
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {template.is_default && <Badge variant="success">Default</Badge>}
                  <button
                    type="button"
                    onClick={() => onEdit(template)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    title="Edit template"
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(template.id)}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Delete template"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </TabPanel>
  )
}
