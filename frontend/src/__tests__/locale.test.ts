// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { describe, expect, it } from 'vitest'
import { formatDateString, formatTimeString } from '@/stores/locale'

describe('locale formatters', () => {
  const d = new Date(2025, 2, 7, 15, 4)

  it('formats dates per setting', () => {
    expect(formatDateString(d, 'YYYY-MM-DD')).toBe('2025-03-07')
    expect(formatDateString(d, 'DD.MM.YYYY')).toBe('07.03.2025')
    expect(formatDateString(d, 'DD/MM/YYYY')).toBe('07/03/2025')
    expect(formatDateString(d, 'MM/DD/YYYY')).toBe('03/07/2025')
  })

  it('formats times per setting', () => {
    expect(formatTimeString(d, '24h')).toBe('15:04')
    expect(formatTimeString(d, '12h')).toBe('3:04 PM')
    expect(formatTimeString(new Date(2025, 0, 1, 0, 5), '12h')).toBe('12:05 AM')
  })
})
