// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { beforeEach, describe, expect, it, vi } from 'vitest'

const get = vi.fn()
const getCalendars = vi.fn()
const getHolidays = vi.fn()

vi.mock('@/api/client', () => ({
  api: { get: (p: string) => get(p) },
  companyCalendarsApi: { getCalendars: (id: string) => getCalendars(id) },
  holidayCalendarsApi: { getHolidays: (s: string, e: string) => getHolidays(s, e) },
}))

import { loadCalendarData, toDateKey } from '@/lib/calendarData'
import type { Company } from '@/types'

const companies = [{ id: 'c1' }] as Company[]

async function defaultGet(path: string) {
  if (path.startsWith('/events?')) return [{ id: 'e1' }]
  if (path === '/todos?due_from=2025-01-01&due_to=2025-02-01')
    return [{ id: 't1', due_date: '2025-01-02' }]
  throw new Error(`unexpected ${path}`)
}

describe('loadCalendarData', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    get.mockImplementation(defaultGet)
    getCalendars.mockResolvedValue([{ id: 'cal1' }])
    getHolidays.mockResolvedValue({ holidays: [{ date: '2025-01-01' }] })
  })

  it('loads every source and reads todos with one date-range call', async () => {
    const data = await loadCalendarData('2025-01-01', '2025-02-01', companies)
    expect(data.errors).toEqual([])
    expect(data.events).toHaveLength(1)
    expect(data.holidays).toHaveLength(1)
    expect(data.calendars).toHaveLength(1)
    expect(data.todos.map((t) => t.id)).toEqual(['t1'])
    const todoCalls = get.mock.calls.filter(([p]) => String(p).includes('/todos'))
    expect(todoCalls).toEqual([['/todos?due_from=2025-01-01&due_to=2025-02-01']])
    expect(get).not.toHaveBeenCalledWith('/events/e1/todos')
  })

  it('a failing todos request is reported and keeps the other sources', async () => {
    get.mockImplementation(async (path: string) => {
      if (path.startsWith('/todos?')) throw new Error('todo down')
      return defaultGet(path)
    })
    const data = await loadCalendarData('2025-01-01', '2025-02-01', companies)
    expect(data.todos).toEqual([])
    expect(data.events).toHaveLength(1)
    expect(data.holidays).toHaveLength(1)
    expect(data.calendars).toHaveLength(1)
    expect(data.errors).toEqual(['Todos: todo down'])
  })

  it('a failing holiday request does not blank the other sources and is reported', async () => {
    getHolidays.mockRejectedValue(new Error('boom'))
    const data = await loadCalendarData('2025-01-01', '2025-02-01', companies)
    expect(data.events).toHaveLength(1)
    expect(data.todos).toHaveLength(1)
    expect(data.calendars).toHaveLength(1)
    expect(data.holidays).toEqual([])
    expect(data.errors).toEqual(['Holidays: boom'])
  })

  it('a failing events request is reported and others still load', async () => {
    get.mockImplementation(async (path: string) => {
      if (path.startsWith('/events?')) throw new Error('nope')
      return defaultGet(path)
    })
    const data = await loadCalendarData('2025-01-01', '2025-02-01', companies)
    expect(data.events).toEqual([])
    expect(data.holidays).toHaveLength(1)
    expect(data.errors).toEqual(['Events: nope'])
  })

  it('reads company calendars for the companies passed in and never fetches companies', async () => {
    await loadCalendarData('2025-01-01', '2025-02-01', companies)
    expect(getCalendars).toHaveBeenCalledWith('c1')
    expect(get).not.toHaveBeenCalledWith('/companies')
  })

  it('reports a failing calendar request without losing events', async () => {
    getCalendars.mockRejectedValue(new Error('cal down'))
    const data = await loadCalendarData('2025-01-01', '2025-02-01', companies)
    expect(data.events).toHaveLength(1)
    expect(data.errors).toEqual(['Company calendars: cal down'])
  })
})

describe('toDateKey', () => {
  it('keeps the local date at local midnight', () => {
    expect(toDateKey(new Date(2026, 10, 1, 0, 0, 0))).toBe('2026-11-01')
    expect(toDateKey(new Date(2026, 9, 26, 23, 59, 0))).toBe('2026-10-26')
  })
})
