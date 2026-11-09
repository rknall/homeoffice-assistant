// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import type { CompanyType, EventStatus, ExpenseCategory, PaymentType } from '@/types'

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

// Status is computed from dates on the backend
export const eventStatusLabels: Record<EventStatus, string> = {
  upcoming: 'Upcoming',
  active: 'Active',
  past: 'Past',
}

export const eventStatusColors: Record<EventStatus, 'default' | 'warning' | 'info'> = {
  upcoming: 'warning',
  active: 'info',
  past: 'default',
}

export const companyTypeLabels: Record<CompanyType, string> = {
  employer: 'Employer',
  third_party: 'Third Party',
}

/** Keys of a label map in declaration order, typed for `z.enum`. */
export function enumValues<K extends string>(labels: Record<K, string>): [K, ...K[]] {
  return Object.keys(labels) as [K, ...K[]]
}

/** `{ value, label }` pairs of a label map in declaration order. */
export function labelOptions<K extends string>(
  labels: Record<K, string>,
): Array<{ value: K; label: string }> {
  return (Object.keys(labels) as K[]).map((value) => ({ value, label: labels[value] }))
}
