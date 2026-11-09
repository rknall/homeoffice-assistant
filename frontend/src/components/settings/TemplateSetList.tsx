// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight, Pencil, Trash2 } from 'lucide-react'
import type { OffsetReference, TemplateSet, TodoTemplate } from '@/types'
import { TODO_CATEGORY_COLORS, TODO_CATEGORY_LABELS } from '@/types'

export function formatDaysOffset(days: number, reference: OffsetReference) {
  const refLabel = reference === 'start_date' ? 'start' : 'end'
  if (days === 0) return `On event ${refLabel}`
  if (days > 0) return `${days} day${days !== 1 ? 's' : ''} after ${refLabel}`
  return `${Math.abs(days)} day${Math.abs(days) !== 1 ? 's' : ''} before ${refLabel}`
}

interface TemplateSetListProps {
  sets: TemplateSet[]
  expandedSets: Set<string>
  onToggle: (setName: string) => void
  /** Show edit and delete buttons (own templates only). */
  onEdit?: (template: TodoTemplate) => void
  onDelete?: (template: TodoTemplate) => void
}

export function TemplateSetList({
  sets,
  expandedSets,
  onToggle,
  onEdit,
  onDelete,
}: TemplateSetListProps) {
  const editable = Boolean(onEdit && onDelete)
  return (
    <div className="space-y-3">
      {sets.map((set) => {
        const isExpanded = expandedSets.has(set.name)
        return (
          <div key={set.name} className="border border-gray-200 rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => onToggle(set.name)}
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
                    <div key={template.id} className="flex items-center justify-between p-3">
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">{template.title}</p>
                        {template.description && (
                          <p className="text-xs text-gray-500 mt-0.5">{template.description}</p>
                        )}
                      </div>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${colors.bg} ${colors.text} mr-3`}
                      >
                        {TODO_CATEGORY_LABELS[template.category]}
                      </span>
                      <span
                        className={`text-xs text-gray-500 w-32 text-right${editable ? ' mr-3' : ''}`}
                      >
                        {formatDaysOffset(template.days_offset, template.offset_reference)}
                      </span>
                      {onEdit && onDelete && (
                        <div className="flex gap-1">
                          <button
                            type="button"
                            onClick={() => onEdit(template)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                            title="Edit template"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => onDelete(template)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                            title="Delete template"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
