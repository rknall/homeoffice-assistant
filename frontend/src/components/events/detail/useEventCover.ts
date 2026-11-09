// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from 'react'
import { api, errorMessage } from '@/api/client'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { Event, LocationImage } from '@/types'

/** Cover image / location banner of an event, including vertical position adjusting. */
export function useEventCover(
  id: string | undefined,
  event: Event | null,
  setEvent: React.Dispatch<React.SetStateAction<Event | null>>,
  setError: (message: string | null) => void,
) {
  const { setHideGlobal } = useBreadcrumb()
  const [locationImage, setLocationImage] = useState<LocationImage | null>(null)
  const [isAdjustingPosition, setIsAdjustingPosition] = useState(false)
  const [imagePosition, setImagePosition] = useState<number>(50)

  const fetchLocationImage = useCallback(async (eventData: Event) => {
    // If event has a cover image, use that instead of fetching from Unsplash
    if (eventData.cover_image_url) {
      setLocationImage({
        image_url: eventData.cover_image_url,
        thumbnail_url: eventData.cover_thumbnail_url || eventData.cover_image_url,
        photographer_name: eventData.cover_photographer_name || null,
        photographer_url: eventData.cover_photographer_url || null,
        attribution_html: eventData.cover_photographer_name
          ? `Photo by <a href="${eventData.cover_photographer_url || '#'}" target="_blank" rel="noopener noreferrer">${eventData.cover_photographer_name}</a> on <a href="https://unsplash.com" target="_blank" rel="noopener noreferrer">Unsplash</a>`
          : null,
      })
      return
    }

    // Otherwise fetch from Unsplash
    try {
      const image = await api.get<LocationImage | null>(`/events/${eventData.id}/location-image`)
      setLocationImage(image)
    } catch {
      // Location image is optional, ignore errors
      setLocationImage(null)
    }
  }, [])

  // Hide global breadcrumb when location image is present (we render our own)
  useEffect(() => {
    if (locationImage) {
      setHideGlobal(true)
    }
    return () => setHideGlobal(false)
  }, [locationImage, setHideGlobal])

  const adjustImagePosition = (delta: number) => {
    setImagePosition((prev) => Math.max(0, Math.min(100, prev + delta)))
  }

  const saveImagePosition = async () => {
    if (!id) return
    try {
      await api.put(`/events/${id}`, { cover_image_position_y: imagePosition })
      setEvent((prev) => (prev ? { ...prev, cover_image_position_y: imagePosition } : prev))
      setIsAdjustingPosition(false)
    } catch (e) {
      setError(errorMessage(e, 'Failed to save image position'))
    }
  }

  const cancelPositionAdjustment = () => {
    setImagePosition(event?.cover_image_position_y ?? 50)
    setIsAdjustingPosition(false)
  }

  return {
    locationImage,
    isAdjustingPosition,
    setIsAdjustingPosition,
    imagePosition,
    setImagePosition,
    fetchLocationImage,
    adjustImagePosition,
    saveImagePosition,
    cancelPositionAdjustment,
  }
}

export type EventCoverState = ReturnType<typeof useEventCover>
