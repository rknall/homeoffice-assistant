// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { PhotoAsset } from '../../types'

/** Format a distance in km as metres below 1 km. */
function formatDistance(km: number | null) {
  if (km === null) return null
  if (km < 1) return `${Math.round(km * 1000)}m`
  return `${km.toFixed(1)}km`
}

interface AvailablePhotoCardProps {
  photo: PhotoAsset
  formatDate: (dateStr: string | null) => string | null
  onAdd: (photo: PhotoAsset) => void
}

export function AvailablePhotoCard({ photo, formatDate, onAdd }: AvailablePhotoCardProps) {
  return (
    <div
      key={photo.id}
      className="group relative overflow-hidden rounded-lg border border-gray-200 bg-white"
    >
      <div className="aspect-square">
        <img
          src={photo.thumbnail_url || ''}
          alt={photo.original_filename || 'Photo'}
          className="h-full w-full object-cover"
          loading="lazy"
        />
      </div>
      <div className="absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/40" />
      <button
        type="button"
        onClick={() => onAdd(photo)}
        className="absolute inset-0 flex items-center justify-center opacity-0 transition-opacity group-hover:opacity-100"
      >
        <span className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white">
          Add
        </span>
      </button>
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
        <div className="text-xs text-white">
          {formatDate(photo.taken_at)}
          {photo.distance_km !== null && (
            <span className="ml-2">{formatDistance(photo.distance_km)} away</span>
          )}
        </div>
      </div>
    </div>
  )
}
