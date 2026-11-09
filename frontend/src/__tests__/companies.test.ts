// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { beforeEach, describe, expect, it, vi } from 'vitest'

const get = vi.fn()

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client')
  return { ...actual, api: { get: (p: string) => get(p) } }
})

import { ApiError } from '@/api/client'
import { useCompanies } from '@/stores/companies'

describe('companies store', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    useCompanies.setState({ companies: [], isLoading: true, error: null })
  })

  it('loads the company list', async () => {
    get.mockResolvedValue([{ id: 'c1' }])
    await useCompanies.getState().fetchCompanies()
    expect(get).toHaveBeenCalledWith('/companies')
    expect(useCompanies.getState()).toMatchObject({
      companies: [{ id: 'c1' }],
      isLoading: false,
      error: null,
    })
  })

  it('keeps the previous list and sets the server error on failure', async () => {
    get.mockResolvedValueOnce([{ id: 'c1' }])
    await useCompanies.getState().fetchCompanies()
    get.mockRejectedValueOnce(new ApiError(403, 'Missing permission companies.read'))
    await useCompanies.getState().fetchCompanies()
    expect(useCompanies.getState().companies).toEqual([{ id: 'c1' }])
    expect(useCompanies.getState().error).toBe('Missing permission companies.read')
  })
})
