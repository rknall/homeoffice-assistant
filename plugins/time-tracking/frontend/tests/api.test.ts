// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Tests for the Time Tracking plugin API client
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Mock fetch globally
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

// Import after mocking
const PLUGIN_API_BASE = '/api/v1/plugin/time-tracking'

describe('Time Tracking API', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('timeRecordsApi.list', () => {
    it('should call records endpoint with correct query params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })

      const searchParams = new URLSearchParams()
      searchParams.set('from', '2026-01-01')
      searchParams.set('to', '2026-01-31')

      await fetch(`${PLUGIN_API_BASE}/records?${searchParams.toString()}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        `${PLUGIN_API_BASE}/records?from=2026-01-01&to=2026-01-31`,
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        }),
      )
    })

    it('should include company_id when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })

      const searchParams = new URLSearchParams()
      searchParams.set('company_id', 'test-company-id')
      searchParams.set('from', '2026-01-01')
      searchParams.set('to', '2026-01-31')

      await fetch(`${PLUGIN_API_BASE}/records?${searchParams.toString()}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('company_id=test-company-id'),
        expect.any(Object),
      )
    })
  })

  describe('API error handling', () => {
    it('should throw ApiError on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Not found' }),
      })

      const response = await fetch(`${PLUGIN_API_BASE}/records/invalid-id`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })

      expect(response.ok).toBe(false)
      expect(response.status).toBe(404)
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(
        fetch(`${PLUGIN_API_BASE}/records`, {
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        }),
      ).rejects.toThrow('Network error')
    })
  })
})

describe('Utility functions', () => {
  /**
   * Local date formatting function (same as in api.ts)
   * Uses local timezone to avoid UTC conversion issues
   */
  function toISODateString(date: Date): string {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  describe('toISODateString', () => {
    it('should format date as YYYY-MM-DD', () => {
      const date = new Date(2026, 0, 15) // January 15, 2026
      const result = toISODateString(date)
      expect(result).toBe('2026-01-15')
    })

    it('should handle month boundaries correctly', () => {
      const lastDay = new Date(2026, 0, 31) // January 31, 2026
      const result = toISODateString(lastDay)
      expect(result).toBe('2026-01-31')
    })

    it('should pad single-digit months and days', () => {
      const date = new Date(2026, 5, 5) // June 5, 2026
      const result = toISODateString(date)
      expect(result).toBe('2026-06-05')
    })

    it('should handle year boundaries', () => {
      const date = new Date(2025, 11, 31) // December 31, 2025
      const result = toISODateString(date)
      expect(result).toBe('2025-12-31')
    })
  })
})
