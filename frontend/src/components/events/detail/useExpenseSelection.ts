// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useState } from 'react'
import { api, errorMessage } from '@/api/client'
import type { Expense, ExpenseStatus } from '@/types'

/** Status filter, row selection and bulk status updates of the expense list. */
export function useExpenseSelection(
  id: string | undefined,
  expenses: Expense[],
  refresh: () => Promise<void>,
  setError: (message: string | null) => void,
) {
  const [statusFilter, setStatusFilter] = useState<ExpenseStatus | 'all'>('all')
  const [selectedExpenses, setSelectedExpenses] = useState<Set<string>>(new Set())
  const [isUpdatingBulkStatus, setIsUpdatingBulkStatus] = useState(false)

  const filteredExpenses = expenses.filter(
    (e) => statusFilter === 'all' || e.status === statusFilter,
  )
  // Reports cover the selected expenses, or all open ones when nothing is selected
  const reportExpenseIds = selectedExpenses.size > 0 ? Array.from(selectedExpenses) : null

  const toggleExpenseSelection = (expenseId: string) => {
    setSelectedExpenses((prev) => {
      const next = new Set(prev)
      if (next.has(expenseId)) {
        next.delete(expenseId)
      } else {
        next.add(expenseId)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedExpenses.size === filteredExpenses.length) {
      setSelectedExpenses(new Set())
    } else {
      setSelectedExpenses(new Set(filteredExpenses.map((e) => e.id)))
    }
  }

  const clearSelection = () => {
    setSelectedExpenses(new Set())
  }

  const updateBulkStatus = async (status: ExpenseStatus, rejectionReason?: string) => {
    if (!id || selectedExpenses.size === 0) return
    setIsUpdatingBulkStatus(true)
    try {
      await api.post(`/events/${id}/expenses/bulk-status`, {
        expense_ids: Array.from(selectedExpenses),
        status,
        rejection_reason: rejectionReason || null,
      })
      await refresh()
      clearSelection()
    } catch (e) {
      setError(errorMessage(e, 'Failed to update expense status'))
    } finally {
      setIsUpdatingBulkStatus(false)
    }
  }

  return {
    statusFilter,
    setStatusFilter,
    selectedExpenses,
    filteredExpenses,
    reportExpenseIds,
    isUpdatingBulkStatus,
    toggleExpenseSelection,
    toggleSelectAll,
    clearSelection,
    updateBulkStatus,
  }
}

export type ExpenseSelectionState = ReturnType<typeof useExpenseSelection>
