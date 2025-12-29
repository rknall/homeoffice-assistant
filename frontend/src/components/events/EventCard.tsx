// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { MapPin, Pencil, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/Badge'
import { useLocale } from '@/stores/locale'
import type { EventStatus, EventWithSummary } from '@/types'

// Status is computed from dates on the backend, displayed as read-only
const statusColors: Record<EventStatus, 'default' | 'warning' | 'info'> = {
  upcoming: 'warning',
  active: 'info',
  past: 'default',
}

const statusLabels: Record<EventStatus, string> = {
  upcoming: 'Upcoming',
  active: 'Active',
  past: 'Past',
}

interface EventCardProps {
  event: EventWithSummary
  onEdit: (e: React.MouseEvent, event: EventWithSummary) => void
  onDelete: (e: React.MouseEvent, eventId: string) => void
  daysUntil?: number
}

export function EventCard({ event, onEdit, onDelete, daysUntil }: EventCardProps) {
  const { formatDate } = useLocale()

  const getDaysLabel = () => {
    if (daysUntil === undefined) return null
    if (daysUntil === 0) return 'Today'
    if (daysUntil === 1) return 'Tomorrow'
    if (daysUntil < 0) return `${Math.abs(daysUntil)}d ago`
    return `in ${daysUntil}d`
  }

  const daysLabel = getDaysLabel()

  return (
    <Link
      to={`/events/${event.id}`}
      className={`relative block rounded-lg overflow-hidden transition-all hover:shadow-md ${
        event.cover_thumbnail_url ? 'min-h-[100px]' : 'bg-gray-50 hover:bg-gray-100'
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
      <div
        className={`relative flex items-center justify-between p-4 ${
          event.cover_thumbnail_url ? 'text-white' : ''
        }`}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3
              className={`font-medium truncate ${event.cover_thumbnail_url ? 'text-white' : 'text-gray-900'}`}
            >
              {event.name}
            </h3>
            {daysLabel && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${
                  event.cover_thumbnail_url ? 'bg-white/20 text-white' : 'bg-blue-100 text-blue-700'
                }`}
              >
                {daysLabel}
              </span>
            )}
          </div>
          <p className={`text-sm ${event.cover_thumbnail_url ? 'text-white/80' : 'text-gray-500'}`}>
            {event.company_name && (
              <span className={event.cover_thumbnail_url ? 'text-white/90' : 'text-gray-600'}>
                {event.company_name} &middot;{' '}
              </span>
            )}
            {formatDate(event.start_date)} to {formatDate(event.end_date)}
            {(event.city || event.country) && (
              <span className="ml-2">
                <MapPin className="inline h-3 w-3" />{' '}
                {event.city ? `${event.city}, ${event.country}` : event.country}
              </span>
            )}
          </p>
          {/* Summary stats */}
          <div
            className={`mt-1 text-xs flex items-center gap-3 ${
              event.cover_thumbnail_url ? 'text-white/70' : 'text-gray-400'
            }`}
          >
            {event.expense_count > 0 && (
              <span>
                {event.expense_count} expense{event.expense_count !== 1 ? 's' : ''} &middot; EUR{' '}
                {event.expense_total.toFixed(2)}
              </span>
            )}
            {event.todo_incomplete_count > 0 && (
              <span>
                {event.todo_incomplete_count} todo{event.todo_incomplete_count !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 ml-4">
          {/* Status badge - computed from dates, read-only */}
          <Badge variant={statusColors[event.status]}>{statusLabels[event.status]}</Badge>
          <button
            type="button"
            onClick={(e) => onEdit(e, event)}
            className={`p-1 ${event.cover_thumbnail_url ? 'text-white/70 hover:text-white' : 'text-gray-400 hover:text-gray-600'}`}
            title="Edit event"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={(e) => onDelete(e, event.id)}
            className={`p-1 ${event.cover_thumbnail_url ? 'text-white/70 hover:text-red-400' : 'text-gray-400 hover:text-red-600'}`}
            title="Delete event"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </Link>
  )
}
