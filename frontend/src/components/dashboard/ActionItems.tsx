// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { AlertCircle, CheckSquare, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useLocale } from '@/stores/locale'
import type { EventNeedingReport, IncompleteTodo } from '@/types'

interface ActionItemsProps {
  reportsNeeded: EventNeedingReport[]
  incompleteTodos: IncompleteTodo[]
}

export function ActionItems({ reportsNeeded, incompleteTodos }: ActionItemsProps) {
  const { formatDate } = useLocale()
  const hasItems = reportsNeeded.length > 0 || incompleteTodos.length > 0

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
              {incompleteTodos.map((todo) => (
                <Link
                  key={todo.id}
                  to={`/events/${todo.event_id}`}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 group"
                >
                  <div
                    className={`p-1.5 rounded ${
                      todo.is_overdue ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'
                    }`}
                  >
                    {todo.is_overdue ? (
                      <AlertCircle className="w-4 h-4" />
                    ) : (
                      <CheckSquare className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
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
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
