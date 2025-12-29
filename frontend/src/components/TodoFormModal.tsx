// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import type { Todo, TodoCategory } from '@/types'
import { TODO_CATEGORY_LABELS } from '@/types'

const todoSchema = z.object({
  title: z.string().min(1, 'Title is required').max(200, 'Title is too long'),
  description: z.string().optional(),
  due_date: z.string().optional(),
  category: z.enum([
    'travel',
    'accommodation',
    'preparation',
    'equipment',
    'contacts',
    'followup',
    'other',
  ]),
})

type TodoFormData = z.infer<typeof todoSchema>

const categoryOptions: Array<{ value: TodoCategory; label: string }> = [
  { value: 'travel', label: TODO_CATEGORY_LABELS.travel },
  { value: 'accommodation', label: TODO_CATEGORY_LABELS.accommodation },
  { value: 'preparation', label: TODO_CATEGORY_LABELS.preparation },
  { value: 'equipment', label: TODO_CATEGORY_LABELS.equipment },
  { value: 'contacts', label: TODO_CATEGORY_LABELS.contacts },
  { value: 'followup', label: TODO_CATEGORY_LABELS.followup },
  { value: 'other', label: TODO_CATEGORY_LABELS.other },
]

interface TodoFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: TodoFormData) => Promise<void>
  todo?: Todo | null
  isLoading?: boolean
}

export function TodoFormModal({
  isOpen,
  onClose,
  onSubmit,
  todo,
  isLoading = false,
}: TodoFormModalProps) {
  const isEditing = !!todo

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TodoFormData>({
    resolver: zodResolver(todoSchema),
    defaultValues: {
      title: '',
      description: '',
      due_date: '',
      category: 'other',
    },
  })

  // Reset form when modal opens/closes or todo changes
  useEffect(() => {
    if (isOpen) {
      if (todo) {
        reset({
          title: todo.title,
          description: todo.description || '',
          due_date: todo.due_date || '',
          category: todo.category,
        })
      } else {
        reset({
          title: '',
          description: '',
          due_date: '',
          category: 'other',
        })
      }
    }
  }, [isOpen, todo, reset])

  const handleFormSubmit = async (data: TodoFormData) => {
    await onSubmit(data)
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={isEditing ? 'Edit Todo' : 'Add Todo'}>
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
        <Input
          label="Title"
          placeholder="Enter todo title..."
          {...register('title')}
          error={errors.title?.message}
        />

        <Textarea
          label="Description"
          placeholder="Optional description..."
          rows={3}
          {...register('description')}
          error={errors.description?.message}
        />

        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Category"
            options={categoryOptions}
            {...register('category')}
            error={errors.category?.message}
          />

          <Input
            label="Due Date"
            type="date"
            {...register('due_date')}
            error={errors.due_date?.message}
          />
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading}>
            {isEditing ? 'Save Changes' : 'Add Todo'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
