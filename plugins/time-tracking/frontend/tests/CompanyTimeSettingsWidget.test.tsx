// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CompanyTimeSettingsWidget } from '../components/CompanyTimeSettingsWidget'

const SETTINGS = {
  id: 's1',
  company_id: 'c1',
  timezone: 'Europe/Vienna',
  country_code: 'AT',
  vacation_days_per_year: 25,
  daily_overtime_threshold: 8,
  weekly_overtime_threshold: 40,
  overtime_threshold_hours: 0,
  comp_time_warning_balance: 40,
  default_timesheet_contact_id: null,
  lock_period_days: 7,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

function reply(status: number, body: unknown) {
  return { ok: status < 400, status, json: () => Promise.resolve(body) }
}

describe('CompanyTimeSettingsWidget', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows the stored settings', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply(200, SETTINGS)))
    render(<CompanyTimeSettingsWidget companyId="c1" />)

    expect(await screen.findByText('Europe/Vienna')).toBeTruthy()
    expect(screen.getByText('25 days')).toBeTruthy()
    expect(screen.getByText('Edit')).toBeTruthy()
  })

  it('creates settings with POST when none exist', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(200, null))
      .mockResolvedValueOnce(reply(200, SETTINGS))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<CompanyTimeSettingsWidget companyId="c1" />)

    await user.click(await screen.findByText('Configure'))
    await user.click(screen.getByText('Save Settings'))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' })
    expect(await screen.findByText('Edit')).toBeTruthy()
  })

  it('shows the server detail when saving is forbidden', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(reply(200, SETTINGS))
      .mockResolvedValueOnce(reply(403, { detail: 'Permission denied: settings.write' }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<CompanyTimeSettingsWidget companyId="c1" />)

    await user.click(await screen.findByText('Edit'))
    await user.click(screen.getByText('Save Settings'))

    expect(await screen.findByText('Permission denied: settings.write')).toBeTruthy()
  })
})
