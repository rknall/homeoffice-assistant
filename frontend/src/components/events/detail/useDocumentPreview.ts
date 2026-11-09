// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useEffect, useState } from 'react'
import { api } from '@/api/client'

/**
 * Load a Paperless document preview as an object URL for an event document.
 *
 * Pass `null` as `docId` to clear it. A failing preview is optional and silent.
 */
export function useDocumentPreview(eventId: string, docId: number | null) {
  const [url, setUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (docId === null) return
    let cancelled = false
    let objectUrl: string | null = null
    setIsLoading(true)
    api
      .blob(`/events/${eventId}/documents/${docId}/preview`)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(() => {
        // Preview failed, continue without it
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      setUrl(null)
    }
  }, [eventId, docId])

  return { url, isLoading }
}
