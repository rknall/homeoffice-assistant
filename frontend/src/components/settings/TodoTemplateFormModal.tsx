// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { Dispatch, SetStateAction } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import type { OffsetReference, TodoCategory, TodoTemplateCreate } from '@/types'
import { OFFSET_REFERENCE_LABELS, TODO_CATEGORY_LABELS } from '@/types'
import { labelOptions } from '@/utils/labels'
import { formatDaysOffset } from './TemplateSetList'

const categoryOptions = labelOptions(TODO_CATEGORY_LABELS)

const offsetReferenceOptions = labelOptions(OFFSET_REFERENCE_LABELS)

interface TodoTemplateFormModalProps {
  isOpen: boolean
  isEditing: boolean
  isSaving: boolean
  formData: TodoTemplateCreate
  setFormData: Dispatch<SetStateAction<TodoTemplateCreate>>
  onSubmit: (e: React.FormEvent) => void
  onClose: () => void
}

export function TodoTemplateFormModal({
  isOpen,
  isEditing,
  isSaving,
  formData,
  setFormData,
  onSubmit,
  onClose,
}: TodoTemplateFormModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={isEditing ? 'Edit Template' : 'New Template'}>
      <form onSubmit={onSubmit} className="space-y-4">
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
          onChange={(e) => setFormData((prev) => ({ ...prev, template_set_name: e.target.value }))}
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
            {formatDaysOffset(formData.days_offset ?? 0, formData.offset_reference ?? 'start_date')}
          </strong>
        </p>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving}>
            {isEditing ? 'Save Changes' : 'Create Template'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
