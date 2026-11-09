// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Camera } from 'lucide-react'
import { PhotoGallery } from '@/components/PhotoGallery'
import type { Event } from '@/types'

interface PhotosTabProps {
  event: Event
  eventId: string
  photoCount: number
  onPhotoCountChange: (count: number) => void
}

/** Photos tab: linked Immich photos with a count badge. */
export function PhotosTab({ event, eventId, photoCount, onPhotoCountChange }: PhotosTabProps) {
  return (
    <>
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
        <Camera className="h-5 w-5" />
        Photos from Immich
        {photoCount > 0 && (
          <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
            {photoCount} linked
          </span>
        )}
      </h3>
      <PhotoGallery
        eventId={eventId}
        hasLocation={!!(event.latitude && event.longitude)}
        eventStartDate={event.start_date}
        onPhotoCountChange={onPhotoCountChange}
      />
    </>
  )
}
