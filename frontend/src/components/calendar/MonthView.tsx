// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { toDateKey } from '@/lib/calendarData'
import type { HolidayEntry } from '@/types'
import type { CalendarEvent } from './types'

interface MonthViewProps {
  currentDate: Date
  events: CalendarEvent[]
  holidays: HolidayEntry[]
  getMonthBoundaries: (date: Date) => { start: Date; end: Date }
}

export function MonthView({ currentDate, events, holidays, getMonthBoundaries }: MonthViewProps) {
  const { start: monthStart } = getMonthBoundaries(currentDate)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // Get calendar grid start (Monday of the week containing month start)
  const gridStart = new Date(monthStart)
  const day = gridStart.getDay()
  gridStart.setDate(gridStart.getDate() - (day === 0 ? 6 : day - 1))

  // Generate 6 weeks of days
  const days = Array.from({ length: 42 }, (_, i) => {
    const date = new Date(gridStart)
    date.setDate(date.getDate() + i)
    return date
  })

  const isToday = (date: Date) => date.toDateString() === today.toDateString()
  const isCurrentMonth = (date: Date) =>
    date.getMonth() === currentDate.getMonth() && date.getFullYear() === currentDate.getFullYear()
  const isWeekend = (date: Date) => {
    const d = date.getDay()
    return d === 0 || d === 6
  }

  const getHolidaysForDate = (date: Date): HolidayEntry[] => {
    const dateStr = toDateKey(date)
    return holidays.filter((h) => h.date === dateStr)
  }

  const isHoliday = (date: Date): boolean => {
    return getHolidaysForDate(date).length > 0
  }

  const getEventsForDay = (date: Date) => {
    return events.filter((event) => {
      const eventStart = new Date(event.start)
      const eventEnd = new Date(event.end)
      const dayStart = new Date(date)
      dayStart.setHours(0, 0, 0, 0)
      const dayEnd = new Date(date)
      dayEnd.setHours(23, 59, 59, 999)

      return eventStart <= dayEnd && eventEnd >= dayStart
    })
  }

  return (
    <div className="p-4">
      {/* Day Headers */}
      <div className="grid grid-cols-7 mb-2">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((dayName, idx) => (
          <div
            key={dayName}
            className={`text-center text-xs font-semibold py-2 ${
              idx >= 5 ? 'text-gray-400' : 'text-gray-500'
            }`}
          >
            {dayName}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 border-l border-t border-gray-200">
        {days.map((date) => {
          const dayEvents = getEventsForDay(date)
          const inCurrentMonth = isCurrentMonth(date)

          return (
            <div
              key={date.toISOString()}
              className={`min-h-28 border-r border-b border-gray-200 p-1 ${
                !inCurrentMonth
                  ? 'bg-gray-50'
                  : isWeekend(date) || isHoliday(date)
                    ? 'bg-gray-50'
                    : isToday(date)
                      ? 'bg-blue-50 ring-2 ring-inset ring-blue-500'
                      : ''
              }`}
            >
              <div
                className={`text-xs font-medium mb-1 ${
                  !inCurrentMonth
                    ? 'text-gray-400'
                    : isToday(date)
                      ? 'font-bold text-blue-700'
                      : isWeekend(date) || isHoliday(date)
                        ? 'text-gray-600'
                        : 'text-gray-900'
                }`}
              >
                {date.getDate()}
              </div>
              {/* Holiday labels */}
              {getHolidaysForDate(date).map((holiday) => (
                <div
                  key={`${holiday.date}-${holiday.display_label}`}
                  className="text-xs text-gray-600 bg-gray-200 px-1 rounded truncate mb-0.5"
                  title={`${holiday.display_label} - ${holiday.name}`}
                >
                  {holiday.display_label}
                </div>
              ))}
              <div className="space-y-0.5">
                {dayEvents.slice(0, 3).map((event) => (
                  <button
                    key={event.id}
                    type="button"
                    className={`w-full text-left text-xs px-1 py-0.5 rounded truncate ${
                      event.type === 'homeoffice'
                        ? 'text-white'
                        : event.type === 'todo'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-blue-100 text-blue-700'
                    }`}
                    style={
                      event.type === 'homeoffice' ? { backgroundColor: event.color } : undefined
                    }
                  >
                    <span className="flex items-center">
                      {event.type === 'external' && (
                        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1 flex-shrink-0" />
                      )}
                      {event.title}
                    </span>
                  </button>
                ))}
                {dayEvents.length > 3 && (
                  <button
                    type="button"
                    className="w-full text-left text-xs text-gray-500 hover:text-gray-700"
                  >
                    +{dayEvents.length - 3} more
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
