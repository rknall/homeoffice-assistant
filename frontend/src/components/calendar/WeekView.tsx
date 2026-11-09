// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { toDateKey } from '@/lib/calendarData'
import type { HolidayEntry } from '@/types'
import type { CalendarEvent } from './types'

interface WeekViewProps {
  currentDate: Date
  events: CalendarEvent[]
  holidays: HolidayEntry[]
  getWeekBoundaries: (date: Date) => { start: Date; end: Date }
}

export function WeekView({ currentDate, events, holidays, getWeekBoundaries }: WeekViewProps) {
  const { start } = getWeekBoundaries(currentDate)
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(start)
    date.setDate(date.getDate() + i)
    return date
  })

  const hours = Array.from({ length: 11 }, (_, i) => i + 8) // 8:00 to 18:00

  const isToday = (date: Date) => {
    return date.toDateString() === today.toDateString()
  }

  const isWeekend = (date: Date) => {
    const day = date.getDay()
    return day === 0 || day === 6
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
      const eventDate = new Date(event.start)
      return eventDate.toDateString() === date.toDateString()
    })
  }

  const getAllDayEvents = () => {
    return events.filter((event) => {
      const eventStart = new Date(event.start)
      const eventEnd = new Date(event.end)
      const weekStart = new Date(start)
      const weekEnd = new Date(start)
      weekEnd.setDate(weekEnd.getDate() + 6)

      // Check if multi-day event overlaps with this week
      return event.allDay && eventStart <= weekEnd && eventEnd >= weekStart
    })
  }

  const formatDayHeader = (date: Date) => {
    const dayName = date.toLocaleDateString(undefined, { weekday: 'short' })
    const dayNum = date.getDate()
    return { dayName, dayNum }
  }

  return (
    <div className="calendar-grid overflow-auto" style={{ maxHeight: '600px' }}>
      {/* All-Day Events Row */}
      <div className="grid grid-cols-8 border-b border-gray-200 bg-gray-50 sticky top-0 z-10">
        <div className="p-2 text-xs font-medium text-gray-500 border-r border-gray-200 w-16">
          All Day
        </div>
        {days.map((day) => {
          const { dayName, dayNum } = formatDayHeader(day)
          const dayEvents = getAllDayEvents().filter((event) => {
            const eventStart = new Date(event.start)
            const eventEnd = new Date(event.end)
            return eventStart <= day && eventEnd >= day
          })

          return (
            <div
              key={day.toISOString()}
              className={`p-2 border-r border-gray-200 min-h-[60px] ${
                isToday(day) ? 'bg-blue-50' : isWeekend(day) || isHoliday(day) ? 'bg-gray-100' : ''
              }`}
            >
              <div
                className={`text-xs font-medium mb-1 ${
                  isToday(day) ? 'text-blue-700' : 'text-gray-500'
                }`}
              >
                {dayName} {dayNum}
                {isToday(day) && ' (Today)'}
              </div>
              {/* Holiday labels */}
              {getHolidaysForDate(day).map((holiday) => (
                <div
                  key={`${holiday.date}-${holiday.display_label}`}
                  className="text-xs text-gray-600 bg-gray-200 px-1 rounded truncate mb-0.5"
                  title={`${holiday.display_label} - ${holiday.name}`}
                >
                  {holiday.display_label} - {holiday.name}
                </div>
              ))}
              <div className="space-y-0.5">
                {dayEvents.slice(0, 2).map((event) => (
                  <button
                    key={event.id}
                    type="button"
                    className="block w-full text-left text-xs text-white px-1 py-0.5 rounded truncate hover:opacity-80 transition-opacity"
                    style={{ backgroundColor: event.color }}
                  >
                    {event.title}
                  </button>
                ))}
                {dayEvents.length > 2 && (
                  <span className="text-xs text-gray-500">+{dayEvents.length - 2} more</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Time Slots Grid */}
      <div className="grid grid-cols-8">
        {/* Time Labels Column */}
        <div className="border-r border-gray-200 w-16">
          {hours.map((hour) => (
            <div
              key={hour}
              className="h-12 border-b border-gray-100 text-xs text-gray-500 text-right pr-2 pt-1"
            >
              {hour.toString().padStart(2, '0')}:00
            </div>
          ))}
        </div>

        {/* Day Columns */}
        {days.map((day) => {
          const dayEvents = getEventsForDay(day).filter((e) => !e.allDay)

          return (
            <div
              key={day.toISOString()}
              className={`border-r border-gray-200 relative ${
                isToday(day)
                  ? 'bg-blue-50/50'
                  : isWeekend(day) || isHoliday(day)
                    ? 'bg-gray-50'
                    : ''
              }`}
            >
              {hours.map((hour) => (
                <div key={hour} className="h-12 border-b border-gray-100" />
              ))}

              {/* Render timed events */}
              {dayEvents.map((event) => {
                const eventStart = new Date(event.start)
                const hour = eventStart.getHours()
                const minutes = eventStart.getMinutes()
                const topOffset = (hour - 8) * 48 + (minutes / 60) * 48
                const height = 36 // Default 45 min height

                if (hour < 8 || hour > 18) return null

                return (
                  <button
                    key={event.id}
                    type="button"
                    className="absolute left-1 right-1 text-white text-xs px-1 rounded cursor-pointer hover:opacity-80 transition-opacity truncate text-left"
                    style={{
                      top: `${topOffset}px`,
                      height: `${height}px`,
                      backgroundColor: event.color,
                      borderStyle: event.type === 'external' ? 'dashed' : 'solid',
                      borderWidth: '1px',
                      borderColor: event.color,
                    }}
                  >
                    {event.title}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}
