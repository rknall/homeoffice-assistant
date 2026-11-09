// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useLocale } from '../stores/locale'
import type { PhotoAsset, PhotoReference } from '../types'
import { AvailablePhotoCard } from './photos/AvailablePhotoCard'
import { LinkedPhotoCard } from './photos/LinkedPhotoCard'

interface PhotoGalleryProps {
  eventId: string
  hasLocation: boolean
  eventStartDate?: string // ISO date string to determine if event is past
  onPhotoCountChange?: (count: number) => void
}

export function PhotoGallery({
  eventId,
  hasLocation,
  eventStartDate,
  onPhotoCountChange,
}: PhotoGalleryProps) {
  const [availablePhotos, setAvailablePhotos] = useState<PhotoAsset[]>([])
  const [linkedPhotos, setLinkedPhotos] = useState<PhotoReference[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDateSearchLoading, setIsDateSearchLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'available' | 'linked'>('linked')
  const [editingCaption, setEditingCaption] = useState<string | null>(null)
  const [captionText, setCaptionText] = useState('')
  const [searchMode, setSearchMode] = useState<'location' | 'date'>('location')

  // Check if event is in the past (date search only available for past events)
  const isPastEvent = eventStartDate ? new Date(eventStartDate) <= new Date() : false

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
      const refs = await api.get<PhotoReference[]>(`/events/${eventId}/photos/references`)
      setLinkedPhotos(refs)
      onPhotoCountChange?.(refs.length)
    } catch (err) {
      console.error('Failed to fetch linked photos:', err)
    }
  }, [eventId, onPhotoCountChange])

  // Fetch photos by date range (manual trigger)
  const fetchPhotosByDate = async () => {
    setIsDateSearchLoading(true)
    setError(null)
    try {
      const photos = await api.get<PhotoAsset[]>(`/events/${eventId}/photos/by-date`)
      setAvailablePhotos(photos)
      setSearchMode('date')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch photos by date'
      setError(message)
    } finally {
      setIsDateSearchLoading(false)
    }
  }

  // Switch back to location search
  const switchToLocationSearch = async () => {
    setSearchMode('location')
    await fetchAvailablePhotos()
  }

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
      const newRef = await api.post<PhotoReference>(`/events/${eventId}/photos`, {
        immich_asset_id: photo.id,
        thumbnail_url: photo.thumbnail_url,
        taken_at: photo.taken_at,
        latitude: photo.latitude,
        longitude: photo.longitude,
      })
      // Update state locally instead of refetching
      setAvailablePhotos((prev) =>
        prev.map((p) => (p.id === photo.id ? { ...p, is_linked: true } : p)),
      )
      setLinkedPhotos((prev) => [...prev, newRef])
      onPhotoCountChange?.(linkedPhotos.length + 1)
    } catch (err) {
      console.error('Failed to add photo:', err)
    }
  }

  // Remove photo from event
  const handleRemovePhoto = async (photoId: string) => {
    try {
      const photoToRemove = linkedPhotos.find((p) => p.id === photoId)
      await api.delete(`/events/${eventId}/photos/${photoId}`)
      // Update state locally instead of refetching
      setLinkedPhotos((prev) => prev.filter((p) => p.id !== photoId))
      onPhotoCountChange?.(linkedPhotos.length - 1)
      // Update available photos to mark as unlinked
      if (photoToRemove) {
        setAvailablePhotos((prev) =>
          prev.map((p) =>
            p.id === photoToRemove.immich_asset_id ? { ...p, is_linked: false } : p,
          ),
        )
      }
    } catch (err) {
      console.error('Failed to remove photo:', err)
    }
  }

  // Toggle include in report
  const handleToggleIncludeInReport = async (photoId: string, currentValue: boolean) => {
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

  // Format date
  const formatLocaleDate = useLocale((state) => state.formatDate)
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null
    return formatLocaleDate(dateStr)
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
          onClick={() => setActiveTab('linked')}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === 'linked'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Linked ({linkedPhotos.length})
        </button>
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
      </div>

      {/* Error message */}
      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {/* Loading state */}
      {(isLoading || isDateSearchLoading) && (
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
          {isDateSearchLoading && (
            <span className="ml-2 text-sm text-gray-500">Searching by date...</span>
          )}
        </div>
      )}

      {/* Search mode indicator */}
      {searchMode === 'date' && (
        <div className="flex items-center justify-between rounded-md bg-blue-50 px-3 py-2 text-sm">
          <span className="text-blue-700">Showing photos by date range (ignoring location)</span>
          <button
            type="button"
            onClick={switchToLocationSearch}
            className="text-blue-600 hover:text-blue-800 underline"
          >
            Switch to location search
          </button>
        </div>
      )}

      {/* Available photos tab */}
      {activeTab === 'available' &&
        !isLoading &&
        !isDateSearchLoading &&
        (!hasLocation && searchMode === 'location' ? (
          <div className="py-4 text-center text-gray-500">Add a location to search for photos.</div>
        ) : availablePhotos.filter((p) => !p.is_linked).length === 0 ? (
          <div className="space-y-3 py-4 text-center">
            <p className="text-gray-500">
              {searchMode === 'location'
                ? 'No photos found for this location.'
                : 'No photos found for this date range.'}
            </p>
            {searchMode === 'location' && isPastEvent && (
              <button
                type="button"
                onClick={fetchPhotosByDate}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Search by Date Instead
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {availablePhotos
              .filter((p) => !p.is_linked)
              .map((photo) => (
                <AvailablePhotoCard
                  key={photo.id}
                  photo={photo}
                  formatDate={formatDate}
                  onAdd={handleAddPhoto}
                />
              ))}
          </div>
        ))}

      {/* Linked photos tab */}
      {activeTab === 'linked' &&
        (linkedPhotos.length === 0 ? (
          <div className="py-4 text-center text-gray-500">No photos linked to this event yet.</div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {linkedPhotos.map((photo) => (
              <LinkedPhotoCard
                key={photo.id}
                eventId={eventId}
                photo={photo}
                isEditingCaption={editingCaption === photo.id}
                captionText={captionText}
                formatDate={formatDate}
                onCaptionTextChange={setCaptionText}
                onStartEditCaption={startEditingCaption}
                onSaveCaption={handleSaveCaption}
                onCancelEditCaption={() => setEditingCaption(null)}
                onToggleIncludeInReport={handleToggleIncludeInReport}
                onRemove={handleRemovePhoto}
              />
            ))}
          </div>
        ))}

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
