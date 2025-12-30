// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { todoTemplatesApi } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { useLocale } from '@/stores/locale'
import type { Event, TemplateSetWithComputedDates, TodoTemplateWithComputedDate } from '@/types'
import { TODO_CATEGORY_COLORS, TODO_CATEGORY_LABELS } from '@/types'

interface TodoTemplatePickerModalProps {
  isOpen: boolean
  onClose: () => void
  event: Event
  onApply: () => void
}

export function TodoTemplatePickerModal({
  isOpen,
  onClose,
  event,
  onApply,
}: TodoTemplatePickerModalProps) {
  const { formatDate } = useLocale()
  const [templateSets, setTemplateSets] = useState<TemplateSetWithComputedDates[]>([])
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<Set<string>>(new Set())
  const [expandedSets, setExpandedSets] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [isApplying, setIsApplying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load templates when modal opens
  useEffect(() => {
    if (isOpen) {
      setIsLoading(true)
      setError(null)
      setSelectedTemplateIds(new Set())
      todoTemplatesApi
        .getTemplatesForEvent(event.id)
        .then((sets) => {
          setTemplateSets(sets)
          // Expand first set by default
          if (sets.length > 0) {
            setExpandedSets(new Set([sets[0].name]))
          }
        })
        .catch((err) => {
          setError(err.message || 'Failed to load templates')
        })
        .finally(() => {
          setIsLoading(false)
        })
    }
  }, [isOpen, event.id])

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

  const toggleTemplate = (templateId: string) => {
    setSelectedTemplateIds((prev) => {
      const next = new Set(prev)
      if (next.has(templateId)) {
        next.delete(templateId)
      } else {
        next.add(templateId)
      }
      return next
    })
  }

  const selectAllInSet = (templates: TodoTemplateWithComputedDate[]) => {
    setSelectedTemplateIds((prev) => {
      const next = new Set(prev)
      for (const t of templates) {
        next.add(t.id)
      }
      return next
    })
  }

  const deselectAllInSet = (templates: TodoTemplateWithComputedDate[]) => {
    setSelectedTemplateIds((prev) => {
      const next = new Set(prev)
      for (const t of templates) {
        next.delete(t.id)
      }
      return next
    })
  }

  const isAllSelectedInSet = (templates: TodoTemplateWithComputedDate[]): boolean => {
    return templates.every((t) => selectedTemplateIds.has(t.id))
  }

  const handleApply = async () => {
    if (selectedTemplateIds.size === 0) return

    setIsApplying(true)
    setError(null)

    try {
      await todoTemplatesApi.applyTemplatesToEvent(event.id, {
        template_ids: Array.from(selectedTemplateIds),
      })
      onApply()
      onClose()
    } catch (err) {
      setError((err as Error).message || 'Failed to apply templates')
    } finally {
      setIsApplying(false)
    }
  }

  // Get selected templates for summary
  const selectedTemplates = templateSets
    .flatMap((s) => s.templates)
    .filter((t) => selectedTemplateIds.has(t.id))

  const dueDates = selectedTemplates
    .map((t) => t.computed_due_date)
    .filter((d): d is string => d !== null)
    .sort()

  const minDate = dueDates.length > 0 ? dueDates[0] : null
  const maxDate = dueDates.length > 0 ? dueDates[dueDates.length - 1] : null

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Todos from Template" size="xl">
      {/* Event context */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-sm font-medium text-gray-900">{event.name}</p>
        <p className="text-xs text-gray-500">
          {formatDate(event.start_date)} - {formatDate(event.end_date)}
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {/* Error state */}
      {error && <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>}

      {/* Template sets */}
      {!isLoading && templateSets.length === 0 && (
        <div className="py-8 text-center text-gray-500">No templates available.</div>
      )}

      {!isLoading && templateSets.length > 0 && (
        <div className="space-y-3 max-h-80 overflow-y-auto">
          {templateSets.map((set) => {
            const isExpanded = expandedSets.has(set.name)
            const allSelected = isAllSelectedInSet(set.templates)

            return (
              <div key={set.name} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Set header */}
                <div className="flex items-center justify-between p-3 bg-gray-50">
                  <button
                    type="button"
                    onClick={() => toggleSet(set.name)}
                    className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    {set.name}
                    {set.is_global && (
                      <span className="text-xs text-gray-400 font-normal">(Global)</span>
                    )}
                    <span className="text-xs text-gray-400 font-normal">
                      ({set.templates.length} items)
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      allSelected ? deselectAllInSet(set.templates) : selectAllInSet(set.templates)
                    }
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    {allSelected ? 'Deselect All' : 'Select All'}
                  </button>
                </div>

                {/* Template items */}
                {isExpanded && (
                  <div className="divide-y divide-gray-100">
                    {set.templates.map((template) => {
                      const isSelected = selectedTemplateIds.has(template.id)
                      const colors = TODO_CATEGORY_COLORS[template.category]

                      return (
                        <label
                          key={template.id}
                          className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleTemplate(template.id)}
                            className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                          />
                          <div className="flex-1 min-w-0">
                            <span className="text-sm text-gray-900">{template.title}</span>
                          </div>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${colors.bg} ${colors.text}`}
                          >
                            {TODO_CATEGORY_LABELS[template.category]}
                          </span>
                          <span className="text-xs text-gray-500 w-20 text-right">
                            {template.computed_due_date
                              ? formatDate(template.computed_due_date)
                              : '-'}
                          </span>
                        </label>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Summary and actions */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm font-medium text-gray-700">
              Selected: {selectedTemplateIds.size} todo{selectedTemplateIds.size !== 1 ? 's' : ''}
            </p>
            {minDate && maxDate && (
              <p className="text-xs text-gray-500">
                Due dates: {formatDate(minDate)}
                {minDate !== maxDate && ` - ${formatDate(maxDate)}`}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-3 justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleApply}
            disabled={selectedTemplateIds.size === 0}
            isLoading={isApplying}
          >
            Add {selectedTemplateIds.size > 0 ? `${selectedTemplateIds.size} ` : ''}Todo
            {selectedTemplateIds.size !== 1 ? 's' : ''}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
