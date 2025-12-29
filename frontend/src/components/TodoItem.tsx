// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Pencil, Trash2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/Checkbox'
import { cn } from '@/lib/utils'
import { useLocale } from '@/stores/locale'
import type { Todo } from '@/types'
import { TODO_CATEGORY_COLORS, TODO_CATEGORY_LABELS } from '@/types'

interface TodoItemProps {
  todo: Todo
  onToggleComplete: (todo: Todo) => void
  onEdit: (todo: Todo) => void
  onDelete: (todo: Todo) => void
}

export function TodoItem({ todo, onToggleComplete, onEdit, onDelete }: TodoItemProps) {
  const { formatDate } = useLocale()
  const isOverdue =
    todo.due_date &&
    !todo.completed &&
    new Date(todo.due_date) < new Date(new Date().toDateString())

  const categoryColors = TODO_CATEGORY_COLORS[todo.category]

  return (
    <div
      className={cn(
        'flex items-start gap-4 p-4 rounded-lg border transition-colors',
        todo.completed
          ? 'bg-gray-50 border-gray-100 opacity-60'
          : isOverdue
            ? 'bg-red-50 border-red-200 hover:bg-red-100'
            : 'bg-gray-50 border-gray-200 hover:bg-gray-100',
      )}
    >
      <Checkbox
        checked={todo.completed}
        onCheckedChange={() => onToggleComplete(todo)}
        className={cn('mt-1 h-5 w-5', isOverdue && !todo.completed && 'border-red-300')}
        aria-label={`Mark "${todo.title}" as ${todo.completed ? 'incomplete' : 'complete'}`}
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              'font-medium',
              todo.completed
                ? 'text-gray-500 line-through'
                : isOverdue
                  ? 'text-red-700'
                  : 'text-gray-900',
            )}
          >
            {todo.title}
          </span>
          <span
            className={cn(
              'px-2 py-0.5 text-xs rounded-full',
              categoryColors.bg,
              categoryColors.text,
            )}
          >
            {TODO_CATEGORY_LABELS[todo.category]}
          </span>
          {isOverdue && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">
              OVERDUE
            </span>
          )}
        </div>

        {todo.description && (
          <p className={cn('text-sm mt-1', todo.completed ? 'text-gray-400' : 'text-gray-600')}>
            {todo.description}
          </p>
        )}

        <p
          className={cn(
            'text-sm mt-1',
            todo.completed ? 'text-gray-400' : isOverdue ? 'text-red-600' : 'text-gray-500',
          )}
        >
          {todo.completed
            ? 'Completed'
            : todo.due_date
              ? `Due: ${formatDate(todo.due_date)}`
              : 'No due date'}
        </p>
      </div>

      <div className="flex gap-2 flex-shrink-0">
        <button
          type="button"
          onClick={() => onEdit(todo)}
          className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
          title="Edit todo"
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => onDelete(todo)}
          className="p-1 text-gray-400 hover:text-red-600 transition-colors"
          title="Delete todo"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
