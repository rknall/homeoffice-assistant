// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Search } from 'lucide-react'
import type { Company, EventStatus } from '@/types'

export interface EventFiltersState {
  status: EventStatus | 'all'
  companyId: string | 'all'
  search: string
}

interface EventFiltersProps {
  filters: EventFiltersState
  onFiltersChange: (filters: EventFiltersState) => void
  companies: Company[]
}

// Status is computed from dates on the backend
const STATUS_OPTIONS: { value: EventStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'active', label: 'Active' },
  { value: 'past', label: 'Past' },
]

export function EventFilters({ filters, onFiltersChange, companies }: EventFiltersProps) {
  const handleStatusChange = (status: EventStatus | 'all') => {
    onFiltersChange({ ...filters, status })
  }

  const handleCompanyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFiltersChange({ ...filters, companyId: e.target.value })
  }

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({ ...filters, search: e.target.value })
  }

  return (
    <div className="flex flex-wrap items-center gap-4 mb-6">
      {/* Status Pills */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
        {STATUS_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => handleStatusChange(option.value)}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              filters.status === option.value
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Company Dropdown */}
      <select
        value={filters.companyId}
        onChange={handleCompanyChange}
        className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <option value="all">All Companies</option>
        {companies.map((company) => (
          <option key={company.id} value={company.id}>
            {company.name}
          </option>
        ))}
      </select>

      {/* Search Input */}
      <div className="relative flex-1 min-w-[200px] max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search events..."
          value={filters.search}
          onChange={handleSearchChange}
          className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    </div>
  )
}
