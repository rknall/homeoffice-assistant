// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Pencil, Play, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { companyCalendarsApi } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import type { CompanyCalendar } from '@/types'
import { CALENDAR_TYPE_LABELS } from '@/types'
import { CalendarFormModal } from './CalendarFormModal'

interface CalendarConnectionsSectionProps {
  companyId: string
  onCalendarsChanged?: () => void
}

export function CalendarConnectionsSection({
  companyId,
  onCalendarsChanged,
}: CalendarConnectionsSectionProps) {
  const [calendars, setCalendars] = useState<CompanyCalendar[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCalendar, setEditingCalendar] = useState<CompanyCalendar | null>(null)
  const [syncingCalendarId, setSyncingCalendarId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchCalendars = useCallback(async () => {
    try {
      const data = await companyCalendarsApi.getCalendars(companyId)
      setCalendars(data)
    } catch {
      setError('Failed to load calendars')
    } finally {
      setIsLoading(false)
    }
  }, [companyId])

  useEffect(() => {
    fetchCalendars()
  }, [fetchCalendars])

  const openModal = (calendar?: CompanyCalendar) => {
    setEditingCalendar(calendar || null)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingCalendar(null)
  }

  const handleCalendarSaved = () => {
    closeModal()
    fetchCalendars()
    onCalendarsChanged?.()
  }

  const deleteCalendar = async (calendarId: string) => {
    if (!confirm('Are you sure you want to disconnect this calendar?')) return
    try {
      await companyCalendarsApi.deleteCalendar(companyId, calendarId)
      fetchCalendars()
      onCalendarsChanged?.()
    } catch {
      setError('Failed to disconnect calendar')
    }
  }

  const syncCalendar = async (calendarId: string) => {
    setSyncingCalendarId(calendarId)
    try {
      await companyCalendarsApi.syncCalendar(companyId, calendarId)
      await fetchCalendars()
    } catch {
      setError('Failed to sync calendar')
    } finally {
      setSyncingCalendarId(null)
    }
  }

  const toggleActive = async (calendar: CompanyCalendar) => {
    try {
      await companyCalendarsApi.updateCalendar(companyId, calendar.id, {
        is_active: !calendar.is_active,
      })
      fetchCalendars()
      onCalendarsChanged?.()
    } catch {
      setError('Failed to update calendar')
    }
  }

  const formatLastSynced = (lastSyncedAt: string | null): string => {
    if (!lastSyncedAt) return 'Never synced'

    const date = new Date(lastSyncedAt)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} minutes ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`
    return `${Math.floor(diffMins / 1440)} days ago`
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-gray-500">Loading calendars...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Connected Calendars</CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              Sync external calendars to see events related to this company
            </p>
          </div>
          <Button onClick={() => openModal()}>
            <Plus className="h-4 w-4 mr-2" />
            Connect Calendar
          </Button>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md mb-4">{error}</div>
          )}

          {calendars.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No calendars connected. Connect a calendar to see external events.
            </p>
          ) : (
            <div className="divide-y divide-gray-100">
              {calendars.map((calendar) => (
                <div
                  key={calendar.id}
                  className={`py-4 ${!calendar.is_active ? 'bg-gray-50 -mx-6 px-6' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center border ${
                          calendar.is_active
                            ? 'bg-white border-gray-200'
                            : 'bg-gray-200 border-gray-200'
                        }`}
                      >
                        <CalendarTypeIcon type={calendar.calendar_type} />
                      </div>
                      <div>
                        <div
                          className={`font-medium ${calendar.is_active ? 'text-gray-900' : 'text-gray-600'}`}
                        >
                          {calendar.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {CALENDAR_TYPE_LABELS[calendar.calendar_type]}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {/* Color indicator */}
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">Color:</span>
                        <div
                          className="w-6 h-6 rounded-full border-2 border-white shadow"
                          style={{
                            backgroundColor: calendar.color,
                            boxShadow: `0 0 0 2px white, 0 0 0 4px ${calendar.color}`,
                            opacity: calendar.is_active ? 1 : 0.5,
                          }}
                        />
                      </div>

                      {/* Status */}
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full ${calendar.is_active ? 'bg-green-500' : 'bg-gray-400'}`}
                        />
                        <span
                          className={`text-sm ${calendar.is_active ? 'text-green-600' : 'text-gray-500'}`}
                        >
                          {calendar.is_active ? 'Active' : 'Paused'}
                        </span>
                      </div>

                      {/* Actions */}
                      {calendar.is_active ? (
                        <button
                          type="button"
                          onClick={() => syncCalendar(calendar.id)}
                          disabled={syncingCalendarId === calendar.id}
                          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                          title="Sync now"
                        >
                          <RefreshCw
                            className={`h-4 w-4 ${syncingCalendarId === calendar.id ? 'animate-spin' : ''}`}
                          />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => toggleActive(calendar)}
                          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                          title="Resume"
                        >
                          <Play className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => openModal(calendar)}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
                        title="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteCalendar(calendar.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-gray-100 rounded-lg"
                        title="Disconnect"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div
                    className={`mt-3 pt-3 border-t flex items-center justify-between text-sm ${
                      calendar.is_active
                        ? 'border-gray-100 text-gray-500'
                        : 'border-gray-200 text-gray-400'
                    }`}
                  >
                    <span>Last synced: {formatLastSynced(calendar.last_synced_at)}</span>
                    <span>Sync interval: {calendar.sync_interval_minutes} minutes</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Info Box */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-blue-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800">About Calendar Sync</h3>
                <div className="mt-2 text-sm text-blue-700">
                  <ul className="list-disc list-inside space-y-1">
                    <li>Calendars sync at the configured interval</li>
                    <li>Only read access is required - we cannot modify your calendar</li>
                    <li>Events from -30 days to +90 days are displayed</li>
                    <li>You can have multiple calendars per company</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <CalendarFormModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onSuccess={handleCalendarSaved}
        companyId={companyId}
        calendar={editingCalendar}
      />
    </>
  )
}

function CalendarTypeIcon({ type }: { type: string }) {
  if (type === 'google') {
    return (
      <svg viewBox="0 0 24 24" className="w-6 h-6" aria-hidden="true">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        />
      </svg>
    )
  }

  if (type === 'outlook') {
    return (
      <svg viewBox="0 0 24 24" className="w-6 h-6" aria-hidden="true">
        <path fill="#0078D4" d="M24 7.387v10.478c0 .23-.08.424-.238.576-.16.154-.353.23-.578.23h-8.578V6.58h8.578c.226 0 .419.078.578.23.159.153.238.35.238.577z"/>
        <path fill="#0078D4" d="M14.606 6.58v11.99L0 16.063V7.21l14.606-.63z"/>
        <path fill="#fff" d="M7.447 9.066c-.704 0-1.278.288-1.72.865-.443.577-.665 1.302-.665 2.175 0 .89.218 1.62.653 2.192.436.572 1.003.858 1.701.858.712 0 1.29-.283 1.732-.849.442-.566.663-1.29.663-2.172 0-.905-.217-1.638-.65-2.2-.435-.562-1.003-.843-1.706-.869h-.008zm.033 5.03c-.38 0-.684-.174-.913-.52-.228-.347-.343-.805-.343-1.374 0-.576.113-1.04.338-1.392.226-.352.529-.528.91-.528.39 0 .698.173.924.518.226.345.34.8.34 1.367 0 .584-.112 1.053-.335 1.408-.223.354-.533.52-.921.52z"/>
      </svg>
    )
  }

  // Default iCal icon
  return (
    <svg viewBox="0 0 24 24" fill="none" className="w-6 h-6" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}
