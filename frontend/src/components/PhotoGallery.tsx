// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { PhotoAsset, PhotoReference } from '../types'

interface PhotoGalleryProps {
  eventId: string
  hasLocation: boolean
  onPhotoCountChange?: (count: number) => void
}

export function PhotoGallery({
  eventId,
  hasLocation,
  onPhotoCountChange,
}: PhotoGalleryProps) {
  const [availablePhotos, setAvailablePhotos] = useState<PhotoAsset[]>([])
  const [linkedPhotos, setLinkedPhotos] = useState<PhotoReference[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'available' | 'linked'>('available')
  const [editingCaption, setEditingCaption] = useState<string | null>(null)
  const [captionText, setCaptionText] = useState('')

  // Fetch available photos from Immich
  const fetchAvailablePhotos = useCallback(async () => {
    if (!hasLocation) return

    setIsLoading(true)
    setError(null)
    try {
      const photos = await api.get<PhotoAsset[]>(`/events/${eventId}/photos`)
      setAvailablePhotos(photos)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch photos'
      // Don't show error if Immich is not configured
      if (!message.includes('not configured')) {
        setError(message)
      }
    } finally {
      setIsLoading(false)
    }
  }, [eventId, hasLocation])

  // Fetch linked photo references
  const fetchLinkedPhotos = useCallback(async () => {
    try {
      const refs = await api.get<PhotoReference[]>(
        `/events/${eventId}/photos/references`
      )
      setLinkedPhotos(refs)
      onPhotoCountChange?.(refs.length)
    } catch (err) {
      console.error('Failed to fetch linked photos:', err)
    }
  }, [eventId, onPhotoCountChange])

  // Load photos on mount
  useEffect(() => {
    fetchLinkedPhotos()
    if (hasLocation) {
      fetchAvailablePhotos()
    }
  }, [fetchLinkedPhotos, fetchAvailablePhotos, hasLocation])

  // Add photo to event
  const handleAddPhoto = async (photo: PhotoAsset) => {
    try {
      await api.post(`/events/${eventId}/photos`, {
        immich_asset_id: photo.id,
        thumbnail_url: photo.thumbnail_url,
        taken_at: photo.taken_at,
        latitude: photo.latitude,
        longitude: photo.longitude,
      })
      // Refresh both lists
      await Promise.all([fetchAvailablePhotos(), fetchLinkedPhotos()])
    } catch (err) {
      console.error('Failed to add photo:', err)
    }
  }

  // Remove photo from event
  const handleRemovePhoto = async (photoId: string) => {
    try {
      await api.delete(`/events/${eventId}/photos/${photoId}`)
      await fetchLinkedPhotos()
      // Also refresh available to update is_linked status
      if (hasLocation) {
        await fetchAvailablePhotos()
      }
    } catch (err) {
      console.error('Failed to remove photo:', err)
    }
  }

  // Toggle include in report
  const handleToggleIncludeInReport = async (
    photoId: string,
    currentValue: boolean
  ) => {
    try {
      await api.put(`/events/${eventId}/photos/${photoId}`, {
        include_in_report: !currentValue,
      })
      await fetchLinkedPhotos()
    } catch (err) {
      console.error('Failed to update photo:', err)
    }
  }

  // Save caption
  const handleSaveCaption = async (photoId: string) => {
    try {
      await api.put(`/events/${eventId}/photos/${photoId}`, {
        caption: captionText || null,
      })
      setEditingCaption(null)
      setCaptionText('')
      await fetchLinkedPhotos()
    } catch (err) {
      console.error('Failed to update caption:', err)
    }
  }

  // Start editing caption
  const startEditingCaption = (photo: PhotoReference) => {
    setEditingCaption(photo.id)
    setCaptionText(photo.caption || '')
  }

  // Format distance
  const formatDistance = (km: number | null) => {
    if (km === null) return null
    if (km < 1) return `${Math.round(km * 1000)}m`
    return `${km.toFixed(1)}km`
  }

  // Format date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null
    return new Date(dateStr).toLocaleDateString()
  }

  if (!hasLocation && linkedPhotos.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center text-gray-500">
        Add a location to this event to search for photos from Immich.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          type="button"
          onClick={() => setActiveTab('available')}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === 'available'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Available ({availablePhotos.filter((p) => !p.is_linked).length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('linked')}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === 'linked'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Linked ({linkedPhotos.length})
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        </div>
      )}

      {/* Available photos tab */}
      {activeTab === 'available' && !isLoading && (
        <>
          {!hasLocation ? (
            <div className="py-4 text-center text-gray-500">
              Add a location to search for photos.
            </div>
          ) : availablePhotos.filter((p) => !p.is_linked).length === 0 ? (
            <div className="py-4 text-center text-gray-500">
              No photos found for this location and date range.
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              {availablePhotos
                .filter((p) => !p.is_linked)
                .map((photo) => (
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
                      onClick={() => handleAddPhoto(photo)}
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
                          <span className="ml-2">
                            {formatDistance(photo.distance_km)} away
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </>
      )}

      {/* Linked photos tab */}
      {activeTab === 'linked' && (
        <>
          {linkedPhotos.length === 0 ? (
            <div className="py-4 text-center text-gray-500">
              No photos linked to this event yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {linkedPhotos.map((photo) => (
                <div
                  key={photo.id}
                  className="flex gap-3 rounded-lg border border-gray-200 bg-white p-3"
                >
                  <div className="h-24 w-24 flex-shrink-0 overflow-hidden rounded-md">
                    <img
                      src={`/api/v1/events/${eventId}/photos/${photo.immich_asset_id}/thumbnail`}
                      alt={photo.caption || 'Photo'}
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div className="flex flex-1 flex-col">
                    {/* Caption editing */}
                    {editingCaption === photo.id ? (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={captionText}
                          onChange={(e) => setCaptionText(e.target.value)}
                          placeholder="Add caption..."
                          className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveCaption(photo.id)
                            if (e.key === 'Escape') setEditingCaption(null)
                          }}
                        />
                        <button
                          type="button"
                          onClick={() => handleSaveCaption(photo.id)}
                          className="rounded bg-blue-600 px-2 py-1 text-xs text-white"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => startEditingCaption(photo)}
                        className="text-left text-sm text-gray-700 hover:text-gray-900"
                      >
                        {photo.caption || (
                          <span className="italic text-gray-400">
                            Click to add caption...
                          </span>
                        )}
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
                          onChange={() =>
                            handleToggleIncludeInReport(
                              photo.id,
                              photo.include_in_report
                            )
                          }
                          className="h-4 w-4 rounded border-gray-300"
                        />
                        Include in report
                      </label>
                      <button
                        type="button"
                        onClick={() => handleRemovePhoto(photo.id)}
                        className="text-sm text-red-600 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Refresh button */}
      {hasLocation && activeTab === 'available' && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={fetchAvailablePhotos}
            disabled={isLoading}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Refresh Photos
          </button>
        </div>
      )}
    </div>
  )
}
