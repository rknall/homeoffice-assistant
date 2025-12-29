// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Plus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { TodoFormModal } from '@/components/TodoFormModal'
import { TodoItem } from '@/components/TodoItem'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import type { Todo, TodoCreate, TodoUpdate, Uuid } from '@/types'

interface TodoListProps {
  eventId: Uuid
  onTodoCountChange?: (total: number, incomplete: number) => void
}

export function TodoList({ eventId, onTodoCountChange }: TodoListProps) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const fetchTodos = useCallback(async () => {
    try {
      const data = await api.get<Todo[]>(`/events/${eventId}/todos`)
      setTodos(data)
      // Report counts to parent
      const incomplete = data.filter((t) => !t.completed).length
      onTodoCountChange?.(data.length, incomplete)
    } catch {
      setError('Failed to load todos')
    } finally {
      setIsLoading(false)
    }
  }, [eventId, onTodoCountChange])

  useEffect(() => {
    fetchTodos()
  }, [fetchTodos])

  const handleCreateTodo = async (data: TodoCreate) => {
    setIsSaving(true)
    setError(null)
    try {
      // Clean up empty strings to null for optional fields
      const cleanedData = {
        ...data,
        description: data.description || null,
        due_date: data.due_date || null,
      }
      await api.post(`/events/${eventId}/todos`, cleanedData)
      await fetchTodos()
      setIsModalOpen(false)
    } catch {
      setError('Failed to create todo')
    } finally {
      setIsSaving(false)
    }
  }

  const handleUpdateTodo = async (data: TodoUpdate) => {
    if (!editingTodo) return
    setIsSaving(true)
    setError(null)
    try {
      // Clean up empty strings to null for optional fields
      const cleanedData = {
        ...data,
        description: data.description || null,
        due_date: data.due_date || null,
      }
      await api.put(`/events/${eventId}/todos/${editingTodo.id}`, cleanedData)
      await fetchTodos()
      setEditingTodo(null)
    } catch {
      setError('Failed to update todo')
    } finally {
      setIsSaving(false)
    }
  }

  const handleToggleComplete = async (todo: Todo) => {
    try {
      await api.put(`/events/${eventId}/todos/${todo.id}`, {
        completed: !todo.completed,
      })
      await fetchTodos()
    } catch {
      setError('Failed to update todo')
    }
  }

  const handleDeleteTodo = async (todo: Todo) => {
    if (!confirm(`Are you sure you want to delete "${todo.title}"?`)) return
    try {
      await api.delete(`/events/${eventId}/todos/${todo.id}`)
      await fetchTodos()
    } catch {
      setError('Failed to delete todo')
    }
  }

  const handleEditTodo = (todo: Todo) => {
    setEditingTodo(todo)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingTodo(null)
  }

  // Sort todos: incomplete first (by due date), then completed
  const sortedTodos = [...todos].sort((a, b) => {
    // Completed items go to the bottom
    if (a.completed !== b.completed) {
      return a.completed ? 1 : -1
    }
    // For incomplete items, sort by due date (nulls last)
    if (!a.completed && !b.completed) {
      if (!a.due_date && !b.due_date) return 0
      if (!a.due_date) return 1
      if (!b.due_date) return -1
      return new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
    }
    // For completed items, most recently updated first
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  })

  const incompleteTodos = sortedTodos.filter((t) => !t.completed)
  const completedTodos = sortedTodos.filter((t) => t.completed)

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Todos</h3>
        <Button onClick={() => setIsModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Todo
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {todos.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No todos yet. Add your first todo to track tasks for this event.
        </p>
      ) : (
        <div className="space-y-3">
          {/* Incomplete todos */}
          {incompleteTodos.map((todo) => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onToggleComplete={handleToggleComplete}
              onEdit={handleEditTodo}
              onDelete={handleDeleteTodo}
            />
          ))}

          {/* Completed section divider */}
          {completedTodos.length > 0 && incompleteTodos.length > 0 && (
            <div className="border-t border-gray-200 pt-3 mt-4">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
                Completed
              </p>
            </div>
          )}

          {/* Completed todos */}
          {completedTodos.map((todo) => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onToggleComplete={handleToggleComplete}
              onEdit={handleEditTodo}
              onDelete={handleDeleteTodo}
            />
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      <TodoFormModal
        isOpen={isModalOpen || !!editingTodo}
        onClose={handleCloseModal}
        onSubmit={editingTodo ? handleUpdateTodo : handleCreateTodo}
        todo={editingTodo}
        isLoading={isSaving}
      />
    </div>
  )
}
