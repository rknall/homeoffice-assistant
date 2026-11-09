// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Download, Mail, Plus } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { Expense, ExpenseStatus } from '@/types'
import { ExpensesTable } from './ExpensesTable'
import type { ExpenseSelectionState } from './useExpenseSelection'

interface ExpensesTabProps {
  expenses: Expense[]
  selection: ExpenseSelectionState
  baseCurrency: string | undefined
  onExport: () => void
  onEmail: () => void
  onAdd: () => void
  onReject: () => void
  onEdit: (expense: Expense) => void
  onDelete: (expenseId: string) => void
}

/** Expenses tab: report actions, status filter, bulk action bar and table. */
export function ExpensesTab({
  expenses,
  selection,
  baseCurrency,
  onExport,
  onEmail,
  onAdd,
  onReject,
  onEdit,
  onDelete,
}: ExpensesTabProps) {
  const { statusFilter, selectedExpenses, isUpdatingBulkStatus } = selection

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Expenses</h3>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={onExport}>
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
          <Button variant="secondary" onClick={onEmail}>
            <Mail className="h-4 w-4 mr-2" />
            Email Report
          </Button>
          <Button onClick={onAdd}>
            <Plus className="h-4 w-4 mr-2" />
            Add Expense
          </Button>
        </div>
      </div>

      {/* Status Filter */}
      {expenses.length > 0 && (
        <div className="flex items-center gap-4 mb-4">
          <label htmlFor="status-filter" className="text-sm font-medium text-gray-600">
            Filter by status:
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => selection.setStatusFilter(e.target.value as ExpenseStatus | 'all')}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="submitted">Submitted</option>
            <option value="reimbursed">Reimbursed</option>
            <option value="rejected">Rejected</option>
          </select>
          {statusFilter !== 'all' && (
            <span className="text-sm text-gray-500">
              Showing {selection.filteredExpenses.length} of {expenses.length}
            </span>
          )}
        </div>
      )}

      {/* Bulk Action Bar */}
      {selectedExpenses.size > 0 && (
        <div className="flex items-center gap-4 mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <span className="text-sm font-medium text-blue-800">
            {selectedExpenses.size} expense{selectedExpenses.size !== 1 ? 's' : ''} selected
          </span>
          <div className="flex gap-2 ml-auto">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => selection.updateBulkStatus('submitted')}
              disabled={isUpdatingBulkStatus}
            >
              Mark Submitted
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => selection.updateBulkStatus('reimbursed')}
              disabled={isUpdatingBulkStatus}
            >
              Mark Reimbursed
            </Button>
            <Button size="sm" variant="danger" onClick={onReject} disabled={isUpdatingBulkStatus}>
              Mark Rejected
            </Button>
            <Button size="sm" variant="secondary" onClick={selection.clearSelection}>
              Clear
            </Button>
          </div>
        </div>
      )}

      {expenses.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No expenses yet. Add your first expense to get started.
        </p>
      ) : (
        <ExpensesTable
          selection={selection}
          baseCurrency={baseCurrency}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      )}
    </>
  )
}
