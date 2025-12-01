// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, MapPin } from 'lucide-react'
import { api } from '@/api/client'
import type { Event, EventStatus } from '@/types'
import { useLocale } from '@/stores/locale'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'

const statusColors: Record<EventStatus, 'default' | 'warning' | 'info'> = {
  planning: 'warning',
  active: 'info',
  past: 'default',
}

export function Dashboard() {
  const navigate = useNavigate()
  const { formatDate } = useLocale()
  const { clear: clearBreadcrumb } = useBreadcrumb()
  const [events, setEvents] = useState<Event[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    clearBreadcrumb()
  }, [clearBreadcrumb])

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const data = await api.get<Event[]>('/events')
        setEvents(data)
      } catch {
        // Handle error
      } finally {
        setIsLoading(false)
      }
    }
    fetchEvents()
  }, [])

  const activeEvents = events.filter((e) => e.status === 'active')
  const planningEvents = events.filter((e) => e.status === 'planning')
  const pastEvents = events.filter((e) => e.status === 'past')

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Button onClick={() => navigate('/events?new=true')}>
          <Plus className="h-4 w-4 mr-2" />
          New Event
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm font-medium text-gray-500">Active</p>
            <p className="text-2xl font-bold text-gray-900">{activeEvents.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm font-medium text-gray-500">Planning</p>
            <p className="text-2xl font-bold text-gray-900">{planningEvents.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm font-medium text-gray-500">Past</p>
            <p className="text-2xl font-bold text-gray-900">{pastEvents.length}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : events.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No events yet. Create your first event to get started.
            </p>
          ) : (
            <div className="space-y-3">
              {events.slice(0, 5).map((event) => (
                <Link
                  key={event.id}
                  to={`/events/${event.id}`}
                  className={`relative block rounded-lg overflow-hidden transition-all hover:shadow-md ${
                    event.cover_thumbnail_url
                      ? 'min-h-[80px]'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  {event.cover_thumbnail_url && (
                    <>
                      <div
                        className="absolute inset-0 bg-cover bg-center"
                        style={{ backgroundImage: `url(${event.cover_thumbnail_url})` }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/50 to-black/30" />
                    </>
                  )}
                  <div className={`relative flex items-center justify-between p-4 ${
                    event.cover_thumbnail_url ? 'text-white' : ''
                  }`}>
                    <div>
                      <h3 className={`font-medium ${event.cover_thumbnail_url ? 'text-white' : 'text-gray-900'}`}>
                        {event.name}
                      </h3>
                      <p className={`text-sm ${event.cover_thumbnail_url ? 'text-white/80' : 'text-gray-500'}`}>
                        {event.company_name && (
                          <span className={event.cover_thumbnail_url ? 'text-white/90' : 'text-gray-600'}>
                            {event.company_name} &middot;{' '}
                          </span>
                        )}
                        {formatDate(event.start_date)} to {formatDate(event.end_date)}
                        {(event.city || event.country) && (
                          <span className="ml-2">
                            <MapPin className="inline h-3 w-3" /> {event.city ? `${event.city}, ${event.country}` : event.country}
                          </span>
                        )}
                      </p>
                    </div>
                    <Badge variant={statusColors[event.status]}>{event.status}</Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
