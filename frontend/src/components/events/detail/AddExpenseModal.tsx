// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { api, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { ExpenseFormFields } from './ExpenseFormFields'
import { type ExpenseForm, expenseFormDefaults, expenseSchema } from './expenseForm'

interface AddExpenseModalProps {
  isOpen: boolean
  onClose: () => void
  eventId: string
  onSaved: () => Promise<void>
  onError: (message: string | null) => void
}

/** Modal form that adds a manual expense to an event. */
export function AddExpenseModal({
  isOpen,
  onClose,
  eventId,
  onSaved,
  onError,
}: AddExpenseModalProps) {
  const [isSaving, setIsSaving] = useState(false)
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<ExpenseForm>({
    resolver: zodResolver(expenseSchema),
    defaultValues: expenseFormDefaults,
  })

  const close = () => {
    onClose()
    reset()
  }

  const onSubmit = async (data: ExpenseForm) => {
    setIsSaving(true)
    onError(null)
    try {
      await api.post(`/events/${eventId}/expenses`, {
        ...data,
        amount: parseFloat(data.amount),
        description: data.description || null,
      })
      await onSaved()
      onClose()
      reset()
    } catch (e) {
      onError(errorMessage(e, 'Failed to create expense'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={close} title="Add Expense">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <ExpenseFormFields
          register={register}
          errors={errors}
          currency={watch('currency')}
          gridGap="gap-4"
        />
        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving}>
            Add Expense
          </Button>
        </div>
      </form>
    </Modal>
  )
}
