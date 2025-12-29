// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Calendar, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useLocale } from '@/stores/locale'
import type { UpcomingEvent } from '@/types'

interface UpcomingEventsProps {
  events: UpcomingEvent[]
}

function DaysUntilBadge({ days }: { days: number }) {
  let bgColor = 'bg-gray-100 text-gray-600'
  let label = `${days}d`

  if (days === 0) {
    bgColor = 'bg-blue-500 text-white'
    label = 'Today'
  } else if (days === 1) {
    bgColor = 'bg-blue-400 text-white'
    label = 'Tomorrow'
  } else if (days <= 7) {
    bgColor = 'bg-blue-100 text-blue-700'
  }

  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${bgColor}`}>{label}</span>
}

export function UpcomingEvents({ events }: UpcomingEventsProps) {
  const { formatDate } = useLocale()

  if (events.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upcoming Events</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 text-center py-4">No upcoming events scheduled</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Upcoming Events</CardTitle>
          <Link to="/events" className="text-sm text-blue-600 hover:text-blue-800">
            View All
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-gray-200" />

          <div className="space-y-4">
            {events.map((event) => (
              <Link key={event.id} to={`/events/${event.id}`} className="relative flex gap-3 group">
                {/* Timeline dot */}
                <div className="relative z-10 mt-1.5">
                  <div className="w-3.5 h-3.5 rounded-full bg-blue-500 border-2 border-white shadow-sm group-hover:bg-blue-600" />
                </div>

                {/* Event content */}
                <div className="flex-1 pb-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className="font-medium text-gray-900 group-hover:text-blue-600 truncate">
                        {event.name}
                      </h4>
                      {event.company_name && (
                        <p className="text-sm text-gray-500 truncate">{event.company_name}</p>
                      )}
                    </div>
                    <DaysUntilBadge days={event.days_until} />
                  </div>

                  <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(event.start_date)}
                      {event.start_date !== event.end_date && ` - ${formatDate(event.end_date)}`}
                    </span>
                    {(event.city || event.country) && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {event.city ? `${event.city}, ${event.country}` : event.country}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
