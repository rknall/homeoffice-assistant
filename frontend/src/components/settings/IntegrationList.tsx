// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { CheckCircle, Mail, Pencil, Trash2, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import type { IntegrationConfig } from '@/types'

export type TestResult = { success: boolean; message: string }

interface IntegrationListProps {
  integrations: IntegrationConfig[]
  isLoading: boolean
  testResults: Record<string, TestResult>
  testingId: string | null
  onTest: (id: string) => void
  onSendTestEmail: (id: string) => void
  onEdit: (integration: IntegrationConfig) => void
  onDelete: (id: string) => void
}

export function IntegrationList({
  integrations,
  isLoading,
  testResults,
  testingId,
  onTest,
  onSendTestEmail,
  onEdit,
  onDelete,
}: IntegrationListProps) {
  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    )
  }
  if (integrations.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        No integrations configured. Add your first integration to connect external services.
      </p>
    )
  }
  return (
    <div className="divide-y divide-gray-200">
      {integrations.map((integration) => (
        <div key={integration.id} className="flex items-center justify-between py-4">
          <div>
            <h3 className="font-medium text-gray-900">{integration.name}</h3>
            <p className="text-sm text-gray-500 capitalize">{integration.integration_type}</p>
          </div>
          <div className="flex items-center gap-4">
            {testResults[integration.id] && (
              <div className="flex items-center gap-1">
                {testResults[integration.id].success ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
                <span className="text-sm text-gray-500">{testResults[integration.id].message}</span>
              </div>
            )}
            <Badge variant={integration.is_active ? 'success' : 'default'}>
              {integration.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onTest(integration.id)}
              isLoading={testingId === integration.id}
            >
              Test
            </Button>
            {integration.integration_type === 'smtp' && (
              <Button size="sm" variant="secondary" onClick={() => onSendTestEmail(integration.id)}>
                <Mail className="h-4 w-4 mr-1" />
                Send Test
              </Button>
            )}
            <button
              type="button"
              onClick={() => onEdit(integration)}
              aria-label="Edit integration"
              className="p-1 text-gray-400 hover:text-blue-600"
            >
              <Pencil className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => onDelete(integration.id)}
              className="p-1 text-gray-400 hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
