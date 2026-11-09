// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Pencil, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { useLocale } from '@/stores/locale'
import type { Expense } from '@/types'
import { EXPENSE_STATUS_CONFIG } from '@/types'
import { getCategoryLabel, getPaymentTypeLabel } from '@/utils/labels'
import type { ExpenseSelectionState } from './useExpenseSelection'

interface ExpensesTableProps {
  selection: ExpenseSelectionState
  baseCurrency: string | undefined
  onEdit: (expense: Expense) => void
  onDelete: (expenseId: string) => void
}

/** Selectable table of the (filtered) event expenses. */
export function ExpensesTable({ selection, baseCurrency, onEdit, onDelete }: ExpensesTableProps) {
  const { formatDate } = useLocale()
  const { filteredExpenses, selectedExpenses } = selection

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="py-3 px-2 w-10">
              <input
                type="checkbox"
                checked={
                  filteredExpenses.length > 0 && selectedExpenses.size === filteredExpenses.length
                }
                onChange={selection.toggleSelectAll}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                aria-label="Select all expenses"
              />
            </th>
            <th className="text-left py-3 px-4 font-medium text-gray-500">Date</th>
            <th className="text-left py-3 px-4 font-medium text-gray-500">Description</th>
            <th className="text-left py-3 px-4 font-medium text-gray-500">Category</th>
            <th className="text-left py-3 px-4 font-medium text-gray-500">Payment</th>
            <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
            <th className="text-right py-3 px-4 font-medium text-gray-500">Amount</th>
            <th className="py-3 px-4"></th>
          </tr>
        </thead>
        <tbody>
          {filteredExpenses.map((expense) => {
            const statusConfig = EXPENSE_STATUS_CONFIG[expense.status]
            return (
              <tr
                key={expense.id}
                className={`border-b border-gray-100 hover:bg-gray-50 ${
                  selectedExpenses.has(expense.id) ? 'bg-blue-50' : ''
                }`}
              >
                <td className="py-3 px-2">
                  <input
                    type="checkbox"
                    checked={selectedExpenses.has(expense.id)}
                    onChange={() => selection.toggleExpenseSelection(expense.id)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    aria-label={`Select expense ${expense.description || expense.id}`}
                  />
                </td>
                <td className="py-3 px-4">{formatDate(expense.date)}</td>
                <td className="py-3 px-4">
                  <div className="flex flex-col">
                    <span>{expense.description || '-'}</span>
                    {expense.rejection_reason && (
                      <span className="text-xs text-red-600 mt-0.5">
                        Reason: {expense.rejection_reason}
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <Badge variant="default">{getCategoryLabel(expense.category)}</Badge>
                </td>
                <td className="py-3 px-4">{getPaymentTypeLabel(expense.payment_type)}</td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-1">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${statusConfig.bgColor} ${statusConfig.textColor}`}
                    >
                      {statusConfig.label}
                    </span>
                    {expense.is_private && (
                      <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-purple-100 text-purple-700">
                        Private
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4 text-right font-medium">
                  <div>
                    {Number(expense.amount).toFixed(2)} {expense.currency}
                  </div>
                  {expense.converted_amount && expense.currency !== baseCurrency && (
                    <div
                      className="text-xs text-gray-500"
                      title={`Rate: ${expense.exchange_rate} on ${expense.rate_date}`}
                    >
                      = {Number(expense.converted_amount).toFixed(2)} {baseCurrency}
                    </div>
                  )}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onEdit(expense)}
                      className="text-gray-400 hover:text-blue-600"
                      title="Edit expense"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(expense.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Delete expense"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
