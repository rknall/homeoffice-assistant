// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { LocationSuggestion } from '../types'

interface LocationAutocompleteProps {
  value: {
    city: string | null
    country: string | null
    country_code: string | null
    latitude: number | null
    longitude: number | null
  }
  onChange: (location: {
    city: string | null
    country: string | null
    country_code: string | null
    latitude: number | null
    longitude: number | null
  }) => void
  placeholder?: string
  disabled?: boolean
}

export function LocationAutocomplete({
  value,
  onChange,
  placeholder = 'Search for a city...',
  disabled = false,
}: LocationAutocompleteProps) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Display value
  const displayValue = value.city && value.country
    ? `${value.city}, ${value.country}`
    : value.country || ''

  // Debounced search
  const searchLocations = useCallback(async (searchQuery: string) => {
    if (searchQuery.length < 2) {
      setSuggestions([])
      return
    }

    setIsLoading(true)
    try {
      const results = await api.get<LocationSuggestion[]>(
        `/locations/autocomplete?q=${encodeURIComponent(searchQuery)}`
      )
      setSuggestions(results)
      setSelectedIndex(-1)
    } catch (error) {
      console.error('Failed to fetch locations:', error)
      setSuggestions([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Handle input change with debounce
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value
    setQuery(newQuery)
    setIsOpen(true)

    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      searchLocations(newQuery)
    }, 300)
  }

  // Handle suggestion selection
  const handleSelect = (suggestion: LocationSuggestion) => {
    onChange({
      city: suggestion.city,
      country: suggestion.country,
      country_code: suggestion.country_code,
      latitude: suggestion.latitude,
      longitude: suggestion.longitude,
    })
    setQuery('')
    setIsOpen(false)
    setSuggestions([])
  }

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleSelect(suggestions[selectedIndex])
        }
        break
      case 'Escape':
        setIsOpen(false)
        break
    }
  }

  // Handle clear
  const handleClear = () => {
    onChange({
      city: null,
      country: null,
      country_code: null,
      latitude: null,
      longitude: null,
    })
    setQuery('')
    inputRef.current?.focus()
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [])

  return (
    <div ref={containerRef} className="relative">
      {/* Selected location display */}
      {displayValue && !query ? (
        <div className="flex items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2">
          <span className="text-gray-900">{displayValue}</span>
          <button
            type="button"
            onClick={handleClear}
            disabled={disabled}
            className="ml-2 text-gray-400 hover:text-gray-600"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      ) : (
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 2 && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
        />
      )}

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        </div>
      )}

      {/* Suggestions dropdown */}
      {isOpen && suggestions.length > 0 && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          {suggestions.map((suggestion, index) => (
            <li
              key={`${suggestion.latitude}-${suggestion.longitude}`}
              onClick={() => handleSelect(suggestion)}
              className={`cursor-pointer px-3 py-2 ${
                index === selectedIndex
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-900 hover:bg-gray-50'
              }`}
            >
              <div className="font-medium">
                {suggestion.city
                  ? `${suggestion.city}, ${suggestion.country}`
                  : suggestion.country}
              </div>
              <div className="text-xs text-gray-500 truncate">
                {suggestion.display_name}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* No results message */}
      {isOpen && query.length >= 2 && !isLoading && suggestions.length === 0 && (
        <div className="absolute z-10 mt-1 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-gray-500 shadow-lg">
          No locations found
        </div>
      )}
    </div>
  )
}
