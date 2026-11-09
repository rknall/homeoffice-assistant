// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { MapPin, Pencil, Trash2 } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { useLocale } from '@/stores/locale'
import type { Event } from '@/types'
import { eventStatusColors, eventStatusLabels } from '@/utils/labels'

interface EventStandardHeaderProps {
  event: Event
  onEdit: () => void
  onDelete: () => void
}

/** Plain event header shown when the event has no location or cover image. */
export function EventStandardHeader({ event, onEdit, onDelete }: EventStandardHeaderProps) {
  const { formatDate } = useLocale()

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{event.name}</h1>
          <p className="text-gray-500">
            {event.company_name && (
              <span className="text-gray-600">{event.company_name} &middot; </span>
            )}
            {formatDate(event.start_date)} to {formatDate(event.end_date)}
            {(event.city || event.country) && (
              <span className="ml-2 text-gray-600">
                <MapPin className="inline h-4 w-4" />{' '}
                {event.city ? `${event.city}, ${event.country}` : event.country}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={eventStatusColors[event.status]}>{eventStatusLabels[event.status]}</Badge>
          <button
            type="button"
            onClick={onEdit}
            className="p-2 text-gray-400 hover:text-gray-600"
            title="Edit event"
          >
            <Pencil className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="p-2 text-gray-400 hover:text-red-600"
            title="Delete event"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
