// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight, ChevronUp, MapPin, Move, Pencil, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/Badge'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { useLocale } from '@/stores/locale'
import type { Event, LocationImage } from '@/types'
import { eventStatusColors, eventStatusLabels } from '@/utils/labels'
import type { EventCoverState } from './useEventCover'

interface EventCoverBannerProps {
  event: Event
  image: LocationImage
  cover: EventCoverState
  onEdit: () => void
  onDelete: () => void
}

/** Header with the location or cover image, overlaid breadcrumb and position controls. */
export function EventCoverBanner({ event, image, cover, onEdit, onDelete }: EventCoverBannerProps) {
  const { formatDate } = useLocale()
  const { items: breadcrumbItems } = useBreadcrumb()
  const { isAdjustingPosition, setIsAdjustingPosition } = cover

  return (
    <div className="relative mb-6 -mx-6 -mt-6 h-48 overflow-hidden">
      <img
        src={image.image_url}
        alt={event.city ? `${event.city}, ${event.country}` : event.country || ''}
        className="h-full w-full object-cover"
        style={{ objectPosition: `center ${cover.imagePosition}%` }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
      {/* Breadcrumb overlaid on image */}
      <nav className="absolute top-4 left-6 flex items-center text-sm">
        <div className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-black/30 backdrop-blur-sm">
          <Link to="/" className="text-white/80 hover:text-white transition-colors">
            Dashboard
          </Link>
          {breadcrumbItems.map((item) => {
            const key = item.href ? `link-${item.href}` : `label-${item.label}`
            return (
              <span key={key} className="flex items-center">
                <ChevronRight className="h-4 w-4 mx-1 text-white/50" />
                {item.href ? (
                  <Link to={item.href} className="text-white/80 hover:text-white transition-colors">
                    {item.label}
                  </Link>
                ) : (
                  <span className="text-white font-medium">{item.label}</span>
                )}
              </span>
            )
          })}
        </div>
      </nav>
      <div className="absolute bottom-4 left-6 right-6">
        <h1 className="text-2xl font-bold text-white drop-shadow-lg">{event.name}</h1>
        <p className="text-white/90 drop-shadow">
          {event.company_name && <span>{event.company_name} &middot; </span>}
          {formatDate(event.start_date)} to {formatDate(event.end_date)}
          {(event.city || event.country) && (
            <span className="ml-2">
              <MapPin className="inline h-4 w-4" />{' '}
              {event.city ? `${event.city}, ${event.country}` : event.country}
            </span>
          )}
        </p>
      </div>
      <div className="absolute top-4 right-6 flex items-center gap-3">
        <Badge variant={eventStatusColors[event.status]}>{eventStatusLabels[event.status]}</Badge>
        {/* Position adjustment controls - only for Unsplash images */}
        {event.cover_image_url && !isAdjustingPosition && (
          <button
            type="button"
            onClick={() => setIsAdjustingPosition(true)}
            className="p-2 text-white/80 hover:text-white bg-black/20 rounded-full"
            title="Adjust image position"
          >
            <Move className="h-5 w-5" />
          </button>
        )}
        {isAdjustingPosition && (
          <div className="flex items-center gap-1 bg-black/40 rounded-full px-2 py-1">
            <button
              type="button"
              onClick={() => cover.adjustImagePosition(-10)}
              className="p-1 text-white/80 hover:text-white"
              title="Move up"
            >
              <ChevronUp className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => cover.adjustImagePosition(10)}
              className="p-1 text-white/80 hover:text-white"
              title="Move down"
            >
              <ChevronDown className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={cover.saveImagePosition}
              className="px-2 py-1 text-xs text-white bg-blue-600 hover:bg-blue-700 rounded"
            >
              Save
            </button>
            <button
              type="button"
              onClick={cover.cancelPositionAdjustment}
              className="px-2 py-1 text-xs text-white/80 hover:text-white"
            >
              Cancel
            </button>
          </div>
        )}
        {!isAdjustingPosition && (
          <>
            <button
              type="button"
              onClick={onEdit}
              className="p-2 text-white/80 hover:text-white bg-black/20 rounded-full"
              title="Edit event"
            >
              <Pencil className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={onDelete}
              className="p-2 text-white/80 hover:text-red-400 bg-black/20 rounded-full"
              title="Delete event"
            >
              <Trash2 className="h-5 w-5" />
            </button>
          </>
        )}
      </div>
      {image.attribution_html && (
        <div
          className="absolute bottom-1 right-2 text-xs text-white/60"
          // biome-ignore lint/security/noDangerouslySetInnerHtml: Location metadata already rendered as trusted HTML
          // biome-ignore lint/style/useNamingConvention: __html is required by React when setting inner HTML
          dangerouslySetInnerHTML={{ __html: image.attribution_html }}
        />
      )}
    </div>
  )
}
