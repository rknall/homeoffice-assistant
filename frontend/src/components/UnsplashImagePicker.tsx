// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '@/api/client'
import { api } from '../api/client'
import type { IntegrationConfig, UnsplashImage, UnsplashSearchResponse } from '../types'
import { Button } from './ui/Button'
import { Modal } from './ui/Modal'
import { Spinner } from './ui/Spinner'

interface UnsplashImagePickerProps {
  value: {
    image_url: string | null
    thumbnail_url: string | null
    photographer_name: string | null
    photographer_url: string | null
  } | null
  onChange: (
    image: {
      image_url: string | null
      thumbnail_url: string | null
      photographer_name: string | null
      photographer_url: string | null
    } | null,
  ) => void
  defaultSearchQuery?: string
  disabled?: boolean
}

export function UnsplashImagePicker({
  value,
  onChange,
  defaultSearchQuery = '',
  disabled = false,
}: UnsplashImagePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState(defaultSearchQuery)
  const [results, setResults] = useState<UnsplashImage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [unsplashConfig, setUnsplashConfig] = useState<IntegrationConfig | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch Unsplash integration config
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const configs = await api.get<IntegrationConfig[]>(
          '/integrations?integration_type=unsplash',
        )
        const activeConfig = configs.find((c) => c.is_active)
        setUnsplashConfig(activeConfig || null)
      } catch {
        setUnsplashConfig(null)
      }
    }
    fetchConfig()
  }, [])

  // Search images
  const searchImages = useCallback(
    async (searchQuery: string, pageNum: number = 1) => {
      if (!unsplashConfig || searchQuery.length < 2) {
        setResults([])
        return
      }

      setIsLoading(true)
      setError(null)

      try {
        const response = await api.get<UnsplashSearchResponse>(
          `/integrations/${unsplashConfig.id}/unsplash/search?query=${encodeURIComponent(searchQuery)}&page=${pageNum}&per_page=12`,
        )
        setResults(response.results)
        setTotalPages(response.total_pages)
        setPage(pageNum)
      } catch (err) {
        setError(errorMessage(err, 'Failed to search images'))
        setResults([])
      } finally {
        setIsLoading(false)
      }
    },
    [unsplashConfig],
  )

  // Handle search input change with debounce
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value
    setQuery(newQuery)

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      searchImages(newQuery, 1)
    }, 500)
  }

  // Handle image selection
  const handleSelect = async (image: UnsplashImage) => {
    if (!unsplashConfig) return

    try {
      // Trigger download tracking (required by Unsplash API guidelines)
      await api.post(`/integrations/${unsplashConfig.id}/unsplash/download/${image.id}`, {})

      onChange({
        image_url: image.urls.regular,
        thumbnail_url: image.urls.small,
        photographer_name: image.user.name,
        photographer_url: image.links.html,
      })
      setIsOpen(false)
    } catch (err) {
      setError(errorMessage(err, 'Failed to select image'))
    }
  }

  // Handle clear
  const handleClear = () => {
    onChange(null)
  }

  // Open modal and search with default query
  const handleOpen = () => {
    setIsOpen(true)
    if (defaultSearchQuery && !query) {
      setQuery(defaultSearchQuery)
      searchImages(defaultSearchQuery, 1)
    }
  }

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [])

  // No Unsplash integration configured
  if (!unsplashConfig) {
    return (
      <div className="text-sm text-gray-500">
        Unsplash integration not configured. Add it in Settings.
      </div>
    )
  }

  return (
    <div>
      {/* Selected image preview */}
      {value?.thumbnail_url ? (
        <div className="relative">
          <img
            src={value.thumbnail_url}
            alt="Selected"
            className="w-full h-48 object-cover rounded-lg"
          />
          <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs p-2 rounded-b-lg">
            Photo by{' '}
            <a
              href={value.photographer_url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              {value.photographer_name}
            </a>{' '}
            on{' '}
            <a
              href="https://unsplash.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              Unsplash
            </a>
          </div>
          <div className="absolute top-2 right-2 flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleOpen}
              disabled={disabled}
            >
              Change
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={handleClear}
              disabled={disabled}
            >
              Remove
            </Button>
          </div>
        </div>
      ) : (
        <Button
          type="button"
          variant="secondary"
          onClick={handleOpen}
          disabled={disabled}
          className="w-full"
        >
          Search for an image on Unsplash
        </Button>
      )}

      {/* Image picker modal */}
      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Select Image from Unsplash">
        <div className="space-y-4">
          {/* Search input */}
          <input
            type="text"
            value={query}
            onChange={handleSearchChange}
            placeholder="Search for images..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />

          {/* Error message */}
          {error && <div className="text-sm text-red-600">{error}</div>}

          {/* Loading state */}
          {isLoading && (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          )}

          {/* Results grid */}
          {!isLoading && results.length > 0 && (
            <>
              <div className="grid grid-cols-3 gap-2 max-h-96 overflow-y-auto">
                {results.map((image) => (
                  <button
                    key={image.id}
                    type="button"
                    onClick={() => handleSelect(image)}
                    className="relative aspect-square overflow-hidden rounded-lg hover:ring-2 hover:ring-blue-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    style={{ backgroundColor: image.color || '#f3f4f6' }}
                  >
                    <img
                      src={image.urls.thumb}
                      alt={image.description || 'Unsplash image'}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                    <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs p-1 truncate">
                      {image.user.name}
                    </div>
                  </button>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => searchImages(query, page - 1)}
                    disabled={page <= 1}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-gray-600 self-center">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => searchImages(query, page + 1)}
                    disabled={page >= totalPages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}

          {/* No results */}
          {!isLoading && query.length >= 2 && results.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              No images found. Try a different search term.
            </div>
          )}

          {/* Initial state */}
          {!isLoading && query.length < 2 && results.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              Enter at least 2 characters to search for images.
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
