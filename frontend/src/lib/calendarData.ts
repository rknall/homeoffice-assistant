// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { api, companyCalendarsApi, holidayCalendarsApi } from '@/api/client'
import type { Company, CompanyCalendar, EventWithSummary, HolidayEntry, Todo } from '@/types'

export interface CalendarData {
  events: EventWithSummary[]
  calendars: CompanyCalendar[]
  todos: Todo[]
  holidays: HolidayEntry[]
  /** One message per source that failed to load; empty when everything loaded. */
  errors: string[]
}

function failure(source: string, reason: unknown): string {
  const detail = reason instanceof Error && reason.message ? reason.message : 'request failed'
  return `${source}: ${detail}`
}

/**
 * Load every calendar source independently so one failure leaves the others intact.
 *
 * Todos come from the date-range endpoint (`GET /todos?due_from=&due_to=`), which returns
 * only todos due in the range. Companies come from the shared companies store and are
 * passed in, so they are fetched once for the whole app.
 */
export async function loadCalendarData(
  startDate: string,
  endDate: string,
  companies: Company[],
): Promise<CalendarData> {
  const errors: string[] = []

  const [eventsRes, holidaysRes, todosRes] = await Promise.allSettled([
    api.get<EventWithSummary[]>('/events?include_summary=true'),
    holidayCalendarsApi.getHolidays(startDate, endDate),
    api.get<Todo[]>(`/todos?due_from=${startDate}&due_to=${endDate}`),
  ])

  const events = eventsRes.status === 'fulfilled' ? eventsRes.value : []
  if (eventsRes.status === 'rejected') errors.push(failure('Events', eventsRes.reason))

  const holidays = holidaysRes.status === 'fulfilled' ? holidaysRes.value.holidays : []
  if (holidaysRes.status === 'rejected') errors.push(failure('Holidays', holidaysRes.reason))

  const todos = todosRes.status === 'fulfilled' ? todosRes.value : []
  if (todosRes.status === 'rejected') errors.push(failure('Todos', todosRes.reason))

  const calendarResults = await Promise.allSettled(
    companies.map((c) => companyCalendarsApi.getCalendars(c.id)),
  )

  const calendars: CompanyCalendar[] = []
  let calendarFailure: unknown
  for (const result of calendarResults) {
    if (result.status === 'fulfilled') calendars.push(...result.value)
    else calendarFailure = result.reason
  }
  if (calendarFailure !== undefined) {
    errors.push(failure('Company calendars', calendarFailure))
  }

  return { events, calendars, todos, holidays, errors }
}

/** Local calendar date as YYYY-MM-DD (toISOString would shift by the UTC offset). */
export function toDateKey(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}
