// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Plus } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/api/client'
import { EventFormModal } from '@/components/EventFormModal'
import { EventCard, EventFilters, type EventFiltersState, TimelineGroup } from '@/components/events'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type {
  Company,
  Event,
  EventCustomFieldChoices as EventCustomFieldChoicesType,
  EventStatus,
  EventWithSummary,
} from '@/types'

function calculateDaysUntil(startDate: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const start = new Date(startDate)
  start.setHours(0, 0, 0, 0)
  return Math.ceil((start.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function isWithinDays(dateStr: string, days: number): boolean {
  const date = new Date(dateStr)
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  return date >= cutoff
}

export function Events() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [events, setEvents] = useState<EventWithSummary[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [customFieldChoices, setCustomFieldChoices] = useState<EventCustomFieldChoicesType | null>(
    null,
  )
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingEvent, setEditingEvent] = useState<Event | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Filters state - initialize from URL params
  const [filters, setFilters] = useState<EventFiltersState>(() => ({
    status: (searchParams.get('status') as EventStatus | 'all') || 'all',
    companyId: searchParams.get('company') || 'all',
    search: searchParams.get('q') || '',
  }))

  const fetchData = useCallback(async () => {
    try {
      const [eventsData, companiesData, choicesData] = await Promise.all([
        api.get<EventWithSummary[]>('/events?include_summary=true'),
        api.get<Company[]>('/companies'),
        api.get<EventCustomFieldChoicesType>('/integrations/event-custom-field-choices'),
      ])
      setEvents(eventsData)
      setCompanies(companiesData)
      setCustomFieldChoices(choicesData)
    } catch {
      setError('Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    setBreadcrumb([{ label: 'Events' }])
  }, [setBreadcrumb])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Sync filters to URL
  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.status !== 'all') params.set('status', filters.status)
    if (filters.companyId !== 'all') params.set('company', filters.companyId)
    if (filters.search) params.set('q', filters.search)
    setSearchParams(params, { replace: true })
  }, [filters, setSearchParams])

  // Open modal if navigated with ?new=true (only if companies exist)
  useEffect(() => {
    if (searchParams.get('new') === 'true' && !isLoading) {
      if (companies.length > 0) {
        setIsModalOpen(true)
      }
      const newParams = new URLSearchParams(searchParams)
      newParams.delete('new')
      setSearchParams(newParams, { replace: true })
    }
  }, [searchParams, setSearchParams, isLoading, companies.length])

  // Filter and group events
  const { filteredEvents, groupedEvents } = useMemo(() => {
    let filtered = events

    // Apply status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter((e) => e.status === filters.status)
    }

    // Apply company filter
    if (filters.companyId !== 'all') {
      filtered = filtered.filter((e) => e.company_id === filters.companyId)
    }

    // Apply search filter
    if (filters.search) {
      const search = filters.search.toLowerCase()
      filtered = filtered.filter(
        (e) =>
          e.name.toLowerCase().includes(search) ||
          e.company_name?.toLowerCase().includes(search) ||
          e.city?.toLowerCase().includes(search) ||
          e.country?.toLowerCase().includes(search),
      )
    }

    // Group events by timeline
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const upcoming: EventWithSummary[] = []
    const active: EventWithSummary[] = []
    const recentlyCompleted: EventWithSummary[] = []
    const older: EventWithSummary[] = []

    // Group based on computed status (status is derived from dates by backend)
    for (const event of filtered) {
      if (event.status === 'active') {
        active.push(event)
      } else if (event.status === 'upcoming') {
        upcoming.push(event)
      } else if (event.status === 'past') {
        if (isWithinDays(event.end_date, 30)) {
          recentlyCompleted.push(event)
        } else {
          older.push(event)
        }
      }
    }

    // Sort each group
    upcoming.sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
    active.sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
    recentlyCompleted.sort(
      (a, b) => new Date(b.end_date).getTime() - new Date(a.end_date).getTime(),
    )
    older.sort((a, b) => new Date(b.end_date).getTime() - new Date(a.end_date).getTime())

    return {
      filteredEvents: filtered,
      groupedEvents: { upcoming, active, recentlyCompleted, older },
    }
  }, [events, filters])

  const deleteEvent = async (e: React.MouseEvent, eventId: string) => {
    e.preventDefault()
    e.stopPropagation()
    if (
      !confirm(
        'Are you sure you want to delete this event? This will also delete all associated expenses, contacts, notes, and todos.',
      )
    ) {
      return
    }
    try {
      await api.delete(`/events/${eventId}`)
      await fetchData()
    } catch {
      setError('Failed to delete event')
    }
  }

  const openEditModal = (e: React.MouseEvent, event: EventWithSummary) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingEvent(event)
  }

  // Note: Status is now computed from dates, no manual status updates

  const handleEventCreated = (event?: Event) => {
    if (event) {
      navigate(`/events/${event.id}`)
    }
  }

  const handleEventUpdated = () => {
    fetchData()
    setEditingEvent(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
        <div className="relative group">
          <Button onClick={() => setIsModalOpen(true)} disabled={companies.length === 0}>
            <Plus className="h-4 w-4 mr-2" />
            New Event
          </Button>
          {companies.length === 0 && (
            <div className="absolute right-0 top-full mt-1 w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
              Create a company first before adding events
            </div>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Filters */}
      <EventFilters filters={filters} onFiltersChange={setFilters} companies={companies} />

      <Card>
        <CardHeader>
          <CardTitle>
            {filteredEvents.length} Event{filteredEvents.length !== 1 ? 's' : ''}
            {filters.status !== 'all' && ` (${filters.status})`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : filteredEvents.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              {events.length === 0
                ? 'No events yet. Create your first event to get started.'
                : 'No events match your filters.'}
            </p>
          ) : (
            <div>
              {/* Upcoming Events */}
              <TimelineGroup
                title="Upcoming"
                count={groupedEvents.upcoming.length}
                defaultOpen={true}
              >
                {groupedEvents.upcoming.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    onEdit={openEditModal}
                    onDelete={deleteEvent}
                    daysUntil={calculateDaysUntil(event.start_date)}
                  />
                ))}
              </TimelineGroup>

              {/* Active Events */}
              <TimelineGroup title="Active" count={groupedEvents.active.length} defaultOpen={true}>
                {groupedEvents.active.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    onEdit={openEditModal}
                    onDelete={deleteEvent}
                  />
                ))}
              </TimelineGroup>

              {/* Recently Completed */}
              <TimelineGroup
                title="Recently Completed"
                count={groupedEvents.recentlyCompleted.length}
                defaultOpen={true}
              >
                {groupedEvents.recentlyCompleted.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    onEdit={openEditModal}
                    onDelete={deleteEvent}
                  />
                ))}
              </TimelineGroup>

              {/* Older Events */}
              <TimelineGroup
                title="Older"
                count={groupedEvents.older.length}
                defaultOpen={false}
                variant="muted"
              >
                {groupedEvents.older.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    onEdit={openEditModal}
                    onDelete={deleteEvent}
                  />
                ))}
              </TimelineGroup>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Event Modal */}
      <EventFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleEventCreated}
        companies={companies}
        customFieldChoices={customFieldChoices}
      />

      {/* Edit Event Modal */}
      <EventFormModal
        isOpen={!!editingEvent}
        onClose={() => setEditingEvent(null)}
        onSuccess={handleEventUpdated}
        event={editingEvent}
        companies={companies}
        customFieldChoices={customFieldChoices}
      />
    </div>
  )
}
