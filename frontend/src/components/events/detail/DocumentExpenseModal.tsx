// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { Receipt } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { api, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import type { Document } from '@/types'
import { DocumentPreviewPane } from './DocumentPreviewPane'
import { ExpenseFormFields } from './ExpenseFormFields'
import { type ExpenseForm, expenseFormDefaults, expenseSchema } from './expenseForm'
import { ScanControls } from './ScanControls'
import { useDocumentPreview } from './useDocumentPreview'
import { useExpenseScan } from './useExpenseScan'

interface DocumentExpenseModalProps {
  document: Document | null
  onClose: () => void
  eventId: string
  hasLlmIntegration: boolean
  onSaved: () => Promise<void>
  onError: (message: string | null) => void
}

/** Modal with document preview that creates an expense from a Paperless document. */
export function DocumentExpenseModal({
  document: doc,
  onClose,
  eventId,
  hasLlmIntegration,
  onSaved,
  onError,
}: DocumentExpenseModalProps) {
  const [isCreating, setIsCreating] = useState(false)
  const preview = useDocumentPreview(eventId, doc?.id ?? null)
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

  // Pre-fill the form with document data whenever a document is opened
  useEffect(() => {
    clearScan()
    if (!doc) {
      reset()
      return
    }
    reset({
      date: doc.created ? doc.created.split('T')[0] : new Date().toISOString().split('T')[0],
      amount: '',
      currency: 'EUR',
      payment_type: 'cash',
      category: 'other',
      description: doc.title,
    })
  }, [doc, reset, clearScan])

  const onSubmit = async (data: ExpenseForm) => {
    if (!doc) return
    setIsCreating(true)
    onError(null)
    try {
      await api.post(`/events/${eventId}/expenses`, {
        ...data,
        amount: parseFloat(data.amount),
        description: data.description || null,
        paperless_doc_id: doc.id,
        original_filename: doc.original_file_name,
      })
      await onSaved()
      onClose()
    } catch (e) {
      onError(errorMessage(e, 'Failed to create expense'))
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Modal isOpen={doc !== null} onClose={onClose} title="Add Document as Expense" size="4xl">
      <div className="flex gap-6" style={{ minHeight: '500px' }}>
        <DocumentPreviewPane isLoading={preview.isLoading} url={preview.url} />

        {/* Expense Form - Right Side */}
        <div className="w-80 flex-shrink-0">
          {doc && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-900 truncate" title={doc.title}>
                {doc.title}
              </p>
              <p className="text-xs text-gray-500 truncate" title={doc.original_file_name}>
                {doc.original_file_name}
              </p>
            </div>
          )}
          {hasLlmIntegration && doc && (
            <ScanControls
              isScanning={scan.isScanning}
              error={scan.error}
              warnings={scan.warnings}
              onScan={() => scan.scan(doc.id, setValue)}
            />
          )}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <ExpenseFormFields
              register={register}
              errors={errors}
              currency={watch('currency')}
              gridGap="gap-3"
            />
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isCreating}>
                <Receipt className="h-4 w-4 mr-2" />
                Add Expense
              </Button>
            </div>
          </form>
        </div>
      </div>
    </Modal>
  )
}
