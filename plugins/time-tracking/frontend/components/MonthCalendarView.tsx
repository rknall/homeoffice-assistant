// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useMemo, useState } from 'react'
import { toISODateString } from '../api'
import type { TimeRecord } from '../types'
import { DAY_TYPE_LABELS } from '../types'

interface MonthCalendarViewProps {
  currentDate: Date
  recordsByDate: Map<string, TimeRecord[]>
  overlappingRecordIds: Set<string>
  getCompanyColor: (companyId: string) => string
  onRecordClick: (record: TimeRecord) => void
  onDateClick: (date: string) => void
  isLoading: boolean
}

interface CalendarDay {
  date: Date
  dateString: string
  isCurrentMonth: boolean
  isToday: boolean
  isWeekend: boolean
}

/**
 * MonthCalendarView - Monthly calendar grid with time entries
 *
 * Displays days in a grid with entries shown as colored badges
 * indicating the day type in the company's color.
 */
export function MonthCalendarView({
  currentDate,
  recordsByDate,
  overlappingRecordIds,
  getCompanyColor,
  onRecordClick,
  onDateClick,
  isLoading,
}: MonthCalendarViewProps) {
  const [hoveredRecordId, setHoveredRecordId] = useState<string | null>(null)

  // Generate calendar days for the month grid
  const calendarDays = useMemo((): CalendarDay[] => {
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    // First day of the month
    const firstDay = new Date(year, month, 1)
    // Last day of the month
    const lastDay = new Date(year, month + 1, 0)

    // Start from Monday of the week containing the first day
    const startDate = new Date(firstDay)
    const dayOfWeek = startDate.getDay()
    // Adjust for Monday start (Sunday = 0 -> offset 6, Monday = 1 -> offset 0)
    const offsetToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    startDate.setDate(startDate.getDate() - offsetToMonday)

    // End on Sunday of the week containing the last day
    const endDate = new Date(lastDay)
    const lastDayOfWeek = endDate.getDay()
    // Adjust to reach Sunday (Sunday = 0 -> add 0, Saturday = 6 -> add 1)
    const offsetToSunday = lastDayOfWeek === 0 ? 0 : 7 - lastDayOfWeek
    endDate.setDate(endDate.getDate() + offsetToSunday)

    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayString = toISODateString(today)

    const days: CalendarDay[] = []
    const current = new Date(startDate)

    while (current <= endDate) {
      const dateString = toISODateString(current)
      const dayOfWeekNum = current.getDay()

      days.push({
        date: new Date(current),
        dateString,
        isCurrentMonth: current.getMonth() === month,
        isToday: dateString === todayString,
        isWeekend: dayOfWeekNum === 0 || dayOfWeekNum === 6,
      })

      current.setDate(current.getDate() + 1)
    }

    return days
  }, [currentDate])

  // Day of week headers (Monday first)
  const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  // Check if a record is editable (not a public holiday)
  const isEditable = (record: TimeRecord): boolean => {
    return record.day_type !== 'public_holiday'
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Week day headers */}
      <div className="grid grid-cols-7 border-b border-gray-200">
        {weekDays.map((day, index) => (
          <div
            key={day}
            className={`
              py-2 text-center text-sm font-medium
              ${index >= 5 ? 'text-gray-400' : 'text-gray-700'}
            `}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7">
        {calendarDays.map((day) => {
          const dayRecords = recordsByDate.get(day.dateString) || []

          return (
            <div
              key={day.dateString}
              className={`
                min-h-[100px] border-b border-r border-gray-100 p-1
                ${!day.isCurrentMonth ? 'bg-gray-50' : ''}
                ${day.isWeekend && day.isCurrentMonth ? 'bg-gray-50/50' : ''}
                ${day.isToday ? 'bg-blue-50/50' : ''}
              `}
            >
              {/* Date number */}
              <button
                type="button"
                onClick={() => onDateClick(day.dateString)}
                className={`
                  w-7 h-7 flex items-center justify-center text-sm rounded-full
                  transition-colors hover:bg-gray-200
                  ${day.isToday ? 'bg-blue-600 text-white hover:bg-blue-700' : ''}
                  ${!day.isCurrentMonth ? 'text-gray-400' : 'text-gray-900'}
                  ${day.isWeekend && day.isCurrentMonth && !day.isToday ? 'text-gray-500' : ''}
                `}
              >
                {day.date.getDate()}
              </button>

              {/* Time entries for this day */}
              <div className="mt-1 space-y-1">
                {dayRecords.map((record) => {
                  const hasOverlap = overlappingRecordIds.has(record.id)
                  const isHovered = hoveredRecordId === record.id
                  const editable = isEditable(record)
                  const companyColor = getCompanyColor(record.company_id)

                  // Use button for editable entries, span for non-editable
                  if (editable) {
                    return (
                      <button
                        type="button"
                        key={record.id}
                        className={`
                          relative w-full text-left px-1.5 py-0.5 rounded text-xs font-medium
                          truncate transition-all hover:opacity-80
                          ${hasOverlap ? 'ring-2 ring-red-500 ring-offset-1' : ''}
                        `}
                        style={{
                          backgroundColor: hasOverlap ? '#FEE2E2' : `${companyColor}20`,
                          color: hasOverlap ? '#991B1B' : companyColor,
                          borderLeft: `3px solid ${companyColor}`,
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          onRecordClick(record)
                        }}
                        onMouseEnter={() => setHoveredRecordId(record.id)}
                        onMouseLeave={() => setHoveredRecordId(null)}
                      >
                        <span className="truncate">
                          {DAY_TYPE_LABELS[record.day_type] || record.day_type}
                        </span>

                        {/* Edit icon on hover */}
                        {isHovered && (
                          <span className="absolute right-1 top-1/2 -translate-y-1/2 opacity-70">
                            <svg
                              className="w-3 h-3"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                              aria-hidden="true"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                              />
                            </svg>
                          </span>
                        )}
                      </button>
                    )
                  }

                  // Non-editable entry (e.g., public holiday)
                  return (
                    <div
                      key={record.id}
                      className={`
                        relative px-1.5 py-0.5 rounded text-xs font-medium
                        truncate cursor-default
                        ${hasOverlap ? 'ring-2 ring-red-500 ring-offset-1' : ''}
                      `}
                      style={{
                        backgroundColor: hasOverlap ? '#FEE2E2' : `${companyColor}20`,
                        color: hasOverlap ? '#991B1B' : companyColor,
                        borderLeft: `3px solid ${companyColor}`,
                      }}
                    >
                      <span className="truncate">
                        {DAY_TYPE_LABELS[record.day_type] || record.day_type}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
          <div className="text-gray-500">Loading...</div>
        </div>
      )}

      {/* Legend */}
      <div className="p-3 border-t border-gray-200 flex items-center gap-4 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded ring-2 ring-red-500" />
          <span>Overlapping entries</span>
        </div>
        <div className="flex items-center gap-1">
          <span>Colors indicate company</span>
        </div>
      </div>
    </div>
  )
}
