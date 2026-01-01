// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useState, useMemo } from 'react'
import type { TimeRecord, DayType, ComplianceWarning } from '../types'
import { DAY_TYPE_LABELS, DAY_TYPE_COLORS, WARNING_LEVEL_COLORS } from '../types'
import { formatTime, formatHours, getWeekStart, toISODateString } from '../api'

interface WeekViewProps {
  records: TimeRecord[]
  currentDate: Date
  onDateChange: (date: Date) => void
  onDayClick: (date: string, record?: TimeRecord) => void
  warnings?: Record<string, ComplianceWarning[]>
  holidays?: Record<string, string>
  isLoading?: boolean
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function WeekView({
  records,
  currentDate,
  onDateChange,
  onDayClick,
  warnings = {},
  holidays = {},
  isLoading = false,
}: WeekViewProps) {
  const weekStart = useMemo(() => getWeekStart(currentDate), [currentDate])

  const weekDays = useMemo(() => {
    const days = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(weekStart)
      date.setDate(date.getDate() + i)
      days.push(date)
    }
    return days
  }, [weekStart])

  const recordsByDate = useMemo(() => {
    const map: Record<string, TimeRecord> = {}
    for (const record of records) {
      map[record.date] = record
    }
    return map
  }, [records])

  const totalHours = useMemo(() => {
    return records.reduce((sum, r) => sum + (r.net_hours || 0), 0)
  }, [records])

  const goToPrevWeek = () => {
    const prev = new Date(weekStart)
    prev.setDate(prev.getDate() - 7)
    onDateChange(prev)
  }

  const goToNextWeek = () => {
    const next = new Date(weekStart)
    next.setDate(next.getDate() + 7)
    onDateChange(next)
  }

  const goToToday = () => {
    onDateChange(new Date())
  }

  const formatWeekRange = () => {
    const end = new Date(weekStart)
    end.setDate(end.getDate() + 6)

    const startStr = weekStart.toLocaleDateString('de-AT', {
      day: '2-digit',
      month: '2-digit',
    })
    const endStr = end.toLocaleDateString('de-AT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
    return `${startStr} - ${endStr}`
  }

  const isToday = (date: Date) => {
    const today = new Date()
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header with navigation */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={goToPrevWeek}
            className="p-2 rounded-md hover:bg-gray-100"
            aria-label="Previous week"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <title>Previous week</title>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-lg font-semibold text-gray-900 min-w-[200px] text-center">
            {formatWeekRange()}
          </span>
          <button
            type="button"
            onClick={goToNextWeek}
            className="p-2 rounded-md hover:bg-gray-100"
            aria-label="Next week"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <title>Next week</title>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={goToToday}
            className="px-3 py-1 text-sm font-medium text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Today
          </button>
          <div className="text-sm text-gray-500">
            Total: <span className="font-semibold text-gray-900">{formatHours(totalHours)}</span>
          </div>
        </div>
      </div>

      {/* Week grid */}
      {isLoading ? (
        <div className="p-8 text-center text-gray-500">Loading...</div>
      ) : (
        <div className="grid grid-cols-7 divide-x divide-gray-200">
          {weekDays.map((date, index) => {
            const dateStr = toISODateString(date)
            const record = recordsByDate[dateStr]
            const dayWarnings = warnings[dateStr] || []
            const holidayName = holidays[dateStr]
            const isWeekend = date.getDay() === 0 || date.getDay() === 6
            const today = isToday(date)

            return (
              <button
                type="button"
                key={dateStr}
                onClick={() => onDayClick(dateStr, record)}
                className={`p-3 text-left hover:bg-gray-50 transition-colors min-h-[120px] flex flex-col ${
                  today ? 'bg-blue-50' : isWeekend ? 'bg-gray-50' : ''
                }`}
              >
                {/* Day header */}
                <div className="flex items-center justify-between mb-2">
                  <span
                    className={`text-xs font-medium ${
                      today ? 'text-blue-600' : 'text-gray-500'
                    }`}
                  >
                    {WEEKDAYS[index]}
                  </span>
                  <span
                    className={`text-sm font-semibold ${
                      today
                        ? 'text-white bg-blue-600 w-7 h-7 rounded-full flex items-center justify-center'
                        : 'text-gray-900'
                    }`}
                  >
                    {date.getDate()}
                  </span>
                </div>

                {/* Holiday indicator */}
                {holidayName && (
                  <div className="text-xs text-purple-600 font-medium mb-1 truncate">
                    {holidayName}
                  </div>
                )}

                {/* Record content */}
                {record ? (
                  <div className="flex-1">
                    {/* Day type badge */}
                    <span
                      className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${
                        DAY_TYPE_COLORS[record.day_type].bg
                      } ${DAY_TYPE_COLORS[record.day_type].text}`}
                    >
                      {DAY_TYPE_LABELS[record.day_type]}
                    </span>

                    {/* Time info for work days */}
                    {(record.day_type === 'work' || record.day_type === 'doctor_visit') && (
                      <div className="mt-2 space-y-1">
                        <div className="text-xs text-gray-600">
                          {formatTime(record.check_in)} - {formatTime(record.check_out)}
                        </div>
                        {record.net_hours !== null && (
                          <div className="text-sm font-medium text-gray-900">
                            {formatHours(record.net_hours)}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Lock indicator */}
                    {record.is_locked && (
                      <div className="mt-1">
                        <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                          <title>Locked</title>
                          <path
                            fillRule="evenodd"
                            d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <span className="text-xs text-gray-400">No entry</span>
                  </div>
                )}

                {/* Warning indicators */}
                {dayWarnings.length > 0 && (
                  <div className="mt-2 flex gap-1">
                    {dayWarnings.map((warning, i) => (
                      <span
                        key={i}
                        className={`w-2 h-2 rounded-full ${
                          warning.level === 'error'
                            ? 'bg-red-500'
                            : warning.level === 'warning'
                              ? 'bg-yellow-500'
                              : 'bg-blue-500'
                        }`}
                        title={warning.message}
                      />
                    ))}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
