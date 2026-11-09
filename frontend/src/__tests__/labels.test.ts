// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { describe, expect, it } from 'vitest'
import type { ExpenseCategory } from '@/types'
import {
  categoryLabels,
  companyTypeLabels,
  enumValues,
  eventStatusColors,
  eventStatusLabels,
  getCategoryLabel,
  getPaymentTypeLabel,
  labelOptions,
  paymentTypeLabels,
} from '@/utils/labels'

describe('labels', () => {
  it('maps known values', () => {
    expect(getPaymentTypeLabel('credit_card')).toBe('Credit Card')
    expect(getCategoryLabel('meals')).toBe('Meals')
  })

  it('falls back to the raw value', () => {
    expect(getCategoryLabel('unknown' as ExpenseCategory)).toBe('unknown')
  })

  it('enumValues returns the keys in declaration order', () => {
    expect(enumValues(paymentTypeLabels)).toEqual([
      'cash',
      'credit_card',
      'debit_card',
      'company_card',
      'prepaid',
      'invoice',
      'other',
    ])
    expect(enumValues(categoryLabels)[0]).toBe('travel')
  })

  it('labelOptions returns value/label pairs in declaration order', () => {
    const options = labelOptions(paymentTypeLabels)
    expect(options[0]).toEqual({ value: 'cash', label: 'Cash' })
    expect(options[1]).toEqual({ value: 'credit_card', label: 'Credit Card' })
    expect(options.map((o) => o.value)).toEqual(enumValues(paymentTypeLabels))
  })

  it('event status and company type maps cover every value', () => {
    expect(labelOptions(eventStatusLabels)).toEqual([
      { value: 'upcoming', label: 'Upcoming' },
      { value: 'active', label: 'Active' },
      { value: 'past', label: 'Past' },
    ])
    expect(eventStatusColors).toEqual({ upcoming: 'warning', active: 'info', past: 'default' })
    expect(labelOptions(companyTypeLabels)).toEqual([
      { value: 'employer', label: 'Employer' },
      { value: 'third_party', label: 'Third Party' },
    ])
  })
})
