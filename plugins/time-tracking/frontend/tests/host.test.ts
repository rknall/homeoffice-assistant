// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom

/**
 * Tests for the Time Tracking plugin host bridge
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { confirmAction } from '../host'

describe('host confirmAction', () => {
  afterEach(() => {
    window.hoaHost = undefined
    vi.unstubAllGlobals()
  })

  it('forwards the options to the host and returns its result', async () => {
    const hostConfirm = vi.fn().mockResolvedValue(true)
    window.hoaHost = { confirmAction: hostConfirm }
    const options = { title: 'Delete time entry', message: 'Sure?' }

    await expect(confirmAction(options)).resolves.toBe(true)
    expect(hostConfirm).toHaveBeenCalledWith(options)
  })

  it('returns false when the host resolves false', async () => {
    window.hoaHost = { confirmAction: vi.fn().mockResolvedValue(false) }
    await expect(confirmAction({ title: 't', message: 'm' })).resolves.toBe(false)
  })

  it('rejects without the host API and never opens the browser dialog', async () => {
    const browserDialog = vi.fn()
    vi.stubGlobal('confirm', browserDialog)
    window.hoaHost = undefined

    await expect(confirmAction({ title: 't', message: 'm' })).rejects.toThrow(Error)
    expect(browserDialog).not.toHaveBeenCalled()
  })
})
