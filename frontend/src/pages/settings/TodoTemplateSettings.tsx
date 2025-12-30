// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { todoTemplatesApi } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type {
  OffsetReference,
  TemplateSet,
  TodoCategory,
  TodoTemplate,
  TodoTemplateCreate,
  TodoTemplateUpdate,
} from '@/types'
import { OFFSET_REFERENCE_LABELS, TODO_CATEGORY_COLORS, TODO_CATEGORY_LABELS } from '@/types'

const categoryOptions = (Object.keys(TODO_CATEGORY_LABELS) as TodoCategory[]).map((cat) => ({
  value: cat,
  label: TODO_CATEGORY_LABELS[cat],
}))

const offsetReferenceOptions = (Object.keys(OFFSET_REFERENCE_LABELS) as OffsetReference[]).map(
  (ref) => ({
    value: ref,
    label: OFFSET_REFERENCE_LABELS[ref],
  }),
)

export function TodoTemplateSettings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [templateSets, setTemplateSets] = useState<TemplateSet[]>([])
  const [expandedSets, setExpandedSets] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<TodoTemplate | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  // Form state
  const [formData, setFormData] = useState<TodoTemplateCreate>({
    title: '',
    description: '',
    category: 'other',
    days_offset: 0,
    offset_reference: 'start_date',
    template_set_name: 'My Templates',
  })

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Todo Templates' }])
  }, [setBreadcrumb])

  const fetchTemplates = useCallback(async () => {
    try {
      const sets = await todoTemplatesApi.getTemplateSets()
      setTemplateSets(sets)
      // Expand user sets by default
      const userSets = sets.filter((s) => !s.is_global).map((s) => s.name)
      setExpandedSets((prev) => new Set([...prev, ...userSets]))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load templates')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTemplates()
  }, [fetchTemplates])

  const toggleSet = (setName: string) => {
    setExpandedSets((prev) => {
      const next = new Set(prev)
      if (next.has(setName)) {
        next.delete(setName)
      } else {
        next.add(setName)
      }
      return next
    })
  }

  const openCreateModal = () => {
    setEditingTemplate(null)
    setFormData({
      title: '',
      description: '',
      category: 'other',
      days_offset: 0,
      offset_reference: 'start_date',
      template_set_name: 'My Templates',
    })
    setIsModalOpen(true)
  }

  const openEditModal = (template: TodoTemplate) => {
    setEditingTemplate(template)
    setFormData({
      title: template.title,
      description: template.description || '',
      category: template.category,
      days_offset: template.days_offset,
      offset_reference: template.offset_reference,
      template_set_name: template.template_set_name,
    })
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingTemplate(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)
    setSuccess(null)

    try {
      if (editingTemplate) {
        const updateData: TodoTemplateUpdate = {
          title: formData.title,
          description: formData.description || null,
          category: formData.category,
          days_offset: formData.days_offset,
          offset_reference: formData.offset_reference,
          template_set_name: formData.template_set_name,
        }
        await todoTemplatesApi.updateTemplate(editingTemplate.id, updateData)
        setSuccess('Template updated successfully')
      } else {
        await todoTemplatesApi.createTemplate(formData)
        setSuccess('Template created successfully')
      }
      await fetchTemplates()
      closeModal()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save template')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (template: TodoTemplate) => {
    if (!confirm(`Are you sure you want to delete "${template.title}"?`)) return

    setError(null)
    setSuccess(null)
    try {
      await todoTemplatesApi.deleteTemplate(template.id)
      setSuccess('Template deleted successfully')
      await fetchTemplates()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete template')
    }
  }

  const formatDaysOffset = (days: number, reference: OffsetReference) => {
    const refLabel = reference === 'start_date' ? 'start' : 'end'
    if (days === 0) return `On event ${refLabel}`
    if (days > 0) return `${days} day${days !== 1 ? 's' : ''} after ${refLabel}`
    return `${Math.abs(days)} day${Math.abs(days) !== 1 ? 's' : ''} before ${refLabel}`
  }

  // Separate global and user templates
  const globalSets = templateSets.filter((s) => s.is_global)
  const userSets = templateSets.filter((s) => !s.is_global)

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Todo Templates</h1>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}
      {success && (
        <Alert variant="success" className="mb-4">
          {success}
        </Alert>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : (
        <>
          {/* Global Templates */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Global Templates (Read-only)</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500 mb-4">
                These are system-provided templates available to all users.
              </p>
              {globalSets.length === 0 ? (
                <p className="text-gray-400 text-center py-4">No global templates available.</p>
              ) : (
                <div className="space-y-3">
                  {globalSets.map((set) => {
                    const isExpanded = expandedSets.has(set.name)
                    return (
                      <div
                        key={set.name}
                        className="border border-gray-200 rounded-lg overflow-hidden"
                      >
                        <button
                          type="button"
                          onClick={() => toggleSet(set.name)}
                          className="flex items-center justify-between w-full p-3 bg-gray-50 text-left hover:bg-gray-100"
                        >
                          <span className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                            {set.name}
                            <span className="text-xs text-gray-400 font-normal">
                              ({set.templates.length} items)
                            </span>
                          </span>
                        </button>

                        {isExpanded && (
                          <div className="divide-y divide-gray-100">
                            {set.templates.map((template) => {
                              const colors = TODO_CATEGORY_COLORS[template.category]
                              return (
                                <div
                                  key={template.id}
                                  className="flex items-center justify-between p-3"
                                >
                                  <div className="flex-1">
                                    <p className="text-sm text-gray-900">{template.title}</p>
                                    {template.description && (
                                      <p className="text-xs text-gray-500 mt-0.5">
                                        {template.description}
                                      </p>
                                    )}
                                  </div>
                                  <span
                                    className={`text-xs px-2 py-0.5 rounded ${colors.bg} ${colors.text} mr-3`}
                                  >
                                    {TODO_CATEGORY_LABELS[template.category]}
                                  </span>
                                  <span className="text-xs text-gray-500 w-32 text-right">
                                    {formatDaysOffset(
                                      template.days_offset,
                                      template.offset_reference,
                                    )}
                                  </span>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* User Templates */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>My Templates</CardTitle>
              <Button onClick={openCreateModal}>
                <Plus className="h-4 w-4 mr-2" />
                New Template
              </Button>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-500 mb-4">
                Create your own custom templates to quickly add todos to events.
              </p>
              {userSets.length === 0 ? (
                <p className="text-gray-400 text-center py-4">
                  No custom templates yet. Click "New Template" to create one.
                </p>
              ) : (
                <div className="space-y-3">
                  {userSets.map((set) => {
                    const isExpanded = expandedSets.has(set.name)
                    return (
                      <div
                        key={set.name}
                        className="border border-gray-200 rounded-lg overflow-hidden"
                      >
                        <button
                          type="button"
                          onClick={() => toggleSet(set.name)}
                          className="flex items-center justify-between w-full p-3 bg-gray-50 text-left hover:bg-gray-100"
                        >
                          <span className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                            {set.name}
                            <span className="text-xs text-gray-400 font-normal">
                              ({set.templates.length} items)
                            </span>
                          </span>
                        </button>

                        {isExpanded && (
                          <div className="divide-y divide-gray-100">
                            {set.templates.map((template) => {
                              const colors = TODO_CATEGORY_COLORS[template.category]
                              return (
                                <div
                                  key={template.id}
                                  className="flex items-center justify-between p-3"
                                >
                                  <div className="flex-1">
                                    <p className="text-sm text-gray-900">{template.title}</p>
                                    {template.description && (
                                      <p className="text-xs text-gray-500 mt-0.5">
                                        {template.description}
                                      </p>
                                    )}
                                  </div>
                                  <span
                                    className={`text-xs px-2 py-0.5 rounded ${colors.bg} ${colors.text} mr-3`}
                                  >
                                    {TODO_CATEGORY_LABELS[template.category]}
                                  </span>
                                  <span className="text-xs text-gray-500 w-32 text-right mr-3">
                                    {formatDaysOffset(
                                      template.days_offset,
                                      template.offset_reference,
                                    )}
                                  </span>
                                  <div className="flex gap-1">
                                    <button
                                      type="button"
                                      onClick={() => openEditModal(template)}
                                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                                      title="Edit template"
                                    >
                                      <Pencil className="h-4 w-4" />
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => handleDelete(template)}
                                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                                      title="Delete template"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </button>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={editingTemplate ? 'Edit Template' : 'New Template'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Title"
            value={formData.title}
            onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
            required
          />

          <Input
            label="Description (optional)"
            value={formData.description || ''}
            onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
          />

          <Select
            label="Category"
            value={formData.category}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, category: e.target.value as TodoCategory }))
            }
            options={categoryOptions}
          />

          <Input
            label="Template Set Name"
            value={formData.template_set_name}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, template_set_name: e.target.value }))
            }
            required
            placeholder="e.g., Client Visit, Team Meeting"
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              type="number"
              label="Days Offset"
              value={formData.days_offset}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  days_offset: parseInt(e.target.value, 10) || 0,
                }))
              }
              description="Negative = before, Positive = after"
            />

            <Select
              label="Relative To"
              value={formData.offset_reference}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  offset_reference: e.target.value as OffsetReference,
                }))
              }
              options={offsetReferenceOptions}
            />
          </div>

          <p className="text-sm text-gray-500">
            Due date:{' '}
            <strong>
              {formatDaysOffset(
                formData.days_offset ?? 0,
                formData.offset_reference ?? 'start_date',
              )}
            </strong>
          </p>

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSaving}>
              {editingTemplate ? 'Save Changes' : 'Create Template'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
