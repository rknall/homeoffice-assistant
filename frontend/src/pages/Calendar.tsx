// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, companyCalendarsApi } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { Company, CompanyCalendar, EventWithSummary, Todo } from '@/types'

type ViewMode = 'week' | 'month'

interface CalendarFilters {
  showHomeOfficeEvents: boolean
  showExternalCalendars: boolean
  showTodos: boolean
  companyId: string
}

interface CalendarEvent {
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

export function Calendar() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { setItems: setBreadcrumb } = useBreadcrumb()

  const [viewMode, setViewMode] = useState<ViewMode>(
    (searchParams.get('view') as ViewMode) || 'week',
  )
  const [currentDate, setCurrentDate] = useState(() => {
    const dateParam = searchParams.get('date')
    return dateParam ? new Date(dateParam) : new Date()
  })

  const [events, setEvents] = useState<EventWithSummary[]>([])
  const [_calendars, setCalendars] = useState<CompanyCalendar[]>([])
  const [todos, setTodos] = useState<Todo[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [lastSynced, setLastSynced] = useState<Date | null>(null)

  const [filters, setFilters] = useState<CalendarFilters>({
    showHomeOfficeEvents: true,
    showExternalCalendars: true,
    showTodos: true,
    companyId: 'all',
  })

  useEffect(() => {
    setBreadcrumb([{ label: 'Calendar' }])
  }, [setBreadcrumb])

  // Sync state to URL
  useEffect(() => {
    const params = new URLSearchParams()
    params.set('view', viewMode)
    params.set('date', currentDate.toISOString().split('T')[0])
    setSearchParams(params, { replace: true })
  }, [viewMode, currentDate, setSearchParams])

  const fetchData = useCallback(async () => {
    try {
      const [eventsData, companiesData, todosData] = await Promise.all([
        api.get<EventWithSummary[]>('/events?include_summary=true'),
        api.get<Company[]>('/companies'),
        api.get<Todo[]>('/todos'),
      ])
      setEvents(eventsData)
      setCompanies(companiesData)
      setTodos(todosData)

      // Fetch calendars for all companies
      const allCalendars: CompanyCalendar[] = []
      for (const company of companiesData) {
        try {
          const companyCalendars = await companyCalendarsApi.getCalendars(company.id)
          allCalendars.push(...companyCalendars)
        } catch {
          // Silently ignore - company may have no calendars
        }
      }
      setCalendars(allCalendars)
      setLastSynced(new Date())
    } catch {
      // Error handling
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = async () => {
    setIsSyncing(true)
    await fetchData()
    setIsSyncing(false)
  }

  const goToToday = () => {
    setCurrentDate(new Date())
  }

  const navigate = (direction: 'prev' | 'next') => {
    const newDate = new Date(currentDate)
    if (viewMode === 'week') {
      newDate.setDate(newDate.getDate() + (direction === 'next' ? 7 : -7))
    } else {
      newDate.setMonth(newDate.getMonth() + (direction === 'next' ? 1 : -1))
    }
    setCurrentDate(newDate)
  }

  // Convert events to calendar events
  const calendarEvents = useMemo((): CalendarEvent[] => {
    const result: CalendarEvent[] = []

    // HomeOffice events
    if (filters.showHomeOfficeEvents) {
      for (const event of events) {
        if (filters.companyId !== 'all' && event.company_id !== filters.companyId) continue
        const company = companies.find((c) => c.id === event.company_id)
        result.push({
          id: event.id,
          title: event.name,
          start: new Date(event.start_date),
          end: new Date(event.end_date),
          allDay: true,
          type: 'homeoffice',
          color: company?.type === 'employer' ? '#f97316' : '#22c55e',
          companyName: company?.name,
          location: event.city || undefined,
        })
      }
    }

    // Todos with due dates
    if (filters.showTodos) {
      for (const todo of todos) {
        if (!todo.due_date) continue
        result.push({
          id: todo.id,
          title: todo.title,
          start: new Date(todo.due_date),
          end: new Date(todo.due_date),
          allDay: false,
          type: 'todo',
          color: '#8b5cf6',
        })
      }
    }

    return result
  }, [events, todos, companies, filters])

  // Get week boundaries
  const getWeekBoundaries = useCallback((date: Date) => {
    const start = new Date(date)
    const day = start.getDay()
    const diff = start.getDate() - day + (day === 0 ? -6 : 1) // Monday start
    start.setDate(diff)
    start.setHours(0, 0, 0, 0)

    const end = new Date(start)
    end.setDate(end.getDate() + 6)
    end.setHours(23, 59, 59, 999)

    return { start, end }
  }, [])

  // Get month boundaries
  const getMonthBoundaries = useCallback((date: Date) => {
    const start = new Date(date.getFullYear(), date.getMonth(), 1)
    const end = new Date(date.getFullYear(), date.getMonth() + 1, 0)
    return { start, end }
  }, [])

  // Format header date
  const headerText = useMemo(() => {
    if (viewMode === 'week') {
      const { start, end } = getWeekBoundaries(currentDate)
      const startMonth = start.toLocaleDateString('en-US', { month: 'short' })
      const endMonth = end.toLocaleDateString('en-US', { month: 'short' })
      if (startMonth === endMonth) {
        return `Week of ${startMonth} ${start.getDate()}-${end.getDate()}, ${start.getFullYear()}`
      }
      return `Week of ${startMonth} ${start.getDate()} - ${endMonth} ${end.getDate()}, ${start.getFullYear()}`
    }
    return currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }, [viewMode, currentDate, getWeekBoundaries])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Calendar</h1>

      <Card>
        <CardHeader className="border-b border-gray-200 px-6 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            {/* Navigation */}
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => navigate('prev')}
                className="px-3 py-1.5 text-sm bg-gray-100 text-gray-900 hover:bg-gray-200 rounded-md font-medium transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <Button variant="primary" size="sm" onClick={goToToday}>
                Today
              </Button>
              <button
                type="button"
                onClick={() => navigate('next')}
                className="px-3 py-1.5 text-sm bg-gray-100 text-gray-900 hover:bg-gray-200 rounded-md font-medium transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <span className="text-lg font-semibold text-gray-900 ml-2">{headerText}</span>
            </div>

            {/* View Toggle & Refresh */}
            <div className="flex items-center space-x-3">
              <div className="flex rounded-md shadow-sm">
                <button
                  type="button"
                  onClick={() => setViewMode('week')}
                  className={`px-4 py-2 text-sm font-medium rounded-l-md ${
                    viewMode === 'week'
                      ? 'text-white bg-blue-600'
                      : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  Week
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('month')}
                  className={`px-4 py-2 text-sm font-medium rounded-r-md ${
                    viewMode === 'month'
                      ? 'text-white bg-blue-600'
                      : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  Month
                </button>
              </div>
              <button
                type="button"
                onClick={handleRefresh}
                disabled={isSyncing}
                className="inline-flex items-center px-3 py-2 text-sm bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-md font-medium transition-colors disabled:opacity-50"
                title={lastSynced ? `Last synced: ${lastSynced.toLocaleTimeString()}` : 'Refresh'}
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${isSyncing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </CardHeader>

        {/* Filters Panel */}
        <div className="px-6 py-3 border-b border-gray-200 bg-gray-50">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-4">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.showHomeOfficeEvents}
                  onChange={(e) =>
                    setFilters((f) => ({ ...f, showHomeOfficeEvents: e.target.checked }))
                  }
                  className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">HomeOffice Events</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.showExternalCalendars}
                  onChange={(e) =>
                    setFilters((f) => ({ ...f, showExternalCalendars: e.target.checked }))
                  }
                  className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">External Calendars</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.showTodos}
                  onChange={(e) => setFilters((f) => ({ ...f, showTodos: e.target.checked }))}
                  className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Todos</span>
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <label htmlFor="company-filter" className="text-sm text-gray-600">
                Companies:
              </label>
              <select
                id="company-filter"
                value={filters.companyId}
                onChange={(e) => setFilters((f) => ({ ...f, companyId: e.target.value }))}
                className="text-sm border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <CardContent className="p-0">
          {viewMode === 'week' ? (
            <WeekView
              currentDate={currentDate}
              events={calendarEvents}
              getWeekBoundaries={getWeekBoundaries}
            />
          ) : (
            <MonthView
              currentDate={currentDate}
              events={calendarEvents}
              getMonthBoundaries={getMonthBoundaries}
            />
          )}
        </CardContent>

        {/* Legend */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
          <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
            <span className="font-medium">Legend:</span>
            <span className="flex items-center">
              <span className="w-3 h-3 bg-orange-500 rounded mr-1" />
              HomeOffice Events
            </span>
            <span className="flex items-center">
              <span className="w-3 h-3 bg-blue-500 rounded mr-1 border border-dashed border-blue-600" />
              External Calendar
            </span>
            <span className="flex items-center">
              <span className="w-3 h-3 bg-purple-500 rounded mr-1 border border-dotted border-purple-600" />
              Todos
            </span>
          </div>
        </div>
      </Card>
    </div>
  )
}

interface WeekViewProps {
  currentDate: Date
  events: CalendarEvent[]
  getWeekBoundaries: (date: Date) => { start: Date; end: Date }
}

function WeekView({ currentDate, events, getWeekBoundaries }: WeekViewProps) {
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
    const dayName = date.toLocaleDateString('en-US', { weekday: 'short' })
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
                isToday(day) ? 'bg-blue-50' : isWeekend(day) ? 'bg-gray-100' : ''
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
                isToday(day) ? 'bg-blue-50/50' : isWeekend(day) ? 'bg-gray-50' : ''
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

interface MonthViewProps {
  currentDate: Date
  events: CalendarEvent[]
  getMonthBoundaries: (date: Date) => { start: Date; end: Date }
}

function MonthView({ currentDate, events, getMonthBoundaries }: MonthViewProps) {
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
                  : isWeekend(date)
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
                      : isWeekend(date)
                        ? 'text-gray-600'
                        : 'text-gray-900'
                }`}
              >
                {date.getDate()}
              </div>
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
