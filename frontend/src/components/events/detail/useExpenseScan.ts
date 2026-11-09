// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useState } from 'react'
import type { UseFormSetValue } from 'react-hook-form'
import { api, errorMessage } from '@/api/client'
import type { ExpenseScanResult } from '@/types'
import type { ExpenseForm } from './expenseForm'

/** LLM document scan state: fills an expense form from a Paperless document. */
export function useExpenseScan(eventId: string) {
  const [isScanning, setIsScanning] = useState(false)
  const [warnings, setWarnings] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const clear = useCallback(() => {
    setWarnings((prev) => (prev.length > 0 ? [] : prev))
    setError(null)
  }, [])

  const scan = async (docId: number, setValue: UseFormSetValue<ExpenseForm>) => {
    setIsScanning(true)
    clear()
    try {
      const result = await api.post<ExpenseScanResult>(
        `/events/${eventId}/documents/${docId}/scan-expense`,
      )
      if (result.date) setValue('date', result.date)
      if (result.amount != null) setValue('amount', String(result.amount))
      if (result.currency) setValue('currency', result.currency)
      if (result.category) setValue('category', result.category)
      if (result.payment_type) setValue('payment_type', result.payment_type)
      if (result.description) setValue('description', result.description)
      setWarnings(result.warnings)
    } catch (e) {
      setError(errorMessage(e, 'Scan failed'))
    } finally {
      setIsScanning(false)
    }
  }

  return { isScanning, warnings, error, scan, clear }
}
