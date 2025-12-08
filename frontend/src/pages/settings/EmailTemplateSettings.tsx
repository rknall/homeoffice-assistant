// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect, useState } from 'react'
import { Plus, Trash2, Pencil } from 'lucide-react'
import { api } from '@/api/client'
import type { EmailTemplate, TemplateReason } from '@/types'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'
import { EmailTemplateEditor } from '@/components/EmailTemplateEditor'

export function EmailTemplateSettings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [reasons, setReasons] = useState<TemplateReason[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setBreadcrumb([
      { label: 'Settings', href: '/settings' },
      { label: 'Email Templates' },
    ])
  }, [setBreadcrumb])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      const [templatesData, reasonsData] = await Promise.all([
        api.get<EmailTemplate[]>('/email-templates/global'),
        api.get<TemplateReason[]>('/email-templates/reasons'),
      ])
      setTemplates(templatesData)
      setReasons(reasonsData)
    } catch {
      setError('Failed to load email templates')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const openEditor = (template: EmailTemplate | null = null) => {
    setEditingTemplate(template)
    setIsEditorOpen(true)
  }

  const closeEditor = () => {
    setIsEditorOpen(false)
    setEditingTemplate(null)
  }

  const handleSaved = async () => {
    await fetchData()
    closeEditor()
  }

  const deleteTemplate = async (id: string) => {
    if (templates.length <= 1) {
      setError('Cannot delete the last email template. At least one template must exist.')
      return
    }
    if (!confirm('Are you sure you want to delete this email template?')) return
    try {
      await api.delete(`/email-templates/${id}`)
      await fetchData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete template')
    }
  }

  const isLastTemplate = templates.length <= 1

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Email Templates</h1>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Global Templates</CardTitle>
          <Button onClick={() => openEditor()}>
            <Plus className="h-4 w-4 mr-2" />
            Add Template
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : templates.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No global email templates configured. Add your first template.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="flex items-center justify-between py-4"
                >
                  <div>
                    <h3 className="font-medium text-gray-900">{template.name}</h3>
                    <p className="text-sm text-gray-500">
                      {reasons.find(r => r.reason === template.reason)?.description || template.reason}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    {template.is_default && (
                      <Badge variant="info">Default</Badge>
                    )}
                    <button
                      onClick={() => openEditor(template)}
                      className="p-1 text-gray-400 hover:text-blue-600"
                      title="Edit template"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => deleteTemplate(template.id)}
                      className={`p-1 ${isLastTemplate ? 'text-gray-200 cursor-not-allowed' : 'text-gray-400 hover:text-red-600'}`}
                      title={isLastTemplate ? 'Cannot delete the last template' : 'Delete template'}
                      disabled={isLastTemplate}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <EmailTemplateEditor
        isOpen={isEditorOpen}
        onClose={closeEditor}
        onSaved={handleSaved}
        template={editingTemplate}
        reasons={reasons}
      />
    </div>
  )
}
