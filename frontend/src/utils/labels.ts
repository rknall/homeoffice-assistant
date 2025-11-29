// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import type { PaymentType, ExpenseCategory } from '@/types'

export const paymentTypeLabels: Record<PaymentType, string> = {
  cash: 'Cash',
  credit_card: 'Credit Card',
  debit_card: 'Debit Card',
  company_card: 'Company Card',
  prepaid: 'Prepaid',
  invoice: 'Invoice',
  other: 'Other',
}

export const categoryLabels: Record<ExpenseCategory, string> = {
  travel: 'Travel',
  accommodation: 'Accommodation',
  meals: 'Meals',
  transport: 'Transport',
  equipment: 'Equipment',
  communication: 'Communication',
  other: 'Other',
}

export function getPaymentTypeLabel(type: PaymentType): string {
  return paymentTypeLabels[type] || type
}

export function getCategoryLabel(category: ExpenseCategory): string {
  return categoryLabels[category] || category
}
