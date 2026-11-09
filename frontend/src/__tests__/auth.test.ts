// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '@/stores/auth'
import type { User } from '@/types'

function setUser(permissions: string[], company: Record<string, string[]> = {}) {
  useAuth.setState({
    user: { permissions, company_permissions: company } as unknown as User,
  })
}

describe('auth hasPermission', () => {
  beforeEach(() => useAuth.setState({ user: null }))

  it('is false without a user', () => {
    expect(useAuth.getState().hasPermission('x')).toBe(false)
  })

  it('grants a global permission', () => {
    setUser(['events.read'])
    expect(useAuth.getState().hasPermission('events.read')).toBe(true)
    expect(useAuth.getState().hasPermission('events.write')).toBe(false)
  })

  it('grants a company permission only for that company', () => {
    setUser([], { c1: ['events.write'] })
    expect(useAuth.getState().hasPermission('events.write', 'c1')).toBe(true)
    expect(useAuth.getState().hasPermission('events.write', 'c2')).toBe(false)
    expect(useAuth.getState().hasPermission('events.write')).toBe(false)
  })
})

describe('auth login', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('keeps the global isLoading false on a failed login so the form stays mounted', async () => {
    useAuth.setState({ user: null, isLoading: false, error: null })
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      }),
    )
    const seen: boolean[] = []
    const unsubscribe = useAuth.subscribe((state) => seen.push(state.isLoading))
    await expect(useAuth.getState().login('u', 'p')).rejects.toBeDefined()
    unsubscribe()
    expect(seen).not.toContain(true)
    expect(useAuth.getState().error).toBe('Invalid credentials')
  })
})
