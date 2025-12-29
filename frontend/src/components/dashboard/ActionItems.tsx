// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { AlertCircle, FileText } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { useLocale } from '@/stores/locale'
import type { EventNeedingReport, IncompleteTodo } from '@/types'

interface ActionItemsProps {
  reportsNeeded: EventNeedingReport[]
  incompleteTodos: IncompleteTodo[]
  onTodoCompleted?: () => void
}

export function ActionItems({ reportsNeeded, incompleteTodos, onTodoCompleted }: ActionItemsProps) {
  const { formatDate } = useLocale()
  const [completingTodos, setCompletingTodos] = useState<Set<string>>(new Set())
  const hasItems = reportsNeeded.length > 0 || incompleteTodos.length > 0

  const handleCompleteTodo = async (todo: IncompleteTodo) => {
    setCompletingTodos((prev) => new Set(prev).add(todo.id))
    try {
      await api.put(`/events/${todo.event_id}/todos/${todo.id}`, { completed: true })
      onTodoCompleted?.()
    } catch {
      // Error handling - remove from completing state
      setCompletingTodos((prev) => {
        const next = new Set(prev)
        next.delete(todo.id)
        return next
      })
    }
  }

  if (!hasItems) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Action Items</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 text-center py-4">All caught up!</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Action Items</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Reports Due Section */}
        {reportsNeeded.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Reports Due
            </h4>
            <div className="space-y-2">
              {reportsNeeded.map((event) => (
                <Link
                  key={event.event_id}
                  to={`/events/${event.event_id}`}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 group"
                >
                  <div className="p-1.5 rounded bg-amber-100 text-amber-600">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 group-hover:text-blue-600 truncate">
                      {event.event_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {event.expense_count} expense{event.expense_count !== 1 ? 's' : ''} &middot;{' '}
                      {event.currency} {event.total_amount.toFixed(2)}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Pending Tasks Section */}
        {incompleteTodos.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Pending Tasks
            </h4>
            <div className="space-y-2">
              {incompleteTodos.map((todo) => {
                const isCompleting = completingTodos.has(todo.id)
                return (
                  <div
                    key={todo.id}
                    className={`flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 group ${
                      isCompleting ? 'opacity-50' : ''
                    }`}
                  >
                    <Checkbox
                      checked={isCompleting}
                      onCheckedChange={() => handleCompleteTodo(todo)}
                      disabled={isCompleting}
                      className={`h-5 w-5 flex-shrink-0 ${todo.is_overdue ? 'border-red-300' : ''}`}
                      aria-label={`Mark "${todo.title}" as complete`}
                    />
                    {todo.is_overdue && (
                      <div className="p-1 rounded bg-red-100 text-red-600 flex-shrink-0">
                        <AlertCircle className="w-3.5 h-3.5" />
                      </div>
                    )}
                    <Link to={`/events/${todo.event_id}`} className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium truncate group-hover:text-blue-600 ${
                          todo.is_overdue ? 'text-red-700' : 'text-gray-900'
                        }`}
                      >
                        {todo.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {todo.event_name}
                        {todo.due_date && (
                          <>
                            {' '}
                            &middot;{' '}
                            <span className={todo.is_overdue ? 'text-red-500' : ''}>
                              Due {formatDate(todo.due_date)}
                            </span>
                          </>
                        )}
                      </p>
                    </Link>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
