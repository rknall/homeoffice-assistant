// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { Dispatch, SetStateAction } from 'react'
import type { Company } from '@/types'
import type { CalendarFilters } from './types'

interface CalendarFiltersPanelProps {
  filters: CalendarFilters
  setFilters: Dispatch<SetStateAction<CalendarFilters>>
  companies: Company[]
}

export function CalendarFiltersPanel({
  filters,
  setFilters,
  companies,
}: CalendarFiltersPanelProps) {
  return (
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
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.showHolidays}
              onChange={(e) => setFilters((f) => ({ ...f, showHolidays: e.target.checked }))}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Holidays</span>
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
  )
}
