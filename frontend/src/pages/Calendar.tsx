// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CalendarFiltersPanel } from '@/components/calendar/CalendarFiltersPanel'
import { MonthView } from '@/components/calendar/MonthView'
import type { CalendarEvent, CalendarFilters, ViewMode } from '@/components/calendar/types'
import { WeekView } from '@/components/calendar/WeekView'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { loadCalendarData, toDateKey } from '@/lib/calendarData'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { useCompanies } from '@/stores/companies'
import { useLocale } from '@/stores/locale'
import type { CompanyCalendar, EventWithSummary, HolidayEntry, Todo } from '@/types'

export function Calendar() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const formatTime = useLocale((state) => state.formatTime)

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
  const [holidays, setHolidays] = useState<HolidayEntry[]>([])
  const companies = useCompanies((state) => state.companies)
  const fetchCompanies = useCompanies((state) => state.fetchCompanies)
  const [isLoading, setIsLoading] = useState(true)
  const [loadErrors, setLoadErrors] = useState<string[]>([])
  const [isSyncing, setIsSyncing] = useState(false)
  const [lastSynced, setLastSynced] = useState<Date | null>(null)

  const [filters, setFilters] = useState<CalendarFilters>({
    showHomeOfficeEvents: true,
    showExternalCalendars: true,
    showTodos: true,
    showHolidays: true,
    companyId: 'all',
  })

  useEffect(() => {
    setBreadcrumb([{ label: 'Calendar' }])
  }, [setBreadcrumb])

  // Sync state to URL
  useEffect(() => {
    const params = new URLSearchParams()
    params.set('view', viewMode)
    params.set('date', toDateKey(currentDate))
    setSearchParams(params, { replace: true })
  }, [viewMode, currentDate, setSearchParams])

  // Calculate date range for holiday fetching (3 months window)
  const getHolidayDateRange = useCallback(() => {
    const start = new Date(currentDate)
    start.setMonth(start.getMonth() - 1)
    start.setDate(1)
    const end = new Date(currentDate)
    end.setMonth(end.getMonth() + 2)
    end.setDate(0) // Last day of next month
    return {
      startDate: toDateKey(start),
      endDate: toDateKey(end),
    }
  }, [currentDate])

  const fetchData = useCallback(async () => {
    try {
      const { startDate, endDate } = getHolidayDateRange()
      await fetchCompanies()
      const { companies: loaded, error: companiesError } = useCompanies.getState()
      const data = await loadCalendarData(startDate, endDate, loaded)
      setEvents(data.events)
      setTodos(data.todos)
      setHolidays(data.holidays)
      setCalendars(data.calendars)
      const errors = companiesError ? [`Companies: ${companiesError}`, ...data.errors] : data.errors
      setLoadErrors(errors)
      if (errors.length === 0) setLastSynced(new Date())
    } finally {
      setIsLoading(false)
    }
  }, [getHolidayDateRange, fetchCompanies])

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
      return new Intl.DateTimeFormat(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).formatRange(start, end)
    }
    return currentDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
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

      {loadErrors.length > 0 && (
        <div
          role="alert"
          className="mb-4 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700"
        >
          Some calendar data could not be loaded: {loadErrors.join('; ')}
        </div>
      )}

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
                title={lastSynced ? `Last synced: ${formatTime(lastSynced)}` : 'Refresh'}
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${isSyncing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </CardHeader>

        <CalendarFiltersPanel filters={filters} setFilters={setFilters} companies={companies} />

        <CardContent className="p-0">
          {viewMode === 'week' ? (
            <WeekView
              currentDate={currentDate}
              events={calendarEvents}
              holidays={filters.showHolidays ? holidays : []}
              getWeekBoundaries={getWeekBoundaries}
            />
          ) : (
            <MonthView
              currentDate={currentDate}
              events={calendarEvents}
              holidays={filters.showHolidays ? holidays : []}
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
            <span className="flex items-center">
              <span className="w-3 h-3 bg-gray-200 rounded mr-1" />
              Holiday
            </span>
          </div>
        </div>
      </Card>
    </div>
  )
}
