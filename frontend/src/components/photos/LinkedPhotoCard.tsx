// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { PhotoReference } from '../../types'

interface LinkedPhotoCardProps {
  eventId: string
  photo: PhotoReference
  isEditingCaption: boolean
  captionText: string
  formatDate: (dateStr: string | null) => string | null
  onCaptionTextChange: (value: string) => void
  onStartEditCaption: (photo: PhotoReference) => void
  onSaveCaption: (photoId: string) => void
  onCancelEditCaption: () => void
  onToggleIncludeInReport: (photoId: string, currentValue: boolean) => void
  onRemove: (photoId: string) => void
}

export function LinkedPhotoCard({
  eventId,
  photo,
  isEditingCaption,
  captionText,
  formatDate,
  onCaptionTextChange,
  onStartEditCaption,
  onSaveCaption,
  onCancelEditCaption,
  onToggleIncludeInReport,
  onRemove,
}: LinkedPhotoCardProps) {
  return (
    <div key={photo.id} className="flex gap-3 rounded-lg border border-gray-200 bg-white p-3">
      <div className="h-24 w-24 flex-shrink-0 overflow-hidden rounded-md">
        <img
          src={`/api/v1/events/${eventId}/photos/${photo.immich_asset_id}/thumbnail`}
          alt={photo.caption || 'Photo'}
          className="h-full w-full object-cover"
        />
      </div>
      <div className="flex flex-1 flex-col">
        {/* Caption editing */}
        {isEditingCaption ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={captionText}
              onChange={(e) => onCaptionTextChange(e.target.value)}
              placeholder="Add caption..."
              className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
              onKeyDown={(e) => {
                if (e.key === 'Enter') onSaveCaption(photo.id)
                if (e.key === 'Escape') onCancelEditCaption()
              }}
            />
            <button
              type="button"
              onClick={() => onSaveCaption(photo.id)}
              className="rounded bg-blue-600 px-2 py-1 text-xs text-white"
            >
              Save
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => onStartEditCaption(photo)}
            className="text-left text-sm text-gray-700 hover:text-gray-900"
          >
            {photo.caption || <span className="italic text-gray-400">Click to add caption...</span>}
          </button>
        )}

        {/* Date and location */}
        <div className="mt-1 text-xs text-gray-500">
          {formatDate(photo.taken_at)}
          {photo.latitude && photo.longitude && (
            <span className="ml-2">
              {photo.latitude.toFixed(4)}, {photo.longitude.toFixed(4)}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="mt-auto flex items-center justify-between pt-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={photo.include_in_report}
              onChange={() => onToggleIncludeInReport(photo.id, photo.include_in_report)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Include in report
          </label>
          <button
            type="button"
            onClick={() => onRemove(photo.id)}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  )
}
