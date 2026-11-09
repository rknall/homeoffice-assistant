// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Tests that exercise the real plugin API client (api.ts), not copies of it.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { companySettingsApi, errorMessage, timeEntriesApi } from '../api'
import apiSource from '../api.ts?raw'

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  })
}

describe('plugin API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls no /submissions route, the backend has none', () => {
    const source: string = apiSource
    expect(source).not.toMatch(/[`"']\/submissions/)
    expect(source).not.toContain('submissionsApi')
  })

  it('surfaces the server detail text on a 403', async () => {
    vi.stubGlobal('fetch', respond(403, { detail: 'Permission denied: records.read' }))

    const failure = await timeEntriesApi.list().catch((err: unknown) => err)

    expect(errorMessage(failure, 'fallback')).toBe('Permission denied: records.read')
  })

  it('falls back to a generic message when detail is not a string', async () => {
    vi.stubGlobal('fetch', respond(422, { detail: [{ msg: 'bad' }] }))

    const failure = await timeEntriesApi.list().catch((err: unknown) => err)

    expect(errorMessage(failure, 'fallback')).toBe('Request failed')
    expect(errorMessage('not an error', 'fallback')).toBe('fallback')
  })

  it('creates company settings with POST and updates them with PUT', async () => {
    const fetchMock = respond(200, { id: 's1' })
    vi.stubGlobal('fetch', fetchMock)

    await companySettingsApi.create('c1', { lock_period_days: 3 })
    await companySettingsApi.update('c1', { lock_period_days: 4 })

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/plugin/time-tracking/settings/company/c1',
      expect.objectContaining({ method: 'POST', body: '{"lock_period_days":3}' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/plugin/time-tracking/settings/company/c1',
      expect.objectContaining({ method: 'PUT', body: '{"lock_period_days":4}' }),
    )
  })
})
