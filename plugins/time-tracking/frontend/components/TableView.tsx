// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useMemo, useState } from 'react'
import type { TimeRecord } from '../types'
import { DAY_TYPE_LABELS } from '../types'

interface TableViewProps {
  records: TimeRecord[]
  overlappingRecordIds: Set<string>
  getCompanyColor: (companyId: string) => string
  onRecordClick: (record: TimeRecord) => void
  isLoading: boolean
}

interface TableRow {
  id: string
  record: TimeRecord
  isFirstOfDay: boolean
  entryCount: number
}

/**
 * TableView - Tabular list of time records
 *
 * Displays records in a sortable table format with company colors
 * and overlap highlighting.
 */
export function TableView({
  records,
  overlappingRecordIds,
  getCompanyColor,
  onRecordClick,
  isLoading,
}: TableViewProps) {
  const [sortField, setSortField] = useState<'date' | 'company'>('date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  // Sort and flatten records into table rows
  const tableRows = useMemo((): TableRow[] => {
    // Sort records
    const sorted = [...records].sort((a, b) => {
      let comparison = 0
      if (sortField === 'date') {
        comparison = a.date.localeCompare(b.date)
      } else if (sortField === 'company') {
        comparison = (a.company_name || '').localeCompare(b.company_name || '')
      }
      return sortDirection === 'asc' ? comparison : -comparison
    })

    // Group by date to mark first of day
    const rows: TableRow[] = []
    let lastDate = ''

    for (const record of sorted) {
      const isFirstOfDay = record.date !== lastDate
      lastDate = record.date

      rows.push({
        id: record.id,
        record,
        isFirstOfDay,
        entryCount: 1, // Simplified - could expand for multiple entries per record
      })
    }

    return rows
  }, [records, sortField, sortDirection])

  // Toggle sort
  const handleSort = (field: 'date' | 'company') => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  // Format date for display
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('de-AT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  }

  // Get weekday name
  const getDayName = (dateStr: string): string => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { weekday: 'short' })
  }

  // Format time for display
  const formatTime = (time: string | null): string => {
    if (!time) return '--:--'
    return time
  }

  // Calculate duration in hours
  const calculateDuration = (checkIn: string | null, checkOut: string | null): string => {
    if (!checkIn || !checkOut) return '-'

    const [inH, inM] = checkIn.split(':').map(Number)
    const [outH, outM] = checkOut.split(':').map(Number)

    let minutes = outH * 60 + outM - (inH * 60 + inM)
    // Handle overnight
    if (minutes < 0) minutes += 24 * 60

    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}:${mins.toString().padStart(2, '0')}`
  }

  // Check if record is editable
  const isEditable = (record: TimeRecord): boolean => {
    return record.day_type !== 'public_holiday' && !record.is_locked
  }

  // Sort indicator
  const SortIndicator = ({ field }: { field: 'date' | 'company' }) => {
    if (sortField !== field) return null
    return <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('date')}
              >
                Date
                <SortIndicator field="date" />
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Day</th>
              <th
                className="px-4 py-3 text-left text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('company')}
              >
                Company
                <SortIndicator field="company" />
              </th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Type</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Check In</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Check Out</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Duration</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  {isLoading ? 'Loading...' : 'No records this month'}
                </td>
              </tr>
            ) : (
              tableRows.map((row, index) => {
                const hasOverlap = overlappingRecordIds.has(row.record.id)
                const editable = isEditable(row.record)
                const companyColor = getCompanyColor(row.record.company_id)

                return (
                  <tr
                    key={row.id}
                    className={`
                      ${row.isFirstOfDay ? 'border-t border-gray-200' : ''}
                      ${row.record.is_locked ? 'opacity-60' : ''}
                      ${hasOverlap ? 'bg-red-50' : index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                      ${editable ? 'cursor-pointer hover:bg-blue-50' : ''}
                      transition-colors
                    `}
                  >
                    {/* Date */}
                    <td className="px-4 py-2 text-sm text-gray-900">
                      {row.isFirstOfDay ? formatDate(row.record.date) : ''}
                    </td>

                    {/* Day name */}
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {row.isFirstOfDay ? getDayName(row.record.date) : ''}
                    </td>

                    {/* Company */}
                    <td className="px-4 py-2">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
                        style={{ backgroundColor: companyColor }}
                      >
                        {row.record.company_name || 'Unknown'}
                      </span>
                    </td>

                    {/* Day type */}
                    <td className="px-4 py-2">
                      <span
                        className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                        style={{
                          backgroundColor: `${companyColor}20`,
                          color: companyColor,
                        }}
                      >
                        {DAY_TYPE_LABELS[row.record.day_type] || row.record.day_type}
                      </span>
                    </td>

                    {/* Check In */}
                    <td className="px-4 py-2 text-sm text-gray-900 font-mono">
                      {formatTime(row.record.check_in)}
                    </td>

                    {/* Check Out */}
                    <td className="px-4 py-2 text-sm text-gray-900 font-mono">
                      {formatTime(row.record.check_out)}
                    </td>

                    {/* Duration */}
                    <td className="px-4 py-2 text-sm text-gray-900 font-mono">
                      {calculateDuration(row.record.check_in, row.record.check_out)}
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-2">
                      {editable && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            onRecordClick(row.record)
                          }}
                          className={`
                            px-2 py-1 text-xs font-medium rounded
                            ${hasOverlap ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}
                          `}
                        >
                          {hasOverlap ? 'Fix' : 'Edit'}
                        </button>
                      )}
                      {row.record.is_locked && (
                        <span className="text-xs text-gray-400">Locked</span>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="p-3 border-t border-gray-200 flex items-center gap-4 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-50 border border-red-200" />
          <span>Overlapping entries</span>
        </div>
        <div className="flex items-center gap-1">
          <span>Click row to view details</span>
        </div>
      </div>
    </div>
  )
}
