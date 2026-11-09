// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ConfirmDialogHost } from '@/components/ui/ConfirmDialog'
import { Companies } from '@/pages/Companies'
import { useCompanies } from '@/stores/companies'

const company = {
  id: 'c1',
  name: 'Acme GmbH',
  type: 'employer',
  contacts: [],
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), { status })
}

describe('Companies delete', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    useCompanies.setState({ companies: [], isLoading: true, error: null })
    fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'DELETE') return Promise.resolve(jsonResponse(null, 204))
      return Promise.resolve(jsonResponse([company]))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(
      <MemoryRouter>
        <Companies />
        <ConfirmDialogHost />
      </MemoryRouter>,
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  const deleteCalls = () => fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')

  it('opens the dialog and sends no DELETE when cancelled', async () => {
    const user = userEvent.setup()
    await user.click(await screen.findByTitle('Delete company'))

    expect(await screen.findByRole('alertdialog', { name: 'Delete company' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    await waitFor(() => expect(screen.queryByRole('alertdialog')).toBeNull())
    expect(deleteCalls()).toHaveLength(0)
    expect(screen.getByText('Acme GmbH')).toBeTruthy()
  })

  it('sends the DELETE when confirmed', async () => {
    const user = userEvent.setup()
    await user.click(await screen.findByTitle('Delete company'))
    await screen.findByRole('alertdialog')
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(deleteCalls()).toHaveLength(1))
    expect(deleteCalls()[0][0]).toBe('/api/v1/companies/c1')
  })
})

describe('Companies logo', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  function renderWith(companies: unknown[]) {
    useCompanies.setState({ companies: [], isLoading: true, error: null })
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse(companies))),
    )
    render(
      <MemoryRouter>
        <Companies />
      </MemoryRouter>,
    )
  }

  it('shows the logo of a company that has one', async () => {
    renderWith([{ ...company, logo_path: 'c1_abcd.png' }])

    const logo = await screen.findByAltText('Acme GmbH logo')
    expect(logo.getAttribute('src')).toBe('/api/v1/companies/c1/logo')
  })

  it('shows no image for a company without a logo', async () => {
    renderWith([{ ...company, logo_path: null }])

    await screen.findByText('Acme GmbH')
    expect(screen.queryByAltText('Acme GmbH logo')).toBeNull()
  })
})

describe('Companies row markup', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('does not nest a button inside a button', async () => {
    useCompanies.setState({ companies: [], isLoading: true, error: null })
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse([company]))),
    )
    render(
      <MemoryRouter>
        <Companies />
      </MemoryRouter>,
    )
    await screen.findByText('Acme GmbH')
    expect(document.querySelectorAll('button button')).toHaveLength(0)
    expect(screen.getByTitle('Edit company')).toBeTruthy()
  })
})
