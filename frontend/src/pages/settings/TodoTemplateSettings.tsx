// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { todoTemplatesApi } from '@/api/client'
import { TemplateSetList } from '@/components/settings/TemplateSetList'
import { TodoTemplateFormModal } from '@/components/settings/TodoTemplateFormModal'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { confirmAction } from '@/stores/confirm'
import type { TemplateSet, TodoTemplate, TodoTemplateCreate, TodoTemplateUpdate } from '@/types'

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
    if (
      !(await confirmAction({
        title: 'Delete todo template',
        message: `Are you sure you want to delete "${template.title}"?`,
        confirmLabel: 'Delete',
      }))
    )
      return

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
                <TemplateSetList
                  sets={globalSets}
                  expandedSets={expandedSets}
                  onToggle={toggleSet}
                />
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
                <TemplateSetList
                  sets={userSets}
                  expandedSets={expandedSets}
                  onToggle={toggleSet}
                  onEdit={openEditModal}
                  onDelete={handleDelete}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}

      <TodoTemplateFormModal
        isOpen={isModalOpen}
        isEditing={editingTemplate !== null}
        isSaving={isSaving}
        formData={formData}
        setFormData={setFormData}
        onSubmit={handleSubmit}
        onClose={closeModal}
      />
    </div>
  )
}
