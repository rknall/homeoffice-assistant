// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { z } from 'zod'
import { categoryLabels, enumValues, labelOptions, paymentTypeLabels } from '@/utils/labels'

export const expenseSchema = z.object({
  date: z.string().min(1, 'Date is required'),
  amount: z.string().min(1, 'Amount is required'),
  currency: z.string().min(1, 'Currency is required'),
  payment_type: z.enum(enumValues(paymentTypeLabels)),
  category: z.enum(enumValues(categoryLabels)),
  description: z.string().optional(),
})

export type ExpenseForm = z.infer<typeof expenseSchema>

export const expenseFormDefaults: Partial<ExpenseForm> = {
  currency: 'EUR',
  payment_type: 'cash',
  category: 'other',
}

export const paymentTypeOptions = labelOptions(paymentTypeLabels)

export const categoryOptions = labelOptions(categoryLabels)
