// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useEffect, useState } from 'react'
import { downloadFile } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import type { Expense, ExpenseStatus } from '@/types'
import { EXPENSE_STATUS_CONFIG } from '@/types'

type SelectionMode = 'pending' | 'selected' | 'all'

interface GenerateReportModalProps {
  isOpen: boolean
  onClose: () => void
  eventId: string
  eventName: string
  expenses: Expense[]
  baseCurrency: string
  onReportGenerated?: () => void
}

export function GenerateReportModal({
  isOpen,
  onClose,
  eventId,
  eventName,
  expenses,
  baseCurrency,
  onReportGenerated,
}: GenerateReportModalProps) {
  const [selectionMode, setSelectionMode] = useState<SelectionMode>('pending')
  const [selectedExpenses, setSelectedExpenses] = useState<Set<string>>(new Set())
  const [markAsSubmitted, setMarkAsSubmitted] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filter out private expenses (they are excluded from official reports)
  const reportableExpenses = expenses.filter((e) => !e.is_private)

  // Categorize expenses by status (only non-private expenses)
  const pendingExpenses = reportableExpenses.filter((e) => e.status === 'pending')
  const submittedExpenses = reportableExpenses.filter((e) => e.status === 'submitted')
  const rejectedExpenses = reportableExpenses.filter((e) => e.status === 'rejected')

  // Get expenses based on selection mode (only non-private expenses)
  const getSelectedExpenses = (): Expense[] => {
    switch (selectionMode) {
      case 'pending':
        return pendingExpenses
      case 'all':
        return reportableExpenses
      case 'selected':
        return reportableExpenses.filter((e) => selectedExpenses.has(e.id))
    }
  }

  const expensesToInclude = getSelectedExpenses()
  const total = expensesToInclude.reduce(
    (sum, e) => sum + Number(e.converted_amount ?? e.amount),
    0,
  )

  // Reset selection when mode changes
  useEffect(() => {
    if (selectionMode !== 'selected') {
      setSelectedExpenses(new Set())
    }
  }, [selectionMode])

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectionMode('pending')
      setSelectedExpenses(new Set())
      setMarkAsSubmitted(true)
      setError(null)
    }
  }, [isOpen])

  const toggleExpense = (expenseId: string) => {
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

  const handleGenerate = async () => {
    if (expensesToInclude.length === 0) {
      setError('No expenses selected')
      return
    }

    setIsGenerating(true)
    setError(null)

    try {
      const filename = `expense_report_${eventName.toLowerCase().replace(/\s+/g, '_')}.zip`

      // Build request body
      const body = {
        expense_ids: selectionMode === 'all' ? null : expensesToInclude.map((e) => e.id),
        mark_as_submitted: markAsSubmitted,
        submission_method: 'download',
        notes: null,
      }

      await downloadFile(`/events/${eventId}/expense-report/generate`, filename, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      onReportGenerated?.()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate report')
    } finally {
      setIsGenerating(false)
    }
  }

  const renderStatusBadge = (status: ExpenseStatus) => {
    const config = EXPENSE_STATUS_CONFIG[status]
    return (
      <span
        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${config.bgColor} ${config.textColor}`}
      >
        {config.label}
      </span>
    )
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Generate Expense Report" size="lg">
      <div className="space-y-6">
        {/* Selection Mode */}
        <fieldset>
          <legend className="text-sm font-medium text-gray-700 mb-3">
            Which expenses to include?
          </legend>
          <div className="space-y-2">
            <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                name="selectionMode"
                value="pending"
                checked={selectionMode === 'pending'}
                onChange={() => setSelectionMode('pending')}
                className="text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <span className="font-medium">All pending expenses</span>
                <span className="text-gray-500 ml-2">({pendingExpenses.length})</span>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                name="selectionMode"
                value="selected"
                checked={selectionMode === 'selected'}
                onChange={() => setSelectionMode('selected')}
                className="text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <span className="font-medium">Select specific expenses</span>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                name="selectionMode"
                value="all"
                checked={selectionMode === 'all'}
                onChange={() => setSelectionMode('all')}
                className="text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <span className="font-medium">All expenses</span>
                <span className="text-gray-500 ml-2">({reportableExpenses.length})</span>
              </div>
            </label>
          </div>
        </fieldset>

        {/* Expense Selection List (when mode is 'selected') */}
        {selectionMode === 'selected' && (
          <div className="border rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 border-b flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Select expenses ({selectedExpenses.size} selected)
              </span>
              <button
                type="button"
                onClick={() => {
                  if (selectedExpenses.size === reportableExpenses.length) {
                    setSelectedExpenses(new Set())
                  } else {
                    setSelectedExpenses(new Set(reportableExpenses.map((e) => e.id)))
                  }
                }}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                {selectedExpenses.size === reportableExpenses.length
                  ? 'Deselect all'
                  : 'Select all'}
              </button>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {reportableExpenses.length === 0 ? (
                <p className="p-4 text-center text-gray-500">
                  No expenses available (private expenses are excluded)
                </p>
              ) : (
                reportableExpenses.map((expense) => (
                  <label
                    key={expense.id}
                    className="flex items-center gap-3 px-4 py-2 border-b last:border-b-0 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedExpenses.has(expense.id)}
                      onChange={() => toggleExpense(expense.id)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">
                          {expense.description || 'No description'}
                        </span>
                        {renderStatusBadge(expense.status)}
                      </div>
                      <span className="text-xs text-gray-500">{expense.date}</span>
                    </div>
                    <span className="text-sm font-medium whitespace-nowrap">
                      {Number(expense.converted_amount ?? expense.amount).toFixed(2)} {baseCurrency}
                    </span>
                  </label>
                ))
              )}
            </div>
          </div>
        )}

        {/* Summary by Status (for pending and all modes) */}
        {selectionMode !== 'selected' && (
          <div className="border rounded-lg p-4 bg-gray-50">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Expenses included:</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              {selectionMode === 'pending' && (
                <li>
                  {pendingExpenses.length} pending expense
                  {pendingExpenses.length !== 1 ? 's' : ''}
                </li>
              )}
              {selectionMode === 'all' && (
                <>
                  {pendingExpenses.length > 0 && (
                    <li>
                      {pendingExpenses.length} pending expense
                      {pendingExpenses.length !== 1 ? 's' : ''}
                    </li>
                  )}
                  {submittedExpenses.length > 0 && (
                    <li>
                      {submittedExpenses.length} submitted expense
                      {submittedExpenses.length !== 1 ? 's' : ''}
                    </li>
                  )}
                  {rejectedExpenses.length > 0 && (
                    <li>
                      {rejectedExpenses.length} rejected expense
                      {rejectedExpenses.length !== 1 ? 's' : ''}
                    </li>
                  )}
                </>
              )}
            </ul>
          </div>
        )}

        {/* Total */}
        <div className="flex justify-between items-center p-4 bg-blue-50 rounded-lg border border-blue-200">
          <span className="font-medium text-blue-800">Total</span>
          <span className="text-xl font-bold text-blue-900">
            {total.toFixed(2)} {baseCurrency}
          </span>
        </div>

        {/* Mark as Submitted Option */}
        <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={markAsSubmitted}
            onChange={(e) => setMarkAsSubmitted(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <span className="font-medium">Mark selected expenses as Submitted</span>
            <p className="text-sm text-gray-500">
              Selected expenses will be marked as submitted after report generation
            </p>
          </div>
        </label>

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            isLoading={isGenerating}
            disabled={expensesToInclude.length === 0}
          >
            Generate Report ({expensesToInclude.length} expense
            {expensesToInclude.length !== 1 ? 's' : ''})
          </Button>
        </div>
      </div>
    </Modal>
  )
}
