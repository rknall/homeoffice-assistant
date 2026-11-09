// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { api, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import type { Expense } from '@/types'
import { DocumentPreviewPane } from './DocumentPreviewPane'
import { ExpenseFormFields } from './ExpenseFormFields'
import { type ExpenseForm, expenseFormDefaults, expenseSchema } from './expenseForm'
import { ScanControls } from './ScanControls'
import { useDocumentPreview } from './useDocumentPreview'
import { useExpenseScan } from './useExpenseScan'

interface EditExpenseModalProps {
  expense: Expense | null
  onClose: () => void
  eventId: string
  hasLlmIntegration: boolean
  onSaved: () => Promise<void>
  onError: (message: string | null) => void
}

/** Modal that edits an expense, with the linked document preview when present. */
export function EditExpenseModal({
  expense,
  onClose,
  eventId,
  hasLlmIntegration,
  onSaved,
  onError,
}: EditExpenseModalProps) {
  const [isPrivate, setIsPrivate] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const docId = expense?.paperless_doc_id ?? null
  const preview = useDocumentPreview(eventId, docId)
  const scan = useExpenseScan(eventId)
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ExpenseForm>({
    resolver: zodResolver(expenseSchema),
    defaultValues: expenseFormDefaults,
  })
  const { clear: clearScan } = scan

  // Pre-fill the form with expense data whenever an expense is opened
  useEffect(() => {
    clearScan()
    if (!expense) {
      reset()
      return
    }
    setIsPrivate(expense.is_private)
    reset({
      date: expense.date,
      amount: String(expense.amount),
      currency: expense.currency,
      payment_type: expense.payment_type,
      category: expense.category,
      description: expense.description || '',
    })
  }, [expense, reset, clearScan])

  const onSubmit = async (data: ExpenseForm) => {
    if (!expense) return
    setIsUpdating(true)
    onError(null)
    try {
      await api.put(`/events/${eventId}/expenses/${expense.id}`, {
        ...data,
        amount: parseFloat(data.amount),
        description: data.description || null,
        is_private: isPrivate,
      })
      await onSaved()
      onClose()
    } catch (e) {
      onError(errorMessage(e, 'Failed to update expense'))
    } finally {
      setIsUpdating(false)
    }
  }

  const hasDocument = Boolean(expense?.paperless_doc_id)

  return (
    <Modal
      isOpen={expense !== null}
      onClose={onClose}
      title="Edit Expense"
      size={hasDocument ? '4xl' : 'md'}
    >
      <div
        className={hasDocument ? 'flex gap-6' : ''}
        style={hasDocument ? { minHeight: '500px' } : undefined}
      >
        {hasDocument && <DocumentPreviewPane isLoading={preview.isLoading} url={preview.url} />}

        {/* Expense Form - Right Side (or full width if no document) */}
        <div className={hasDocument ? 'w-80 flex-shrink-0' : ''}>
          {expense?.original_filename && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-900">Linked Document</p>
              <p className="text-xs text-gray-500 truncate" title={expense.original_filename}>
                {expense.original_filename}
              </p>
            </div>
          )}
          {hasLlmIntegration && docId !== null && (
            <ScanControls
              isScanning={scan.isScanning}
              error={scan.error}
              warnings={scan.warnings}
              onScan={() => scan.scan(docId, setValue)}
            />
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <ExpenseFormFields
              register={register}
              errors={errors}
              currency={watch('currency')}
              gridGap="gap-3"
            />
            <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={isPrivate}
                onChange={(e) => setIsPrivate(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1">
                <span className="font-medium">Private expense</span>
                <p className="text-sm text-gray-500">
                  Excluded from official reports, visible only to you
                </p>
              </div>
            </label>
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isUpdating}>
                Save Changes
              </Button>
            </div>
          </form>
        </div>
      </div>
    </Modal>
  )
}
