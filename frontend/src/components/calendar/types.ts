// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

export type ViewMode = 'week' | 'month'

export interface CalendarFilters {
  showHomeOfficeEvents: boolean
  showExternalCalendars: boolean
  showTodos: boolean
  showHolidays: boolean
  companyId: string
}

export interface CalendarEvent {
  id: string
  title: string
  start: Date
  end: Date
  allDay: boolean
  type: 'homeoffice' | 'external' | 'todo'
  color: string
  companyName?: string
  location?: string
}
