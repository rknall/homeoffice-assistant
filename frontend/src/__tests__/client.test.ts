// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, errorMessage } from '@/api/client'

function mockFetch(status: number, body?: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (body === undefined) throw new Error('no body')
      return body
    },
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('returns parsed JSON on success', async () => {
    const fn = mockFetch(200, { a: 1 })
    await expect(api.get('/x')).resolves.toEqual({ a: 1 })
    expect(fn).toHaveBeenCalledWith(
      '/api/v1/x',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('throws ApiError with status and detail', async () => {
    mockFetch(403, { detail: 'Forbidden thing' })
    const err = (await api.get('/x').catch((e: unknown) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(403)
    expect(err.message).toBe('Forbidden thing')
  })

  it('falls back to a generic message without a JSON body', async () => {
    mockFetch(500)
    const err = (await api.get('/x').catch((e: unknown) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('Request failed')
  })

  it('returns undefined for 204', async () => {
    mockFetch(204)
    await expect(api.delete('/x')).resolves.toBeUndefined()
  })
})

describe('request detail handling', () => {
  it('uses a generic message when detail is an array (422)', async () => {
    mockFetch(422, { detail: [{ loc: ['body', 'x'], msg: 'bad', type: 'value_error' }] })
    const err = (await api.get('/x').catch((e: unknown) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(422)
    expect(err.message).toBe('Request failed')
  })
})

describe('errorMessage', () => {
  it('returns the server detail of an ApiError', () => {
    expect(errorMessage(new ApiError(403, 'Permission denied'), 'Failed to load')).toBe(
      'Permission denied',
    )
  })

  it('returns the fallback for a non-ApiError', () => {
    expect(errorMessage(new Error('boom'), 'Failed to load')).toBe('Failed to load')
    expect(errorMessage('x', 'Failed to load')).toBe('Failed to load')
    expect(errorMessage(undefined, 'Failed to load')).toBe('Failed to load')
  })

  it('returns the fallback for an empty message', () => {
    expect(errorMessage(new ApiError(403, ''), 'Failed to load')).toBe('Failed to load')
  })

  it('shows the 403 detail end to end', async () => {
    mockFetch(403, { detail: 'Missing permission integrations.read' })
    const err = await api.get('/x').catch((e: unknown) => e)
    expect(errorMessage(err, 'Failed to load')).toBe('Missing permission integrations.read')
  })
})

describe('api.upload and api.blob', () => {
  it('posts FormData without forcing a JSON content type', async () => {
    const fn = mockFetch(200, { ok: true })
    const form = new FormData()
    form.append('file', new Blob(['x']), 'a.txt')
    await expect(api.upload('/up', form)).resolves.toEqual({ ok: true })
    const [url, options] = fn.mock.calls[0]
    expect(url).toBe('/api/v1/up')
    expect(options.method).toBe('POST')
    expect(options.body).toBe(form)
    expect(options.credentials).toBe('include')
    expect(options.headers).toBeUndefined()
  })

  it('throws the server detail on a failed upload', async () => {
    mockFetch(413, { detail: 'File too large' })
    const err = (await api.upload('/up', new FormData()).catch((e: unknown) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(413)
    expect(err.message).toBe('File too large')
  })

  it('falls back to a generic upload message', async () => {
    mockFetch(500)
    const err = (await api.upload('/up', new FormData()).catch((e: unknown) => e)) as ApiError
    expect(err.message).toBe('Upload failed')
  })

  it('returns the response blob', async () => {
    const blob = new Blob(['pdf'])
    const fn = vi.fn().mockResolvedValue({ ok: true, status: 200, blob: async () => blob })
    vi.stubGlobal('fetch', fn)
    await expect(api.blob('/doc')).resolves.toBe(blob)
    expect(fn).toHaveBeenCalledWith('/api/v1/doc', { credentials: 'include' })
  })

  it('throws ApiError when the blob request fails', async () => {
    mockFetch(404, { detail: 'No preview' })
    const err = (await api.blob('/doc').catch((e: unknown) => e)) as ApiError
    expect(err.status).toBe(404)
    expect(err.message).toBe('No preview')
  })
})
